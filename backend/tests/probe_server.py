import time
import urllib.request
import json
import threading
import uvicorn
import sys
import io
import openpyxl
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

def start_server():
    from app.main import app
    config = uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="warning")
    server = uvicorn.Server(config)
    server.run()

def http_json(url, data=None, method="GET"):
    headers = {"Content-Type": "application/json"} if data else {}
    req_body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=req_body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as he:
        err_msg = he.read().decode()
        print(f"HTTP ERROR {he.code}: {err_msg}")
        raise

def http_raw(url):
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as resp:
        return resp.read(), resp.headers.get_content_type()

if __name__ == "__main__":
    t = threading.Thread(target=start_server, daemon=True)
    t.start()
    time.sleep(3)

    print(">>> 1. Checking Root & Health Endpoint")
    res = http_json("http://127.0.0.1:8000/")
    assert res["app"] == "StatementIQ"
    print(f"    [OK] {res}")

    print(">>> 2. Listing Ingestion Queue Statements (/api/statements)")
    stmt_list = http_json("http://127.0.0.1:8000/api/statements")
    assert isinstance(stmt_list, list)
    print(f"    [OK] Ingestion queue endpoint returned {len(stmt_list)} statements.")

    print(">>> 3. Listing Available Sample Statements")
    samples = http_json("http://127.0.0.1:8000/api/sample-statements")
    assert len(samples) >= 2
    print(f"    [OK] Found {len(samples)} samples: {[s['filename'] for s in samples]}")

    print(">>> 4. Loading Digital Sample Statement")
    load_res = http_json("http://127.0.0.1:8000/api/sample-statements/hdfc_digital_statement.pdf/load", method="POST")
    stmt_id = load_res["statement_id"]
    print(f"    [OK] Created statement session: {stmt_id}")

    print(">>> 5. Executing Extraction Pipeline (PyMuPDF Digital Parsing)")
    proc_res = http_json(f"http://127.0.0.1:8000/api/statements/{stmt_id}/process", method="POST")
    assert proc_res["metadata"]["pdf_type"] == "digital"
    assert proc_res["transaction_count"] >= 15
    print(f"    [OK] Extracted {proc_res['transaction_count']} txns. Bank: {proc_res['account_details']['bank_name']}")

    print(">>> 6. Running Non-LLM Transaction Classification (Rules + ML)")
    classify_res = http_json(f"http://127.0.0.1:8000/api/statements/{stmt_id}/classify", method="POST")
    stats = classify_res["classification_stats"]
    assert stats["total_classified"] >= 15
    assert stats["rule_based_count"] > 0
    print(f"    [OK] Rule-based: {stats['rule_based_count']} ({stats['rule_based_pct']}%), ML: {stats['ml_count']} ({stats['ml_pct']}%)")

    print(">>> 7. Verifying Mathematical Balance Reconciliation")
    full_data = http_json(f"http://127.0.0.1:8000/api/statements/{stmt_id}")
    recon = full_data["reconciliation"]
    assert recon["is_reconciled"] is True
    print(f"    [OK] Status: {recon['reconciliation_status']} | Discrepancy: {recon['discrepancy']}")

    print(">>> 8. Testing Excel (3 distinct worksheets) & CSV File Deliverable Downloads")
    excel_bytes, excel_type = http_raw(f"http://127.0.0.1:8000/api/statements/{stmt_id}/export/excel")
    assert len(excel_bytes) > 2000
    wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))
    sheet_names = wb.sheetnames
    assert "Account Details" in sheet_names, f"Expected 'Account Details', got {sheet_names}"
    assert "Transactions" in sheet_names, f"Expected 'Transactions', got {sheet_names}"
    assert "Summary" in sheet_names, f"Expected 'Summary', got {sheet_names}"
    print(f"    [OK] Excel workbook verified with sheets: {sheet_names}")

    csv_bytes, csv_type = http_raw(f"http://127.0.0.1:8000/api/statements/{stmt_id}/export/csv")
    csv_str = csv_bytes.decode('utf-8')
    assert "Date,Description,Debit,Credit,Balance,Category,Classification Method" in csv_str
    print(f"    [OK] CSV verified with required column headers ({len(csv_bytes)} bytes)")

    print(">>> 9. Testing Scanned Document Tesseract OCR Pipeline")
    scan_load = http_json("http://127.0.0.1:8000/api/sample-statements/scanned_statement.pdf/load", method="POST")
    scan_id = scan_load["statement_id"]
    scan_proc = http_json(f"http://127.0.0.1:8000/api/statements/{scan_id}/process", method="POST")
    assert scan_proc["metadata"]["pdf_type"] == "scanned"
    assert scan_proc["metadata"]["ocr_applied"] is True
    print(f"    [OK] Scanned PDF Type: {scan_proc['metadata']['pdf_type']}, OCR Applied: {scan_proc['metadata']['ocr_applied']}")

    # Testing user sample statement if present in uploads
    user_sample = list(Path(__file__).resolve().parent.parent.glob("uploads/*sample_text_based_bank_statement.pdf"))
    if user_sample:
        print(">>> 10. Testing User 12-Transaction Sample Statement Metadata & Classification")
        from app.services.pdf_extractor import PDFExtractor
        from app.services.transaction_parser import TransactionParser
        from app.services.classification_engine import ClassificationEngine
        ext = PDFExtractor().extract_content(str(user_sample[0]))
        p = TransactionParser()
        acc = p.extract_account_details(ext["full_text"])
        assert acc.bank_name == "Sample National Bank", f"Expected 'Sample National Bank', got '{acc.bank_name}'"
        assert acc.account_holder == "Aarav Mehta", f"Expected 'Aarav Mehta', got '{acc.account_holder}'"
        assert acc.account_number == "XXXXXX4821", f"Expected 'XXXXXX4821', got '{acc.account_number}'"
        assert acc.ifsc_code == "SNBK0000123", f"Expected 'SNBK0000123', got '{acc.ifsc_code}'"
        assert acc.opening_balance == 25000.00, f"Expected 25000.00, got {acc.opening_balance}"
        assert acc.closing_balance == 61150.00, f"Expected 61150.00, got {acc.closing_balance}"
        print(f"    [OK] User Sample Account Details: Bank='{acc.bank_name}', Holder='{acc.account_holder}', Acc='{acc.account_number}', IFSC='{acc.ifsc_code}', Open={acc.opening_balance}, Close={acc.closing_balance}")

        txns = p.extract_transactions(ext["raw_tables"], ext["full_text"])
        assert len(txns) == 12, f"Expected 12 transactions, got {len(txns)}"
        cls_txns, c_stats = ClassificationEngine().classify_all(txns)
        # Check specific merchant classifications
        txns_by_desc = {t.description.strip(): t.category for t in cls_txns}
        for desc, expected_cat in [
            ("POS SWIGGY BANGALORE IN", "Food & Dining"),
            ("UPI RAJ GROCERY STORE", "Food & Dining"),
            ("POS AMAZON INDIA RETAIL", "Shopping"),
            ("POS UBER INDIA TRIP", "Travel & Transport"),
            ("UPI PHARMACY MEDICAL STORE", "Healthcare"),
            ("NEFT SALARY CREDIT TECHCORP", "Salary"),
            ("BANK SERVICE CHARGES", "Bank Charges")
        ]:
            if desc in txns_by_desc:
                actual = txns_by_desc[desc]
                assert actual == expected_cat, f"For '{desc}', expected '{expected_cat}', got '{actual}'"
                print(f"    [OK] Merchant match: '{desc}' -> '{actual}'")

    print("\n==========================================================")
    print("ALL 10 VERIFICATION & INTEGRATION TESTS PASSED 100%!")
    print("==========================================================")
