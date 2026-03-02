import os
import sys
from celery import Celery
from dotenv import load_dotenv

# Ensure we can import services
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.image_processor import compress_image, ImageProcessingError
import base64

load_dotenv()

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "instagrid_worker",
    broker=REDIS_URL,
    backend=REDIS_URL
)

# Optional configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

@celery_app.task(name="process_images_task")
def process_images_task(encoded_files_data):
    """
    Tâche d'arrière-plan Celery pour déporter la compression lourde d'images.
    Reçoit une liste d'images encodées en base64 depuis FastAPI,
    les décode, les compresse en WebP, et les ré-encode pour l'IA.
    """
    processed_images = []
    
    for b64_source in encoded_files_data:
        try:
            # Decode payload
            raw_bytes = base64.b64decode(b64_source)
            # Heavy CPU compression to WebP
            image_bytes = compress_image(raw_bytes, max_size_kb=800)
            # Re-encode to base64 for OpenAI/Gemini
            final_b64 = base64.b64encode(image_bytes).decode('utf-8')
            processed_images.append(final_b64)
        except Exception as e:
            # Return error string handled by caller
            return {"status": "error", "detail": str(e)}

    return {"status": "success", "data": processed_images}
