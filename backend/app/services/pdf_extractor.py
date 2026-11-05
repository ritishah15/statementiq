import os
import fitz  # PyMuPDF
import pdfplumber
from typing import List, Dict, Any, Optional
from app.services.pdf_detector import PDFDetector
from app.services.ocr_processor import OCRProcessor

class PDFExtractor:
    """Orchestrates PDF text and table extraction for DIGITAL, SCANNED, and MIXED files."""

    def __init__(self):
        self.ocr_processor = OCRProcessor()

    def extract_content(self, file_path: str) -> Dict[str, Any]:
        """Detects PDF type and extracts all pages, text streams, and table structures."""
        detection = PDFDetector.detect(file_path)
        pdf_type = detection.get("pdf_type", "UNKNOWN")

        if pdf_type == "UNKNOWN":
            return {
                "detection": detection,
                "is_scanned": False,
                "pages": [],
                "raw_tables": [],
                "full_text": "",
                "raw_ocr": "",
                "is_valid": False,
                "error_message": detection.get("explanation", "Cannot extract content from UNKNOWN or invalid document.")
            }

        extracted_pages = []
        raw_tables = []
        full_text_list = []
        raw_ocr_list = []

        if pdf_type == "SCANNED":
            # Scanned / Image-based PDF -> Full Tesseract OCR pipeline
            ocr_results = self.ocr_processor.process_pdf(file_path)
            for page in ocr_results:
                extracted_pages.append({
                    "page_number": page["page_number"],
                    "text": page["text"],
                    "raw_ocr_text": page.get("raw_ocr_text", page["text"]),
                    "words": page.get("words", []),
                    "method": "OCR (Tesseract)",
                    "rotation_applied": page.get("rotation_applied", 0)
                })
                full_text_list.append(page["text"])
                raw_ocr_list.append(page.get("raw_ocr_text", page["text"]))

        elif pdf_type == "MIXED":
            # Mixed PDF -> Page-level hybrid extraction
            page_analysis = detection.get("page_analysis", [])
            page_map = {p["page_number"]: p["type"] for p in page_analysis}

            doc = fitz.open(file_path)
            for page_num in range(len(doc)):
                p_idx = page_num + 1
                p_type = page_map.get(p_idx, "DIGITAL")
                page = doc[page_num]

                if p_type == "DIGITAL":
                    page_text = page.get_text("text")
                    raw_words = page.get_text("words")
                    formatted_words = [
                        {'text': w[4], 'left': int(w[0] * 300 / 72), 'top': int(w[1] * 300 / 72), 'width': int((w[2] - w[0]) * 300 / 72), 'height': int((w[3] - w[1]) * 300 / 72)}
                        for w in raw_words if w[4].strip()
                    ]
                    extracted_pages.append({
                        "page_number": p_idx,
                        "text": page_text,
                        "raw_ocr_text": "",
                        "words": formatted_words,
                        "method": "Digital Stream (PyMuPDF)"
                    })
                    full_text_list.append(page_text)
                else:
                    # High resolution 300 DPI render for OCR
                    pix = page.get_pixmap(matrix=fitz.Matrix(300 / 72, 300 / 72))
                    from PIL import Image
                    import pytesseract
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    preprocessed, rot_angle = self.ocr_processor.preprocess_image(img, handle_rotation=True)
                    custom_config = r'--oem 3'
                    try:
                        page_text = pytesseract.image_to_string(preprocessed, config=custom_config)
                    except Exception:
                        page_text = pytesseract.image_to_string(preprocessed)

                    words = []
                    try:
                        data = pytesseract.image_to_data(preprocessed, config=custom_config, output_type=pytesseract.Output.DICT)
                        for i in range(len(data['text'])):
                            t = data['text'][i].strip()
                            if t:
                                words.append({
                                    'text': t,
                                    'left': data['left'][i],
                                    'top': data['top'][i],
                                    'width': data['width'][i],
                                    'height': data['height'][i]
                                })
                    except Exception:
                        pass

                    extracted_pages.append({
                        "page_number": p_idx,
                        "text": page_text,
                        "raw_ocr_text": page_text,
                        "words": words,
                        "method": "OCR (Tesseract - Scanned Page)",
                        "rotation_applied": rot_angle
                    })
                    full_text_list.append(page_text)
                    raw_ocr_list.append(page_text)
            doc.close()

            # Attempt table extraction with pdfplumber for digital pages
            try:
                with pdfplumber.open(file_path) as pdf:
                    for page_idx, page in enumerate(pdf.pages):
                        if page_map.get(page_idx + 1) == "DIGITAL":
                            tables = page.extract_tables()
                            for t in tables:
                                if t and len(t) > 1:
                                    raw_tables.append({
                                        "page_number": page_idx + 1,
                                        "table": t
                                    })
            except Exception:
                pass

        else:
            # Digital / Text-based PDF -> PyMuPDF & pdfplumber pipeline
            try:
                doc = fitz.open(file_path)
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    page_text = page.get_text("text")
                    raw_words = page.get_text("words")
                    formatted_words = [
                        {'text': w[4], 'left': int(w[0] * 300 / 72), 'top': int(w[1] * 300 / 72), 'width': int((w[2] - w[0]) * 300 / 72), 'height': int((w[3] - w[1]) * 300 / 72)}
                        for w in raw_words if w[4].strip()
                    ]
                    extracted_pages.append({
                        "page_number": page_num + 1,
                        "text": page_text,
                        "raw_ocr_text": "",
                        "words": formatted_words,
                        "method": "Digital Stream (PyMuPDF)"
                    })
                    full_text_list.append(page_text)
                doc.close()

                # Table grid extraction via pdfplumber
                try:
                    with pdfplumber.open(file_path) as pdf:
                        for page_idx, page in enumerate(pdf.pages):
                            tables = page.extract_tables()
                            for t in tables:
                                if t and len(t) > 1:
                                    raw_tables.append({
                                        "page_number": page_idx + 1,
                                        "table": t
                                    })
                except Exception:
                    pass

            except Exception as e:
                # Fallback to OCR if digital reading fails
                if self.ocr_processor.is_tesseract_available():
                    ocr_results = self.ocr_processor.process_pdf(file_path)
                    for page in ocr_results:
                        extracted_pages.append({
                            "page_number": page["page_number"],
                            "text": page["text"],
                            "raw_ocr_text": page.get("raw_ocr_text", page["text"]),
                            "method": "OCR (Fallback)"
                        })
                        full_text_list.append(page["text"])
                        raw_ocr_list.append(page.get("raw_ocr_text", page["text"]))

        full_text = "\n\n--- PAGE BREAK ---\n\n".join(full_text_list)
        raw_ocr = "\n\n--- OCR PAGE BREAK ---\n\n".join(raw_ocr_list)

        return {
            "detection": detection,
            "is_scanned": pdf_type in ["SCANNED", "MIXED"],
            "pages": extracted_pages,
            "raw_tables": raw_tables,
            "full_text": full_text,
            "raw_ocr": raw_ocr,
            "is_valid": True
        }
