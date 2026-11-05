import os
import json
import uuid
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, UploadFile, File, Query, HTTPException
from fastapi.responses import Response, StreamingResponse
from app.config import UPLOAD_DIR, BASE_DIR
from app.schemas.statement import (
    StatementMetadata, StatementResponse, AccountDetails,
    Transaction, TransactionUpdate, ReconciliationSummary,
    ClassificationStats, CustomRule
)
from app.services.pdf_detector import PDFDetector
from app.services.pdf_extractor import PDFExtractor
from app.services.transaction_parser import TransactionParser
from app.services.data_validator import DataValidator
from app.services.classification_engine import ClassificationEngine
from app.services.reconciliation import ReconciliationService
from app.services.export_service import ExportService
from app.utils.helpers import sanitize_filename, validate_pdf_content, mask_sensitive_log

router = APIRouter(prefix="/api")

# Persistent storage file for active statements
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
SESSIONS_FILE = DATA_DIR / "statement_sessions.json"

statement_store: Dict[str, Dict[str, Any]] = {}

extractor = PDFExtractor()
parser = TransactionParser()
classifier_engine = ClassificationEngine()


def _save_sessions():
    """Persists statement sessions to disk so restarts or page reloads preserve state."""
    try:
        serializable = {}
        for sid, item in statement_store.items():
            meta = item["metadata"]
            acc = item["account_details"]
            txns = item["transactions"]
            recon = item["reconciliation"]
            stats = item.get("classification_stats")

            serializable[sid] = {
                "metadata": meta.model_dump() if hasattr(meta, "model_dump") else meta,
                "file_path": item["file_path"],
                "account_details": acc.model_dump() if hasattr(acc, "model_dump") else acc,
                "transactions": [t.model_dump() if hasattr(t, "model_dump") else t for t in txns],
                "reconciliation": recon.model_dump() if hasattr(recon, "model_dump") else recon,
                "classification_stats": stats.model_dump() if (stats and hasattr(stats, "model_dump")) else stats,
                "raw_text": item.get("raw_text", ""),
                "detection_info": item.get("detection_info", {})
            }
        with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(serializable, f, indent=2)
    except Exception as e:
        print(f"Error persisting statement sessions: {e}")


def _load_sessions():
    """Loads previously saved statements on startup and checks upload directory."""
    global statement_store
    statement_store.clear()

    if SESSIONS_FILE.exists():
        try:
            with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for sid, item in data.items():
                if os.path.exists(item.get("file_path", "")):
                    txns = [Transaction(**t) for t in item.get("transactions", [])]
                    meta = StatementMetadata(**item["metadata"])
                    meta.transaction_count = len(txns)
                    if not meta.file_hash:
                        try:
                            meta.file_hash = hashlib.sha256(open(item["file_path"], "rb").read()).hexdigest()
                        except Exception:
                            pass
                    statement_store[sid] = {
                        "metadata": meta,
                        "file_path": item["file_path"],
                        "account_details": AccountDetails(**item.get("account_details", {})),
                        "transactions": txns,
                        "reconciliation": ReconciliationSummary(**item.get("reconciliation", {})),
                        "classification_stats": ClassificationStats(**item["classification_stats"]) if item.get("classification_stats") else None,
                        "raw_text": item.get("raw_text", ""),
                        "detection_info": item.get("detection_info", {})
                    }
        except Exception as e:
            print(f"Error loading statement sessions: {e}")


# Load sessions on module initialization
_load_sessions()


@router.get("/statements")
async def list_statements():
    """Lists all statements currently in the ingestion queue."""
    return [s["metadata"] for s in statement_store.values()]


