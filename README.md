# StatementIQ – Bank Statement Processing & Classification System
### Internship Assessment Implementation | Non-LLM Architecture

StatementIQ is a full-stack financial document processing, transaction classification, and mathematical reconciliation platform designed to ingest and audit multi-bank statement documents (both native digital PDFs and scanned image-based PDFs) **without using Large Language Models (LLMs) or external generative AI APIs**.

The system combines deterministic rule engines, traditional supervised machine learning (TF-IDF + Multinomial Naive Bayes), OpenCV computer vision image preprocessing, Tesseract OCR, running-balance ledger validation, and formula-injection-safe multi-sheet spreadsheet exports.

---

## 🏛️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           StatementIQ Web Dashboard                         │
│                    (React 18 + Vite + Tailwind CSS + Lucide)                │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ REST API (JSON / Multipart / Streams)
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                              FastAPI Backend                                │
│                     (Uvicorn + Pydantic v2 + OpenPyXL)                      │
└──────┬───────────────────────┬───────────────────────────────┬──────────────┘
       │                       │                               │
┌──────▼────────────┐  ┌───────▼────────────────────┐  ┌───────▼──────────────┐
│  PDF Processing   │  │ Non-LLM Classifier Engine  │  │   Audit & Export     │
│  & OCR Pipeline   │  │ (Priority 4-Tier Flow)     │  │ (Ledger Reconciliation)
├───────────────────┤  ├────────────────────────────┤  ├──────────────────────┤
│ • PyMuPDF (fitz)  │  │ 1. User Custom Rules (1.0) │  │ • Running Balance:   │
│ • pdfplumber      │  │ 2. Predefined Heuristics   │  │   B_prev + Cr - Dr   │
│ • OpenCV / Pillow │  │    (High-priority merchants│  │   = B_curr           │
│ • Tesseract 5.5   │  │    before payment rails)   │  │ • Header Balance:    │
│ • Page-level Type │  │ 3. TF-IDF + Multinomial NB │  │   Open + Cr - Dr     │
│   Detection:      │  │    (Confidence >= 0.45)    │  │   = Closing          │
│   DIGITAL, SCANNED│  │ 4. Fallback: Needs Review  │  │ • 7-Sheet Excel      │
│   MIXED, UNKNOWN  │  │ • "Why this category?" exp │  │ • Multi-Statement Exp│
│ • SHA-256 Dup Id  │  │ • Zero LLM / Zero GenAI    │  │ • Formula Sanitizing │
└───────────────────┘  └────────────────────────────┘  └──────────────────────┘
```

---

## 🛠️ Technology Stack

| Layer | Component | Version / Library | Purpose |
|---|---|---|---|
| **Frontend** | React SPA | React 18.3, Vite 5.4 | Interactive desktop fintech UI |
| **Styling** | Tailwind CSS | Tailwind 3.4 | FinTech design (`#172B4D` navy, `#0D9488` teal) |
| **Backend** | REST API | FastAPI 0.115, Uvicorn | High-performance asynchronous API server |
| **Validation** | Data Schemas | Pydantic v2 | Strict request/response typing and schema checks |
| **PDF Extraction**| Native & Tables | PyMuPDF (fitz), pdfplumber | Text coordinate extraction and table grid parsing |
| **OCR Engine** | Scanned Documents | Tesseract 5.5, pytesseract | Optical character recognition on rasterized scans |
| **Image Vision** | Preprocessing | OpenCV (cv2), Pillow | Grayscale, Gaussian blur, Otsu thresholding, deskew |
| **Machine Learning**| Supervised ML | Scikit-learn, joblib | TF-IDF (1-2 ngrams) + Multinomial Naive Bayes |
| **Spreadsheets** | Excel / CSV | OpenPyXL | 7-sheet styled financial reports & CSV generation |
| **Testing** | Automated Suites | pytest, pytest-cov, Starlette TestClient | 38 automated unit, security, and e2e integration tests |

---

## 📦 Installation & Setup

