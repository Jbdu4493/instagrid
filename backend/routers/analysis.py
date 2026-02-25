from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import List
import base64
import yaml
from config import client, logger
from models import AnalysisResponse, RegenerateRequest, RegenerateResponse, RegenerateResponseParts
from utils import compress_image

router = APIRouter()

async def _process_uploaded_images(files: List[UploadFile]) -> List[str]:
    """Compresses and encodes uploaded images to base64."""
    encoded_images = []
    for file in files:
        content = await file.read()
        compressed_content = compress_image(content, max_size_kb=800)
        encoded_images.append(base64.b64encode(compressed_content).decode('utf-8'))
        await file.seek(0)
    return encoded_images

def _load_analysis_prompt(user_context: str, context_0: str, context_1: str, context_2: str) -> str:
    """Loads and formats the system prompt from YAML."""
    common_instruction = f"IMPORTANT - FIL ROUGE / THÈME COMMUN : {user_context}" if user_context else ""
    c0 = f"Contexte pour l'Image 1 (Gauche) : {context_0}" if context_0 else ""
    c1 = f"Contexte pour l'Image 2 (Milieu) : {context_1}" if context_1 else ""
    c2 = f"Contexte pour l'Image 3 (Droite) : {context_2}" if context_2 else ""

    try:
        with open("prompts.yaml", "r") as f:
            prompts = yaml.safe_load(f)
            system_prompt_template = prompts["instagram_grid_analysis"]["system"]
            return system_prompt_template.format(
                common_instruction=common_instruction,
                context_0=c0,
                context_1=c1,
                context_2=c2
            )
    except Exception as e:
        logger.error(f"Failed to load prompts.yaml: {e}")
        raise HTTPException(500, detail="Configuration Error: Could not load prompts.")

def _build_openai_messages(system_prompt: str, encoded_images: List[str]) -> List[dict]:
    """Constructs the message payload for the OpenAI API."""
    user_content = [
        {"type": "text", "text": "Analyse ces 3 images pour une stratégie de grille Instagram. Le but est de créer une seule ligne cohérente de 3 photos consécutives sur le profil Instagram (la photo 3 (Droite) sera postée en premier, puis la 2 (Milieu), puis la 1 (Gauche) afin qu'elles apparaissent de gauche à droite sur le profil)."}
    ]
    
    positions = ["Image 1 (Gauche)", "Image 2 (Milieu)", "Image 3 (Droite)"]
    
    for idx, img_base64 in enumerate(encoded_images):
        user_content.append({
            "type": "text",
            "text": f"--- {positions[idx]} ---"
        })
        user_content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{img_base64}"
            }
        })

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content}
    ]


def _call_openai_analysis(messages: List[dict]) -> AnalysisResponse:
    """Calls the OpenAI API and returns the parsed AnalysisResponse."""
    try:
        response = client.beta.chat.completions.parse(
            model="gpt-5-mini",
            messages=messages,
            response_format=AnalysisResponse
        )
        
        result = response.choices[0].message.parsed
        
        if result.suggested_order and any(x > 2 for x in result.suggested_order):
            logger.info(f"AI returned 1-based indices: {result.suggested_order}. Converting to 0-based.")
            result.suggested_order = [x - 1 for x in result.suggested_order]
            
        return result

    except Exception as e:
        logger.error(f"OpenAI API Error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"AI Analysis failed: {str(e)}")

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_images(
    files: List[UploadFile] = File(...),
    user_context: str = Form(None),
    context_0: str = Form(None),
    context_1: str = Form(None),
    context_2: str = Form(None)
):
    if len(files) != 3:
        raise HTTPException(status_code=400, detail="Please upload exactly 3 images.")

    logger.info("Received 3 images for analysis.")
    logger.info(f"User Context: {user_context}")
    
    # 1. Traitement des images
    encoded_images = await _process_uploaded_images(files)

    # 2. Préparation du prompt métier
    system_prompt = _load_analysis_prompt(user_context, context_0, context_1, context_2)

    # 3. Construction des messages pour l'IA
    messages = _build_openai_messages(system_prompt, encoded_images)

    # 4. Appel à l'IA et formatage de la réponse
    return _call_openai_analysis(messages)


@router.post("/regenerate_caption", response_model=RegenerateResponse)
async def regenerate_caption(request: RegenerateRequest):
    logger.info("Regenerating caption...")
    
    common_instruction = f"{request.common_context}" if request.common_context else "Aucun fil rouge spécifique."
    individual_context = f"{request.individual_context}" if request.individual_context else "Aucun contexte spécifique."
    
    captions_history_text = "Aucune pour le moment."
    if request.captions_history:
        captions_history_text = "\n".join(f"- {c}" for c in request.captions_history)
    
    try:
        with open("prompts.yaml", "r") as f:
            prompts = yaml.safe_load(f)
            system_prompt_template = prompts["single_image_caption"]["system"]
            system_prompt = system_prompt_template.format(
                common_instruction=common_instruction,
                individual_context=individual_context,
                common_thread_fr=request.common_thread_fr,
                common_thread_en=request.common_thread_en,
                captions_history=captions_history_text
            )
    except Exception as e:
        logger.error(f"Failed to load prompts.yaml: {e}")
        raise HTTPException(500, detail="Configuration Error")

    user_content = [
        {"type": "text", "text": "Régénère la partie spécifique de la légende."},
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{request.image_base64}"
            }
        }
    ]

    try:
        response = client.beta.chat.completions.parse(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            response_format=RegenerateResponseParts
        )
        parts = response.choices[0].message.parsed
        
        full_caption = (
            f"{parts.specific_fr} {request.common_thread_fr}\n\n"
            f"{parts.specific_en} {request.common_thread_en}"
        )
        
        return RegenerateResponse(caption=full_caption)

    except Exception as e:
        logger.error(f"Regeneration failed: {e}")
        raise HTTPException(status_code=500, detail=f"Regeneration failed: {str(e)}")