def process_upload_content(filename: str, content: bytes, allow_duplicate: bool = False) -> StatementMetadata:
    """Core upload processor: validates PDF integrity, sanitizes filename, handles SHA-256 duplicate detection, file storage, and PDF detection."""
    # File upload security: validate actual PDF content and enforce size limit
    is_valid_pdf, validation_err = validate_pdf_content(content, max_size_mb=25)
    if not is_valid_pdf:
        status_code = 413 if "exceeds maximum limit" in (validation_err or "") else 400
        raise HTTPException(status_code=status_code, detail=validation_err or "Invalid or malformed PDF file.")

    # Sanitize filename against path traversal (../, ..\, control chars, null bytes)
    clean_filename = sanitize_filename(filename)

    file_hash = PDFDetector.calculate_file_hash(content)

    # Duplicate detection check via SHA-256
    existing_dup = None
    for sid, s in statement_store.items():
        if s["metadata"].file_hash == file_hash:
            existing_dup = s["metadata"]
            break

    if existing_dup and not allow_duplicate:
        # Uploading the same PDF twice must not create duplicate records or overwrite identity
        is_processed = existing_dup.current_stage >= 4
        existing_dup.is_duplicate = True
        existing_dup.upload_status = "already_processed" if is_processed else "duplicate"
        existing_dup.duplicate_notice = f"Duplicate of {existing_dup.filename} (already processed as {existing_dup.statement_id})"
        _save_sessions()
        return existing_dup

    statement_id = f"STMT-{uuid.uuid4().hex[:8].upper()}"
    file_path = UPLOAD_DIR / f"{statement_id}_{clean_filename}"

    with open(file_path, "wb") as f:
        f.write(content)

    # Immediate deep PDF inspection
    detection = PDFDetector.detect(str(file_path))
    pdf_type = detection.get("pdf_type", "UNKNOWN")
    is_valid = pdf_type != "UNKNOWN"

    meta = StatementMetadata(
        statement_id=statement_id,
        filename=clean_filename,
        file_size=len(content),
        file_hash=file_hash,
        page_count=detection.get("page_count", 0),
        digital_pages=detection.get("digital_pages", 0),
        scanned_pages=detection.get("scanned_pages", 0),
        pdf_type=pdf_type,
        detection_confidence=detection.get("confidence", 0.0),
        text_density_score=detection.get("text_density_score", 0.0),
        detection_explanation=detection.get("explanation"),
        page_analysis=detection.get("page_analysis", []),
        ocr_applied=detection.get("ocr_required", False),
        status="type_detected" if is_valid else "error",
        current_stage=2 if is_valid else 1,
        stage_name="Type Detected" if is_valid else "Detection Failed",
        error_message=None if is_valid else detection.get("explanation"),
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        is_duplicate=bool(existing_dup),
        duplicate_of=existing_dup.statement_id if existing_dup else None,
        duplicate_notice=f"Duplicate of {existing_dup.filename} ({existing_dup.statement_id})" if existing_dup else None,
        upload_status="duplicate" if existing_dup else "newly_uploaded",
        transaction_count=0
    )

    statement_store[statement_id] = {
        "metadata": meta,
        "file_path": str(file_path),
        "account_details": AccountDetails(),
        "transactions": [],
        "reconciliation": ReconciliationSummary(),
        "classification_stats": None,
        "raw_text": "",
        "detection_info": detection
    }
    _save_sessions()
    return meta


