import pytest
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

from services.image_processor import compress_image, crop_image, ImageProcessingError

def test_compress_image_success():
    """Vérifie que la compression d'une fausse image lève bien une erreur explicite, et non un crash silencieux."""
    corrupted_bytes = b"ceci n'est pas une image valide, c'est du texte brut"
    with pytest.raises(ImageProcessingError) as exc_info:
        compress_image(corrupted_bytes)
    assert "Format d'image invalide" in str(exc_info.value)

def test_crop_image_invalid_ratio():
    """Un ratio original ou inconnu doit retourner les octets intacts."""
    test_bytes = b"fake bytes"
    result = crop_image(test_bytes, ratio="original")
    assert result == test_bytes

    result_unknown = crop_image(test_bytes, ratio="ratio_imaginaire")
    assert result_unknown == test_bytes

def test_crop_image_corrupted():
    """Tenter un vrai crop sur une fausse image lève une erreur."""
    corrupted_bytes = b"bad image"
    with pytest.raises(ImageProcessingError) as exc_info:
        crop_image(corrupted_bytes, ratio="1:1")
    assert "Image illisible" in str(exc_info.value)
