import re
from datetime import datetime
from typing import Optional, Tuple

def clean_text(text: str) -> str:
    """Removes extra whitespaces, carriage returns, and control characters."""
    if not text:
        return ""
    text = re.sub(r'[\r\t\f\v]', ' ', text)
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()

def mask_account_number(acc_num: str) -> str:
    """Masks an account number consistently as XXXXXX9281 (last 4 digits only)."""
    if not acc_num or acc_num in ["Not Found", "N/A", ""]:
        return "Not Found"
    clean = re.sub(r'[^a-zA-Z0-9]', '', str(acc_num))
    if len(clean) <= 4:
        return clean
    return f"XXXXXX{clean[-4:]}"

def parse_amount(val) -> Optional[float]:
    """Parses various currency formats into float.
    Handles:
      - Indian numbering (1,20,000.00, 45,200.00)
      - OCR artifacts where commas become dots (1.65.200.00, 2.400.00, 4.200.00)
      - Standard international (1,234.56, 120000.00)
      - Accounting negatives ((500.00), -500.00)
      - Cr / Dr suffixes and currency symbols (INR, Rs., ₹, $, €)
      - Nil / - / None
    """
    if val is None:
        return None
    val_str = str(val).strip()
    if not val_str or val_str in ["-", "--", "Nil", "nil", "N/A", "NA"]:
        return 0.0
    
    # Check accounting negative e.g. (123.45)
    is_negative = False
    if val_str.startswith("(") and val_str.endswith(")"):
        is_negative = True
        val_str = val_str[1:-1]
        
    # Check minus sign
    if val_str.startswith("-"):
        is_negative = True
        val_str = val_str[1:]
        
    # Remove currency symbols, INR, Rs., and spaces
    val_str = re.sub(r'(?i)(inr|rs\.?|[₹$€£\s])', '', val_str)
    # Strip leading glyphs like 'I' or '|' before digits
    val_str = re.sub(r'^[Il|]\s*(?=\d)', '', val_str)
    # Remove Dr / Cr suffix if attached
    val_str = re.sub(r'(?i)(dr|cr)', '', val_str).strip()
    
    # Remove standard commas
    val_str = val_str.replace(',', '')
    
    # Handle multiple periods caused by OCR commas scanned as dots (e.g. 1.65.200.00 or 2.400.00)
    parts = val_str.split('.')
    if len(parts) > 2:
        # If last part is 2 digits (paisa/cents), keep last dot as decimal and treat prior dots as separators
        if len(parts[-1]) <= 2:
            val_str = ''.join(parts[:-1]) + '.' + parts[-1]
        else:
            val_str = ''.join(parts)
    
    try:
        amount = float(val_str)
        return -amount if is_negative else amount
    except ValueError:
        # Try extracting the first valid float pattern
        match = re.search(r'\d+(\.\d+)?', val_str)
        if match:
            try:
                amt = float(match.group(0))
                return -amt if is_negative else amt
            except ValueError:
                return None
        return None

DATE_FORMATS = [
    "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
    "%d/%m/%y", "%d-%m-%y", "%d.%m.%y",
    "%Y-%m-%d", "%Y/%m/%d",
    "%d %b %Y", "%d-%b-%Y", "%d %B %Y", "%d-%B-%Y",
    "%d %b, %Y", "%d %b %y", "%d-%b-%y",
    "%m/%d/%Y", "%m-%d-%Y",
    "%b %d, %Y", "%b %d %Y"
]

def parse_date(date_str: str) -> Tuple[Optional[str], Optional[str]]:
    """Tries parsing date string and returns (standard_YYYY-MM-DD, original_str)."""
    if not date_str:
        return None, None
    clean = date_str.strip()
    # Normalize multiple spaces
    clean = re.sub(r'\s+', ' ', clean)
    
    for fmt in DATE_FORMATS:
        try:
            dt = datetime.strptime(clean, fmt)
            # Basic sanity check: year should be between 1990 and 2040
            if 1990 <= dt.year <= 2040:
                return dt.strftime("%Y-%m-%d"), clean
        except ValueError:
            continue
            
    # Try regex match for DD/MM/YYYY or similar inside text
    m = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', clean)
    if m:
        for fmt in ["%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y", "%m/%d/%Y", "%m-%d-%Y"]:
            try:
                dt = datetime.strptime(m.group(1), fmt)
                if 1990 <= dt.year <= 2040:
                    return dt.strftime("%Y-%m-%d"), clean
            except ValueError:
                pass

    return None, None


# ---------------- Security & Sanitization Helpers ----------------

FORMULA_INJECTION_PREFIXES = ('=', '+', '-', '@', '\t', '\r')

def sanitize_spreadsheet_value(val):
    """
    Prevents spreadsheet formula injection (CSV/Excel injection).
    If a string value begins with =, +, -, @, tab, or CR, prefix with a single quote
    so spreadsheet software renders it strictly as literal text.
    Leaves numbers (int, float) untouched so mathematical calculations remain valid.
    """
    if val is None:
        return ""
    if isinstance(val, (int, float)):
        return val
    s = str(val)
    if s.startswith(FORMULA_INJECTION_PREFIXES):
        return f"'{s}"
    return s


def sanitize_filename(filename: str) -> str:
    """
    Strips directory traversal sequences (../, ..\\) and dangerous characters.
    Extracts base filename and ensures safe characters.
    """
    import os
    if not filename:
        return "statement.pdf"
    
    # Strip path separators and traversal attempts
    base = os.path.basename(filename.replace('\\', '/'))
    base = re.sub(r'[\r\n\0]', '', base)
    # Remove path traversal tokens
    base = re.sub(r'\.\.+', '.', base)
    # Keep only alphanumeric, dot, underscore, dash, space
    clean = re.sub(r'[^a-zA-Z0-9._\-\s]', '_', base).strip()
    if not clean.lower().endswith(".pdf"):
        clean += ".pdf"
    # Ensure length is reasonable (max 100 chars)
    if len(clean) > 100:
        clean = clean[:96] + ".pdf"
    return clean or "statement.pdf"


def validate_pdf_content(content: bytes, max_size_mb: int = 25) -> Tuple[bool, Optional[str]]:
    """
    Validates actual PDF byte content:
    - Non-empty
    - Under maximum size limit
    - Contains valid PDF magic byte signature (%PDF-)
    - Validates PDF structure with PyMuPDF
    """
    if not content or len(content) == 0:
        return False, "File is completely empty (0 bytes)."

    max_bytes = max_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        return False, f"File size ({len(content) / (1024*1024):.1f} MB) exceeds maximum limit of {max_size_mb} MB."

    # Check magic bytes: standard PDFs begin with %PDF- (or within first 1024 bytes)
    header_check = content[:1024]
    if b"%PDF-" not in header_check:
        return False, "Invalid file signature: Content does not match valid PDF specification."

    # Validate structure using fitz
    try:
        import fitz
        doc = fitz.open(stream=content, filetype="pdf")
        page_count = doc.page_count
        is_encrypted = doc.is_encrypted
        doc.close()
        if page_count == 0:
            return False, "Malformed PDF: Document contains 0 readable pages."
        return True, None
    except Exception as e:
        return False, f"Corrupted or malformed PDF structure: {str(e)}"


def mask_sensitive_log(text: str) -> str:
    """
    Masks bank account numbers and card numbers in log statements
    to comply with financial security best practices.
    """
    if not text:
        return ""
    # Mask 9-18 digit account numbers / card numbers
    return re.sub(r'\b(\d{4})\d{4,10}(\d{4})\b', r'\1******\2', str(text))

