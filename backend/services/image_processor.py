import io
from PIL import Image
from typing import Dict, Optional, Union
from config import logger

class ImageProcessingError(Exception):
    """
    Exception métier levée si le traitement de l'image (rognage, compression)
    échoue en raison d'un format corrompu ou illisible.
    """
    pass

# Ratios de crop supportés
CROP_RATIOS: Dict[str, Optional[float]] = {
    "original": None,
    "1:1": 1.0,
    "4:5": 4.0 / 5.0,
    "16:9": 16.0 / 9.0,
}

def compress_image(image_bytes: bytes, max_size_kb: int = 800) -> bytes:
    """
    Compresse une image pour s'assurer qu'elle occupe moins de mémoire que spécifié,
    en la redimensionnant au préalable si elle dépasse 1080px de large/haut.

    :param image_bytes: Les octets bruts de l'image (ex: reçus via FormData ou S3).
    :type image_bytes: bytes
    :param max_size_kb: La limite de poids en kilo-octets (par défaut: 800).
    :type max_size_kb: int
    :return: Les nouveaux octets représentant l'image compressée (format JPEG).
    :rtype: bytes
    :raises ImageProcessingError: Si l'image source est corrompue et illisible par Pillow.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        
        # S'assurer d'un format compatible pour le JPEG
        if img.mode != 'RGB':
            img = img.convert('RGB')
            
        max_dimension = 1080
        if img.width > max_dimension or img.height > max_dimension:
            # Redimensionnement proportionnel (Lanczos pour haute qualité)
            img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
            logger.debug(f"Image redimensionnée à {img.width}x{img.height}")
            
        output = io.BytesIO()
        quality = 90
        img.save(output, format='JPEG', quality=quality)
        
        # Réduire itérativement la qualité jusqu'à passer sous la barre des `max_size_kb`
        while output.tell() > max_size_kb * 1024 and quality > 10:
            output = io.BytesIO()
            quality -= 5
            img.save(output, format='JPEG', quality=quality)
            
        logger.info(f"Image compressée: {output.tell() / 1024:.2f} KB (Qualité finale: {quality})")
        return output.getvalue()
        
    except OSError as e:
        logger.error(f"Erreur Pillow lors de la lecture des octets bruts: {e}", exc_info=True)
        raise ImageProcessingError("Format d'image invalide ou données corrompues.") from e
    except Exception as e:
        logger.critical(f"Erreur système critique lors de la compression d'image: {e}", exc_info=True)
        raise ImageProcessingError("Une exception inattendue s'est produite durant la compression.") from e

def crop_image(image_bytes: bytes, ratio: str, position: Optional[Dict[str, int]] = None) -> bytes:
    """
    Rogne (crop) une image pour qu'elle corresponde exactement à un ratio spécifique, 
    tout en préservant le point d'intérêt selon les coordonnées (X,Y) paramétrées.

    :param image_bytes: Les octets bruts de l'image source.
    :type image_bytes: bytes
    :param ratio: Le nom du ratio ciblé ("1:1", "4:5", "16:9", ou "original").
    :type ratio: str
    :param position: Dictionnaire optionnel indiquant le point d'ancrage en pourcentage {"x": int, "y": int}. 
                     (Défaut: {"x": 50, "y": 50} pour cibler le centre).
    :type position: Optional[Dict[str, int]]
    :return: Les octets de l'image rognée en JPEG. 
             Si 'original' est passé, renvoie les octets source sans retouche.
    :rtype: bytes
    :raises ImageProcessingError: Si l'image source est corrompue et illisible par Pillow.
    """
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
        
        # Validation stricte des coordonnées de position entre 0 et 100
        pos_x = max(0, min(100, position.get("x", 50))) / 100.0
        pos_y = max(0, min(100, position.get("y", 50))) / 100.0

        if img_ratio > target_ratio:
            # L'image est proportionnellement trop large -> Rognage gauche/droite
            new_width = int(img.height * target_ratio)
            max_left = img.width - new_width
            left = int(max_left * pos_x)
            img = img.crop((left, 0, left + new_width, img.height))
            
        elif img_ratio < target_ratio:
            # L'image est proportionnellement trop haute -> Rognage haut/bas
            new_height = int(img.width / target_ratio)
            max_top = img.height - new_height
            top = int(max_top * pos_y)
            img = img.crop((0, top, img.width, top + new_height))

        output = io.BytesIO()
        img.save(output, format='JPEG', quality=95)
        logger.info(f"Image rognée au ratio '{ratio}', cible d'ancrage {position} -> Dimensions finales {img.width}x{img.height}")
        return output.getvalue()

    except OSError as e:
        logger.error(f"Échec de lecture de l'image pour le crop: {e}", exc_info=True)
        raise ImageProcessingError("Image illisible, le rognage a échoué.") from e
    except Exception as e:
        logger.critical(f"Exception système grave lors du rognage de l'image: {e}", exc_info=True)
        raise ImageProcessingError("Une erreur fatale est survenue pendant l'ajustement du ratio.") from e
