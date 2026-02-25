import os
import requests
from abc import ABC, abstractmethod
from botocore.exceptions import BotoCoreError, ClientError
from typing import Optional
from config import logger

class StorageError(Exception):
    """
    Exception personnalisée pour les erreurs de stockage.
    Déclenchée lorsqu'un upload vers un service tiers échoue.
    """
    pass

class StorageStrategy(ABC):
    """
    Interface définissant le contrat pour tous les fournisseurs de stockage.
    """
    @abstractmethod
    def upload(self, image_bytes: bytes, key: str) -> str:
        """
        Uploade un tableau d'octets (image) vers le service de stockage et retourne une URL publique.

        :param image_bytes: Le contenu de l'image en octets (bytes).
        :type image_bytes: bytes
        :param key: L'identifiant unique ou le chemin souhaité pour le fichier (ex: 'temp/image1.jpg').
        :type key: str
        :return: L'URL publique permettant d'accéder à l'image stockée.
        :rtype: str
        :raises StorageError: Si le transfert échoue en raison du réseau ou d'une erreur d'autorisation.
        """
        pass

class S3Storage(StorageStrategy):
    """
    Implémentation de StorageStrategy pour Amazon S3.
    """
    def __init__(self, client, bucket_name: str):
        """
        Initialise le service S3.

        :param client: Une instance de client boto3 (s3).
        :type client: botocore.client.S3
        :param bucket_name: Le nom du bucket cible.
        :type bucket_name: str
        """
        self.client = client
        self.bucket = bucket_name

    def upload(self, image_bytes: bytes, key: str) -> str:
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=image_bytes,
                ContentType="image/jpeg"
            )
            presigned_url = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=3600
            )
            logger.info(f"Image uploadée sur S3 avec succès: {key}")
            return presigned_url
        except (BotoCoreError, ClientError) as e:
            logger.error(f"Erreur AWS S3 lors de l'upload: {e}", exc_info=True)
            raise StorageError("Échec de l'upload vers Amazon S3.") from e

class TmpfilesStorage(StorageStrategy):
    """
    Implémentation de StorageStrategy utilisant l'API publique temporaire tmpfiles.org.
    Idéal pour le développement local sans credentials AWS.
    """
    def upload(self, image_bytes: bytes, key: str) -> str:
        try:
            filename = key.split("/")[-1]
            resp = requests.post(
                "https://tmpfiles.org/api/v1/upload",
                files={"file": (filename, image_bytes, "image/jpeg")},
                timeout=30
            )
            
            if resp.status_code != 200:
                raise StorageError(f"tmpfiles.org a retourné le code HTTP {resp.status_code}")
            
            raw_url = resp.json().get("data", {}).get("url", "")
            if not raw_url:
                raise StorageError("L'URL retournée par tmpfiles.org est vide.")
                
            public_url = raw_url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
            if public_url.startswith("http://"):
                public_url = public_url.replace("http://", "https://", 1)
                
            logger.info(f"Image uploadée sur tmpfiles.org avec succès: {filename}")
            return public_url
            
        except requests.RequestException as e:
            logger.error(f"Erreur réseau vers tmpfiles.org: {e}", exc_info=True)
            raise StorageError("Échec de communication réseau avec le service de stockage temporaire.") from e

class StorageService:
    """
    Service frontal pour gérer le stockage asynchrone / abstrait.
    S'appuie sur le patron de conception Strategy (StorageStrategy).
    """
    def __init__(self, strategy: StorageStrategy):
        """
        Initialise le service de stockage avec la stratégie désirée.

        :param strategy: L'implémentation concrète de stockage à utiliser.
        :type strategy: StorageStrategy
        """
        self._strategy = strategy
        
    def upload_image(self, image_bytes: bytes, key: str) -> str:
        """
        Uploade une image via la stratégie active.

        :param image_bytes: Le binaire de l'image.
        :type image_bytes: bytes
        :param key: Identifiant/chemin cible de l'image.
        :type key: str
        :return: Une URL publique permettant d'accéder au fichier.
        :rtype: str
        :raises StorageError: En cas d'échec de la stratégie.
        """
        return self._strategy.upload(image_bytes, key)
