"""
Draft Store — Save/load/manage post drafts.
Dual backend: S3 (preferred) or local filesystem (fallback).
"""

import json
import os
import time
import uuid
import logging
import shutil
from abc import ABC, abstractmethod
from typing import List, Optional

logger = logging.getLogger(__name__)


class DraftStore(ABC):
    """Abstract draft store interface."""

    @abstractmethod
    def load_index(self) -> list:
        """Load all drafts metadata."""
        ...

    @abstractmethod
    def save_index(self, drafts: list):
        """Persist drafts metadata."""
        ...

    @abstractmethod
    def save_image(self, image_bytes: bytes, key: str):
        """Save an image."""
        ...

    @abstractmethod
    def get_image_url(self, key: str) -> str:
        """Get a URL/path to access the image."""
        ...

    @abstractmethod
    def delete_image(self, key: str):
        """Delete an image."""
        ...

    # --- High-level operations ---

    def list_drafts(self) -> list:
        return self.load_index()

    def get_draft(self, draft_id: str) -> Optional[dict]:
        drafts = self.load_index()
        for d in drafts:
            if d["id"] == draft_id:
                return d
        return None

    def save_draft(self, images: list, captions: list) -> dict:
        """Create a new draft with 3 images + captions."""
        drafts = self.load_index()
        draft_id = uuid.uuid4().hex[:8]
        now = time.strftime("%Y-%m-%dT%H:%M:%S")

        posts = []
        for idx, (img_bytes, caption) in enumerate(zip(images, captions)):
            key = f"drafts/images/draft_{draft_id}_{idx}.jpg"
            self.save_image(img_bytes, key)
            posts.append({"image_key": key, "caption": caption})

        draft = {
            "id": draft_id,
            "created_at": now,
            "updated_at": now,
            "status": "draft",
            "posted_at": None,
            "posts": posts,
        }
        drafts.append(draft)
        self.save_index(drafts)
        logger.info(f"Draft saved: {draft_id}")
        return draft

    def update_draft(self, draft_id: str, captions: list) -> Optional[dict]:
        """Update captions of an existing draft."""
        drafts = self.load_index()
        for d in drafts:
            if d["id"] == draft_id:
                for idx, caption in enumerate(captions):
                    if idx < len(d["posts"]):
                        d["posts"][idx]["caption"] = caption
                d["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
                self.save_index(drafts)
                logger.info(f"Draft updated: {draft_id}")
                return d
        return None

    def mark_as_posted(self, draft_id: str) -> Optional[dict]:
        """Mark a draft as posted."""
        drafts = self.load_index()
        for d in drafts:
            if d["id"] == draft_id:
                d["status"] = "posted"
                d["posted_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
                self.save_index(drafts)
                logger.info(f"Draft marked as posted: {draft_id}")
                return d
        return None

    def delete_draft(self, draft_id: str) -> bool:
        """Delete a draft and its images."""
        drafts = self.load_index()
        draft = None
        for d in drafts:
            if d["id"] == draft_id:
                draft = d
                break
        if not draft:
            return False

        # Delete images
        for post in draft["posts"]:
            try:
                self.delete_image(post["image_key"])
            except Exception as e:
                logger.warning(f"Could not delete image {post['image_key']}: {e}")

        drafts = [d for d in drafts if d["id"] != draft_id]
        self.save_index(drafts)
        logger.info(f"Draft deleted: {draft_id}")
        return True


# --- S3 Implementation ---

class S3DraftStore(DraftStore):
    def __init__(self, s3_client, bucket: str):
        self.s3 = s3_client
        self.bucket = bucket
        self.index_key = "drafts/index.json"

    def load_index(self) -> list:
        try:
            resp = self.s3.get_object(Bucket=self.bucket, Key=self.index_key)
            return json.loads(resp["Body"].read().decode("utf-8"))
        except self.s3.exceptions.NoSuchKey:
            return []
        except Exception as e:
            logger.warning(f"Could not load drafts index from S3: {e}")
            return []

    def save_index(self, drafts: list):
        self.s3.put_object(
            Bucket=self.bucket,
            Key=self.index_key,
            Body=json.dumps(drafts, indent=2, ensure_ascii=False).encode("utf-8"),
            ContentType="application/json",
        )

    def save_image(self, image_bytes: bytes, key: str):
        self.s3.put_object(
            Bucket=self.bucket, Key=key, Body=image_bytes, ContentType="image/jpeg"
        )

    def get_image_url(self, key: str) -> str:
        return self.s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=3600,
        )

    def delete_image(self, key: str):
        self.s3.delete_object(Bucket=self.bucket, Key=key)


# --- Local Filesystem Implementation ---

class LocalDraftStore(DraftStore):
    def __init__(self, base_dir: str = "data/drafts"):
        self.base_dir = base_dir
        self.images_dir = os.path.join(base_dir, "images")
        self.index_path = os.path.join(base_dir, "index.json")
        os.makedirs(self.images_dir, exist_ok=True)

    def load_index(self) -> list:
        try:
            if os.path.exists(self.index_path):
                with open(self.index_path, "r") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load drafts index: {e}")
        return []

    def save_index(self, drafts: list):
        with open(self.index_path, "w") as f:
            json.dump(drafts, f, indent=2, ensure_ascii=False)

    def save_image(self, image_bytes: bytes, key: str):
        filepath = os.path.join(self.base_dir, os.path.basename(key))
        # Store in images dir but keep the key format for consistency
        actual_path = os.path.join(self.images_dir, os.path.basename(key))
        with open(actual_path, "wb") as f:
            f.write(image_bytes)

    def get_image_url(self, key: str) -> str:
        # Return a local path that the frontend can access via a /drafts/image endpoint
        return f"/drafts/image/{os.path.basename(key)}"

    def delete_image(self, key: str):
        filepath = os.path.join(self.images_dir, os.path.basename(key))
        if os.path.exists(filepath):
            os.remove(filepath)
