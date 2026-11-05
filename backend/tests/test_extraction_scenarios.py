import os
import sys
import fitz  # PyMuPDF
import cv2
import numpy as np
from PIL import Image, ImageDraw
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.services.pdf_detector import PDFDetector
from app.services.pdf_extractor import PDFExtractor
from app.services.transaction_parser import TransactionParser
from app.services.data_validator import DataValidator

SAMPLE_DIR = BASE_DIR / "sample_statements"
TEMP_DIR = BASE_DIR / "tests" / "test_temp"
TEMP_DIR.mkdir(parents=True, exist_ok=True)


def test_01_digital_statement_extraction():
    """TASK 2 & 5: Digital PDF extraction verifying row order, account details, and transaction columns."""
    digital_pdf = SAMPLE_DIR / "hdfc_digital_statement.pdf"
    assert digital_pdf.exists(), "hdfc_digital_statement.pdf must exist"

    det = PDFDetector.detect(str(digital_pdf))
    assert det["pdf_type"] == "DIGITAL"
    assert det["ocr_required"] is False
    assert det["page_count"] == 2

    extractor = PDFExtractor()
    res = extractor.extract_content(str(digital_pdf))
    assert res["is_valid"] is True
    assert res["is_scanned"] is False
    assert len(res["pages"]) == 2

    parser = TransactionParser()
    acc = parser.extract_account_details(res["full_text"])
    assert acc.bank_name == "HDFC Bank"
    assert "SINGHANIA" in (acc.account_holder or "").upper()
    assert acc.account_number == "50100492817291"
    assert acc.masked_account_number == "XXXXXX7291"
    assert acc.ifsc_code == "HDFC0001234"
    assert acc.opening_balance == 45200.00
    assert acc.closing_balance == 128450.00

    txns = parser.extract_transactions(res["raw_tables"], res["full_text"], pages=res.get("pages"))
    assert len(txns) == 17, f"Expected 17 transactions, got {len(txns)}"

    # Verify first transaction date, description, debit, credit, balance
    t0 = txns[0]
    assert t0.date == "2024-05-01"
    assert "SALARY" in t0.description.upper()
    assert t0.credit == 120000.00
    assert t0.debit == 0.00
    assert t0.balance == 165200.00

    # Verify chronological sequence
    dates = [t.date for t in txns]
    assert dates[0] <= dates[-1], "Transactions must preserve order"


def test_02_scanned_statement_ocr_extraction():
    """TASK 3 & 4: Scanned statement OCR with deskewing and numeric accuracy."""
    scanned_pdf = SAMPLE_DIR / "scanned_statement.pdf"
    assert scanned_pdf.exists(), "scanned_statement.pdf must exist"

    det = PDFDetector.detect(str(scanned_pdf))
    assert det["pdf_type"] == "SCANNED"
    assert det["ocr_required"] is True

    extractor = PDFExtractor()
    res = extractor.extract_content(str(scanned_pdf))
    assert res["is_valid"] is True
    assert res["is_scanned"] is True
    assert len(res["pages"]) >= 2
    assert "raw_ocr" in res and len(res["raw_ocr"]) > 0

    parser = TransactionParser()
    acc = parser.extract_account_details(res["full_text"])
    assert acc.bank_name == "HDFC Bank"
    assert acc.opening_balance == 45200.00
    assert acc.closing_balance == 128450.00

    txns = parser.extract_transactions(res["raw_tables"], res["full_text"], pages=res.get("pages"))
    assert len(txns) == 17, f"Expected 17 transactions from scan, got {len(txns)}"

    validated = DataValidator.validate_all(txns, opening_balance=acc.opening_balance)

    # Verify no simultaneous debit & credit
    for t in validated:
        assert not (t.debit > 0 and t.credit > 0), f"Transaction has both debit and credit: {t.description}"

    # Verify salary transaction
    salary = next(t for t in validated if "SALARY" in t.description.upper())
    assert salary.credit == 120000.00
    assert salary.debit == 0.00
    assert salary.balance == 165200.00

    # Verify electricity bill
    elec = next(t for t in validated if "BESCOM" in t.description.upper())
    assert elec.debit == 2400.00
    assert elec.credit == 0.00


