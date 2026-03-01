import base64
import json
from abc import ABC, abstractmethod
from typing import List
from config import client, gemini_client, logger
from models import AnalysisResponse, RegenerateResponseParts
from google.genai import types

class AIGenerator(ABC):
    @abstractmethod
    def analyze_grid(self, system_prompt: str, encoded_images: List[str]) -> AnalysisResponse:
        pass

    @abstractmethod
    def regenerate_caption(self, system_prompt: str, encoded_image: str) -> RegenerateResponseParts:
        pass

class OpenAIGenerator(AIGenerator):
    def analyze_grid(self, system_prompt: str, encoded_images: List[str]) -> AnalysisResponse:
        user_content = [
            {"type": "text", "text": "Analyse ces 3 images pour une stratégie de grille Instagram. Le but est de créer une seule ligne cohérente de 3 photos consécutives sur le profil Instagram (la photo 3 (Droite) sera postée en premier, puis la 2 (Milieu), puis la 1 (Gauche) afin qu'elles apparaissent de gauche à droite sur le profil)."}
        ]
        
        positions = ["Image 1 (Gauche)", "Image 2 (Milieu)", "Image 3 (Droite)"]
        
        for idx, img_base64 in enumerate(encoded_images):
            user_content.append({"type": "text", "text": f"--- {positions[idx]} ---"})
            user_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{img_base64}"
                }
            })

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
        
        response = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=messages,
            response_format=AnalysisResponse
        )
        return response.choices[0].message.parsed

    def regenerate_caption(self, system_prompt: str, encoded_image: str) -> RegenerateResponseParts:
        user_content = [
            {"type": "text", "text": "Régénère la partie spécifique de la légende."},
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{encoded_image}"
                }
            }
        ]
        
        response = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            response_format=RegenerateResponseParts
        )
        return response.choices[0].message.parsed

class GeminiGenerator(AIGenerator):
    def __init__(self):
        if not gemini_client:
            raise ValueError("Le client Gemini n'est pas initialisé. Vérifiez que la clé GEMINI_API_KEY est valide.")
            
    def analyze_grid(self, system_prompt: str, encoded_images: List[str]) -> AnalysisResponse:
        contents = [
            system_prompt,
            "Analyse ces 3 images pour une stratégie de grille Instagram. Le but est de créer une seule ligne cohérente de 3 photos consécutives sur le profil Instagram (la photo 3 (Droite) sera postée en premier, puis la 2 (Milieu), puis la 1 (Gauche) afin qu'elles apparaissent de gauche à droite sur le profil)."
        ]
        positions = ["Image 1 (Gauche)", "Image 2 (Milieu)", "Image 3 (Droite)"]
        for idx, img_base64 in enumerate(encoded_images):
            contents.append(f"--- {positions[idx]} ---")
            contents.append(
                types.Part.from_bytes(
                    data=base64.b64decode(img_base64),
                    mime_type='image/jpeg'
                )
            )

        response = gemini_client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=AnalysisResponse,
            ),
        )
        
        if hasattr(response, 'parsed') and response.parsed:
            return response.parsed
        else:
            return AnalysisResponse.model_validate_json(response.text)

    def regenerate_caption(self, system_prompt: str, encoded_image: str) -> RegenerateResponseParts:
        contents = [
            system_prompt,
            "Régénère la partie spécifique de la légende.",
            types.Part.from_bytes(
                data=base64.b64decode(encoded_image),
                mime_type='image/jpeg'
            )
        ]
        
        response = gemini_client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=RegenerateResponseParts,
            ),
        )
        if hasattr(response, 'parsed') and response.parsed:
            return response.parsed
        else:
            return RegenerateResponseParts.model_validate_json(response.text)

def get_ai_generator(provider: str) -> AIGenerator:
    if provider.lower() == "gemini":
        return GeminiGenerator()
    return OpenAIGenerator()
