import base64
import json
from abc import ABC, abstractmethod
from typing import List
from config import client, gemini_client, logger
from models import AnalysisResponse, RegenerateResponseParts
from google.genai import types

import asyncio

class AIGenerator(ABC):
    @abstractmethod
    async def analyze_grid(self, system_prompt: str, encoded_images: List[str]) -> AnalysisResponse:
        pass

    @abstractmethod
    async def analyze_grid_stream(self, system_prompt: str, encoded_images: List[str]):
        """Yields chunks of the generated JSON for Server-Sent Events."""
        pass

    @abstractmethod
    async def regenerate_caption(self, system_prompt: str, encoded_image: str) -> RegenerateResponseParts:
        pass

    @abstractmethod
    async def regenerate_caption_stream(self, system_prompt: str, encoded_image: str):
        """Yields chunks of the generated JSON for Server-Sent Events."""
        pass

class OpenAIGenerator(AIGenerator):
    async def analyze_grid(self, system_prompt: str, encoded_images: List[str]) -> AnalysisResponse:
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
        
        response = await client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=messages,
            response_format=AnalysisResponse
        )
        return response.choices[0].message.parsed

    async def analyze_grid_stream(self, system_prompt: str, encoded_images: List[str]):
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
        
        # Note: structured streaming (parse + stream=True) is not natively supported by all OpenAI endpoints
        # yet in the exact same `parse` way, so we fall back to regular completion with JSON schema instruction.
        # But for UI fluidness, returning raw JSON chunks is fine.
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            response_format={"type": "json_object"},
            stream=True
        )
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def regenerate_caption(self, system_prompt: str, encoded_image: str) -> RegenerateResponseParts:
        user_content = [
            {"type": "text", "text": "Régénère la partie spécifique de la légende."},
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{encoded_image}"
                }
            }
        ]
        
        response = await client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            response_format=RegenerateResponseParts
        )
        return response.choices[0].message.parsed

    async def regenerate_caption_stream(self, system_prompt: str, encoded_image: str):
        user_content = [
            {"type": "text", "text": "Régénère la partie spécifique de la légende."},
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{encoded_image}"
                }
            }
        ]
        
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            response_format={"type": "json_object"},
            stream=True
        )
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

class GeminiGenerator(AIGenerator):
    def __init__(self):
        if not gemini_client:
            raise ValueError("Le client Gemini n'est pas initialisé. Vérifiez que la clé GEMINI_API_KEY est valide.")
            
    async def analyze_grid(self, system_prompt: str, encoded_images: List[str]) -> AnalysisResponse:
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

        response = await gemini_client.aio.models.generate_content(
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

    async def analyze_grid_stream(self, system_prompt: str, encoded_images: List[str]):
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

        response = await gemini_client.aio.models.generate_content_stream(
            model='gemini-3-flash-preview',
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        async for chunk in response:
            if chunk.text:
                yield chunk.text

    async def regenerate_caption(self, system_prompt: str, encoded_image: str) -> RegenerateResponseParts:
        contents = [
            system_prompt,
            "Régénère la partie spécifique de la légende.",
            types.Part.from_bytes(
                data=base64.b64decode(encoded_image),
                mime_type='image/jpeg'
            )
        ]
        
        response = await gemini_client.aio.models.generate_content(
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

    async def regenerate_caption_stream(self, system_prompt: str, encoded_image: str):
        contents = [
            system_prompt,
            "Régénère la partie spécifique de la légende.",
            types.Part.from_bytes(
                data=base64.b64decode(encoded_image),
                mime_type='image/jpeg'
            )
        ]
        
        response = await gemini_client.aio.models.generate_content_stream(
            model='gemini-3-flash-preview',
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        async for chunk in response:
            if chunk.text:
                yield chunk.text

def get_ai_generator(provider: str) -> AIGenerator:
    if provider.lower() == "gemini":
        return GeminiGenerator()
    return OpenAIGenerator()
