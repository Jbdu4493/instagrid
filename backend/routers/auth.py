from fastapi import APIRouter, HTTPException
import os
import requests
from config import logger, FB_APP_ID, FB_APP_SECRET, IG_USER_ID
from models import TokenExchangeRequest
from utils import save_token

router = APIRouter()

FACEBOOK_API_URL = "https://graph.facebook.com/v19.0"

def _get_long_lived_token(app_id: str, app_secret: str, short_lived_token: str) -> dict:
    """Step 1: Exchange short-lived -> long-lived user token."""
    logger.info("Step 1: Exchanging short-lived token for long-lived token...")
    exchange_url = f"{FACEBOOK_API_URL}/oauth/access_token"
    resp = requests.get(exchange_url, params={
        "grant_type": "fb_exchange_token",
        "client_id": app_id,
        "client_secret": app_secret,
        "fb_exchange_token": short_lived_token
    })
    
    if resp.status_code != 200:
        error_detail = resp.json().get("error", {}).get("message", resp.text)
        raise HTTPException(400, f"Token exchange failed: {error_detail}")
        
    return resp.json()

def _fetch_page_tokens(long_lived_token: str) -> tuple[int, dict]:
    """Step 2: Get Page tokens from long-lived user token."""
    logger.info("Step 2: Fetching Page tokens...")
    pages_resp = requests.get(
        f"{FACEBOOK_API_URL}/me/accounts",
        params={"access_token": long_lived_token}
    )
    return pages_resp.status_code, pages_resp.json()

def _find_matching_page(pages: list, ig_user_id: str) -> dict:
    """Check pages to find the one linked to our IG account."""
    for page in pages:
        page_token = page.get("access_token")
        page_id = page.get("id")
        page_name = page.get("name", "Unknown")
        
        ig_resp = requests.get(
            f"{FACEBOOK_API_URL}/{page_id}",
            params={
                "fields": "instagram_business_account",
                "access_token": page_token
            }
        )
        
        if ig_resp.status_code == 200:
            ig_account = ig_resp.json().get("instagram_business_account", {})
            linked_ig_id = ig_account.get("id", "")
            
            if linked_ig_id == ig_user_id:
                logger.info(f"Found matching Page: '{page_name}' (ID: {page_id}) → IG: {linked_ig_id}")
                return {"token": page_token, "name": page_name, "id": page_id}
            else:
                logger.info(f"Page '{page_name}' linked to IG {linked_ig_id or 'none'}, not {ig_user_id}")
    return None

@router.post("/exchange-token")
async def exchange_token(request: TokenExchangeRequest):
    """
    Exchange a short-lived token for a permanent Page token.
    
    Flow:
    1. Short-lived user token → Long-lived user token (60 days)
    2. Long-lived user token → Permanent Page token (never expires)
    """
    
    if not FB_APP_ID or not FB_APP_SECRET:
        raise HTTPException(400, "FB_APP_ID and FB_APP_SECRET not configured in .env")
    
    # Step 1: Exchange short-lived → long-lived user token
    token_data = _get_long_lived_token(FB_APP_ID, FB_APP_SECRET, request.short_lived_token)
    long_lived_token = token_data.get("access_token")
    expires_in_sec = token_data.get("expires_in", 0)
    expires_in_days = expires_in_sec // 86400
    
    logger.info(f"Long-lived token obtained. Expires in {expires_in_sec // 3600}h ({expires_in_days} days)")
    
    # Step 2: Get Page tokens
    status_code, pages_data = _fetch_page_tokens(long_lived_token)
    
    # Fallback response helper
    def return_long_lived(msg_suffix: str):
        save_token(long_lived_token, "long_lived_user", {"expires_in_days": expires_in_days})
        return {
            "status": "success",
            "token_type": "long_lived_user",
            "expires_in_days": expires_in_days,
            "access_token": long_lived_token[:20] + "...",
            "message": f"Token étendu à {expires_in_days} jours. {msg_suffix}"
        }

    if status_code != 200:
        logger.warning(f"Could not fetch page tokens: {pages_data}")
        return return_long_lived("Page token non disponible.")
    
    pages = pages_data.get("data", [])
    if not pages:
        logger.warning("No Facebook Pages found. Returning long-lived user token.")
        return return_long_lived("Aucune Page Facebook trouvée pour token permanent.")
    
    # Step 3: Find the page connected to our IG account
    best_page = _find_matching_page(pages, IG_USER_ID) if IG_USER_ID else None
    
    if best_page:
        # Success: Permanent page token!
        permanent_token = best_page["token"]
        save_token(permanent_token, "permanent_page", {"page_name": best_page["name"]})
        logger.info(f"Permanent Page token set for page '{best_page['name']}'!")
        return {
            "status": "success",
            "token_type": "permanent_page",
            "page_name": best_page["name"],
            "access_token": permanent_token[:20] + "...",
            "message": f"🎉 Token PERMANENT obtenu pour la page '{best_page['name']}'! Ne expire jamais."
        }
    else:
        # No matching IG page, fallback to first available page
        first_page = pages[0]
        page_token = first_page.get("access_token")
        save_token(page_token, "page_token", {"page_name": first_page.get("name")})
        return {
            "status": "success",
            "token_type": "page_token",
            "page_name": first_page.get("name"),
            "access_token": page_token[:20] + "...",
            "message": f"Token de page obtenu pour '{first_page.get('name')}'. Vérifiez qu'elle est bien liée à votre compte IG."
        }
