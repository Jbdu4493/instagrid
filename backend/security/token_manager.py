import os
import json
import time
from typing import Optional, Dict
from config import logger

# Note: Ce paramètre global est chargé indépendamment 
TOKEN_FILE = "data/token.json"

class TokenManager:
    """
    Gère la persistance et le chargement des Jetons d'Accès de l'application.
    Permet de maintenir l'état d'authentification entre chaque redémarrage du serveur.
    """

    @staticmethod
    def load_saved_token() -> bool:
        """
        Tente de charger un token d'accès précédemment sauvegardé depuis le disque.
        Si un token est trouvé, il est injecté dans le dictionnaire d'environnement du processus actif
        `os.environ["IG_ACCESS_TOKEN"]`.

        :return: True si un jeton valide a été trouvé et chargé en mémoire, False sinon.
        :rtype: bool
        """
        try:
            if os.path.exists(TOKEN_FILE):
                with open(TOKEN_FILE, "r") as f:
                    data = json.load(f)
                    
                saved_token = data.get("access_token")
                token_type = data.get("token_type", "unknown")
                
                if saved_token:
                    os.environ["IG_ACCESS_TOKEN"] = saved_token
                    logger.info(f"Jeton d'accès de type '{token_type}' chargé avec succès depuis {TOKEN_FILE}")
                    return True
        except json.JSONDecodeError as e:
            logger.error(f"Le fichier de token est corrompu: {e}", exc_info=True)
        except OSError as e:
            logger.error(f"Erreur d'IO lors de l'accès au fichier {TOKEN_FILE}: {e}", exc_info=True)
            
        return False

    @staticmethod
    def save_token(token: str, token_type: str, extra: Optional[Dict] = None) -> None:
        """
        Persiste un jeton d'accès sur le système de fichiers pour survivre aux cycles de vie du programme.
        Met également à jour le processus en cours d'exécution.

        :param token: La chaîne brute du jeton d'accès (ex: jeton Meta longue durée).
        :type token: str
        :param token_type: Identifiant métier du jeton (ex: 'permanent_page', 'long_lived_user').
        :type token_type: str
        :param extra: Un dictionnaire optionnel afin d'ajouter des métadonnées arbitraires (ex: nom de la cible, date log).
        :type extra: Optional[Dict]
        :return: Rien
        :rtype: None
        """
        try:
            os.makedirs(os.path.dirname(TOKEN_FILE) or ".", exist_ok=True)
            
            data = {
                "access_token": token, 
                "token_type": token_type, 
                "saved_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            if extra:
                data.update(extra)
                
            with open(TOKEN_FILE, "w") as f:
                json.dump(data, f, indent=2)
                
            # Mise à jour immédiate du processus actif
            os.environ["IG_ACCESS_TOKEN"] = token
            logger.info(f"Jeton d'accès de type '{token_type}' enregistré sur le disque.")
            
        except OSError as e:
            logger.error(f"Échec critique lors de l'enregistrement du jeton sur le disque: {e}", exc_info=True)