### Prerequisites
- **Python**: 3.10 to 3.13 (developed and tested on Python 3.13.2)
- **Node.js**: 18+ (tested on Node v24.14.0, npm 11.9.0)
- **Tesseract OCR**: 5.0+ installed and on system PATH (or default install directory)

### Tesseract OCR Installation Guide

#### Windows:
1. Download the official Windows installer from [UB-Mannheim Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki).
2. Install to default path: `C:\Program Files\Tesseract-OCR\tesseract.exe`.
3. Add `C:\Program Files\Tesseract-OCR` to your Windows System `PATH` environment variable.
4. Verify in terminal: `tesseract --version`.

#### Ubuntu / Debian Linux:
```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr libtesseract-dev
tesseract --version
```

#### macOS (Homebrew):
```bash
brew install tesseract
tesseract --version
```

---

## 🚀 How to Run the Project

### Quick Start (Windows)
Run the root batch launcher:
```cmd
start_servers.bat
```
This launches:
- **FastAPI Backend**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive Swagger Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **React Frontend**: [http://localhost:5173](http://localhost:5173)

---

### Manual Launch

#### 1. Backend Server:
```bash
# Navigate to backend directory
cd backend

# Install Python requirements
python -m pip install -r requirements.txt

# Run server with hot-reload
python run.py
```

#### 2. Frontend Web Interface:
```bash
# In a separate terminal, navigate to frontend
cd frontend

# Install Node dependencies
npm install

# Start Vite development server
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 🌐 Live Deployment & GitHub Guide

### 1. Push to GitHub

1. Create a new repository on [GitHub](https://github.com/new) (e.g. `statementiq`). Make sure it is set to **Public** so assessors can view your code.
2. In your terminal at the project root (`n_bank`), run:
   ```bash
   # Initialize repository on main branch
   git init -b main

   # Stage all project files (ignoring node_modules, cache, and temp files via .gitignore)
   git add .

   # Commit
   git commit -m "feat: StatementIQ complete non-LLM bank statement processing system"

   # Link your GitHub repository (replace with your actual GitHub repo URL)
   git remote add origin https://github.com/<your-username>/statementiq.git

   # Push to GitHub
   git push -u origin main
   ```

---

### 2. Live Demo Deployment on Vercel

The frontend is fully pre-configured for Vercel with [`vercel.json`](file:///C:/Users/RITI/Desktop/projects/befree/n_bank/vercel.json) and [`frontend/vercel.json`](file:///C:/Users/RITI/Desktop/projects/befree/n_bank/frontend/vercel.json).

#### Option A: Via Vercel Web Dashboard (Recommended)
1. Log in to [Vercel](https://vercel.com).
2. Click **Add New...** → **Project**.
3. Import your GitHub repository `statementiq`.
4. In the Project Configuration settings:
   - **Framework Preset**: `Vite`
   - **Root Directory**: `frontend` (or leave at root with the bundled `vercel.json`)
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
5. *(Optional for live full-stack API)* Under **Environment Variables**, add:
   - **Name**: `VITE_API_URL`
   - **Value**: `https://<your-backend-app>.onrender.com` (your deployed backend URL)
6. Click **Deploy**. Vercel will build and assign you a live URL:
   `https://statementiq-xxxx.vercel.app`

#### Option B: Via Vercel CLI
```bash
npm install -g vercel
vercel login
cd frontend
vercel --prod
```

---

### 3. Live Backend Deployment (Render / Railway with Tesseract OCR)

Because StatementIQ uses **Tesseract OCR (C++ binary)** and **OpenCV**, a containerized environment is provided via [`Dockerfile`](file:///C:/Users/RITI/Desktop/projects/befree/n_bank/Dockerfile):

#### Deploy on Render (Free):
1. Go to [Render.com](https://render.com) and click **New +** → **Web Service**.
2. Connect your GitHub repository `statementiq`.
3. Choose **Docker** as the Runtime (it will automatically detect the root `Dockerfile` containing Tesseract OCR and OpenCV).
4. Instance Type: **Free**.
5. Click **Create Web Service**. Render builds the container and provides your live backend URL (e.g. `https://statementiq-backend.onrender.com`).
6. Copy that URL and paste it as `VITE_API_URL` in your Vercel project environment variables.


---

## 📄 PDF Processing & OCR Workflow

StatementIQ handles heterogeneous bank statement formats through a multi-stage pipeline:

1. **Upload & Hash Verification**:
   - Calculates SHA-256 checksum on raw byte streams before writing to disk.
   - Detects identical re-uploads to prevent record duplication and state corruption.
   - Validates file content using magic bytes (`%PDF-`), PyMuPDF structure inspection, and a 25 MB size limit.
   - Sanitizes filenames against directory traversal attacks (`../`, `..\`, null bytes).

2. **Page-Level Type Detection**:
   - Inspects every page independently:
     - **DIGITAL**: Page contains extractable digital text stream ($> 80$ characters, high text density score).
     - **SCANNED**: Page contains primarily raster images or drawings, requiring OCR.
     - **MIXED**: Hybrid document with digital text on some pages and image scans on others.
     - **UNKNOWN**: Empty or unreadable document stream.

3. **Scanned PDF OCR Pipeline (Tesseract + OpenCV)**:
   - Renders PDF pages to 300 DPI high-resolution pixmaps.
   - Applies OpenCV computer vision preprocessing:
     - Converts to grayscale.
     - Applies bilateral/Gaussian filtering for noise reduction.
     - Performs Otsu's adaptive thresholding for binarization.
     - Detects document skew via minimum area bounding rectangle and deskews image.
   - Executes Tesseract OCR with page segmentation mode (`--psm 6` for uniform blocks of text).
   - Preserves original raw OCR text for full auditability.

4. **Transaction Parsing & Ledger Extraction**:
   - Extracts Account Details: Bank Name, Account Holder, Account Number (with masking toggle: `XXXXXX1234`), IFSC/Routing Code, Statement Period, Opening Balance, Closing Balance.
   - Robust line-item parser: extracts `Date`, `Description`, `Debit`, `Credit`, and `Balance`.
   - Handles multi-line narrations, wrapped descriptions, multi-page ledger continuity, and single-column Dr/Cr indicators (`1,500.00 Dr`, `50,000.00 Cr`).
   - Parses Indian numbering conventions (`1,20,000.00`), international formatting, and OCR artifacts where commas are scanned as dots.

5. **Ledger Verification & Unambiguous OCR Correction**:
   - Verifies row-by-row running balance formula:
     $$\text{Previous Balance} + \text{Credit} - \text{Debit} = \text{Current Balance}$$
   - When OCR noise produces ambiguous simultaneous debits and credits on a single row, applies safe mathematical correction **only if** running balance unambiguously confirms which column was valid, saving `original_ocr_value`, `ocr_correction`, and reason. If ambiguous, flags for manual review without modification.

---

## 🧠 Classification Methodology (Strictly Non-LLM)

No external generative AI APIs (such as OpenAI, Gemini, or Claude) are used for transaction categorization. The classification engine follows a deterministic priority hierarchy:

1. **Priority 1: Custom User Rules (`confidence = 1.00`)**:
   - User-defined keyword and merchant matching rules configured via dashboard.
   - Takes absolute precedence over defaults.

2. **Priority 2: Predefined Heuristic Rules (`confidence = 0.90 – 0.98`)**:
   - High-specificity merchant keywords (`SWIGGY`, `ZOMATO`, `BESCOM`, `AMAZON`, `FLIPKART`, `UBER`, `APOLLO`, `NETFLIX`, `SALARY CREDIT`) are evaluated **before** generic payment rails (`UPI`, `NEFT`, `IMPS`, `TRANSFER`) to prevent misclassification.
   - Word boundaries (`\b`) protect against false-positive substring collisions.

3. **Priority 3: Supervised Machine Learning (TF-IDF + Multinomial Naive Bayes)**:
   - Evaluated when rule heuristics do not trigger.
   - TF-IDF unigram and bigram representation with sublinear term-frequency scaling.
   - Multinomial Naive Bayes classifier with additive smoothing ($\alpha=0.2$).
   - Transactions with model probability $\ge 0.45$ are assigned the predicted class; probabilities $\ge 0.70$ are verified, while probabilities between $0.45$ and $0.70$ are flagged for review.

4. **Priority 4: Fallback / Needs Review**:
   - Transactions lacking matching rules and having low ML probability are assigned `Others` and flagged as `Needs Review`.

### Standardized Transaction Categories (16 Categories):
`Salary`, `Food & Dining`, `Shopping`, `Travel & Transport`, `Utilities & Bills`, `Rent`, `Healthcare`, `Education`, `EMI/Loan`, `ATM Withdrawal`, `Bank Charges`, `Interest`, `Refunds`, `Transfers`, `Other Income`, `Other Expenses`.

### Explainable Classification
For every classified transaction, the system records:
- `category`: Assigned classification.
- `classification_method`: `Custom Rule`, `Rule-Based`, `ML`, or `Manual Override`.
- `confidence`: Heuristic score or actual model posterior probability.
- `explanation.reason`: Human-readable explanation (e.g. `Matched rule keyword 'SWIGGY'`, `Predicted by Multinomial Naive Bayes (confidence: 84%)`).
- `explanation.model_probabilities`: Top candidate class probabilities.

---

## 📊 Model Evaluation Results

Evaluation performed on a held-out test split ($25\%$) using fixed `random_state=42`. Training data consists of $211$ diverse Indian bank transaction records with merchants, payment channels, typos, and abbreviations.

> **Transparency Notice**: The training and test datasets consist of realistic synthetic/benchmark transaction descriptions. In real-world environments, unseen merchant codes and non-standard narrations may exhibit variable accuracy.

| Metric | Score | Split & Configuration |
|---|---|---|
| **Algorithm** | TF-IDF (1-2 ngrams) + Multinomial Naive Bayes ($\alpha=0.2$) | Unigram + Bigram, Sublinear TF |
| **Total Samples** | 211 descriptions across 18 target categories | Synthetic Indian Banking Benchmark |
| **Train / Test Split** | 75% Train (158 samples) / 25% Test (53 samples) | `random_state = 42` |
| **Test Accuracy** | **52.83%** | Held-out unseen test samples |
| **Weighted Precision** | **46.99%** | Held-out unseen test samples |
| **Weighted Recall** | **52.83%** | Held-out unseen test samples |
| **Weighted F1-Score** | **47.96%** | Balanced harmonic mean |

*Note: In production workflows, high-precision deterministic rules handle $>80\%$ of recurring transactions, and the ML model acts as a secondary tier before human review.*

---

## 📑 Export Functionality & Security

### 1. 7-Sheet Styled Excel Export (`.xlsx`)
Exported via OpenPyXL with financial formatting (`#,##0.00`), readable headers, and column autofitting:
- **Sheet 1: Account Details**: Institution, account holder, masked account number, IFSC, statement period, opening balance, closing balance, currency.
- **Sheet 2: Transactions**: Line-item ledger with formatted debit, credit, running balance, category, method, confidence, and total debit/credit sum row.
- **Sheet 3: Summary**: Financial audit metrics, net flow, discrepancy calculation, reconciliation formula verification notes.
- **Sheet 4: Income by Category**: Credits aggregated by category, line-item count, total amount, and percentage share.
- **Sheet 5: Expense by Category**: Debits aggregated by category, line-item count, total amount, and percentage share.
- **Sheet 6: Review Flags**: Audit exception records, transactions flagged for review, OCR correction details, and balance discrepancies.
- **Sheet 7: Classification Explanations**: Explainability report containing transaction description, method, matched keyword, and model probability breakdown.

### 2. Multi-Statement Portfolio Export
Users can export all processed statements in a single batch:
- **Excel**: Master workbook containing `Statement Summaries` across all accounts, `Combined Transactions` (with source filename and statement ID), `Combined Income`, `Combined Expenses`, and `Flagged Review Items`. Avoids silent merging of duplicate items.
- **CSV**: Combined transaction ledger with source statement references.

### 3. Spreadsheet Formula Injection Security (CSV/Excel Injection)
To protect against formula injection vulnerabilities (CWE-1236):
- All string values (descriptions, merchant names, categories, filenames) beginning with `=`, `+`, `-`, `@`, `\t`, or `\r` are sanitized by prepending a single quote (`'`).
- Numeric values are stored as native float/int types to maintain valid mathematical calculation behavior in spreadsheet software.

---

## 🔌 API Endpoints Reference

### Statement Ingestion & Processing
- `POST /api/statements/upload`: Upload single PDF statement (validates magic bytes, size limit, path sanitization, and SHA-256 duplicate detection).
- `POST /api/statements/upload-batch`: Batch upload multiple PDF statements.
- `GET /api/statements`: List all uploaded statements and pipeline stages.
- `GET /api/statements/{id}`: Retrieve statement details, extracted ledger, and metadata.
- `POST /api/statements/{id}/process`: Execute text extraction and transaction parsing (Stages 3 & 4).
- `POST /api/statements/{id}/classify`: Run non-LLM rule and ML classification (Stage 5).
- `POST /api/statements/{id}/retry`: Re-run pipeline on failed statement.
- `PUT /api/statements/{id}/transactions/{txn_id}`: Edit transaction fields, triggering automatic balance recalculation, re-classification, and audit history logging.
- `DELETE /api/statements/{id}`: Delete statement and associated upload file.
- `DELETE /api/statements`: Clear entire statement queue with filesystem cleanup.

### Exports
- `GET /api/statements/{id}/export/excel`: Download 7-sheet styled Excel report for statement.
- `GET /api/statements/{id}/export/csv`: Download sanitized CSV for statement.
- `GET /api/statements/export/excel`: Download consolidated multi-statement Excel portfolio.
- `GET /api/statements/export/csv`: Download combined multi-statement CSV ledger.

### Classifier & Rules Management
- `GET /api/classifier/rules`: View active heuristic rule dictionary.
- `POST /api/classifier/rules`: Register custom keyword rules.
- `GET /api/classifier/info`: Retrieve ML model metadata, features, and status.
- `GET /api/classifier/evaluate`: Compute accuracy, precision, recall, F1, and confusion matrix on held-out test data.
- `POST /api/classifier/retrain`: Retrain TF-IDF + Naive Bayes model on updated training dataset.

### System & Diagnostics
- `GET /api/system`: Check Tesseract OCR engine installation status and ML status.
- `GET /api/sample-statements`: List bundled sample statement files.
- `POST /api/sample-statements/{filename}/load`: Load bundled test statement into active queue.

---

## ⚠️ Known Limitations

1. **Scanned Image Quality**: OCR accuracy depends heavily on scan resolution, lighting, and document alignment. Heavily degraded or skewed scans ($< 150$ DPI) may require manual audit.
2. **Bank Statement Layout Heterogeneity**: While the parser supports standard column arrangements, unstructured narrative statements lacking column delimiters may require manual corrections.
3. **Password-Protected PDFs**: Encrypted PDFs that do not open with blank passwords must be decrypted prior to upload.
4. **Vocabulary Coverage**: Classical machine learning without LLMs relies on training dataset n-grams; highly novel or non-standard merchant abbreviations may fall back to `Needs Review`.

---

## 🔮 Future Improvements

- **Probability Calibration**: Implementation of Platt scaling or Isotonic Regression for calibrated confidence scores.
- **Custom Bank Templates**: Layout configuration files for localized cooperative and international banking institutions.
- **Local Embedded OCR Ensembles**: Combining Tesseract with lightweight offline layout detection models (e.g. PP-Structure or LayoutLM) for complex multi-column tables.

---

## 🧪 Automated Testing & Verification

```bash
# Run complete test suite (38 automated unit, security, and e2e integration tests)
python -m pytest backend/tests -v -p no:cacheprovider

# Build frontend production bundle
cd frontend && npm run build
```
All 38 test suites pass with zero regressions.