def test_03_mixed_pdf_page_level_detection_and_extraction():
    """TASK 1: Verify page-level detection on mixed PDF (Page 1 digital text, Page 2 raster scan)."""
    mixed_path = TEMP_DIR / "synthetic_mixed_statement.pdf"
    doc = fitz.open()

    # Page 1: Digital text with clear transaction table
    p1 = doc.new_page(width=595, height=842)
    p1.insert_text(
        (50, 50),
        "ICICI BANK STATEMENT\n"
        "Customer Name: RAHUL SHARMA\n"
        "Account Number: 109283746152\n"
        "IFSC Code: ICIC0001928\n"
        "Opening Balance: 10000.00\n"
        "Closing Balance: 25000.00\n\n"
        "Date Narration Withdrawal Deposit Balance\n"
        "01/05/2024 OPENING BALANCE 0.00 0.00 10000.00\n"
        "02/05/2024 TECHCORP SALARY 0.00 20000.00 30000.00\n"
        "03/05/2024 SWIGGY FOOD ORDER 500.00 0.00 29500.00\n",
        fontsize=11
    )

    # Page 2: Raster scan image
    img = Image.new("RGB", (800, 1100), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((50, 50), "ICICI BANK (SCANNED PAGE 2)\nDate Narration Withdrawal Deposit Balance\n04/05/2024 UBER TRIP 4500.00 0.00 25000.00\n", fill=(0, 0, 0))
    img_path = TEMP_DIR / "temp_page2.png"
    img.save(str(img_path))

    p2 = doc.new_page(width=595, height=842)
    p2.insert_image(fitz.Rect(0, 0, 595, 842), filename=str(img_path))

    doc.save(str(mixed_path))
    doc.close()

    det = PDFDetector.detect(str(mixed_path))
    assert det["pdf_type"] == "MIXED", f"Expected MIXED, got {det['pdf_type']}"
    assert det["page_count"] == 2
    assert det["digital_pages"] == 1
    assert det["scanned_pages"] == 1
    assert det["page_analysis"][0]["type"] == "DIGITAL"
    assert det["page_analysis"][1]["type"] == "SCANNED"

    extractor = PDFExtractor()
    res = extractor.extract_content(str(mixed_path))
    assert res["is_valid"] is True
    assert res["is_scanned"] is True
    assert len(res["pages"]) == 2


def test_04_rotated_scan_handling():
    """TASK 3: Verify 90-degree rotated scan OCR detection and deskewing."""
    rotated_path = TEMP_DIR / "synthetic_rotated_90_statement.pdf"

    img = Image.new("RGB", (1000, 1400), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    text = (
        "STATE BANK OF INDIA\n"
        "Customer Name: KAVITA PATEL\n"
        "Account Number: 20918273645\n"
        "IFSC Code: SBIN0001234\n"
        "Opening Balance: 50000.00\n"
        "Date Narration Withdrawal Deposit Balance\n"
        "01/05/2024 SALARY CREDIT 0.00 45000.00 95000.00\n"
        "05/05/2024 RENT PAYMENT 15000.00 0.00 80000.00\n"
    )
    draw.text((80, 80), text, fill=(0, 0, 0))

    rotated_img = img.rotate(90, expand=True)
    rotated_img_path = TEMP_DIR / "rotated_page.png"
    rotated_img.save(str(rotated_img_path))

    doc = fitz.open()
    p = doc.new_page(width=842, height=595)
    p.insert_image(fitz.Rect(0, 0, 842, 595), filename=str(rotated_img_path))
    doc.save(str(rotated_path))
    doc.close()

    extractor = PDFExtractor()
    res = extractor.extract_content(str(rotated_path))
    assert res["is_valid"] is True
    assert len(res["full_text"]) > 20
    assert "BANK" in res["full_text"].upper()


def test_05_wrapped_descriptions_and_multiline_transactions():
    """TASK 2 & 4: Verify multi-line wrapped transaction descriptions."""
    wrapped_path = TEMP_DIR / "synthetic_wrapped_statement.pdf"
    doc = fitz.open()
    p = doc.new_page(width=595, height=842)

    content = (
        "AXIS BANK - CURRENT ACCOUNT\n"
        "Customer Name: ENTERPRISE LOGISTICS PVT LTD\n"
        "Account Number: 91802918273645\n"
        "IFSC Code: UTIB0000456\n"
        "Opening Balance: 100000.00\n\n"
        "Date Narration Withdrawal Deposit Balance\n"
        "01/05/2024 NEFT INWARD REMITTANCE FROM TECHCORP 0.00 50000.00 150000.00\n"
        " SOFTWARE SERVICES INVOICE 99482\n"
        " PAYMENT FOR MAY CONSULTING\n"
        "03/05/2024 CLOUD HOSTING SERVICES 12500.00 0.00 137500.00\n"
        " AWS SERVER CLOUD CHARGES AP-SOUTH\n"
    )
    p.insert_text((50, 50), content, fontsize=10)
    doc.save(str(wrapped_path))
    doc.close()

    extractor = PDFExtractor()
    res = extractor.extract_content(str(wrapped_path))
    parser = TransactionParser()

    txns = parser.extract_transactions(res["raw_tables"], res["full_text"], pages=res.get("pages"))
    assert len(txns) >= 2

    t0 = txns[0]
    assert t0.date == "2024-05-01"
    assert "SOFTWARE SERVICES" in t0.description.upper() or "TECHCORP" in t0.description.upper()
    assert t0.credit == 50000.00
    assert t0.balance == 150000.00

    t1 = txns[1]
    assert t1.date == "2024-05-03"
    assert "AWS" in t1.description.upper() or "HOSTING" in t1.description.upper()
    assert t1.debit == 12500.00
    assert t1.balance == 137500.00


def test_06_missing_balance_column_calculation():
    """TASK 4: Verify extraction on statement with no Balance column (calculated from opening balance)."""
    missing_bal_path = TEMP_DIR / "synthetic_no_balance_statement.pdf"
    doc = fitz.open()
    p = doc.new_page(width=595, height=842)

    header_lines = [
        "KOTAK MAHINDRA BANK",
        "Customer Name: ARJUN MEHTA",
        "Account Number: 7091827364",
        "IFSC Code: KKBK0000123",
        "Opening Balance: 20000.00\n"
    ]
    p.insert_text((50, 50), "\n".join(header_lines), fontsize=11)

    y = 150
    p.insert_text((50, y), "Date", fontsize=10)
    p.insert_text((150, y), "Description", fontsize=10)
    p.insert_text((360, y), "Withdrawal", fontsize=10)
    p.insert_text((470, y), "Deposit", fontsize=10)

    rows = [
        ("01/05/2024", "SALARY CREDIT", "0.00", "80000.00"),
        ("02/05/2024", "GROCERY STORE", "2500.00", "0.00"),
        ("03/05/2024", "FUEL STATION", "3500.00", "0.00")
    ]

    for d, desc, deb, cred in rows:
        y += 25
        p.insert_text((50, y), d, fontsize=10)
        p.insert_text((150, y), desc, fontsize=10)
        p.insert_text((360, y), deb, fontsize=10)
        p.insert_text((470, y), cred, fontsize=10)

    doc.save(str(missing_bal_path))
    doc.close()

    extractor = PDFExtractor()
    res = extractor.extract_content(str(missing_bal_path))
    parser = TransactionParser()

    acc = parser.extract_account_details(res["full_text"])
    assert acc.opening_balance == 20000.00

    txns = parser.extract_transactions(res["raw_tables"], res["full_text"], pages=res.get("pages"), opening_balance=acc.opening_balance)
    assert len(txns) == 3

    assert txns[0].balance == 100000.00
    assert txns[1].balance == 97500.00
    assert txns[2].balance == 94000.00


def test_07_multipage_statement_continuity():
    """TASK 2: Verify multi-page statement extraction and continuity across 3 pages."""
    multipage_path = TEMP_DIR / "synthetic_3page_statement.pdf"
    doc = fitz.open()

    for p_idx in range(3):
        p = doc.new_page(width=595, height=842)
        day1 = p_idx * 2 + 1
        day2 = p_idx * 2 + 2
        p.insert_text((50, 50), f"BANK OF BARODA - PAGE {p_idx + 1} OF 3\nCustomer Name: SURESH KUMAR\nAccount Number: 40918273645\nOpening Balance: 50000.00\n", fontsize=10)

        y = 130
        p.insert_text((50, y), "Date", fontsize=10)
        p.insert_text((140, y), "Description", fontsize=10)
        p.insert_text((320, y), "Withdrawal", fontsize=10)
        p.insert_text((410, y), "Deposit", fontsize=10)
        p.insert_text((500, y), "Balance", fontsize=10)

        y += 25
        p.insert_text((50, y), f"0{day1}/05/2024", fontsize=10)
        p.insert_text((140, y), f"TRANSACTION DAY {day1}", fontsize=10)
        p.insert_text((320, y), "1000.00", fontsize=10)
        p.insert_text((410, y), "0.00", fontsize=10)
        p.insert_text((500, y), f"{50000 - day1 * 1000}.00", fontsize=10)

        y += 25
        p.insert_text((50, y), f"0{day2}/05/2024", fontsize=10)
        p.insert_text((140, y), f"TRANSACTION DAY {day2}", fontsize=10)
        p.insert_text((320, y), "1000.00", fontsize=10)
        p.insert_text((410, y), "0.00", fontsize=10)
        p.insert_text((500, y), f"{50000 - day2 * 1000}.00", fontsize=10)

    doc.save(str(multipage_path))
    doc.close()

    extractor = PDFExtractor()
    res = extractor.extract_content(str(multipage_path))
    assert len(res["pages"]) == 3

    parser = TransactionParser()
    txns = parser.extract_transactions(res["raw_tables"], res["full_text"], pages=res.get("pages"))
    assert len(txns) == 6, f"Expected 6 transactions across 3 pages, got {len(txns)}"

    for i in range(len(txns) - 1):
        assert txns[i].date <= txns[i + 1].date


def test_08_error_handling_corrupt_empty_password_no_txns():
    """TASK 6: Verify error handling for corrupt, empty, encrypted, and 0-transaction documents."""
    # 1. Empty 0-byte file
    empty_path = TEMP_DIR / "zero_byte.pdf"
    empty_path.write_bytes(b"")
    det_empty = PDFDetector.detect(str(empty_path))
    assert det_empty["pdf_type"] == "UNKNOWN"
    assert "Empty Document" in det_empty["explanation"]

    # 2. Corrupt non-PDF file
    corrupt_path = TEMP_DIR / "corrupt.pdf"
    corrupt_path.write_bytes(b"This is completely invalid binary gibberish not a PDF")
    det_corrupt = PDFDetector.detect(str(corrupt_path))
    assert det_corrupt["pdf_type"] == "UNKNOWN"
    assert "Unsupported" in det_corrupt["explanation"] or "Corrupted" in det_corrupt["explanation"]

    # 3. Password-protected PDF
    pw_path = TEMP_DIR / "protected.pdf"
    doc = fitz.open()
    p = doc.new_page()
    p.insert_text((50, 50), "Confidential Protected Bank Statement")
    doc.save(str(pw_path), encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="pass123", owner_pw="admin123")
    doc.close()

    det_pw = PDFDetector.detect(str(pw_path))
    assert det_pw["pdf_type"] == "UNKNOWN"
    assert "Password-Protected" in det_pw["explanation"]

    # 4. Zero transactions PDF
    brochure_path = TEMP_DIR / "flyer_no_txns.pdf"
    doc = fitz.open()
    p = doc.new_page()
    p.insert_text((50, 50), "Welcome to HDFC Bank! Explore our new credit card offers with zero annual fee.")
    doc.save(str(brochure_path))
    doc.close()

    extractor = PDFExtractor()
    res = extractor.extract_content(str(brochure_path))
    parser = TransactionParser()
    txns = parser.extract_transactions(res["raw_tables"], res["full_text"], pages=res.get("pages"))
    assert len(txns) == 0, "No transactions should be found in a flyer"


if __name__ == "__main__":
    print("Running test 1: Digital statement extraction...")
    test_01_digital_statement_extraction()
    print("PASS: Digital statement extraction")

    print("Running test 2: Scanned statement OCR extraction...")
    test_02_scanned_statement_ocr_extraction()
    print("PASS: Scanned statement OCR extraction")

    print("Running test 3: Mixed PDF page-level detection & extraction...")
    test_03_mixed_pdf_page_level_detection_and_extraction()
    print("PASS: Mixed PDF page-level detection & extraction")

    print("Running test 4: Rotated scan handling...")
    test_04_rotated_scan_handling()
    print("PASS: Rotated scan handling")

    print("Running test 5: Wrapped descriptions & multiline transactions...")
    test_05_wrapped_descriptions_and_multiline_transactions()
    print("PASS: Wrapped descriptions & multiline transactions")

    print("Running test 6: Missing balance column calculation...")
    test_06_missing_balance_column_calculation()
    print("PASS: Missing balance column calculation")

    print("Running test 7: Multi-page statement continuity...")
    test_07_multipage_statement_continuity()
    print("PASS: Multi-page statement continuity")

    print("Running test 8: Error handling corrupt/empty/password/zero-txns...")
    test_08_error_handling_corrupt_empty_password_no_txns()
    print("PASS: Error handling scenarios")

    print("\nALL 8 EXTRACTION SCENARIOS PASSED 100%!")
