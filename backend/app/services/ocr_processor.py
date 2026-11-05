import os
import re
import fitz  # PyMuPDF
import cv2
import numpy as np
from PIL import Image
import pytesseract
from typing import List, Dict, Any, Tuple
from app.config import TESSERACT_CMD

class OCRProcessor:
    """Renders scanned PDF pages to high-DPI images, applies computer vision preprocessing, and executes Tesseract OCR."""

    def __init__(self):
        if TESSERACT_CMD:
            pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

    @staticmethod
    def is_tesseract_available() -> bool:
        """Verifies whether the Tesseract OCR engine is installed and callable."""
        try:
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    @staticmethod
    def deskew(image: np.ndarray) -> np.ndarray:
        """Calculates skew angle of text lines and deskews the image using affine rotation."""
        try:
            coords = np.column_stack(np.where(image < 200))
            if len(coords) < 100:
                return image
            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = -(90 + angle)
            elif angle > 45:
                angle = 90 - angle
            else:
                angle = -angle

            if 0.25 < abs(angle) < 15.0:
                (h, w) = image.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
                return rotated
        except Exception:
            pass
        return image

    @classmethod
    def fix_rotation(cls, image: np.ndarray) -> Tuple[np.ndarray, int]:
        """Detects 90, 180, or 270 degree page rotations via Tesseract OSD and rotates image upright."""
        rot_angle = 0
        try:
            osd = pytesseract.image_to_osd(image)
            rot_match = re.search(r'(?i)Rotate:\s*(\d+)', osd)
            if rot_match:
                rot_angle = int(rot_match.group(1)) % 360
                if rot_angle == 90:
                    image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
                elif rot_angle == 180:
                    image = cv2.rotate(image, cv2.ROTATE_180)
                elif rot_angle == 270:
                    image = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        except Exception:
            # Fallback if OSD fails: check aspect ratio or test vertical lines
            pass
        return image, rot_angle

    @classmethod
    def preprocess_image(cls, pil_img: Image.Image, handle_rotation: bool = True) -> Tuple[np.ndarray, int]:
        """
        Converts PIL image to OpenCV format, scales low-res images, handles rotation,
        applies CLAHE contrast enhancement, deskewing, and Otsu thresholding.
        """
        open_cv_image = np.array(pil_img)
        if len(open_cv_image.shape) == 3:
            gray = cv2.cvtColor(open_cv_image, cv2.COLOR_RGB2GRAY)
        else:
            gray = open_cv_image

        rot_angle = 0
        if handle_rotation:
            gray, rot_angle = cls.fix_rotation(gray)

        # Scale low-resolution scans (< 1400 px width or height) up to ~300 DPI equivalent
        h, w = gray.shape[:2]
        if w < 1400 or h < 1400:
            scale_factor = min(2.0, 1800.0 / max(w, h))
            if scale_factor > 1.1:
                gray = cv2.resize(gray, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_CUBIC)

        # Deskew small angles
        deskewed = cls.deskew(gray)

        # Contrast enhancement via CLAHE to improve faint numbers and decimal dots
        try:
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(deskewed)
        except Exception:
            enhanced = deskewed

        # Bilateral / Gaussian smoothing to suppress noise while preserving decimal dots and comma boundaries
        denoised = cv2.GaussianBlur(enhanced, (3, 3), 0)

        # Otsu's optimal thresholding
        _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return thresh, rot_angle

    def process_pdf(self, file_path: str, max_pages: int = 10) -> List[Dict[str, Any]]:
        """Processes each page of the scanned PDF with high-resolution 300 DPI rendering and Tesseract OCR."""
        if not self.is_tesseract_available():
            raise RuntimeError("Tesseract OCR engine is not installed or not in PATH.")

        doc = fitz.open(file_path)
        pages_result = []

        total = min(len(doc), max_pages)
        for page_num in range(total):
            page = doc[page_num]

            # Render at 300 DPI (zoom 300/72 = 4.1667)
            zoom = 300 / 72
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)

            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            preprocessed, rot_angle = self.preprocess_image(img, handle_rotation=True)

            custom_config = r'--oem 3'
            try:
                ocr_text = pytesseract.image_to_string(preprocessed, config=custom_config)
            except Exception:
                ocr_text = pytesseract.image_to_string(preprocessed)

            words = []
            try:
                data = pytesseract.image_to_data(preprocessed, config=custom_config, output_type=pytesseract.Output.DICT)
                n = len(data['text'])
                for i in range(n):
                    t = data['text'][i].strip()
                    if t:
                        words.append({
                            'text': t,
                            'left': data['left'][i],
                            'top': data['top'][i],
                            'width': data['width'][i],
                            'height': data['height'][i],
                            'conf': float(data['conf'][i]) if 'conf' in data else 0.0
                        })
            except Exception:
                pass

            pages_result.append({
                "page_number": page_num + 1,
                "text": ocr_text,
                "raw_ocr_text": ocr_text,
                "words": words,
                "char_count": len(ocr_text),
                "words_count": len(ocr_text.split()),
                "width": pix.width,
                "height": pix.height,
                "rotation_applied": rot_angle
            })

        doc.close()
        return pages_result
