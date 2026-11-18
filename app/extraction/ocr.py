"""OCR for images (PNG, JPG/JPEG) using the open-source Tesseract engine."""

from pathlib import Path

import pytesseract
from PIL import Image, ImageOps, UnidentifiedImageError

from app.extraction.errors import ExtractionError

OCR_TIMEOUT_SECONDS = 60


def extract_image_text(path: Path, language: str = "eng") -> str:
    """Run OCR on an image file and return the recognised text."""
    try:
        with Image.open(path) as source:
            source.load()
            image = _prepare(source)
        return pytesseract.image_to_string(
            image, lang=language, timeout=OCR_TIMEOUT_SECONDS
        ).strip()
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError) as exc:
        raise ExtractionError("This file is not a valid image or is corrupted.") from exc
    except pytesseract.TesseractNotFoundError as exc:
        raise ExtractionError("The OCR engine (Tesseract) is not installed on the server.") from exc
    except pytesseract.TesseractError as exc:
        raise ExtractionError("The OCR engine failed to read this image.") from exc
    except RuntimeError as exc:  # pytesseract signals a timeout with a RuntimeError
        raise ExtractionError("OCR took too long on this image and was stopped.") from exc


def _prepare(image: Image.Image) -> Image.Image:
    """Apply the EXIF rotation and flatten transparency onto white, as OCR expects."""
    image = ImageOps.exif_transpose(image)
    if image.mode in ("RGBA", "LA", "P"):
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, "white")
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background
    return image.convert("RGB")
