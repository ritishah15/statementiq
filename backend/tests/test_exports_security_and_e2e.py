import io
import os
import csv
import json
import openpyxl
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.api.routes import statement_store, _save_sessions, _load_sessions
from app.schemas.statement import AccountDetails, Transaction, ReconciliationSummary
from app.services.export_service import ExportService
from app.utils.helpers import (
    sanitize_spreadsheet_value,
    sanitize_filename,
    validate_pdf_content,
    mask_account_number,
    mask_sensitive_log
)


@pytest.fixture
def client():
    return TestClient(app)


def test_sanitize_spreadsheet_value_formula_injection():
    """TASK 4: Test formula injection prevention for =, +, -, @, \\t, \\r."""
    # Malicious injection payloads
    assert sanitize_spreadsheet_value("=SUM(A1:A10)") == "'=SUM(A1:A10)"
    assert sanitize_spreadsheet_value("+cmd|' /C calc'!A0") == "'+cmd|' /C calc'!A0"
    assert sanitize_spreadsheet_value("-1+1") == "'-1+1"
    assert sanitize_spreadsheet_value("@HYPERLINK('http://evil.com')") == "'@HYPERLINK('http://evil.com')"
    assert sanitize_spreadsheet_value("\tTAB_INJECTION") == "'\tTAB_INJECTION"
    assert sanitize_spreadsheet_value("\rCR_INJECTION") == "'\rCR_INJECTION"

    # Numbers must NOT be quoted so they remain valid mathematical values
    assert sanitize_spreadsheet_value(123) == 123
    assert sanitize_spreadsheet_value(45.67) == 45.67

    # Normal text without injection prefix
    assert sanitize_spreadsheet_value("SALARY FOR OCTOBER") == "SALARY FOR OCTOBER"
    assert sanitize_spreadsheet_value("UPI/SWIGGY/123456") == "UPI/SWIGGY/123456"
    assert sanitize_spreadsheet_value("") == ""
    assert sanitize_spreadsheet_value(None) == ""


def test_sanitize_filename_path_traversal():
    """TASK 5: Test filename sanitization and path traversal prevention."""
    assert sanitize_filename("../../etc/passwd.pdf") == "passwd.pdf"
    assert sanitize_filename("..\\..\\windows\\system32\\calc.pdf") == "calc.pdf"
    assert sanitize_filename("foo/bar/statement.pdf") == "statement.pdf"
    assert sanitize_filename("statement\0malicious.pdf") == "statementmalicious.pdf"
    assert sanitize_filename("my statement 2026.pdf") == "my statement 2026.pdf"
    assert sanitize_filename("statement") == "statement.pdf"


def test_validate_pdf_content_security():
    """TASK 5: Test file upload security with magic bytes, size limits, and corrupted files."""
    # Empty file
    valid, err = validate_pdf_content(b"")
    assert not valid
    assert "empty" in err.lower()

    # File size limit (> 25MB)
    huge_file = b"%PDF-1.4 " + b"0" * (26 * 1024 * 1024)
    valid, err = validate_pdf_content(huge_file, max_size_mb=25)
    assert not valid
    assert "exceeds maximum limit" in err.lower()

    # Invalid PDF signature (e.g. text or image file masquerading as .pdf)
    fake_pdf = b"Hello, this is just plain text, not a PDF."
    valid, err = validate_pdf_content(fake_pdf)
    assert not valid
    assert "invalid file signature" in err.lower()

    # Malformed PDF with signature but corrupted structure
    corrupt_pdf = b"%PDF-1.5 this is truncated garbage that cannot be parsed"
    valid, err = validate_pdf_content(corrupt_pdf)
    assert not valid
    assert "corrupted" in err.lower() or "malformed" in err.lower()


def test_mask_sensitive_log_and_account():
    """TASK 5: Test masking account numbers in logs and views."""
    assert mask_account_number("123456789012") == "XXXXXX9012"
    assert mask_account_number("Not Found") == "Not Found"

    raw_log = "Processing transaction for account 50100234567890 with amount 12500"
    masked = mask_sensitive_log(raw_log)
    assert "50100234567890" not in masked
    assert "5010******7890" in masked


