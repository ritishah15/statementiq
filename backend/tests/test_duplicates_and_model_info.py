import io
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.services.ml_classifier import MLClassifier
from app.services.classification_engine import ClassificationEngine
from app.api.routes import (
    process_upload_content,
    get_classifier_info,
    statement_store,
    _load_sessions
)

SAMPLE_PDF = BASE_DIR / "sample_statements" / "hdfc_digital_statement.pdf"

def test_ml_model_info_reports_multinomial_nb():
    """TASK 1: Verify model information consistently reports Multinomial Naive Bayes without Logistic Regression."""
    classifier = MLClassifier()
    info = classifier.get_info()
    assert "Multinomial Naive Bayes" in info["model_type"], f"Expected Multinomial Naive Bayes, got {info['model_type']}"
    assert "Logistic" not in info["model_type"], f"Found Logistic in model_type: {info['model_type']}"
    assert info["is_trained"] is True, "Model should be trained"

    # Test probability calculation (genuine prediction probabilities, not uncalibrated assumptions)
    top_k = classifier.predict_top_k("POS SWIGGY BANGALORE")
    assert len(top_k) > 0
    assert "probability" in top_k[0]
    assert 0.0 <= top_k[0]["probability"] <= 1.0

    # Also test API route response
    route_info = get_classifier_info()
    assert "Multinomial Naive Bayes" in route_info["model_type"]
    assert "Logistic" not in route_info["model_type"]

def test_duplicate_upload_within_session():
    """TASK 2: Verify SHA-256 prevents duplicate records within the same session when allow_duplicate=False."""
    content = SAMPLE_PDF.read_bytes()

    meta1 = process_upload_content("hdfc_digital_statement.pdf", content, allow_duplicate=False)
    sid1 = meta1.statement_id
    assert meta1.file_hash is not None

    count_before = len(statement_store)

    meta2 = process_upload_content("hdfc_digital_statement.pdf", content, allow_duplicate=False)

    assert meta2.statement_id == sid1, "Must return existing statement ID on duplicate upload"
    assert meta2.is_duplicate is True
    assert meta2.upload_status in ["already_processed", "duplicate"]
    assert len(statement_store) == count_before, "Must not create a new statement record"

def test_duplicate_upload_after_restart():
    """TASK 2: Verify duplicate detection persists across server restarts."""
    content = SAMPLE_PDF.read_bytes()

    _load_sessions()
    meta = process_upload_content("hdfc_digital_statement.pdf", content, allow_duplicate=False)
    assert meta.is_duplicate is True
    assert meta.upload_status in ["already_processed", "duplicate"]

def test_allow_duplicate_creates_linked_record():
    """TASK 2: Verify allow_duplicate=True creates a new record referencing the original statement."""
    content = SAMPLE_PDF.read_bytes()

    count_before = len(statement_store)
    meta = process_upload_content("hdfc_digital_statement.pdf", content, allow_duplicate=True)
    assert meta.is_duplicate is True
    assert meta.duplicate_of is not None
    assert len(statement_store) == count_before + 1

def test_state_consistency_and_transaction_count():
    """TASK 4: Verify queue and detail views share consistent metadata and transaction count."""
    _load_sessions()
    assert len(statement_store) > 0
    for sid, detail_item in statement_store.items():
        meta = detail_item["metadata"]
        assert meta.statement_id == sid
        assert meta.transaction_count == len(detail_item["transactions"])
        assert meta.page_count >= 0
        assert meta.pdf_type in ["DIGITAL", "SCANNED", "MIXED", "UNKNOWN"]

if __name__ == "__main__":
    print("Running test 1...")
    test_ml_model_info_reports_multinomial_nb()
    print("Test 1 PASS: ML Model info reports Multinomial Naive Bayes")
    print("Running test 2...")
    test_duplicate_upload_within_session()
    print("Test 2 PASS: Duplicate upload within session handled")
    print("Running test 3...")
    test_duplicate_upload_after_restart()
    print("Test 3 PASS: Duplicate upload after restart handled")
    print("Running test 4...")
    test_allow_duplicate_creates_linked_record()
    print("Test 4 PASS: allow_duplicate=True creates linked record")
    print("Running test 5...")
    test_state_consistency_and_transaction_count()
    print("Test 5 PASS: State consistency verified")
    print("\nALL 5 DUPLICATE & MODEL INFO TESTS PASSED 100%!")
