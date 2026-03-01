from fastapi import APIRouter
import os
import asyncio
from typing import List, Dict

# Local imports
from config import client, gemini_client, logger

router = APIRouter()

async def ping_openai() -> bool:
    if not os.environ.get("OPENAI_API_KEY"):
        return False
    try:
        # A very lightweight call to verify the key
        # Models endpoint is fast and cheap to list
        response = await asyncio.to_thread(client.models.list)
        return True
    except Exception as e:
        logger.warning(f"OpenAI ping failed: {e}")
        return False

async def ping_gemini() -> bool:
    if not gemini_client:
        return False
    try:
        # Similar lightweight call to test Google API
        response = await asyncio.to_thread(gemini_client.models.get, model="gemini-3-flash-preview")
        return True
    except Exception as e:
        logger.warning(f"Gemini ping failed: {e}")
        return False

@router.get("/ai-providers")
async def get_available_ai_providers() -> Dict[str, List[Dict[str, str]]]:
    """
    Checks the availability of configured AI providers dynamically by pinging their APIs in parallel.
    Returns a JSON with `providers` containing only the ready-to-use services.
    """
    logger.info("Pinging AI providers to check availability...")
    
    # Run both network checks in parallel
    openai_ok, gemini_ok = await asyncio.gather(
        ping_openai(),
        ping_gemini()
    )
    
    available_providers = []
    
    if openai_ok:
        available_providers.append({
            "id": "openai",
            "name": "OpenAI (GPT-4o-mini)"
        })
        
    if gemini_ok:
        available_providers.append({
            "id": "gemini",
            "name": "Google Gemini (3-flash-preview)"
        })
        
    return {"providers": available_providers}