def test_excel_export_seven_sheets():
    """TASK 1: Test 7-sheet Excel export, formatting, totals, and column widths."""
    acc = AccountDetails(
        bank_name="HDFC Bank",
        account_holder="Aditi Sharma",
        account_number="50100234567890",
        masked_account_number="XXXXXX7890",
        ifsc_code="HDFC0000123",
        statement_period_start="2026-04-01",
        statement_period_end="2026-04-30",
        opening_balance=50000.0,
        closing_balance=125000.0,
        currency="INR"
    )

    t1 = Transaction(
        id="TXN-1",
        date="2026-04-02",
        description="=HYPERLINK('http://bad.com') SALARY CREDIT",
        debit=0.0,
        credit=100000.0,
        balance=150000.0,
        category="Salary",
        classification_method="Rule-Based",
        confidence=0.98,
        review_status="Verified",
        explanation={
            "category": "Salary",
            "method": "Rule-Based",
            "confidence": 0.98,
            "matched_keyword": "SALARY",
            "reason": "Matched keyword 'SALARY'"
        }
    )

    t2 = Transaction(
        id="TXN-2",
        date="2026-04-05",
        description="SWIGGY BANGALORE",
        debit=1500.0,
        credit=0.0,
        balance=148500.0,
        category="Food & Dining",
        classification_method="Rule-Based",
        confidence=0.95,
        review_status="Verified",
        explanation={
            "category": "Food & Dining",
            "method": "Rule-Based",
            "confidence": 0.95,
            "matched_keyword": "SWIGGY",
            "reason": "Matched keyword 'SWIGGY'"
        }
    )

    t3 = Transaction(
        id="TXN-3",
        date="2026-04-10",
        description="UNKNOWN MERCHANT X",
        debit=23500.0,
        credit=0.0,
        balance=125000.0,
        category="Others",
        classification_method="ML Classifier",
        confidence=0.35,
        review_status="Needs Review",
        validation_flags=["low_ml_confidence"],
        explanation={
            "category": "Others",
            "method": "ML Classifier",
            "confidence": 0.35,
            "reason": "Low ML prediction confidence"
        }
    )

    recon = ReconciliationSummary(
        total_transactions=3,
        total_debits=25000.0,
        total_credits=100000.0,
        net_flow=75000.0,
        opening_balance=50000.0,
        closing_balance=125000.0,
        calculated_closing_balance=125000.0,
        discrepancy=0.0,
        is_reconciled=True,
        reconciliation_status="Reconciled",
        notes="Opening Balance + Credits - Debits exactly matches Closing Balance."
    )

    excel_buf = ExportService.generate_excel(acc, [t1, t2, t3], recon, source_filename="statement.pdf")
    assert excel_buf is not None

    wb = openpyxl.load_workbook(excel_buf)
    sheet_names = wb.sheetnames
    expected_sheets = [
        "Account Details",
        "Transactions",
        "Summary",
        "Income by Category",
        "Expense by Category",
        "Review Flags",
        "Classification Explanations"
    ]
    for s in expected_sheets:
        assert s in sheet_names, f"Missing sheet: {s}"

    # Verify formula injection prevented in Transactions sheet
    ws_txns = wb["Transactions"]
    # t1 description was '=HYPERLINK...', must be sanitized to ''=HYPERLINK...'
    val = ws_txns.cell(row=2, column=3).value
    assert val.startswith("'=HYPERLINK")

    # Verify Total row in Transactions sheet
    total_row = 5
    assert ws_txns.cell(row=total_row, column=1).value == "Total"
    assert ws_txns.cell(row=total_row, column=4).value == 25000.0  # Total debits
    assert ws_txns.cell(row=total_row, column=5).value == 100000.0  # Total credits

    # Verify Review Flags sheet contains TXN-3
    ws_flags = wb["Review Flags"]
    flag_txn_id = ws_flags.cell(row=4, column=1).value
    assert flag_txn_id == "TXN-3"


