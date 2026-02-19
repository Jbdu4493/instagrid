import base64
import json
import os
import time
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import uvicorn
import logging
import yaml
from PIL import Image
import io
import requests
import boto3
from botocore.config import Config as BotoConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="InstaGrid AI Backend")

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Validation Error: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": str(exc)},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OpenAI Client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Initialize S3 Client (optional — falls back to tmpfiles.org if not configured)
USE_S3 = bool(os.environ.get("AWS_ACCESS_KEY_ID") and os.environ.get("AWS_SECRET_ACCESS_KEY"))
s3_client = None
S3_BUCKET = os.environ.get("AWS_S3_BUCKET", "")

if USE_S3:
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
        region_name=os.environ.get("AWS_S3_REGION", "eu-west-3"),
        config=BotoConfig(signature_version="s3v4")
    )
    S3_BUCKET = os.environ.get("AWS_S3_BUCKET", "instagrid")
    logger.info(f"S3 configured: bucket={S3_BUCKET}")
else:
    logger.info("No AWS credentials — using tmpfiles.org as fallback")

# Initialize Draft Store
from drafts import S3DraftStore, LocalDraftStore
if USE_S3:
    draft_store = S3DraftStore(s3_client, S3_BUCKET)
    logger.info("DraftStore: S3")
else:
    draft_store = LocalDraftStore("data/drafts")
    logger.info("DraftStore: Local (data/drafts/)")

# --- Token Persistence ---
TOKEN_FILE = "data/token.json"
os.makedirs("data", exist_ok=True)

def load_saved_token():
    """Load token from disk on startup (survives container restarts)."""
    try:
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, "r") as f:
                data = json.load(f)
            saved_token = data.get("access_token")
            token_type = data.get("token_type", "unknown")
            if saved_token:
                os.environ["IG_ACCESS_TOKEN"] = saved_token
                logger.info(f"Loaded saved {token_type} token from {TOKEN_FILE}")
                return True
    except Exception as e:
        logger.warning(f"Could not load saved token: {e}")
    return False

def save_token(token: str, token_type: str, extra: dict = None):
    """Persist token to disk."""
    try:
        data = {"access_token": token, "token_type": token_type, "saved_at": time.strftime("%Y-%m-%d %H:%M:%S")}
        if extra:
            data.update(extra)
        with open(TOKEN_FILE, "w") as f:
            json.dump(data, f, indent=2)
        os.environ["IG_ACCESS_TOKEN"] = token
        logger.info(f"Token saved to {TOKEN_FILE} (type: {token_type})")
    except Exception as e:
        logger.error(f"Could not save token: {e}")

# Load persisted token on startup
load_saved_token()


# --- Pydantic Models ---

class HashtagLadder(BaseModel):
    broad: List[str]
    niche: List[str]
    specific: List[str]

class AnalysisResponse(BaseModel):
    suggested_order: List[int] 
    captions: List[str] 
    individual_scores: List[int]
    hashtags: List[HashtagLadder]
    coherence_score: int
    coherence_reasoning: str
    common_thread_fr: Optional[str] = ""
    common_thread_en: Optional[str] = ""

class PostItem(BaseModel):
    image_base64: str
    caption: str

class PostRequest(BaseModel):
    access_token: Optional[str] = None
    ig_user_id: Optional[str] = None
    posts: List[PostItem] 

class RegenerateRequest(BaseModel):
    image_base64: str
    common_context: Optional[str] = ""
    individual_context: Optional[str] = ""
    captions_history: List[str] = []
    common_thread_fr: Optional[str] = ""
    common_thread_en: Optional[str] = ""

class RegenerateResponseParts(BaseModel):
    specific_fr: str
    specific_en: str

class RegenerateResponse(BaseModel):
    caption: str


# --- Helper Functions ---

