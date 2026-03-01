from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import List, Optional
import base64
import yaml
from config import client, logger
from models import AnalysisResponse, RegenerateRequest, RegenerateResponse, RegenerateResponseParts
from services.image_processor import compress_image, ImageProcessingError
from services.ai_service import get_ai_generator

router = APIRouter()

async def _process_uploaded_images(files: List[UploadFile]) -> List[str]:
    """Compresses and encodes uploaded images to base64."""
    processed_images = []
    for file in files:
        content = await file.read()
        try:
            image_bytes = compress_image(content, max_size_kb=800)
            base64_img = base64.b64encode(image_bytes).decode('utf-8')
            processed_images.append(base64_img)
        except ImageProcessingError as e:
            logger.error(f"Failed to process image {file.filename}: {e}")
            raise HTTPException(status_code=400, detail=str(e))
    return processed_images

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



@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_images(
    files: List[UploadFile] = File(...),
    ai_provider: Optional[str] = Form("openai"),
    user_context: Optional[str] = Form(None),
    context_0: Optional[str] = Form(None), 
    context_1: Optional[str] = Form(None),
    context_2: Optional[str] = Form(None)
):
    if len(files) != 3:
        raise HTTPException(status_code=400, detail="Please upload exactly 3 images.")

    logger.info(f"Received 3 images for analysis using AI Provider: {ai_provider}.")
    logger.info(f"User Context: {user_context}")
    
    # 1. Traitement des images
    encoded_images = await _process_uploaded_images(files)

    # 2. Préparation du prompt métier
    system_prompt = _load_analysis_prompt(user_context, context_0, context_1, context_2)

    # 3. Récupération du moteur IA (Strategy Pattern)
    try:
        ai_generator = get_ai_generator(ai_provider)
        
        # 4. Appel à l'IA et formatage de la réponse
        result = ai_generator.analyze_grid(system_prompt, encoded_images)
        
        # Conformity check
        if result.suggested_order and any(x > 2 for x in result.suggested_order):
            logger.info(f"AI returned 1-based indices: {result.suggested_order}. Converting to 0-based.")
            result.suggested_order = [x - 1 for x in result.suggested_order]
            
        return result
    except Exception as e:
        logger.error(f"AI Generator Error ({ai_provider}): {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"L'analyse IA a échoué: {str(e)}")


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

    try:
        ai_provider = getattr(request, 'ai_provider', 'openai')
        ai_generator = get_ai_generator(ai_provider)
        
        parts = ai_generator.regenerate_caption(system_prompt, request.image_base64)
        
        full_caption = (
            f"{parts.specific_fr} {request.common_thread_fr}\n\n"
            f"{parts.specific_en} {request.common_thread_en}"
        )
        
        return RegenerateResponse(caption=full_caption)

    except Exception as e:
        logger.error(f"Regeneration failed ({getattr(request, 'ai_provider', 'openai')}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Regeneration failed: {str(e)}")