def test_csv_export_single_and_multi():
    """TASK 2 & 3: Test single and combined CSV exports."""
    t1 = Transaction(
        id="TXN-1",
        date="2026-04-02",
        description="@CMD PAY",
        debit=100.0,
        credit=0.0,
        balance=9900.0,
        category="Shopping",
        classification_method="Rule-Based",
        confidence=0.9
    )

    csv_data = ExportService.generate_csv([t1], source_filename="test.pdf", statement_id="STMT-123")
    reader = list(csv.reader(io.StringIO(csv_data)))
    assert reader[0][0] == "Statement ID"
    assert reader[1][0] == "STMT-123"
    assert reader[1][1] == "test.pdf"
    # Formula injection sanitized
    assert reader[1][4].startswith("'@CMD PAY")

    # Multi statement combined CSV
    stmt_data = [
        {
            "statement_id": "STMT-001",
            "filename": "stmt1.pdf",
            "transactions": [t1]
        }
    ]
    comb_csv = ExportService.generate_combined_csv(stmt_data)
    reader_comb = list(csv.reader(io.StringIO(comb_csv)))
    assert reader_comb[0][0] == "Statement ID"
    assert reader_comb[1][0] == "STMT-001"
    assert reader_comb[1][1] == "stmt1.pdf"


def test_end_to_end_api_workflow(client):
    """TASK 8: Comprehensive end-to-end API test workflow."""
    # 1. Check system info
    res = client.get("/api/system")
    assert res.status_code == 200
    assert "TF-IDF + Naive Bayes" in res.json()["ml_model"]

    # 2. Check classifier evaluation endpoint
    eval_res = client.get("/api/classifier/evaluate")
    assert eval_res.status_code == 200
    eval_data = eval_res.json()
    assert "accuracy" in eval_data
    assert "confusion_matrix" in eval_data

    # 3. Load sample statement
    load_res = client.post("/api/sample-statements/hdfc_digital_statement.pdf/load")
    assert load_res.status_code == 200
    meta = load_res.json()
    statement_id = meta["statement_id"]
    assert meta["pdf_type"] in ["DIGITAL", "SCANNED", "MIXED"]

    # 4. Duplicate upload check: Re-loading same sample must detect duplicate SHA-256
    dup_res = client.post("/api/sample-statements/hdfc_digital_statement.pdf/load")
    assert dup_res.status_code == 200
    assert dup_res.json()["is_duplicate"] is True

    # 5. Process statement
    proc_res = client.post(f"/api/statements/{statement_id}/process")
    assert proc_res.status_code == 200
    data = proc_res.json()
    assert data["transaction_count"] > 0
    assert "account_details" in data

    # 6. Classify statement
    class_res = client.post(f"/api/statements/{statement_id}/classify")
    assert class_res.status_code == 200
    classified = class_res.json()
    assert "classification_stats" in classified
    assert len(classified["transactions"]) > 0

    first_txn = classified["transactions"][0]
    assert first_txn["category"] is not None
    assert "explanation" in first_txn

    # 7. Edit transaction and verify recalculation + audit trail
    orig_cat = first_txn["category"]
    edit_payload = {"category": "Investments"}
    update_res = client.put(f"/api/statements/{statement_id}/transactions/{first_txn['id']}", json=edit_payload)
    assert update_res.status_code == 200
    updated_txn = update_res.json()
    assert updated_txn["category"] == "Investments"
    assert updated_txn["review_status"] == "Corrected"
    assert len(updated_txn["audit_history"]) >= 1
    assert updated_txn["audit_history"][0]["field"] == "category"
    assert updated_txn["audit_history"][0]["old_value"] == orig_cat

    # 8. Export Single Excel
    excel_res = client.get(f"/api/statements/{statement_id}/export/excel")
    assert excel_res.status_code == 200
    assert excel_res.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    # 9. Export Single CSV
    csv_res = client.get(f"/api/statements/{statement_id}/export/csv")
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers["content-type"]

    # 10. Multi-statement Excel export
    multi_excel = client.get("/api/statements/export/excel")
    assert multi_excel.status_code == 200

    # 11. Multi-statement CSV export
    multi_csv = client.get("/api/statements/export/csv")
    assert multi_csv.status_code == 200

    # 12. Session persistence test
    _save_sessions()
    _load_sessions()
    assert statement_id in statement_store
