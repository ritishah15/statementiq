import os
import hashlib
import fitz  # PyMuPDF
from typing import Dict, Any, List

class PDFDetector:
    """Detects whether a PDF is DIGITAL (text-based), SCANNED (image-based), MIXED, or UNKNOWN."""

    @staticmethod
    def calculate_file_hash(content: bytes) -> str:
        """Computes SHA-256 hash of document binary content to identify duplicates."""
        return hashlib.sha256(content).hexdigest()

    @staticmethod
    def detect_page(page: fitz.Page, page_num: int = 1) -> Dict[str, Any]:
        """Performs page-level inspection to determine if an individual page is DIGITAL, SCANNED, or UNKNOWN."""
        try:
            text = page.get_text("text").strip()
            words = page.get_text("words")
            images = page.get_images()
            try:
                drawings = page.get_drawings()
                draw_count = len(drawings)
            except Exception:
                draw_count = 0

            char_count = len(text)
            word_count = len(words)
            img_count = len(images)

            if char_count >= 60 and word_count >= 10:
                page_type = "DIGITAL"
                confidence = 0.98
                explanation = f"Page contains extractable digital text ({char_count} chars, {word_count} words)."
            elif (img_count > 0 or draw_count > 0) and char_count < 60:
                page_type = "SCANNED"
                confidence = 0.95
                explanation = f"Page primarily contains visual/graphic elements ({img_count} image(s), {draw_count} drawing(s)) and requires OCR."
            elif char_count == 0 and img_count == 0 and draw_count == 0:
                page_type = "UNKNOWN"
                confidence = 0.10
                explanation = "Extraction is insufficient to determine page type (completely empty page stream)."
            elif char_count < 20 and img_count == 0:
                page_type = "UNKNOWN"
                confidence = 0.20
                explanation = "Extraction is insufficient to determine page type (negligible text and no graphics found)."
            else:
                page_type = "UNKNOWN"
                confidence = 0.40
                explanation = f"Insufficient text ({char_count} chars) to determine page type."

            return {
                "page_number": page_num,
                "type": page_type,
                "char_count": char_count,
                "word_count": word_count,
                "image_count": img_count,
                "confidence": confidence,
                "explanation": explanation
            }
        except Exception as e:
            return {
                "page_number": page_num,
                "type": "UNKNOWN",
                "char_count": 0,
                "word_count": 0,
                "image_count": 0,
                "confidence": 0.0,
                "explanation": f"Page inspection error: {str(e)}"
            }

    @staticmethod
    def detect(file_path: str) -> Dict[str, Any]:
        """Performs immediate deep inspection of the PDF using PyMuPDF to classify as DIGITAL, SCANNED, MIXED, or UNKNOWN."""
        # 1. Existence and empty file validation
        if not os.path.exists(file_path):
            return {
                "pdf_type": "UNKNOWN",
                "confidence": 0.0,
                "text_density_score": 0.0,
                "page_count": 0,
                "digital_pages": 0,
                "scanned_pages": 0,
                "unknown_pages": 0,
                "ocr_required": False,
                "reasons": ["File not found on disk."],
                "explanation": "File does not exist on disk.",
                "page_analysis": []
            }

        file_size = os.path.getsize(file_path)
        if file_size == 0:
            return {
                "pdf_type": "UNKNOWN",
                "confidence": 0.0,
                "text_density_score": 0.0,
                "page_count": 0,
                "digital_pages": 0,
                "scanned_pages": 0,
                "unknown_pages": 0,
                "ocr_required": False,
                "reasons": ["Empty document: The uploaded PDF file is 0 bytes."],
                "explanation": "Empty Document: File size is 0 bytes.",
                "page_analysis": []
            }

        # 2. Check for PDF header signature (%PDF-)
        try:
            with open(file_path, "rb") as f:
                header = f.read(5)
            if header != b"%PDF-":
                return {
                    "pdf_type": "UNKNOWN",
                    "confidence": 0.0,
                    "text_density_score": 0.0,
                    "page_count": 0,
                    "digital_pages": 0,
                    "scanned_pages": 0,
                    "unknown_pages": 0,
                    "ocr_required": False,
                    "reasons": ["Invalid file format: Missing '%PDF-' header signature."],
                    "explanation": "Unsupported / Invalid Format: File is not a valid PDF document.",
                    "page_analysis": []
                }
        except Exception as e:
            return {
                "pdf_type": "UNKNOWN",
                "confidence": 0.0,
                "text_density_score": 0.0,
                "page_count": 0,
                "digital_pages": 0,
                "scanned_pages": 0,
                "unknown_pages": 0,
                "ocr_required": False,
                "reasons": [f"Cannot read file header: {str(e)}"],
                "explanation": f"Corrupted Document: {str(e)}",
                "page_analysis": []
            }

        # 3. Open with PyMuPDF
        try:
            doc = fitz.open(file_path)
        except fitz.FileDataError as fde:
            return {
                "pdf_type": "UNKNOWN",
                "confidence": 0.0,
                "text_density_score": 0.0,
                "page_count": 0,
                "digital_pages": 0,
                "scanned_pages": 0,
                "unknown_pages": 0,
                "ocr_required": False,
                "reasons": [f"Corrupted PDF document: {str(fde)}"],
                "explanation": "Corrupted PDF: Unable to parse document structure or cross-reference table.",
                "page_analysis": []
            }
        except Exception as e:
            return {
                "pdf_type": "UNKNOWN",
                "confidence": 0.0,
                "text_density_score": 0.0,
                "page_count": 0,
                "digital_pages": 0,
                "scanned_pages": 0,
                "unknown_pages": 0,
                "ocr_required": False,
                "reasons": [f"PDF open error: {str(e)}"],
                "explanation": f"Corrupted PDF: {str(e)}",
                "page_analysis": []
            }

        try:
            # 4. Check for Password Protection / Encryption
            if doc.is_encrypted:
                doc.close()
                return {
                    "pdf_type": "UNKNOWN",
                    "confidence": 0.0,
                    "text_density_score": 0.0,
                    "page_count": 0,
                    "digital_pages": 0,
                    "scanned_pages": 0,
                    "unknown_pages": 0,
                    "ocr_required": False,
                    "reasons": ["Password-protected PDF: This document is encrypted and requires a password to open."],
                    "explanation": "Password-Protected PDF: This statement is encrypted and requires a password to open.",
                    "page_analysis": []
                }

            total_pages = len(doc)
            if total_pages == 0:
                doc.close()
                return {
                    "pdf_type": "UNKNOWN",
                    "confidence": 0.0,
                    "text_density_score": 0.0,
                    "page_count": 0,
                    "digital_pages": 0,
                    "scanned_pages": 0,
                    "unknown_pages": 0,
                    "ocr_required": False,
                    "reasons": ["Empty document: PDF contains 0 pages."],
                    "explanation": "Empty Document: The uploaded PDF has no pages.",
                    "page_analysis": []
                }

            # 5. Page-level checks for Digital vs Scanned vs Unknown
            page_analysis: List[Dict[str, Any]] = []
            digital_pages = 0
            scanned_pages = 0
            unknown_pages = 0
            total_chars = 0
            total_words = 0
            sample_texts = []

            for page_num in range(total_pages):
                page = doc[page_num]
                p_info = PDFDetector.detect_page(page, page_num + 1)
                page_analysis.append(p_info)

                p_type = p_info["type"]
                if p_type == "DIGITAL":
                    digital_pages += 1
                elif p_type == "SCANNED":
                    scanned_pages += 1
                else:
                    unknown_pages += 1

                total_chars += p_info["char_count"]
                total_words += p_info["word_count"]

                text = page.get_text("text").strip()
                if text and len(sample_texts) < 2:
                    sample_texts.append(text[:200])

            doc.close()

            avg_chars = total_chars / total_pages
            avg_words = total_words / total_pages

            # Document-level classification based on page-level types
            if unknown_pages == total_pages:
                pdf_type = "UNKNOWN"
                ocr_required = False
                confidence = 0.0
                explanation = "Extraction is insufficient to determine the document type across all pages."
            elif digital_pages == total_pages:
                pdf_type = "DIGITAL"
                ocr_required = False
                confidence = 0.98
                explanation = f"Digital PDF: All {total_pages} page(s) contain searchable digital text (avg {int(avg_chars)} chars, {int(avg_words)} words/page)."
            elif scanned_pages == total_pages:
                pdf_type = "SCANNED"
                ocr_required = True
                confidence = 0.96
                explanation = f"Scanned PDF: All {total_pages} page(s) lack extractable text and require Tesseract OCR."
            elif digital_pages > 0 and (scanned_pages > 0 or unknown_pages > 0):
                pdf_type = "MIXED"
                ocr_required = True
                confidence = 0.92
                explanation = f"Mixed PDF: {digital_pages} page(s) are digital text; {scanned_pages} page(s) are scanned; {unknown_pages} page(s) undetermined."
            else:
                pdf_type = "SCANNED"
                ocr_required = True
                confidence = 0.90
                explanation = f"Scanned PDF: {scanned_pages} page(s) require OCR."

            return {
                "pdf_type": pdf_type,
                "confidence": confidence,
                "text_density_score": round(avg_chars, 1),
                "page_count": total_pages,
                "digital_pages": digital_pages,
                "scanned_pages": scanned_pages,
                "unknown_pages": unknown_pages,
                "ocr_required": ocr_required,
                "explanation": explanation,
                "reasons": [explanation],
                "page_analysis": page_analysis,
                "sample_preview": " ... ".join(sample_texts)[:300] if sample_texts else ""
            }

        except Exception as e:
            if 'doc' in locals() and not doc.is_closed:
                doc.close()
            return {
                "pdf_type": "UNKNOWN",
                "confidence": 0.0,
                "text_density_score": 0.0,
                "page_count": 0,
                "digital_pages": 0,
                "scanned_pages": 0,
                "ocr_required": False,
                "reasons": [f"Detection processing error: {str(e)}"],
                "explanation": f"Document detection error: {str(e)}",
                "page_analysis": []
            }
