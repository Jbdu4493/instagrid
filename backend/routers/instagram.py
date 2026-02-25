from fastapi import APIRouter, HTTPException
import os
import time
import base64
import requests
from config import logger, USE_S3, IG_USER_ID, storage_service, instagram_service
from models import PostRequest
from services.image_processor import compress_image, ImageProcessingError
from services.instagram_service import InstagramAPIError

router = APIRouter()

@router.post("/post")
async def post_to_grid(request: PostRequest):
    """
    Publie 3 images consécutives sur Instagram via la Graph API Meta et un service de stockage.
    L'ordre de publication est inversé (LIFO) : Droite -> Milieu -> Gauche, 
    afin que le rendu final sur la grille Instagram soit chronologiquement correct (Gauche à Droite).

    :param request: Objet de requête contenant exactement 3 posts (images encodées en base64 et légendes) 
                    ainsi que les identifiants Instagram optionnels.
    :type request: PostRequest
    :return: Un dictionnaire confirmant le statut de l'opération avec les logs internes de chaque image.
    :rtype: dict
    :raises HTTPException: Erreur 400 si validation échoue, 502 si erreur de stockage, 500 si l'API Meta échoue.
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
            # 1. Prepare image
            image_bytes = base64.b64decode(post.image_base64)
            try:
                image_bytes = compress_image(image_bytes)
            except ImageProcessingError as e:
                raise HTTPException(status_code=400, detail=f"Image illisible pour {position_name}: {e}")
            
            # 2. Upload image via Strategy Pattern (S3 or tmpfiles.org)
            s3_key = f"temp/post_{timestamp}_{idx}.jpg"
            logger.info(f"Uploading {position_name} via le service de stockage...")
            try:
                public_url = storage_service.upload_image(image_bytes, s3_key)
            except Exception as e:
                raise HTTPException(status_code=502, detail=f"Erreur de stockage: {e}")
            
            logger.info(f"Posting {position_name} via Graph API.")
            
            # 3. Process via InstagramService (Container + Polling + Publish)
            try:
                post_id = instagram_service.publish_image(user_id, token, public_url, post.caption)
                results.append(f"Posted {position_name}: ID {post_id}")
                logger.info(f"Successfully published {position_name}")
            except InstagramAPIError as e:
                raise Exception(f"Publishing Failed: {e}")

        except Exception as e:
            logger.error(f"Erreur pour {position_name}: {e}")
            raise HTTPException(status_code=500, detail=f"Échec de publication: {str(e)}")
    
    return {
        "status": "success", 
        "message": "All 3 images posted via Graph API!",
        "logs": results
    }

@router.get("/ig-posts")
async def get_ig_posts(ig_user_id: str, access_token: str):
    """
    Récupère les 12 derniers médias publiés pour un utilisateur Instagram donné.
    Particulièrement utilisé par le front-end pour afficher la 'Grille Instagram Actuelle' 
    et permettre un aperçu cohérent de la planification.

    :param ig_user_id: L'identifiant unique de compte Instagram (Business/Creator) cible.
    :type ig_user_id: str
    :param access_token: Le jeton d'accès (User Token ou Page Token) de l'utilisateur courant.
    :type access_token: str
    :return: Un dictionnaire contenant la liste des objets posts récents (id, permalink, caption...).
    :rtype: dict
    :raises HTTPException: Erreur 400 si identifiants manquants, ou codes HTTP natifs de Meta (ex: 401).
    """
    if not ig_user_id or not access_token:
        raise HTTPException(status_code=400, detail="Missing ig_user_id or access_token")
    
    try:
        posts = instagram_service.fetch_recent_posts(ig_user_id, access_token, limit=12)
        return {"posts": posts}
    except InstagramAPIError as e:
        raise HTTPException(status_code=500, detail=str(e))
