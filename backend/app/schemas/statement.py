from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class Transaction(BaseModel):
    id: str
    date: str
    description: str
    debit: Optional[float] = 0.0
    credit: Optional[float] = 0.0
    balance: Optional[float] = None
    category: str = "Others"
    classification_method: str = "Unclassified"  # Rule-Based, ML Classifier, Manual Override
    confidence: Optional[float] = None
    review_status: str = "Verified"  # Verified, Needs Review, Corrected
    validation_flags: List[str] = Field(default_factory=list)
    raw_text: Optional[str] = None
    explanation: Optional[Dict[str, Any]] = None
    original_ocr_value: Optional[Dict[str, Any]] = None
    ocr_correction: Optional[Dict[str, Any]] = None
    audit_history: List[Dict[str, Any]] = Field(default_factory=list)

class TransactionUpdate(BaseModel):
    date: Optional[str] = None
    description: Optional[str] = None
    debit: Optional[float] = None
    credit: Optional[float] = None
    balance: Optional[float] = None
    category: Optional[str] = None
    review_status: Optional[str] = "Corrected"

class AccountDetails(BaseModel):
    bank_name: str = "Not Found"
    account_holder: str = "Not Found"
    account_number: str = "Not Found"
    masked_account_number: str = "Not Found"
    ifsc_code: str = "Not Found"
    statement_period_start: str = "Not Found"
    statement_period_end: str = "Not Found"
    opening_balance: Optional[float] = None
    closing_balance: Optional[float] = None
    currency: str = "INR"

class ReconciliationSummary(BaseModel):
    total_transactions: int = 0
    total_debits: float = 0.0
    total_credits: float = 0.0
    net_flow: float = 0.0
    opening_balance: Optional[float] = None
    closing_balance: Optional[float] = None
    calculated_closing_balance: Optional[float] = None
    discrepancy: Optional[float] = None
    is_reconciled: bool = False
    reconciliation_status: str = "Pending"  # Reconciled, Discrepancy Detected, Missing Balance Info
    notes: str = ""

class ClassificationStats(BaseModel):
    total_classified: int = 0
    rule_based_count: int = 0
    rule_based_pct: float = 0.0
    ml_count: int = 0
    ml_pct: float = 0.0
    needs_review_count: int = 0
    needs_review_pct: float = 0.0
    average_confidence: float = 0.0
    category_distribution: Dict[str, int] = Field(default_factory=dict)
    spend_by_category: Dict[str, float] = Field(default_factory=dict)

class StatementMetadata(BaseModel):
    statement_id: str
    filename: str
    file_size: int
    file_hash: Optional[str] = None
    page_count: int = 0
    digital_pages: int = 0
    scanned_pages: int = 0
    pdf_type: str = "UNKNOWN"  # DIGITAL | SCANNED | MIXED | UNKNOWN
    detection_confidence: float = 0.0
    text_density_score: float = 0.0
    detection_explanation: Optional[str] = None
    page_analysis: List[Dict[str, Any]] = Field(default_factory=list)
    ocr_applied: bool = False
    status: str = "uploaded"  # uploaded, type_detected, extracting, parsed, classifying, completed, error
    current_stage: int = 1
    total_stages: int = 6
    stage_name: str = "File Uploaded"
    error_message: Optional[str] = None
    created_at: str
    is_duplicate: bool = False
    duplicate_of: Optional[str] = None
    duplicate_notice: Optional[str] = None
    upload_status: str = "newly_uploaded"  # newly_uploaded, already_processed, duplicate
    transaction_count: int = 0

class StatementResponse(BaseModel):
    metadata: StatementMetadata
    account_details: AccountDetails
    transactions: List[Transaction] = Field(default_factory=list)
    reconciliation: ReconciliationSummary
    classification_stats: Optional[ClassificationStats] = None

class CustomRule(BaseModel):
    category: str
    keywords: List[str]
    case_sensitive: bool = False
    priority: int = 10
