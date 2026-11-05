import os
import io
import sys
import openpyxl
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.pdf_detector import PDFDetector
from app.services.pdf_extractor import PDFExtractor
from app.services.transaction_parser import TransactionParser
from app.services.rule_classifier import RuleClassifier
from app.services.ml_classifier import MLClassifier
from app.services.classification_engine import ClassificationEngine
from app.services.reconciliation import ReconciliationService
from app.services.export_service import ExportService
from app.schemas.statement import AccountDetails, Transaction

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_statements"
DIGITAL_PDF = SAMPLE_DIR / "hdfc_digital_statement.pdf"
SCANNED_PDF = SAMPLE_DIR / "scanned_statement.pdf"

def test_pdf_detector():
    """Verifies text-based vs scanned PDF auto-detection."""
    assert DIGITAL_PDF.exists(), "Digital PDF sample must exist"
    assert SCANNED_PDF.exists(), "Scanned PDF sample must exist"

    # Test digital detection
    res_digital = PDFDetector.detect(str(DIGITAL_PDF))
    assert res_digital["pdf_type"].upper() == "DIGITAL"
    assert res_digital["ocr_required"] is False
    assert res_digital["confidence"] >= 0.70

    # Test scanned detection
    res_scanned = PDFDetector.detect(str(SCANNED_PDF))
    assert res_scanned["pdf_type"].upper() == "SCANNED"
    assert res_scanned["ocr_required"] is True

def test_rule_classifier():
    """Verifies deterministic keyword-based transaction classification with high-priority merchants."""
    classifier = RuleClassifier()

    test_cases = [
        ("POS SWIGGY BANGALORE IN", "Food & Dining"),
        ("UPI RAJ GROCERY STORE", "Food & Dining"),
        ("POS AMAZON INDIA RETAIL", "Shopping"),
        ("POS UBER INDIA TRIP", "Travel & Transport"),
        ("UPI PHARMACY MEDICAL STORE", "Healthcare"),
        ("NEFT SALARY CREDIT TECHCORP", "Salary"),
        ("BANK SERVICE CHARGES", "Bank Charges"),
        ("ACH CREDIT TECHCORP SALARY MAY 2024", "Salary"),
        ("ATM CASH WDL HDFC INDIRANAGAR", "ATM Withdrawal"),
        ("ZERODHA BROKING LTD EQUITY ADD FUNDS", "Investments")
    ]

    for desc, expected_cat in test_cases:
        cat, conf, kw = classifier.classify(desc)
        assert cat == expected_cat, f"For description '{desc}', expected '{expected_cat}' but got '{cat}'"
        assert conf >= 0.85, f"Confidence for '{desc}' was {conf}, expected >= 0.85"

def test_ml_classifier():
    """Verifies traditional supervised ML classification using TF-IDF + Naive Bayes."""
    ml = MLClassifier()
    assert ml.is_trained is True

    # Test prediction on unseen / varied phrasing
    cat, conf = ml.predict("Zomato foods limited online dinner order")
    assert cat == "Food & Dining"
    assert conf > 0.30

    cat, conf = ml.predict("Direct deposit payroll tech employee monthly")
    assert cat == "Salary"

    info = ml.get_info()
    assert info["is_trained"] is True
    assert len(info["classes"]) >= 10
    assert info["vocabulary_size"] > 50

