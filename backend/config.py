import os
import sys
import logging
from openai import OpenAI
import boto3
from botocore.config import Config as BotoConfig
from drafts import S3DraftStore, LocalDraftStore, PCloudDraftStore
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ensure we can import new back-end packages
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.storage import StorageService, S3Storage, TmpfilesStorage, PCloudStorage
from services.instagram_service import InstagramService
from security.token_manager import TokenManager

# Global Configurations
FB_APP_ID = os.environ.get("FB_APP_ID")
FB_APP_SECRET = os.environ.get("FB_APP_SECRET")
IG_USER_ID = os.environ.get("IG_USER_ID", "")

# Instagram Graph API Service
FACEBOOK_API_URL = "https://graph.facebook.com/v19.0"
instagram_service = InstagramService(FACEBOOK_API_URL)

# Initialize OpenAI Client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Initialize S3 Client & Storage Strategy
USE_S3 = bool(os.environ.get("AWS_ACCESS_KEY_ID") and os.environ.get("AWS_SECRET_ACCESS_KEY"))
s3_client = None
S3_BUCKET = os.environ.get("AWS_S3_BUCKET", "")

# Initialize pCloud Client
USE_PCLOUD = bool(os.environ.get("USE_PCLOUD", "").lower() == "true" and os.environ.get("PCLOUD_ACCESS_TOKEN"))
PCLOUD_ACCESS_TOKEN = os.environ.get("PCLOUD_ACCESS_TOKEN", "")
PCLOUD_FOLDER_ID = int(os.environ.get("PCLOUD_FOLDER_ID", "0"))

# Initialize Storage Strategy for Instagram Proxy Upload
# (Facebook Graph API blocks pCloud direct links, so we use S3 or Tmpfiles.org temporarily just for publishing)
if USE_S3:
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
        region_name=os.environ.get("AWS_S3_REGION", "eu-west-3"),
        config=BotoConfig(signature_version="s3v4")
    )
    S3_BUCKET = os.environ.get("AWS_S3_BUCKET", "instagrid")
    logger.info(f"S3 configured for ephemeral StorageService: bucket={S3_BUCKET}")
    storage_service = StorageService(S3Storage(s3_client, S3_BUCKET))
else:
    logger.info("Using tmpfiles.org as fallback ephemeral StorageService")
    storage_service = StorageService(TmpfilesStorage())

# Initialize Draft Store
if USE_PCLOUD:
    draft_store = PCloudDraftStore(PCLOUD_ACCESS_TOKEN, PCLOUD_FOLDER_ID)
    logger.info("DraftStore: pCloud")
elif USE_S3:
    draft_store = S3DraftStore(s3_client, S3_BUCKET)
    logger.info("DraftStore: S3")
else:
    draft_store = LocalDraftStore("data/drafts")
    logger.info("DraftStore: Local (data/drafts/)")

os.makedirs("data", exist_ok=True)

