import time
import requests
from typing import List, Dict, Optional
from config import logger

class InstagramAPIError(Exception):
    """Exception métier pour les défaillances de communication avec l'API Graph Meta."""
    pass

class InstagramService:
    """
    Facade isolant l'application de la complexité technique de l'API Graph d'Instagram.
    Gère la création asynchrone des conteneurs, le polling et la publication.
    """
    def __init__(self, base_url: str):
        """
        Initialise le service avec l'URL de base de l'API Graph.
        
        :param base_url: L'URL racine de l'API Facebook (ex: https://graph.facebook.com/v19.0).
        :type base_url: str
        """
        self.base_url = base_url

    def publish_image(self, user_id: str, token: str, image_url: str, caption: str) -> str:
        """
        Gère le processus complet en 3 étapes de publication pour un seul média :
        1. Création du conteneur (Media Container)
        2. Sondage asynchrone (Polling) pour vérifier que Facebook a fini le traitement
        3. Ordre de publication (Media Publish)
        
        :param user_id: L'ID du compte Instagram professionnel cible.
        :type user_id: str
        :param token: Le jeton d'accès (User Token ou Page Token).
        :type token: str
        :param image_url: L'URL publique de l'image préparée et accessible par les serveurs Facebook.
        :type image_url: str
        :param caption: La légende accompagnant le post.
        :type caption: str
        :return: L'ID officiel Meta du post Instagram publié.
        :rtype: str
        :raises InstagramAPIError: En cas de refus ou de timeout de l'API Facebook.
        """
        try:
            # 1. Create Media Container
            create_url = f"{self.base_url}/{user_id}/media"
            payload = {
                "image_url": image_url,
                "caption": caption,
                "access_token": token
            }
            
            resp = requests.post(create_url, data=payload, timeout=15)
            if resp.status_code != 200:
                raise InstagramAPIError(f"Échec de création du conteneur: {resp.text}")
            
            container_id = resp.json().get("id")
            logger.info(f"Conteneur créé: {container_id}. En attente de traitement par Meta...")
            
            # 2. Poll for container status
            status_url = f"{self.base_url}/{container_id}"
            for attempt in range(12):  # Max 60 seconds (12 x 5s)
                time.sleep(5)
                status_resp = requests.get(status_url, params={
                    "fields": "status_code",
                    "access_token": token
                }, timeout=10)
                
                status_data = status_resp.json()
                status_code = status_data.get("status_code", "UNKNOWN")
                logger.info(f"Statut du conteneur {container_id}: {status_code} (essai {attempt+1}/12)")
                
                if status_code == "FINISHED":
                    break
                elif status_code == "ERROR":
                    raise InstagramAPIError(f"Rejet du conteneur par Instagram: {status_data}")
            else:
                raise InstagramAPIError(f"Le conteneur {container_id} a expiré après 60 secondes d'attente.")
            
            # 3. Publish Media
            publish_url = f"{self.base_url}/{user_id}/media_publish"
            pub_payload = {
                "creation_id": container_id,
                "access_token": token
            }
            
            pub_resp = requests.post(publish_url, data=pub_payload, timeout=15)
            if pub_resp.status_code != 200:
                raise InstagramAPIError(f"Échec de l'ordre de publication finale: {pub_resp.text}")
                
            post_id = pub_resp.json().get("id")
            
            # 4. Verification
            verify_resp = requests.get(f"{self.base_url}/{post_id}", params={
                "fields": "id,timestamp", "access_token": token
            }, timeout=10)
            
            if verify_resp.status_code != 200:
                logger.warning("La vérification du post a échoué mais le post semble avoir été publié.")
                
            return post_id

        except requests.RequestException as e:
            logger.error(f"Erreur réseau lors de la communication avec Graph API: {e}", exc_info=True)
            raise InstagramAPIError("Délai d'attente réseau ou URL injoignable.") from e

    def fetch_recent_posts(self, user_id: str, token: str, limit: int = 12) -> List[Dict]:
        """
        Récupère les derniers médias publiés pour un utilisateur Instagram.
        
        :param user_id: L'identifiant de compte Instagram.
        :type user_id: str
        :param token: Le jeton d'accès.
        :type token: str
        :param limit: Nombre maximum de posts à récupérer.
        :type limit: int
        :return: Une liste de dictionnaires représentant les publications.
        :rtype: List[Dict]
        :raises InstagramAPIError: Si Meta renvoie une erreur (jeton expiré, permission refusée...).
        """
        url = f"{self.base_url}/{user_id}/media"
        params = {
            "fields": "id,media_type,media_url,thumbnail_url,permalink,caption,timestamp,like_count,comments_count",
            "limit": limit,
            "access_token": token
        }
        
        try:
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code != 200:
                logger.error(f"Erreur Graph API lors de fetch_recent_posts: {resp.text}")
                raise InstagramAPIError(f"Code {resp.status_code}: {resp.text}")
                
            return resp.json().get("data", [])
            
        except requests.RequestException as e:
            logger.error(f"Erreur réseau sur fetch_recent_posts: {e}", exc_info=True)
            raise InstagramAPIError("Le serveur Facebook est injoignable.") from e
