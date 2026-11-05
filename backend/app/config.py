import os
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
MODELS_DIR = BASE_DIR / "models"
DATA_DIR = BASE_DIR / "data"
SAMPLE_DIR = BASE_DIR / "sample_statements"

for d in [UPLOAD_DIR, MODELS_DIR, DATA_DIR, SAMPLE_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Tesseract binary discovery
def find_tesseract_path() -> str:
    # 1. Environment variable
    if os.getenv("TESSERACT_CMD") and os.path.exists(os.getenv("TESSERACT_CMD")):
        return os.getenv("TESSERACT_CMD")
    
    # 2. Check PATH
    which_tess = shutil.which("tesseract")
    if which_tess:
        return which_tess
        
    # 3. Common Windows paths
    win_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe")
    ]
    for p in win_paths:
        if os.path.exists(p):
            return p
    return "tesseract"

TESSERACT_CMD = find_tesseract_path()

# Supported classification categories
STANDARD_CATEGORIES = [
    "Salary",
    "Food & Dining",
    "Shopping",
    "Rent",
    "Utilities & Bills",
    "Travel & Transport",
    "ATM Withdrawal",
    "Bank Charges",
    "Investments",
    "Transfers",
    "Healthcare",
    "Education",
    "Others"
]