@router.post("/statements/upload")
async def upload_statement(
    file: UploadFile = File(...),
    allow_duplicate: bool = Query(False, description="Allow uploading duplicate document")
):
    """
    Uploads a bank statement, detects duplicate files via SHA-256 hash,
    and performs immediate PDF type detection (DIGITAL, SCANNED, MIXED, or UNKNOWN).
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Unsupported format: Only standard PDF bank statements are accepted."
        )

    content = await file.read()
    return process_upload_content(file.filename, content, allow_duplicate)


@router.post("/statements/upload-batch")
async def upload_batch_statements(
    files: List[UploadFile] = File(...),
    allow_duplicate: bool = Query(False)
):
    """Uploads multiple PDF bank statements in a single batch request."""
    results = []
    errors = []

    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            errors.append({"filename": file.filename, "error": "Not a PDF document"})
            continue

        try:
            content = await file.read()
            meta = process_upload_content(file.filename, content, allow_duplicate)
            results.append(meta)
        except HTTPException as he:
            errors.append({"filename": file.filename, "error": he.detail})
        except Exception as e:
            errors.append({"filename": file.filename, "error": str(e)})

    return {"uploaded": results, "errors": errors, "total": len(results)}


@router.get("/sample-statements")
async def list_sample_statements():
    """Lists available test statements (digital, scanned OCR)."""
    from app.config import SAMPLE_DIR
    samples = []
    if SAMPLE_DIR.exists():
        allowed_files = ["hdfc_digital_statement.pdf", "scanned_statement.pdf"]
        for f in SAMPLE_DIR.glob("*.pdf"):
            if f.name in allowed_files:
                samples.append({
                    "filename": f.name,
                    "file_size": f.stat().st_size,
                    "type": "SCANNED" if "scan" in f.name.lower() else "DIGITAL"
                })
        # Keep digital first, then scanned
        samples.sort(key=lambda s: 0 if s["type"] == "DIGITAL" else 1)
    return samples


@router.post("/sample-statements/{filename}/load")
async def load_sample_statement(filename: str):
    """Loads a pre-generated sample statement into the active queue for instant testing."""
    from app.config import SAMPLE_DIR, UPLOAD_DIR
    import shutil

    source_path = SAMPLE_DIR / filename
    if not source_path.exists():
        raise HTTPException(status_code=404, detail="Sample statement not found")

    content = source_path.read_bytes()
    file_hash = PDFDetector.calculate_file_hash(content)

    # Prevent creating duplicate statements for pre-loaded samples
    for sid, s in statement_store.items():
        if s["metadata"].file_hash == file_hash:
            existing_meta = s["metadata"]
            existing_meta.is_duplicate = True
            existing_meta.duplicate_notice = "Duplicate - already processed"
            _save_sessions()
            return existing_meta

    statement_id = f"STMT-{uuid.uuid4().hex[:8].upper()}"
    dest_path = UPLOAD_DIR / f"{statement_id}_{filename}"
    shutil.copy(source_path, dest_path)

    # Immediate detection
    detection = PDFDetector.detect(str(dest_path))
    pdf_type = detection.get("pdf_type", "UNKNOWN")
    is_valid = pdf_type != "UNKNOWN"

    meta = StatementMetadata(
        statement_id=statement_id,
        filename=filename,
        file_size=source_path.stat().st_size,
        file_hash=file_hash,
        page_count=detection.get("page_count", 0),
        digital_pages=detection.get("digital_pages", 0),
        scanned_pages=detection.get("scanned_pages", 0),
        pdf_type=pdf_type,
        detection_confidence=detection.get("confidence", 0.0),
        text_density_score=detection.get("text_density_score", 0.0),
        detection_explanation=detection.get("explanation"),
        page_analysis=detection.get("page_analysis", []),
        ocr_applied=detection.get("ocr_required", False),
        status="type_detected" if is_valid else "error",
        current_stage=2 if is_valid else 1,
        stage_name="Type Detected" if is_valid else "Detection Failed",
        error_message=None if is_valid else detection.get("explanation"),
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    statement_store[statement_id] = {
        "metadata": meta,
        "file_path": str(dest_path),
        "account_details": AccountDetails(),
        "transactions": [],
        "reconciliation": ReconciliationSummary(),
        "classification_stats": None,
        "raw_text": "",
        "detection_info": detection
    }
    _save_sessions()
    return meta


@router.get("/system")
async def get_system_info():
    """Returns dynamic system and OCR engine status without hardcoding."""
    ocr_engine = "not installed"
    try:
        import pytesseract
        ver = str(pytesseract.get_tesseract_version()).strip()
        if ver:
            ocr_engine = f"Tesseract {ver}"
    except Exception:
        ocr_engine = "not installed"

    return {
        "ocr_engine": ocr_engine,
        "ml_model": "TF-IDF + Naive Bayes",
        "status": "healthy"
    }


@router.delete("/statements")
async def clear_all_statements():
    """Clears all statements and cleans up temporary uploads."""
    cleared = len(statement_store)
    for sid, item in list(statement_store.items()):
        fp = item.get("file_path")
        if fp and os.path.exists(fp):
            try:
                os.remove(fp)
            except Exception:
                pass
    statement_store.clear()
    _save_sessions()
    return {"message": "All statements cleared successfully", "cleared_count": cleared}


@router.delete("/statements/{statement_id}")
async def delete_statement(statement_id: str):
    """Removes a statement and cleans up temporary uploads."""
    if statement_id not in statement_store:
        raise HTTPException(status_code=404, detail="Statement not found")

    file_path = statement_store[statement_id]["file_path"]
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass

    del statement_store[statement_id]
    _save_sessions()
    return {"message": "Statement removed successfully"}


@router.post("/statements/{statement_id}/retry")
async def retry_statement(statement_id: str):
    """Retries processing on a failed or error statement."""
    if statement_id not in statement_store:
        raise HTTPException(status_code=404, detail="Statement not found")

    item = statement_store[statement_id]
    meta: StatementMetadata = item["metadata"]
    file_path = item["file_path"]

    # Re-run detection
    detection = PDFDetector.detect(file_path)
    meta.pdf_type = detection.get("pdf_type", "UNKNOWN")
    meta.page_count = detection.get("page_count", 0)
    meta.detection_explanation = detection.get("explanation")
    meta.error_message = None

    if meta.pdf_type == "UNKNOWN":
        meta.status = "error"
        meta.error_message = detection.get("explanation", "Detection error")
        meta.current_stage = 1
        meta.stage_name = "Detection Failed"
        _save_sessions()
        return {"metadata": meta, "message": "Detection failed again"}

    meta.current_stage = 2
    meta.status = "type_detected"
    meta.stage_name = "Type Detected"
    _save_sessions()

    # Automatically trigger extraction
    return await process_statement(statement_id)


@router.post("/statements/{statement_id}/process")
async def process_statement(statement_id: str):
    """
    Executes actual pipeline stages:
    Stage 3: Text/OCR Extraction
    Stage 4: Transaction Parsing & Account Details Extraction
    """
    if statement_id not in statement_store:
        raise HTTPException(status_code=404, detail="Statement not found")

    item = statement_store[statement_id]
    meta: StatementMetadata = item["metadata"]
    file_path = item["file_path"]

    if meta.pdf_type == "UNKNOWN":
        meta.status = "error"
        meta.error_message = meta.detection_explanation or "Cannot process UNKNOWN or corrupted document."
        _save_sessions()
        raise HTTPException(status_code=400, detail=meta.error_message)

    try:
        # Stage 3: Text/OCR Extraction
        meta.status = "extracting"
        meta.current_stage = 3
        meta.stage_name = "Text/OCR Extraction"
        meta.error_message = None

        extraction_res = extractor.extract_content(file_path)
        detection = extraction_res["detection"]

        meta.pdf_type = detection["pdf_type"]
        meta.detection_confidence = detection["confidence"]
        meta.text_density_score = detection["text_density_score"]
        meta.page_count = detection["page_count"]
        meta.ocr_applied = extraction_res["is_scanned"]
        meta.detection_explanation = detection.get("explanation")

        item["raw_text"] = extraction_res["full_text"]
        item["detection_info"] = detection

        # Stage 4: Parse Account Details & Transactions
        meta.status = "parsing"
        meta.current_stage = 4
        meta.stage_name = "Transaction Parsing"

        acc_details = parser.extract_account_details(extraction_res["full_text"])
        raw_txns = parser.extract_transactions(
            extraction_res["raw_tables"], 
            extraction_res["full_text"], 
            pages=extraction_res.get("pages", []),
            opening_balance=acc_details.opening_balance
        )

        # Check for zero transaction extraction
        if len(raw_txns) == 0:
            meta.status = "error"
            meta.current_stage = 4
            meta.stage_name = "Parsing Failed"
            meta.error_message = "No identifiable transaction records found in document."
            _save_sessions()
            raise HTTPException(status_code=422, detail="No identifiable transaction records found in document.")

        # Validate extracted transactions including running balance
        validated_txns = DataValidator.validate_all(raw_txns, opening_balance=acc_details.opening_balance)

        item["account_details"] = acc_details
        item["transactions"] = validated_txns
        meta.transaction_count = len(validated_txns)

        # Preliminary reconciliation
        recon = ReconciliationService.reconcile(acc_details, validated_txns)
        item["reconciliation"] = recon

        meta.status = "parsed"
        meta.current_stage = 4
        meta.stage_name = "Transactions Extracted"

        _save_sessions()

        return {
            "metadata": meta,
            "account_details": acc_details,
            "transaction_count": len(validated_txns),
            "reconciliation": recon
        }

    except HTTPException:
        raise
    except RuntimeError as re_err:
        err_str = str(re_err)
        meta.status = "error"
        meta.error_message = err_str
        _save_sessions()
        if "Tesseract OCR" in err_str:
            raise HTTPException(status_code=503, detail="Tesseract OCR engine is not installed or available.")
        raise HTTPException(status_code=500, detail=err_str)
    except Exception as e:
        meta.status = "error"
        meta.error_message = str(e)
        _save_sessions()
        raise HTTPException(status_code=500, detail=f"Extraction pipeline error: {str(e)}")


@router.post("/statements/{statement_id}/classify")
async def classify_statement(statement_id: str):
    """
    Executes actual pipeline stages:
    Stage 5: Classification (Deterministic Rules & Supervised ML)
    Stage 6: Reconciliation & Export Ready
    """
    if statement_id not in statement_store:
        raise HTTPException(status_code=404, detail="Statement not found")

    item = statement_store[statement_id]
    meta: StatementMetadata = item["metadata"]
    txns = item["transactions"]

    if not txns:
        raise HTTPException(status_code=400, detail="No transactions available to classify. Process the statement first.")

    try:
        # Stage 5: Classification
        meta.status = "classifying"
        meta.current_stage = 5
        meta.stage_name = "Classification"

        classified_txns, stats = classifier_engine.classify_all(txns)
        item["transactions"] = classified_txns
        item["classification_stats"] = stats

        # Re-run reconciliation with final records
        recon = ReconciliationService.reconcile(item["account_details"], classified_txns)
        item["reconciliation"] = recon

        # Stage 6: Processing & Validation Complete
        meta.status = "completed"
        meta.current_stage = 6
        meta.stage_name = "Processing & Validation Complete"

        _save_sessions()

        return {
            "metadata": meta,
            "classification_stats": stats,
            "transactions": classified_txns,
            "reconciliation": recon
        }
    except Exception as e:
        meta.status = "error"
        meta.error_message = f"Classification error: {str(e)}"
        _save_sessions()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statements/{statement_id}")
async def get_statement(statement_id: str):
    """Retrieves current processing status, account details, and metadata."""
    if statement_id not in statement_store:
        raise HTTPException(status_code=404, detail="Statement not found")

    item = statement_store[statement_id]
    return StatementResponse(
        metadata=item["metadata"],
        account_details=item["account_details"],
        transactions=item["transactions"],
        reconciliation=item["reconciliation"],
        classification_stats=item["classification_stats"]
    )


@router.get("/statements/{statement_id}/transactions")
async def get_transactions(statement_id: str):
    """Retrieves all parsed and classified transactions for a statement."""
    if statement_id not in statement_store:
        raise HTTPException(status_code=404, detail="Statement not found")

    return statement_store[statement_id]["transactions"]


@router.put("/statements/{statement_id}/transactions/{transaction_id}")
async def update_transaction(statement_id: str, transaction_id: str, update: TransactionUpdate):
    """Allows manual inline correction of any transaction field and maintains audit history."""
    if statement_id not in statement_store:
        raise HTTPException(status_code=404, detail="Statement not found")

    item = statement_store[statement_id]
    txns: List[Transaction] = item["transactions"]

    for t in txns:
        if t.id == transaction_id:
            now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if update.date is not None and update.date != t.date:
                t.audit_history.append({"field": "date", "old_value": t.date, "new_value": update.date, "timestamp": now_ts})
                t.date = update.date

            if update.description is not None and update.description != t.description:
                t.audit_history.append({"field": "description", "old_value": t.description, "new_value": update.description, "timestamp": now_ts})
                t.description = update.description
                if update.category is None:
                    t = classifier_engine.classify_transaction(t)

            if update.debit is not None and update.debit != t.debit:
                t.audit_history.append({"field": "debit", "old_value": t.debit, "new_value": update.debit, "timestamp": now_ts})
                t.debit = update.debit

            if update.credit is not None and update.credit != t.credit:
                t.audit_history.append({"field": "credit", "old_value": t.credit, "new_value": update.credit, "timestamp": now_ts})
                t.credit = update.credit

            if update.balance is not None and update.balance != t.balance:
                t.audit_history.append({"field": "balance", "old_value": t.balance, "new_value": update.balance, "timestamp": now_ts})
                t.balance = update.balance

            if update.category is not None and update.category != t.category:
                t.audit_history.append({"field": "category", "old_value": t.category, "new_value": update.category, "timestamp": now_ts})
                t.category = update.category
                t.classification_method = "Manual Override"
                t.confidence = 1.0
                t.explanation = {
                    "category": update.category,
                    "method": "Manual Override",
                    "confidence": 1.0,
                    "reason": "Manually selected by user override."
                }

            t.review_status = "Corrected"

            # Re-validate transactions including running balance and duplicates
            item["transactions"] = DataValidator.validate_all(txns, opening_balance=item["account_details"].opening_balance)
            # Re-run reconciliation with updated records
            item["reconciliation"] = ReconciliationService.reconcile(item["account_details"], item["transactions"])
            
            # Recalculate classification statistics
            cat_dist = {}
            spend_dist = {}
            for tx in item["transactions"]:
                c = tx.category
                cat_dist[c] = cat_dist.get(c, 0) + 1
                spend_dist[c] = spend_dist.get(c, 0.0) + (tx.debit or 0.0)
            if item.get("classification_stats"):
                item["classification_stats"].category_distribution = cat_dist
                item["classification_stats"].spend_by_category = {k: round(v, 2) for k, v in spend_dist.items()}

            _save_sessions()
            return t

    raise HTTPException(status_code=404, detail="Transaction ID not found")


@router.get("/statements/{statement_id}/results")
async def get_results(statement_id: str):
    """Retrieves complete final processed results for audit and reconciliation."""
    if statement_id not in statement_store:
        raise HTTPException(status_code=404, detail="Statement not found")

    item = statement_store[statement_id]
    return StatementResponse(
        metadata=item["metadata"],
        account_details=item["account_details"],
        transactions=item["transactions"],
        reconciliation=item["reconciliation"],
        classification_stats=item["classification_stats"]
    )


@router.get("/statements/export/excel")
async def export_all_excel(statement_ids: Optional[str] = Query(None, description="Comma-separated statement IDs, or omit for all")):
    """Downloads a consolidated multi-sheet Excel workbook containing all processed statements."""
    selected_items = []
    if statement_ids:
        ids = [i.strip() for i in statement_ids.split(",") if i.strip()]
        for i in ids:
            if i in statement_store:
                selected_items.append(statement_store[i])
    else:
        # Default: all statements that have transactions
        selected_items = [s for s in statement_store.values() if s.get("transactions")]
        if not selected_items:
            selected_items = list(statement_store.values())

    if not selected_items:
        raise HTTPException(status_code=404, detail="No statement records available for multi-statement export.")

    excel_stream = ExportService.generate_combined_excel(selected_items)
    filename = f"StatementIQ_MultiStatement_Portfolio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return StreamingResponse(
        excel_stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/statements/export/csv")
async def export_all_csv(statement_ids: Optional[str] = Query(None, description="Comma-separated statement IDs, or omit for all")):
    """Downloads a consolidated CSV file containing all transactions across processed statements."""
    selected_items = []
    if statement_ids:
        ids = [i.strip() for i in statement_ids.split(",") if i.strip()]
        for i in ids:
            if i in statement_store:
                selected_items.append(statement_store[i])
    else:
        selected_items = [s for s in statement_store.values() if s.get("transactions")]
        if not selected_items:
            selected_items = list(statement_store.values())

    if not selected_items:
        raise HTTPException(status_code=404, detail="No statement records available for multi-statement export.")

    csv_content = ExportService.generate_combined_csv(selected_items)
    filename = f"StatementIQ_MultiStatement_Transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/statements/{statement_id}/export/excel")
async def export_excel(statement_id: str):
    """Downloads an Excel workbook (.xlsx) containing Account Details, Transactions, Summary, Income/Expense breakdowns, Review Flags, and Explanations."""
    if statement_id not in statement_store:
        raise HTTPException(status_code=404, detail="Statement not found")

    item = statement_store[statement_id]
    excel_stream = ExportService.generate_excel(
        item["account_details"],
        item["transactions"],
        item["reconciliation"],
        source_filename=item["metadata"].filename
    )

    filename = f"StatementIQ_{statement_id}.xlsx"
    return StreamingResponse(
        excel_stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/statements/{statement_id}/export/csv")
async def export_csv(statement_id: str):
    """Downloads a CSV file (.csv) containing all processed transactions with statement reference."""
    if statement_id not in statement_store:
        raise HTTPException(status_code=404, detail="Statement not found")

    item = statement_store[statement_id]
    csv_content = ExportService.generate_csv(
        item["transactions"],
        source_filename=item["metadata"].filename,
        statement_id=statement_id
    )
    filename = f"StatementIQ_{statement_id}.csv"

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ----------------- Classifier Management Endpoints -----------------

@router.get("/classifier/rules")
async def get_rules():
    """Returns active deterministic keyword matching rules."""
    return classifier_engine.rule_engine.rules


@router.post("/classifier/rules")
async def add_rule(rule: CustomRule):
    """Adds custom keyword rules for heuristic classification."""
    for kw in rule.keywords:
        classifier_engine.rule_engine.add_rule(rule.category, kw)
    return {"message": f"Successfully updated rules for category '{rule.category}'"}


@router.get("/classifier/info")
def get_classifier_info():
    """Returns machine learning model metadata, training status, and accuracy."""
    return classifier_engine.ml_engine.get_info()


@router.get("/classifier/evaluate")
def evaluate_classifier():
    """Evaluates the supervised ML model on a held-out test split, reporting Accuracy, Precision, Recall, F1, and Confusion Matrix."""
    return classifier_engine.ml_engine.evaluate_model()


@router.post("/classifier/retrain")
async def retrain_classifier():
    """Retrains the supervised ML model using the training dataset."""
    res = classifier_engine.ml_engine.train()
    return res
