import os
import time
import json
import io
import requests
from PIL import Image
from config import logger, TOKEN_FILE, USE_S3, s3_client, S3_BUCKET

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

def crop_image(image_bytes: bytes, ratio: str, position: dict = None) -> bytes:
    """Center-crop image to target aspect ratio using position offsets."""
    if ratio == "original" or ratio not in CROP_RATIOS or CROP_RATIOS[ratio] is None:
        return image_bytes

    if position is None:
        position = {"x": 50, "y": 50}

    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode != 'RGB':
            img = img.convert('RGB')

        target_ratio = CROP_RATIOS[ratio]
        img_ratio = img.width / img.height
        pos_x = max(0, min(100, position.get("x", 50))) / 100.0
        pos_y = max(0, min(100, position.get("y", 50))) / 100.0

        if img_ratio > target_ratio:
            # Image is wider — crop width
            new_width = int(img.height * target_ratio)
            max_left = img.width - new_width
            left = int(max_left * pos_x)
            img = img.crop((left, 0, left + new_width, img.height))
        elif img_ratio < target_ratio:
            # Image is taller — crop height
            new_height = int(img.width / target_ratio)
            max_top = img.height - new_height
            top = int(max_top * pos_y)
            img = img.crop((0, top, img.width, top + new_height))

        output = io.BytesIO()
        img.save(output, format='JPEG', quality=95)
        logger.info(f"Cropped image to {ratio} at pos ({position}) -> {img.width}x{img.height}")
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
