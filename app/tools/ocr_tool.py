import io
import os
import logging
from typing import Optional
from PIL import Image
import pytesseract
import pdf2image
from google.cloud import vision

from app.config import settings

logger = logging.getLogger(__name__)

class OCRTool:
    def __init__(self):
        self.use_google_vision = bool(settings.GOOGLE_APPLICATION_CREDENTIALS)
        if self.use_google_vision:
            try:
                self.vision_client = vision.ImageAnnotatorClient()
            except Exception as e:
                logger.warning(f"Failed to init Google Vision client: {e}. Falling back to Tesseract.")
                self.use_google_vision = False

    def extract_text(self, file_content: bytes, mime_type: str) -> str:
        """Determines method and extracts text from image or PDF bytes."""
        try:
            if self.use_google_vision:
                return self._extract_google_vision(file_content, mime_type)
            else:
                return self._extract_tesseract(file_content, mime_type)
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return ""

    def _extract_google_vision(self, content: bytes, mime_type: str) -> str:
        """Extract text using Google Cloud Vision."""
        # Note: For PDF/TIFF files, GCV requires 'async_batch_annotate_files' and GCS storage usually,
        # but for single page images 'annotate_image' works. 
        # For simplicity in this demo, if PDF, convert to image first, then send to GCV 
        # or use Tesseract for PDF if GCV PDF flow is too complex for this snippet.
        
        images = []
        if mime_type == 'application/pdf':
            images = pdf2image.convert_from_bytes(content)
        else:
            images = [Image.open(io.BytesIO(content))]

        full_text = ""
        for img in images:
            # Convert PIL image to bytes for GCV
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            content_bytes = img_byte_arr.getvalue()

            image = vision.Image(content=content_bytes)
            response = self.vision_client.text_detection(image=image)
            
            if response.error.message:
                raise Exception(f"{response.error.message}")
                
            texts = response.text_annotations
            if texts:
                full_text += texts[0].description + "\n\n"
        
        return full_text

    def _extract_tesseract(self, content: bytes, mime_type: str) -> str:
        """Extract text using Tesseract OCR."""
        images = []
        if mime_type == 'application/pdf':
            images = pdf2image.convert_from_bytes(content)
        else:
            images = [Image.open(io.BytesIO(content))]
            
        full_text = ""
        for img in images:
            text = pytesseract.image_to_string(img)
            full_text += text + "\n\n"
            
        return full_text

ocr_tool = OCRTool()