def test_extraction_and_reconciliation():
    """Verifies end-to-end PDF extraction and balance reconciliation."""
    extractor = PDFExtractor()
    parser = TransactionParser()
    classifier_engine = ClassificationEngine()

    content = extractor.extract_content(str(DIGITAL_PDF))
    assert len(content["pages"]) >= 2
    assert content["is_scanned"] is False

    acc = parser.extract_account_details(content["full_text"])
    assert "HDFC" in acc.bank_name
    assert "50100492817291" in acc.account_number
    assert acc.ifsc_code == "HDFC0001234"
    assert acc.opening_balance == 45200.00
    assert acc.closing_balance == 128450.00

    txns = parser.extract_transactions(content["raw_tables"], content["full_text"])
    assert len(txns) >= 15

    classified_txns, stats = classifier_engine.classify_all(txns)
    assert stats.total_classified == len(txns)
    assert stats.rule_based_count > 0

    recon = ReconciliationService.reconcile(acc, classified_txns)
    assert recon.total_transactions == len(txns)
    assert recon.opening_balance == 45200.00
    assert recon.closing_balance == 128450.00
    # Formula: 45,200 (open) + 1,73,125 (cr) - 89,875 (dr) = 1,28,450 (closing)
    assert recon.is_reconciled is True
    assert recon.discrepancy == 0.0
    assert recon.reconciliation_status == "Reconciled"

def test_user_sample_statement_metadata():
    """Verifies that the user's 12-transaction sample statement metadata extracts exact values."""
    user_samples = list(Path(__file__).resolve().parent.parent.glob("uploads/*sample_text_based_bank_statement.pdf"))
    if not user_samples:
        return

    sample_pdf = user_samples[0]
    extractor = PDFExtractor()
    parser = TransactionParser()
    content = extractor.extract_content(str(sample_pdf))

    acc = parser.extract_account_details(content["full_text"])
    assert acc.bank_name == "Sample National Bank", f"Expected 'Sample National Bank', got '{acc.bank_name}'"
    assert acc.account_holder == "Aarav Mehta", f"Expected 'Aarav Mehta', got '{acc.account_holder}'"
    assert acc.account_number == "XXXXXX4821", f"Expected 'XXXXXX4821', got '{acc.account_number}'"
    assert acc.ifsc_code == "SNBK0000123", f"Expected 'SNBK0000123', got '{acc.ifsc_code}'"
    assert acc.opening_balance == 25000.00, f"Expected 25000.00, got {acc.opening_balance}"
    assert acc.closing_balance == 61150.00, f"Expected 61150.00, got {acc.closing_balance}"

    txns = parser.extract_transactions(content["raw_tables"], content["full_text"])
    assert len(txns) == 12, f"Expected 12 transactions, got {len(txns)}"

    # Reconcile user statement: 25000.0 + 56000.0 (Credits) - 19850.0 (Debits) = 61150.0
    recon = ReconciliationService.reconcile(acc, txns)
    assert recon.is_reconciled is True
    assert recon.discrepancy == 0.0
    assert recon.calculated_closing_balance == 61150.00

def test_excel_and_csv_export():
    """Verifies Excel (with 3 distinct sheets) and CSV export deliverables."""
    acc = AccountDetails(
        bank_name="Sample National Bank",
        account_holder="Aarav Mehta",
        account_number="XXXXXX4821",
        ifsc_code="SNBK0000123",
        opening_balance=25000.0,
        closing_balance=61150.0
    )
    txns = [
        Transaction(id="TXN-1", date="2024-05-01", description="SALARY CREDIT", debit=0.0, credit=50000.0, balance=75000.0, category="Salary", classification_method="Rule-Based", confidence=0.98),
        Transaction(id="TXN-2", date="2024-05-02", description="SWIGGY ORDER", debit=500.0, credit=0.0, balance=74500.0, category="Food & Dining", classification_method="Rule-Based", confidence=0.95)
    ]
    recon = ReconciliationService.reconcile(acc, txns)

    # Excel with 3 distinct sheets
    excel_stream = ExportService.generate_excel(acc, txns, recon)
    wb = openpyxl.load_workbook(excel_stream)
    assert "Account Details" in wb.sheetnames
    assert "Transactions" in wb.sheetnames
    assert "Summary" in wb.sheetnames

    # CSV with required fields
    csv_str = ExportService.generate_csv(txns)
    lines = csv_str.strip().splitlines()
    assert lines[0] == "Date,Description,Debit,Credit,Balance,Category,Classification Method"
    assert "SALARY CREDIT" in csv_str
    assert "SWIGGY ORDER" in csv_str
