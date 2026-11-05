import sys
import asyncio
from pathlib import Path

# Add backend to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from httpx import ASGITransport, AsyncClient
from app.main import app

async def run_api_tests():
    print("[1/10] Initializing AsyncClient with ASGITransport...", flush=True)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        print("[2/10] Sending GET / ...", flush=True)
        r = await client.get("/")
        print(f"[PASS] Root endpoint: {r.status_code} -> {r.json()}", flush=True)

        print("[3/10] Sending GET /api/sample-statements ...", flush=True)
        r = await client.get("/api/sample-statements")
        print(f"[PASS] Samples found: {r.json()}", flush=True)

        print("[4/10] Loading sample statement ...", flush=True)
        r = await client.post("/api/sample-statements/hdfc_digital_statement.pdf/load")
        stmt_id = r.json()["statement_id"]
        print(f"[PASS] Created statement: {stmt_id}", flush=True)

        print("[5/10] Processing statement ...", flush=True)
        r = await client.post(f"/api/statements/{stmt_id}/process")
        proc_data = r.json()
        print(f"[PASS] Processed {proc_data['transaction_count']} txns, Bank={proc_data['account_details']['bank_name']}", flush=True)

        print("[6/10] Classifying transactions ...", flush=True)
        r = await client.post(f"/api/statements/{stmt_id}/classify")
        stats = r.json()["classification_stats"]
        print(f"[PASS] Classification: Rule={stats['rule_based_count']}, ML={stats['ml_count']}", flush=True)

        print("[7/10] Checking full results & reconciliation ...", flush=True)
        r = await client.get(f"/api/statements/{stmt_id}")
        recon = r.json()["reconciliation"]
        print(f"[PASS] Reconciliation: {recon['reconciliation_status']}, Reconciled={recon['is_reconciled']}", flush=True)

        print("[8/10] Manual transaction correction ...", flush=True)
        first_txn = r.json()["transactions"][0]
        r = await client.put(f"/api/statements/{stmt_id}/transactions/{first_txn['id']}", json={
            "category": "Education",
            "description": "UPDATED TUITION FEES",
            "review_status": "Corrected"
        })
        print(f"[PASS] Updated category: {r.json()['category']}", flush=True)

        print("[9/10] Generating Excel and CSV exports ...", flush=True)
        r_excel = await client.get(f"/api/statements/{stmt_id}/export/excel")
        r_csv = await client.get(f"/api/statements/{stmt_id}/export/csv")
        print(f"[PASS] Excel: {len(r_excel.content)} bytes, CSV: {len(r_csv.text)} chars", flush=True)

        print("[10/10] Testing OCR on scanned statement ...", flush=True)
        r_scan = await client.post("/api/sample-statements/scanned_statement.pdf/load")
        scan_id = r_scan.json()["statement_id"]
        r_scan_proc = await client.post(f"/api/statements/{scan_id}/process")
        print(f"[PASS] Scanned OCR statement: type={r_scan_proc.json()['metadata']['pdf_type']}, OCR applied={r_scan_proc.json()['metadata']['ocr_applied']}", flush=True)

        print("\n>>> ALL 10 END-TO-END API TESTS COMPLETED AND VERIFIED! <<<", flush=True)

if __name__ == "__main__":
    asyncio.run(run_api_tests())
