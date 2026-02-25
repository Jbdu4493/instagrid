from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from typing import List
import os
import time
import base64
import requests
from config import logger, draft_store, USE_S3, s3_client, S3_BUCKET, IG_USER_ID
from models import SaveDraftRequest, UpdateDraftRequest, PostDraftRequest
from utils import compress_image, crop_image, upload_image

router = APIRouter()

def _get_raw_image_bytes(image_key: str) -> bytes:
    """Retrieve raw image bytes from S3 or local storage."""
    if USE_S3:
        obj = s3_client.get_object(Bucket=S3_BUCKET, Key=image_key)
        return obj["Body"].read()
    
    image_path = os.path.join("data/drafts/images", os.path.basename(image_key))
    with open(image_path, "rb") as f:
        return f.read()

def _process_instagram_publication(user_id: str, token: str, image_url: str, caption: str) -> str:
    """Handles the 3-step Graph API publication process (Create Container, Poll, Publish)."""
    # 1. Create container
    create_url = f"https://graph.facebook.com/v19.0/{user_id}/media"
    resp = requests.post(create_url, data={
        "image_url": image_url,
        "caption": caption,
        "access_token": token
    })
    if resp.status_code != 200:
        raise Exception(f"Container Creation Failed: {resp.text}")

    container_id = resp.json().get("id")

    # 2. Poll for status
    status_url = f"https://graph.facebook.com/v19.0/{container_id}"
    for _ in range(12):
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

    # 3. Publish
    pub_resp = requests.post(
        f"https://graph.facebook.com/v19.0/{user_id}/media_publish",
        data={"creation_id": container_id, "access_token": token}
    )
    if pub_resp.status_code != 200:
        raise Exception(f"Publishing Failed: {pub_resp.text}")

    post_id = pub_resp.json().get("id")

    # 4. Verify
    verify_resp = requests.get(f"https://graph.facebook.com/v19.0/{post_id}", params={
        "fields": "id,timestamp", "access_token": token
    })
    
    if verify_resp.status_code != 200:
        raise Exception("Post verification failed")

    return post_id

# Serve local draft images (only used when S3 is not configured)
@router.get("/image/{filename}")
async def get_draft_image(filename: str):
    """Serve a draft image from local storage."""
    filepath = os.path.join("data/drafts/images", filename)
    if not os.path.exists(filepath):
        raise HTTPException(404, "Image not found")
    return FileResponse(filepath, media_type="image/jpeg")

@router.get("/")
async def list_drafts():
    """List all saved drafts."""
    drafts = draft_store.list_drafts()
    # Add image URLs to each draft
    for draft in drafts:
        for post in draft["posts"]:
            post["image_url"] = draft_store.get_image_url(post["image_key"])
    return {"drafts": drafts}

@router.post("/")
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

    draft = draft_store.save_draft(images, captions, request.crop_ratios, request.crop_positions)
    return {"status": "success", "message": f"Draft saved: {draft['id']}", "draft": draft}

@router.put("/{draft_id}")
async def update_draft(draft_id: str, request: UpdateDraftRequest):
    """Update captions, crop ratios, crop positions, and/or post order of an existing draft."""
    draft = draft_store.update_draft(
        draft_id, 
        request.captions, 
        request.crop_ratios, 
        request.crop_positions,
        request.post_order
    )
    if not draft:
        raise HTTPException(404, f"Draft '{draft_id}' not found")
    return {"status": "success", "message": f"Draft updated: {draft_id}", "draft": draft}

@router.delete("/{draft_id}")
async def delete_draft(draft_id: str):
    """Delete a draft and its images."""
    deleted = draft_store.delete_draft(draft_id)
    if not deleted:
        raise HTTPException(404, f"Draft '{draft_id}' not found")
    return {"status": "success", "message": f"Draft deleted: {draft_id}"}

@router.post("/{draft_id}/post")
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
    user_id = request.ig_user_id or IG_USER_ID

    if not token or not user_id:
        raise HTTPException(400, "Missing Instagram credentials.")

    # Post in LIFO order: Right (2) -> Middle (1) -> Left (0)
    posts_ordered = [draft["posts"][2], draft["posts"][1], draft["posts"][0]]
    results = []

    for idx, post in enumerate(posts_ordered):
        position_name = ["Right", "Middle", "Left"][idx]

        try:
            # 1. Fetch raw image from Data Store
            image_bytes = _get_raw_image_bytes(post["image_key"])

            # 2. Apply crop + compression
            crop_ratio = post.get("crop_ratio", "original")
            crop_position = post.get("crop_position", {"x": 50, "y": 50})
            image_bytes = crop_image(image_bytes, crop_ratio, crop_position)
            image_bytes = compress_image(image_bytes)
            logger.info(f"Prepared {position_name}: crop={crop_ratio}")

            # 3. Upload processed image online for Instagram to fetch
            image_url = upload_image(image_bytes, f"temp/draft_{draft_id}_{idx}.jpg")

            # 4. Talk with Graph API to publish
            post_id = _process_instagram_publication(user_id, token, image_url, post["caption"])

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
