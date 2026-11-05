import os
import io
import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import fitz
from app.services.pdf_detector import PDFDetector
from app.services.pdf_extractor import PDFExtractor
from app.services.transaction_parser import TransactionParser
from app.services.reconciliation import ReconciliationService

BASE_DIR = Path(__file__).resolve().parent.parent
SAMPLE_DIR = BASE_DIR / "sample_statements"
TEMP_TEST_DIR = BASE_DIR / "tests" / "test_temp"
TEMP_TEST_DIR.mkdir(parents=True, exist_ok=True)

DIGITAL_PDF = SAMPLE_DIR / "hdfc_digital_statement.pdf"
SCANNED_PDF = SAMPLE_DIR / "scanned_statement.pdf"

def create_mixed_test_pdf() -> str:
    """Generates a 2-page mixed PDF: Page 1 with digital text, Page 2 with image/no text."""
    path = TEMP_TEST_DIR / "mixed_test_document.pdf"
    doc = fitz.open()

    # Page 1: Digital text
    p1 = doc.new_page(width=595, height=842)
    p1.insert_text((50, 50), "Sample Bank Statement - Digital Stream Page\nAccount No: 123456789\nDate: 2024-05-01 Description: Salary Credit Amount: 50000.00 Balance: 100000.00\nDate: 2024-05-02 Description: Grocery Store Amount: 1200.00 Balance: 98800.00\nEnd of digital page narration and ledger entries.", fontsize=11)

    # Page 2: Blank / scanned placeholder (no text)
    p2 = doc.new_page(width=595, height=842)
    # Draw a rectangle to simulate an image/stamp without text
    p2.draw_rect(fitz.Rect(100, 100, 400, 400), color=(0.2, 0.2, 0.2), fill=(0.9, 0.9, 0.9))

    doc.save(str(path))
    doc.close()
    return str(path)

def create_encrypted_pdf() -> str:
    """Generates a password-protected PDF to test encryption detection."""
    path = TEMP_TEST_DIR / "encrypted_test_document.pdf"
    doc = fitz.open()
    p = doc.new_page()
    p.insert_text((50, 50), "Confidential Banking Information", fontsize=12)
    # Save with user/owner password
    perm = int(
        fitz.PDF_PERM_ACCESSIBILITY |
        fitz.PDF_PERM_PRINT |
        fitz.PDF_PERM_COPY |
        fitz.PDF_PERM_ANNOTATE
    )
    doc.save(str(path), encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="secret123", owner_pw="admin123", permissions=perm)
    doc.close()
    return str(path)

def create_corrupted_pdf() -> str:
    """Generates an invalid/corrupted PDF file."""
    path = TEMP_TEST_DIR / "corrupted_test_document.pdf"
    with open(path, "wb") as f:
        f.write(b"%PDF-1.4 Corrupted header and invalid stream content garbage...")
    return str(path)

def create_empty_pdf() -> str:
    """Generates a 0-byte file."""
    path = TEMP_TEST_DIR / "empty_test_document.pdf"
    with open(path, "wb") as f:
        f.write(b"")
    return str(path)


def test_1_text_based_pdf():
    print("--- 1. Testing Text-Based (DIGITAL) PDF ---", flush=True)
    res = PDFDetector.detect(str(DIGITAL_PDF))
    assert res["pdf_type"] == "DIGITAL", f"Expected DIGITAL, got {res['pdf_type']}"
    assert res["confidence"] >= 0.90
    assert res["ocr_required"] is False
    assert res["page_count"] >= 2
    assert res["digital_pages"] == res["page_count"]
    print(f"    [OK] Detected as {res['pdf_type']} ({res['page_count']} pages, {res['confidence']*100}% confidence)")

def test_2_scanned_pdf():
    print("--- 2. Testing Scanned (IMAGE-BASED) PDF ---", flush=True)
    res = PDFDetector.detect(str(SCANNED_PDF))
    assert res["pdf_type"] == "SCANNED", f"Expected SCANNED, got {res['pdf_type']}"
    assert res["ocr_required"] is True
    assert res["scanned_pages"] == res["page_count"]
    print(f"    [OK] Detected as {res['pdf_type']} (OCR Required: {res['ocr_required']})")

def test_3_mixed_pdf():
    print("--- 3. Testing Mixed (TEXT + SCANNED) PDF ---", flush=True)
    mixed_path = create_mixed_test_pdf()
    res = PDFDetector.detect(mixed_path)
    assert res["pdf_type"] == "MIXED", f"Expected MIXED, got {res['pdf_type']}"
    assert res["ocr_required"] is True
    assert res["digital_pages"] == 1
    assert res["scanned_pages"] == 1
    print(f"    [OK] Detected as {res['pdf_type']} ({res['digital_pages']} digital / {res['scanned_pages']} scanned pages)")

def test_4_multi_page_pdf():
    print("--- 4. Testing Multi-Page Bank Statement ---", flush=True)
    res = PDFDetector.detect(str(DIGITAL_PDF))
    assert res["page_count"] > 1, f"Expected multi-page, got {res['page_count']}"
    assert len(res["page_analysis"]) == res["page_count"]
    print(f"    [OK] Verified {res['page_count']} individual page analyses")

def test_5_repeated_uploads_duplicate_detection():
    print("--- 5. Testing Repeated Uploads & SHA-256 Hash Duplicate Detection ---", flush=True)
    content1 = DIGITAL_PDF.read_bytes()
    hash1 = PDFDetector.calculate_file_hash(content1)
    content2 = DIGITAL_PDF.read_bytes()
    hash2 = PDFDetector.calculate_file_hash(content2)
    assert hash1 == hash2, "Identical files must have identical SHA-256 hashes"
    assert len(hash1) == 64
    print(f"    [OK] SHA-256 Hash verified: {hash1[:16]}... (Exact match detected)")

def test_6_invalid_corrupted_empty_encrypted_pdfs():
    print("--- 6. Testing Error Handling (Corrupted, Encrypted, Empty) ---", flush=True)
    # A. Encrypted PDF
    enc_path = create_encrypted_pdf()
    res_enc = PDFDetector.detect(enc_path)
    assert res_enc["pdf_type"] == "UNKNOWN"
    assert "password-protected" in res_enc["explanation"].lower()
    print(f"    [OK] Encrypted PDF handled: {res_enc['explanation']}")

    # B. Corrupted PDF
    corrupt_path = create_corrupted_pdf()
    res_corrupt = PDFDetector.detect(corrupt_path)
    assert res_corrupt["pdf_type"] == "UNKNOWN"
    assert "Corrupted" in res_corrupt["explanation"] or "Invalid" in res_corrupt["explanation"]
    print(f"    [OK] Corrupted PDF handled: {res_corrupt['explanation']}")

    # C. Empty PDF (0 bytes)
    empty_path = create_empty_pdf()
    res_empty = PDFDetector.detect(empty_path)
    assert res_empty["pdf_type"] == "UNKNOWN"
    assert "Empty" in res_empty["explanation"]
    print(f"    [OK] Empty PDF handled: {res_empty['explanation']}")

if __name__ == "__main__":
    print("\n========================================================")
    print("STARTING INGESTION & AUTO-DETECTION TEST SUITE")
    print("========================================================\n")
    test_1_text_based_pdf()
    test_2_scanned_pdf()
    test_3_mixed_pdf()
    test_4_multi_page_pdf()
    test_5_repeated_uploads_duplicate_detection()
    test_6_invalid_corrupted_empty_encrypted_pdfs()
    print("\n========================================================")
    print("ALL 6 INGESTION & DETECTION TESTS PASSED 100%!")
    print("========================================================\n")
