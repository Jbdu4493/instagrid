from fastapi import APIRouter, HTTPException
import os
import time
import base64
import requests
from config import logger, USE_S3, IG_USER_ID
from models import PostRequest
from utils import compress_image, upload_image
router = APIRouter()

FACEBOOK_API_URL = "https://graph.facebook.com/v19.0"

@router.post("/post")
async def post_to_grid(request: PostRequest):
    """
    Post 3 images to Instagram via Graph API + S3.
    Posts in REVERSE (LIFO) order: Right -> Middle -> Left.
    """
    if len(request.posts) != 3:
        raise HTTPException(status_code=400, detail="Must provide exactly 3 posts.")

    # Resolve credentials (request params override env vars)
    token = request.access_token or os.environ.get("IG_ACCESS_TOKEN")
    user_id = request.ig_user_id or IG_USER_ID

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
            create_url = f"{FACEBOOK_API_URL}/{user_id}/media"
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
            status_url = f"{FACEBOOK_API_URL}/{container_id}"
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
            publish_url = f"{FACEBOOK_API_URL}/{user_id}/media_publish"
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

@router.get("/ig-posts")
async def get_ig_posts(ig_user_id: str, access_token: str):
    """
    Fetch the last 12 media items for the given Instagram User ID.
    Used for previewing the 'Grille Instagram Actuelle'.
    """
    if not ig_user_id or not access_token:
        raise HTTPException(status_code=400, detail="Missing ig_user_id or access_token")
    
    url = f"{FACEBOOK_API_URL}/{ig_user_id}/media"
    params = {
        "fields": "id,media_type,media_url,thumbnail_url,permalink,caption,timestamp",
        "limit": 12,
        "access_token": access_token
    }
    
    try:
        resp = requests.get(url, params=params)
        if resp.status_code != 200:
            logger.error(f"Failed to fetch IG posts: {resp.text}")
            raise HTTPException(status_code=resp.status_code, detail=f"Graph API Error: {resp.text}")
        
        data = resp.json()
        return {"posts": data.get("data", [])}
    except Exception as e:
        logger.error(f"Error fetching IG posts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