def compress_image(image_bytes: bytes, max_size_kb: int = 800) -> bytes:
    """Compresses an image to be under max_size_kb, resizing if necessary."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        
        if img.mode != 'RGB':
            img = img.convert('RGB')
            
        max_dimension = 1080
        if img.width > max_dimension or img.height > max_dimension:
            img.thumbnail((max_dimension, max_dimension), Image.LANCZOS)
            logger.info(f"Resized image to {img.width}x{img.height}")
            
        output = io.BytesIO()
        quality = 90
        img.save(output, format='JPEG', quality=quality)
        
        while output.tell() > max_size_kb * 1024 and quality > 10:
            output = io.BytesIO()
            quality -= 5
            img.save(output, format='JPEG', quality=quality)
            
        logger.info(f"Compressed image to {output.tell() / 1024:.2f} KB (Quality: {quality})")
        return output.getvalue()
        
    except Exception as e:
        logger.error(f"Compression failed: {e}")
        return image_bytes


CROP_RATIOS = {
    "original": None,
    "1:1": 1.0,
    "4:5": 4.0 / 5.0,
    "16:9": 16.0 / 9.0,
}

def crop_image(image_bytes: bytes, ratio: str) -> bytes:
    """Center-crop image to target aspect ratio. Returns original if ratio is 'original'."""
    if ratio == "original" or ratio not in CROP_RATIOS or CROP_RATIOS[ratio] is None:
        return image_bytes

    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode != 'RGB':
            img = img.convert('RGB')

        target_ratio = CROP_RATIOS[ratio]
        img_ratio = img.width / img.height

        if img_ratio > target_ratio:
            # Image is wider — crop width
            new_width = int(img.height * target_ratio)
            left = (img.width - new_width) // 2
            img = img.crop((left, 0, left + new_width, img.height))
        elif img_ratio < target_ratio:
            # Image is taller — crop height
            new_height = int(img.width / target_ratio)
            top = (img.height - new_height) // 2
            img = img.crop((0, top, img.width, top + new_height))

        output = io.BytesIO()
        img.save(output, format='JPEG', quality=95)
        logger.info(f"Cropped image to {ratio} ({img.width}x{img.height})")
        return output.getvalue()

    except Exception as e:
        logger.error(f"Crop failed: {e}")
        return image_bytes


def upload_to_s3(image_bytes: bytes, key: str) -> str:
    """Upload image bytes to S3 and return a presigned URL (1h expiry)."""
    s3_client.put_object(
        Bucket=S3_BUCKET,
        Key=key,
        Body=image_bytes,
        ContentType="image/jpeg"
    )
    presigned_url = s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": S3_BUCKET, "Key": key},
        ExpiresIn=3600
    )
    return presigned_url


def upload_to_tmpfiles(image_bytes: bytes, filename: str) -> str:
    """Upload image to tmpfiles.org (free, no account needed). Files expire after 1h."""
    resp = requests.post(
        "https://tmpfiles.org/api/v1/upload",
        files={"file": (filename, image_bytes, "image/jpeg")}
    )
    if resp.status_code != 200:
        raise Exception(f"tmpfiles.org upload failed: {resp.text}")
    
    raw_url = resp.json().get("data", {}).get("url", "")
    # Convert to direct download link
    public_url = raw_url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
    # Ensure HTTPS
    if public_url.startswith("http://"):
        public_url = public_url.replace("http://", "https://", 1)
    return public_url


def upload_image(image_bytes: bytes, key: str) -> str:
    """Upload image to S3 if configured, otherwise tmpfiles.org."""
    if USE_S3:
        return upload_to_s3(image_bytes, key)
    else:
        filename = key.split("/")[-1]  # extract filename from s3-style key
        return upload_to_tmpfiles(image_bytes, filename)


# --- Endpoints ---

@app.get("/")
def read_root():
    return {"status": "ok", "message": "InstaGrid AI Backend is running"}

@app.get("/config")
def get_config():
    """Expose environment variables to frontend for auto-fill."""
    return {
        "ig_user_id": os.getenv("IG_USER_ID", ""),
        "ig_access_token": os.getenv("IG_ACCESS_TOKEN", ""),
        "fb_app_configured": bool(os.getenv("FB_APP_ID") and os.getenv("FB_APP_SECRET")),
    }


class TokenExchangeRequest(BaseModel):
    short_lived_token: str


@app.post("/exchange-token")
async def exchange_token(request: TokenExchangeRequest):
    """
    Exchange a short-lived token for a permanent Page token.
    
    Flow:
    1. Short-lived user token → Long-lived user token (60 days)
    2. Long-lived user token → Permanent Page token (never expires)
    """
    app_id = os.environ.get("FB_APP_ID")
    app_secret = os.environ.get("FB_APP_SECRET")
    
    if not app_id or not app_secret:
        raise HTTPException(400, "FB_APP_ID and FB_APP_SECRET not configured in .env")
    
    # Step 1: Exchange short-lived → long-lived user token
    logger.info("Step 1: Exchanging short-lived token for long-lived token...")
    exchange_url = "https://graph.facebook.com/v19.0/oauth/access_token"
    resp = requests.get(exchange_url, params={
        "grant_type": "fb_exchange_token",
        "client_id": app_id,
        "client_secret": app_secret,
        "fb_exchange_token": request.short_lived_token
    })
    
    if resp.status_code != 200:
        error_detail = resp.json().get("error", {}).get("message", resp.text)
        raise HTTPException(400, f"Token exchange failed: {error_detail}")
    
    long_lived_token = resp.json().get("access_token")
    expires_in = resp.json().get("expires_in", 0)
    logger.info(f"Long-lived token obtained. Expires in {expires_in // 3600}h ({expires_in // 86400} days)")
    
    # Step 2: Get Page tokens from long-lived user token
    logger.info("Step 2: Fetching Page tokens...")
    pages_resp = requests.get(
        "https://graph.facebook.com/v19.0/me/accounts",
        params={"access_token": long_lived_token}
    )
    
    if pages_resp.status_code != 200:
        # If Page tokens fail, return the long-lived token (still 60 days)
        logger.warning(f"Could not fetch page tokens: {pages_resp.text}")
        save_token(long_lived_token, "long_lived_user", {"expires_in_days": expires_in // 86400})
        return {
            "status": "success",
            "token_type": "long_lived_user",
            "expires_in_days": expires_in // 86400,
            "access_token": long_lived_token[:20] + "...",
            "message": f"Token étendu à {expires_in // 86400} jours. Page token non disponible."
        }
    
    pages = pages_resp.json().get("data", [])
    
    if not pages:
        # No pages found — return long-lived token
        logger.warning("No Facebook Pages found. Returning long-lived user token.")
        save_token(long_lived_token, "long_lived_user", {"expires_in_days": expires_in // 86400})
        return {
            "status": "success",
            "token_type": "long_lived_user",
            "expires_in_days": expires_in // 86400,
            "access_token": long_lived_token[:20] + "...",
            "message": f"Token étendu à {expires_in // 86400} jours. Aucune Page Facebook trouvée pour token permanent."
        }
    
    # Find the page connected to our IG account
    ig_user_id = os.environ.get("IG_USER_ID", "")
    best_page = None
    
    for page in pages:
        page_token = page.get("access_token")
        page_id = page.get("id")
        page_name = page.get("name", "Unknown")
        
        # Check if this page is linked to our IG account
        ig_resp = requests.get(
            f"https://graph.facebook.com/v19.0/{page_id}",
            params={
                "fields": "instagram_business_account",
                "access_token": page_token
            }
        )
        
        if ig_resp.status_code == 200:
            ig_account = ig_resp.json().get("instagram_business_account", {})
            linked_ig_id = ig_account.get("id", "")
            
            if linked_ig_id == ig_user_id:
                best_page = {"token": page_token, "name": page_name, "id": page_id}
                logger.info(f"Found matching Page: '{page_name}' (ID: {page_id}) → IG: {linked_ig_id}")
                break
            else:
                logger.info(f"Page '{page_name}' linked to IG {linked_ig_id or 'none'}, not {ig_user_id}")
    
    if best_page:
        # Permanent page token!
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
        # No matching page, use first page or fallback to long-lived
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


@app.post("/analyze", response_model=AnalysisResponse)
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
    
    encoded_images = []
    for file in files:
        content = await file.read()
        compressed_content = compress_image(content, max_size_kb=800)
        encoded_images.append(base64.b64encode(compressed_content).decode('utf-8'))
        await file.seek(0)

    common_instruction = f"IMPORTANT - FIL ROUGE / COMMON THREAD: {user_context}" if user_context else ""
    c0 = f"Context for Image 1 (Left): {context_0}" if context_0 else ""
    c1 = f"Context for Image 2 (Middle): {context_1}" if context_1 else ""
    c2 = f"Context for Image 3 (Right): {context_2}" if context_2 else ""

    try:
        with open("prompts.yaml", "r") as f:
            prompts = yaml.safe_load(f)
            system_prompt_template = prompts["instagram_grid_analysis"]["system"]
            system_prompt = system_prompt_template.format(
                common_instruction=common_instruction,
                context_0=c0,
                context_1=c1,
                context_2=c2
            )
    except Exception as e:
        logger.error(f"Failed to load prompts.yaml: {e}")
        raise HTTPException(500, detail="Configuration Error: Could not load prompts.")

    user_content = [
        {"type": "text", "text": "Analyze these 3 images for an Instagram Grid strategy."}
    ]
    
    for img_base64 in encoded_images:
        user_content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{img_base64}"
            }
        })

    try:
        response = client.beta.chat.completions.parse(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
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


@app.post("/regenerate_caption", response_model=RegenerateResponse)
async def regenerate_caption(request: RegenerateRequest):
    logger.info("Regenerating caption...")
    
    common_instruction = f"{request.common_context}" if request.common_context else "Aucun fil rouge spécifique."
    individual_context = f"{request.individual_context}" if request.individual_context else "Aucun contexte spécifique."
    
    try:
        with open("prompts.yaml", "r") as f:
            prompts = yaml.safe_load(f)
            system_prompt_template = prompts["single_image_caption"]["system"]
            system_prompt = system_prompt_template.format(
                common_instruction=common_instruction,
                individual_context=individual_context,
                common_thread_fr=request.common_thread_fr,
                common_thread_en=request.common_thread_en
            )
    except Exception as e:
        logger.error(f"Failed to load prompts.yaml: {e}")
        raise HTTPException(500, detail="Configuration Error")

    user_content = [
        {"type": "text", "text": "Regenerate the specific part of the caption."},
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


@app.post("/post")
async def post_to_grid(request: PostRequest):
    """
    Post 3 images to Instagram via Graph API + S3.
    Posts in REVERSE (LIFO) order: Right -> Middle -> Left.
    """
    if len(request.posts) != 3:
        raise HTTPException(status_code=400, detail="Must provide exactly 3 posts.")

    # Resolve credentials (request params override env vars)
    token = request.access_token or os.environ.get("IG_ACCESS_TOKEN")
    user_id = request.ig_user_id or os.environ.get("IG_USER_ID")

    if not token or not user_id:
        raise HTTPException(status_code=400, detail="Missing Instagram credentials (access_token / ig_user_id).")

    hosting = "S3" if USE_S3 else "tmpfiles.org"
    logger.info(f"Posting via Instagram Graph API + {hosting}...")

    # Grid: [Left (0), Middle (1), Right (2)]
    # Post Order: Right (2) -> Middle (1) -> Left (0)
    posts_to_publish = [
        request.posts[2],  # Right
        request.posts[1],  # Middle
        request.posts[0]   # Left
    ]
    
    results = []
    timestamp = int(time.time())

    for idx, post in enumerate(posts_to_publish):
        position_name = ["Right", "Middle", "Left"][idx]
        
        try:
            # 1. Prepare image (compress & convert to JPEG)
            image_bytes = base64.b64decode(post.image_base64)
            image_bytes = compress_image(image_bytes)
            
            # 2. Upload image (S3 or tmpfiles.org)
            s3_key = f"temp/post_{timestamp}_{idx}.jpg"
            logger.info(f"Uploading {position_name} via {hosting}...")
            public_url = upload_image(image_bytes, s3_key)
            
            logger.info(f"Posting {position_name} via Graph API.")
            
            # 3. Create Media Container
            create_url = f"https://graph.facebook.com/v19.0/{user_id}/media"
            payload = {
                "image_url": public_url,
                "caption": post.caption,
                "access_token": token
            }
            
            resp = requests.post(create_url, data=payload)
            if resp.status_code != 200:
                raise Exception(f"Container Creation Failed: {resp.text}")
            
            container_id = resp.json().get("id")
            logger.info(f"Container created: {container_id}. Waiting for processing...")
            
            # 4. Poll for container status (Facebook needs time to process)
            status_url = f"https://graph.facebook.com/v19.0/{container_id}"
            for attempt in range(12):  # Max 60 seconds (12 x 5s)
                time.sleep(5)
                status_resp = requests.get(status_url, params={
                    "fields": "status_code",
                    "access_token": token
                })
                status_data = status_resp.json()
                status_code = status_data.get("status_code", "UNKNOWN")
                logger.info(f"Container {container_id} status: {status_code} (attempt {attempt+1})")
                
                if status_code == "FINISHED":
                    break
                elif status_code == "ERROR":
                    raise Exception(f"Container processing failed: {status_data}")
            else:
                raise Exception(f"Container {container_id} still not ready after 60s")
            
            # 5. Publish Media
            publish_url = f"https://graph.facebook.com/v19.0/{user_id}/media_publish"
            pub_payload = {
                "creation_id": container_id,
                "access_token": token
            }
            
            pub_resp = requests.post(publish_url, data=pub_payload)
            if pub_resp.status_code != 200:
                raise Exception(f"Publishing Failed: {pub_resp.text}")
                
            post_id = pub_resp.json().get("id")
            results.append(f"Posted {position_name}: ID {post_id}")
            logger.info(f"Successfully published {position_name}")
            
        except Exception as e:
            logger.error(f"Graph API Error for {position_name}: {e}")
            raise HTTPException(status_code=500, detail=f"Graph API Failed: {str(e)}")
    
    return {
        "status": "success", 
        "message": "All 3 images posted via Graph API!",
        "logs": results
    }


# --- Draft Endpoints ---

# Serve local draft images (only used when S3 is not configured)
from fastapi.responses import FileResponse

@app.get("/drafts/image/{filename}")
async def get_draft_image(filename: str):
    """Serve a draft image from local storage."""
    filepath = os.path.join("data/drafts/images", filename)
    if not os.path.exists(filepath):
        raise HTTPException(404, "Image not found")
    return FileResponse(filepath, media_type="image/jpeg")


class SaveDraftRequest(BaseModel):
    posts: List[PostItem]
    crop_ratios: Optional[List[str]] = None  # ["original", "1:1", "4:5", "16:9"]


class UpdateDraftRequest(BaseModel):
    captions: Optional[List[str]] = None
    crop_ratios: Optional[List[str]] = None


class PostDraftRequest(BaseModel):
    access_token: Optional[str] = None
    ig_user_id: Optional[str] = None
    force: bool = False  # Set to True to re-post an already posted draft


@app.get("/drafts")
async def list_drafts():
    """List all saved drafts."""
    drafts = draft_store.list_drafts()
    # Add image URLs to each draft
    for draft in drafts:
        for post in draft["posts"]:
            post["image_url"] = draft_store.get_image_url(post["image_key"])
    return {"drafts": drafts}


@app.post("/drafts")
async def save_draft(request: SaveDraftRequest):
    """Save a new draft (3 images + captions). Images stored RAW — no compression."""
    if len(request.posts) != 3:
        raise HTTPException(400, "Must provide exactly 3 posts.")

    images = []
    captions = []
    for post in request.posts:
        image_bytes = base64.b64decode(post.image_base64)
        # NO compression — store raw for non-destructive editing
        images.append(image_bytes)
        captions.append(post.caption)

    draft = draft_store.save_draft(images, captions, request.crop_ratios)
    return {"status": "success", "message": f"Draft saved: {draft['id']}", "draft": draft}


@app.put("/drafts/{draft_id}")
async def update_draft(draft_id: str, request: UpdateDraftRequest):
    """Update captions and/or crop ratios of an existing draft."""
    draft = draft_store.update_draft(draft_id, request.captions, request.crop_ratios)
    if not draft:
        raise HTTPException(404, f"Draft '{draft_id}' not found")
    return {"status": "success", "message": f"Draft updated: {draft_id}", "draft": draft}


@app.delete("/drafts/{draft_id}")
async def delete_draft(draft_id: str):
    """Delete a draft and its images."""
    deleted = draft_store.delete_draft(draft_id)
    if not deleted:
        raise HTTPException(404, f"Draft '{draft_id}' not found")
    return {"status": "success", "message": f"Draft deleted: {draft_id}"}


@app.post("/drafts/{draft_id}/post")
async def post_draft(draft_id: str, request: PostDraftRequest):
    """Post a draft to Instagram. Verifies publication before marking as posted."""
    draft = draft_store.get_draft(draft_id)
    if not draft:
        raise HTTPException(404, f"Draft '{draft_id}' not found")

    # Warning if already posted
    if draft["status"] == "posted" and not request.force:
        raise HTTPException(
            409,
            f"Ce brouillon a déjà été publié le {draft['posted_at']}. "
            f"Envoyez force=true pour re-publier."
        )

    token = request.access_token or os.environ.get("IG_ACCESS_TOKEN")
    user_id = request.ig_user_id or os.environ.get("IG_USER_ID")

    if not token or not user_id:
        raise HTTPException(400, "Missing Instagram credentials.")

    # Post in LIFO order: Right (2) -> Middle (1) -> Left (0)
    posts_ordered = [draft["posts"][2], draft["posts"][1], draft["posts"][0]]
    results = []

    for idx, post in enumerate(posts_ordered):
        position_name = ["Right", "Middle", "Left"][idx]

        try:
            # Get raw image from store
            crop_ratio = post.get("crop_ratio", "original")

            # Read raw image bytes
            if USE_S3:
                obj = s3_client.get_object(Bucket=S3_BUCKET, Key=post["image_key"])
                image_bytes = obj["Body"].read()
            else:
                image_path = os.path.join("data/drafts/images", os.path.basename(post["image_key"]))
                with open(image_path, "rb") as f:
                    image_bytes = f.read()

            # Apply crop + compression (ONLY at post time — destructive step)
            image_bytes = crop_image(image_bytes, crop_ratio)
            image_bytes = compress_image(image_bytes)
            logger.info(f"Prepared {position_name}: crop={crop_ratio}")

            # Upload processed image for Graph API
            image_url = upload_image(image_bytes, f"temp/draft_{draft_id}_{idx}.jpg")

            # Create container
            create_url = f"https://graph.facebook.com/v19.0/{user_id}/media"
            resp = requests.post(create_url, data={
                "image_url": image_url,
                "caption": post["caption"],
                "access_token": token
            })
            if resp.status_code != 200:
                raise Exception(f"Container Creation Failed: {resp.text}")

            container_id = resp.json().get("id")
            logger.info(f"Draft {draft_id} - Container created for {position_name}: {container_id}")

            # Poll for status
            status_url = f"https://graph.facebook.com/v19.0/{container_id}"
            for attempt in range(12):
                time.sleep(5)
                status_resp = requests.get(status_url, params={
                    "fields": "status_code",
                    "access_token": token
                })
                status_code = status_resp.json().get("status_code", "UNKNOWN")
                if status_code == "FINISHED":
                    break
                elif status_code == "ERROR":
                    raise Exception(f"Container processing failed: {status_resp.json()}")
            else:
                raise Exception(f"Container {container_id} still not ready after 60s")

            # Publish
            pub_resp = requests.post(
                f"https://graph.facebook.com/v19.0/{user_id}/media_publish",
                data={"creation_id": container_id, "access_token": token}
            )
            if pub_resp.status_code != 200:
                raise Exception(f"Publishing Failed: {pub_resp.text}")

            post_id = pub_resp.json().get("id")

            # Verify the post exists on IG (100% confirmation)
            verify_resp = requests.get(
                f"https://graph.facebook.com/v19.0/{post_id}",
                params={"fields": "id,timestamp", "access_token": token}
            )
            if verify_resp.status_code != 200:
                raise Exception(f"Post verification failed for {position_name}")

            results.append(f"Posted {position_name}: ID {post_id} ✅ verified")
            logger.info(f"Draft {draft_id} - {position_name} published and verified: {post_id}")

        except Exception as e:
            logger.error(f"Draft post error for {position_name}: {e}")
            raise HTTPException(500, f"Publication failed at {position_name}: {str(e)}")

    # All 3 posted successfully — mark as posted
    draft_store.mark_as_posted(draft_id)

    return {
        "status": "success",
        "message": f"Draft '{draft_id}' published to Instagram!",
        "logs": results
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
