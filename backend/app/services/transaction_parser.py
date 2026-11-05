import re
import uuid
from typing import List, Dict, Any, Optional, Tuple
from app.schemas.statement import AccountDetails, Transaction
from app.utils.helpers import clean_text, mask_account_number, parse_amount, parse_date

KNOWN_BANKS = [
    "HDFC Bank", "State Bank of India", "SBI", "ICICI Bank", "Axis Bank",
    "Kotak Mahindra Bank", "Punjab National Bank", "Bank of Baroda",
    "Canara Bank", "Union Bank of India", "IndusInd Bank", "Yes Bank",
    "Federal Bank", "IDFC FIRST Bank", "IDBI Bank",
    "Chase", "JPMorgan Chase", "Bank of America", "Wells Fargo", "Citibank",
    "Barclays", "HSBC", "Standard Chartered"
]

class TransactionParser:
    """Extracts account details and tabular transaction records from text streams and table grids."""

    def __init__(self):
        pass

    def extract_account_details(self, text: str) -> AccountDetails:
        """Extracts Account Holder, Account Number, Bank Name, IFSC, Statement Period, and Balances."""
        details = AccountDetails()
        header_text = text
        for split_marker in [
            "TRANSACTION ACTIVITY", "TRANSACTION DETAILS", "STATEMENT TRANSACTIONS",
            "ACCOUNT ACTIVITY", "TRANSACTION SUMMARY", "DATE NARRATION"
        ]:
            idx = header_text.upper().find(split_marker)
            if idx > 0:
                header_text = header_text[:idx]
                break

        lines = [clean_text(l) for l in header_text.split("\n") if clean_text(l)]

        stops = [
            "bank name", "account holder", "customer name", "account number", "account no",
            "a/c no", "ifsc", "statement period", "period", "branch", "account type",
            "currency", "opening balance", "closing balance", "total debits", "total credits",
            "transaction details", "date", "narration", "balance", "withdrawal", "deposit"
        ]

        def find_field(label_pats: List[str]) -> Optional[str]:
            for i, line in enumerate(lines):
                for pat in label_pats:
                    m_inline = re.match(r'^' + pat + r'[\s.:\-]+\s*(.+)$', line, re.IGNORECASE)
                    if m_inline:
                        val = clean_text(m_inline.group(1))
                        for s in stops:
                            idx = val.lower().find(s.lower())
                            if idx > 0:
                                val = clean_text(val[:idx].rstrip(":- \t"))
                        if val and not any(val.lower() == s.lower() for s in stops):
                            return val

                    m_line = re.match(r'^' + pat + r'[\s.:\-]*$', line, re.IGNORECASE)
                    if m_line and i + 1 < len(lines):
                        cand = clean_text(lines[i + 1])
                        if cand and not any(cand.lower().startswith(s.lower()) for s in stops):
                            for s in stops:
                                idx = cand.lower().find(s.lower())
                                if idx > 0:
                                    cand = clean_text(cand[:idx].rstrip(":- \t"))
                            if cand:
                                return cand
            return None

        # 1. Bank Name detection
        bank_name = find_field([r'Bank\s*Name', r'Institution\s*Name', r'Name\s*of\s*Bank'])
        if not bank_name:
            for bank in KNOWN_BANKS:
                if re.search(r'\b' + re.escape(bank) + r'\b', text, re.IGNORECASE):
                    bank_name = bank
                    break
        if not bank_name:
            for line in lines[:8]:
                if "BANK" in line.upper() and not any(w in line.upper() for w in ["STATEMENT", "ILLUSTRATIVE", "PAGE", "ACCOUNT", "HOLDER", "BRANCH"]):
                    bank_name = line
                    break
        if bank_name:
            if bank_name.isupper() and len(bank_name) > 4:
                bank_name = bank_name.title()
            details.bank_name = bank_name

        # 2. Account Holder Name
        holder = find_field([
            r'Account\s*Holder(?:\s*Name)?',
            r'Customer\s*Name',
            r'Name\s*of\s*(?:the\s*)?Account\s*Holder',
            r'Client\s*Name',
            r'Beneficiary\s*Name',
            r'Name'
        ])
        if not holder:
            m_salut = re.search(r'(?:Mr\.|Mrs\.|Ms\.|M/s)\s+([A-Za-z\.\s]{3,35})(?:\n|$)', text)
            if m_salut:
                cand = clean_text(m_salut.group(1))
                if not any(stop in cand.lower() for stop in stops):
                    holder = cand
        if holder:
            details.account_holder = holder

        # 3. Account Number
        acc_num = find_field([r'Account\s*(?:Number|No|#)', r'A/C\s*(?:No|Number|#)', r'Acc\s*No', r'Account\s*ID'])
        if acc_num:
            m_acc = re.search(r'[A-Za-z0-9X\*\-]{6,22}', acc_num)
            if m_acc:
                raw_acc = m_acc.group(0).replace("-", "").replace(" ", "")
                details.account_number = raw_acc
                details.masked_account_number = mask_account_number(raw_acc)
        else:
            m_acc = re.search(r'(?:Account\s*(?:Number|No|#)|A/C\s*(?:No|#)|Acc\s*No)[\s.:#-]*([0-9A-Za-zX\*\-]{6,22})', text, re.IGNORECASE)
            if m_acc:
                raw_acc = clean_text(m_acc.group(1)).replace("-", "").replace(" ", "")
                details.account_number = raw_acc
                details.masked_account_number = mask_account_number(raw_acc)

        # 4. IFSC Code
        m_ifsc = re.search(r'\b([A-Z]{4}0[A-Z0-9]{6})\b', text)
        if m_ifsc:
            details.ifsc_code = m_ifsc.group(1)
        else:
            ifsc_val = find_field([r'IFSC(?:\s*Code)?', r'Routing\s*(?:Number|No)', r'Sort\s*Code'])
            if ifsc_val:
                details.ifsc_code = ifsc_val

        # 5. Statement Period
        period_str = find_field([r'Statement\s*Period', r'Period', r'Statement\s*from', r'Period\s*Covered'])
        if period_str:
            parts = re.split(r'\s+(?:to|-|through)\s+', period_str, flags=re.IGNORECASE)
            if len(parts) >= 2:
                p_start, _ = parse_date(clean_text(parts[0]))
                p_end, _ = parse_date(clean_text(parts[1]))
                details.statement_period_start = p_start or clean_text(parts[0])
                details.statement_period_end = p_end or clean_text(parts[1])
            else:
                details.statement_period_start = period_str
                details.statement_period_end = period_str
        else:
            period_patterns = [
                r'(?:Statement\s*Period|Period|Statement\s*from)[\s.:]*([0-9A-Za-z/.\-]+)\s*(?:to|-|through)\s*([0-9A-Za-z/.\-]+)',
                r'(?:From\s*Date)[\s.:]*([0-9A-Za-z/.\-]+)\s*(?:To\s*Date)[\s.:]*([0-9A-Za-z/.\-]+)'
            ]
            for pat in period_patterns:
                m = re.search(pat, text, re.IGNORECASE)
                if m:
                    p_start, _ = parse_date(clean_text(m.group(1)))
                    p_end, _ = parse_date(clean_text(m.group(2)))
                    details.statement_period_start = p_start or clean_text(m.group(1))
                    details.statement_period_end = p_end or clean_text(m.group(2))
                    break

        # 6. Opening & Closing Balances
        open_val = find_field([r'Opening\s*Balance', r'Bal\s*b/f', r'B/F\s*Bal(?:ance)?', r'Initial\s*Balance'])
        if open_val:
            amt = parse_amount(open_val)
            if amt is not None:
                details.opening_balance = amt
        else:
            open_patterns = [
                r'(?:Opening\s*Balance|Bal\s*b/f|B/F\s*Bal(?:ance)?)[\s.:INR$₹]*([0-9,]+(?:\.[0-9]{2})?)',
                r'(?:Initial\s*Balance)[\s.:INR$₹]*([0-9,]+(?:\.[0-9]{2})?)'
            ]
            for pat in open_patterns:
                m = re.search(pat, text, re.IGNORECASE)
                if m:
                    amt = parse_amount(m.group(1))
                    if amt is not None:
                        details.opening_balance = amt
                        break

        close_val = find_field([r'Closing\s*Balance', r'Bal\s*c/f', r'Ending\s*Balance', r'Available\s*Balance', r'Total\s*Balance'])
        if close_val:
            amt = parse_amount(close_val)
            if amt is not None:
                details.closing_balance = amt
        else:
            close_patterns = [
                r'(?:Closing\s*Balance|Bal\s*c/f|Ending\s*Balance|Available\s*Balance)[\s.:INR$₹]*([0-9,]+(?:\.[0-9]{2})?)',
                r'(?:Total\s*Balance)[\s.:INR$₹]*([0-9,]+(?:\.[0-9]{2})?)'
            ]
            for pat in close_patterns:
                m = re.search(pat, text, re.IGNORECASE)
                if m:
                    amt = parse_amount(m.group(1))
                    if amt is not None:
                        details.closing_balance = amt
                        break

        return details

    def parse_tables(self, raw_tables: List[Dict[str, Any]]) -> List[Transaction]:
        """Parses structured tables extracted by pdfplumber, handling multiple column layouts."""
        transactions: List[Transaction] = []

        for item in raw_tables:
            table = item.get("table", [])
            if not table or len(table) < 2:
                continue

            header_idx = -1
            col_map = {}

            for r_idx, row in enumerate(table[:5]):
                row_str = " ".join([str(c).lower() for c in row if c])
                if any(k in row_str for k in ["date", "txn", "transaction"]) and any(k in row_str for k in ["debit", "withdrawal", "credit", "deposit", "balance", "amount"]):
                    header_idx = r_idx
                    header_row = [str(c).strip().lower() if c else "" for c in row]
                    for c_idx, col_name in enumerate(header_row):
                        if any(k in col_name for k in ["date", "txn dt", "value dt"]):
                            if "date" not in col_map:
                                col_map["date"] = c_idx
                        elif any(k in col_name for k in ["description", "narration", "particulars", "transaction details", "remarks"]):
                            col_map["description"] = c_idx
                        elif any(k in col_name for k in ["withdrawal", "debit", "dr", "paid out"]):
                            col_map["debit"] = c_idx
                        elif any(k in col_name for k in ["deposit", "credit", "cr", "paid in"]):
                            col_map["credit"] = c_idx
                        elif any(k in col_name for k in ["amount", "txn amount", "amt"]):
                            col_map["amount"] = c_idx
                        elif any(k in col_name for k in ["type", "dr/cr", "cr/dr", "d/c", "trans type"]):
                            col_map["type"] = c_idx
                        elif any(k in col_name for k in ["balance", "bal", "closing", "running bal"]):
                            col_map["balance"] = c_idx
                    break

            if header_idx == -1 or "date" not in col_map:
                continue

            current_txn: Optional[Transaction] = None

            for row in table[header_idx + 1:]:
                if not any(row):
                    continue

                date_cell = row[col_map["date"]] if col_map.get("date") is not None and col_map["date"] < len(row) else None
                desc_cell = row[col_map["description"]] if col_map.get("description") is not None and col_map["description"] < len(row) else ""
                debit_cell = row[col_map["debit"]] if col_map.get("debit") is not None and col_map["debit"] < len(row) else None
                credit_cell = row[col_map["credit"]] if col_map.get("credit") is not None and col_map["credit"] < len(row) else None
                bal_cell = row[col_map["balance"]] if col_map.get("balance") is not None and col_map["balance"] < len(row) else None
                amount_cell = row[col_map["amount"]] if col_map.get("amount") is not None and col_map["amount"] < len(row) else None
                type_cell = row[col_map["type"]] if col_map.get("type") is not None and col_map["type"] < len(row) else ""

                std_date, raw_date = parse_date(str(date_cell) if date_cell else "")

                if std_date and (debit_cell or credit_cell or amount_cell or bal_cell):
                    if current_txn:
                        transactions.append(current_txn)

                    debit_val = parse_amount(debit_cell) or 0.0
                    credit_val = parse_amount(credit_cell) or 0.0
                    bal_val = parse_amount(bal_cell)

                    # Handle single amount column with DR/CR flag
                    if "amount" in col_map and not debit_cell and not credit_cell:
                        amt = parse_amount(amount_cell) or 0.0
                        amt_str = (str(amount_cell) + " " + str(type_cell)).upper().strip()
                        if "DR" in amt_str or amt < 0:
                            debit_val = abs(amt)
                            credit_val = 0.0
                        else:
                            credit_val = abs(amt)
                            debit_val = 0.0

                    # Mutual exclusivity check: a transaction must not have both debit and credit
                    if debit_val > 0 and credit_val > 0:
                        if transactions and transactions[-1].balance is not None and bal_val is not None:
                            prev_b = transactions[-1].balance
                            diff = round(bal_val - prev_b, 2)
                            if diff > 0 and abs(diff - credit_val) < 0.05:
                                debit_val = 0.0
                            elif diff < 0 and abs(abs(diff) - debit_val) < 0.05:
                                credit_val = 0.0

                    current_txn = Transaction(
                        id=f"TXN-{uuid.uuid4().hex[:8].upper()}",
                        date=std_date,
                        description=clean_text(str(desc_cell)) if desc_cell else "Transaction",
                        debit=debit_val,
                        credit=credit_val,
                        balance=bal_val,
                        raw_text=clean_text(" | ".join([str(c) for c in row if c]))
                    )
                elif current_txn and desc_cell and not debit_cell and not credit_cell and not amount_cell:
                    # Multi-line description continuation
                    current_txn.description += " " + clean_text(str(desc_cell))

            if current_txn:
                transactions.append(current_txn)

        return transactions

    def parse_positional_words(self, pages: List[Dict[str, Any]]) -> List[Transaction]:
        """Maps tabular transactions using precise OCR/digital word positions and table header boundaries."""
        import numpy as np
        transactions: List[Transaction] = []
        last_col_bounds = None

        for page in pages:
            words = page.get("words", [])
            if not words or len(words) < 8:
                continue

            header_candidates = [
                w for w in words 
                if re.search(r'\b(date|narration|description|particulars|withdrawal|deposit|closing|balance|debit|credit|dr|cr|amount)\b', w['text'].lower())
            ]

            col_headers = {}
            header_y = None

            if header_candidates:
                bins: Dict[int, List[Dict[str, Any]]] = {}
                for w in header_candidates:
                    b_key = int(w['top'] // 40) * 40
                    bins.setdefault(b_key, []).append(w)
                best_bin_y = max(bins.keys(), key=lambda k: len(bins[k]))
                header_y = float(np.median([w['top'] for w in bins[best_bin_y]]))

                for w in words:
                    if abs(w['top'] - header_y) < 45:
                        txt = w['text'].lower()
                        if re.search(r'\b(date|txn\s*dt|value\s*dt)\b', txt) and 'date' not in col_headers:
                            col_headers['date'] = w['left']
                        elif re.search(r'\b(narration|description|particulars|details|remarks)\b', txt) and 'desc' not in col_headers:
                            col_headers['desc'] = w['left']
                        elif re.search(r'\b(withdrawal|debit|dr|paid\s*out)\b', txt) and 'debit' not in col_headers:
                            col_headers['debit'] = w['left']
                        elif re.search(r'\b(deposit|credit|cr|paid\s*in)\b', txt) and 'credit' not in col_headers:
                            col_headers['credit'] = w['left']
                        elif re.search(r'\b(amount|amt)\b', txt) and 'amount' not in col_headers:
                            col_headers['amount'] = w['left']
                        elif re.search(r'\b(closing|balance|bal)\b', txt) and 'balance' not in col_headers:
                            col_headers['balance'] = w['left']

            if col_headers and ('debit' in col_headers or 'credit' in col_headers or 'balance' in col_headers or 'amount' in col_headers):
                desc_x = col_headers.get('desc', 440)
                debit_x = col_headers.get('debit', 1440)
                credit_x = col_headers.get('credit', 1780)
                has_balance = 'balance' in col_headers
                balance_x = col_headers.get('balance', 2110)

                split_desc_debit = debit_x - 60
                split_debit_credit = credit_x - 35
                split_credit_balance = (balance_x - 35) if has_balance else 999999.0
                last_col_bounds = (desc_x, split_desc_debit, split_debit_credit, split_credit_balance, has_balance)
            elif last_col_bounds:
                desc_x, split_desc_debit, split_debit_credit, split_credit_balance, has_balance = last_col_bounds
            else:
                continue

            min_y = (header_y + 35) if header_y is not None else 0
            table_words = [w for w in words if w['top'] > min_y]
            table_words.sort(key=lambda w: (w['top'], w['left']))

            rows = []
            current_row = []
            current_row_y = None

            for w in table_words:
                if current_row_y is None:
                    current_row = [w]
                    current_row_y = w['top']
                elif abs(w['top'] - current_row_y) <= 30:
                    current_row.append(w)
                    current_row_y = sum(x['top'] for x in current_row) / len(current_row)
                else:
                    if current_row:
                        rows.append(current_row)
                    current_row = [w]
                    current_row_y = w['top']
            if current_row:
                rows.append(current_row)

            current_txn: Optional[Transaction] = None

            for r in rows:
                r.sort(key=lambda w: w['left'])
                date_words = []
                desc_words = []
                debit_words = []
                credit_words = []
                balance_words = []

                for w in r:
                    x = w['left']
                    if x < desc_x - 30:
                        date_words.append(w['text'])
                    elif x < split_desc_debit:
                        desc_words.append(w['text'])
                    elif x < split_debit_credit:
                        debit_words.append(w['text'])
                    elif x < split_credit_balance:
                        credit_words.append(w['text'])
                    else:
                        balance_words.append(w['text'])

                d_str = " ".join(date_words).strip()
                std_date, _ = parse_date(d_str)
                if not std_date and date_words:
                    std_date, _ = parse_date(date_words[0])

                if std_date:
                    if current_txn:
                        transactions.append(current_txn)

                    desc = clean_text(" ".join(desc_words))
                    deb_val = parse_amount("".join(debit_words)) or 0.0
                    cred_val = parse_amount("".join(credit_words)) or 0.0
                    bal_val = parse_amount("".join(balance_words)) if has_balance and balance_words else None

                    # Mutual exclusivity resolution
                    if deb_val > 0 and cred_val > 0:
                        if transactions and transactions[-1].balance is not None and bal_val is not None:
                            prev_b = transactions[-1].balance
                            diff = round(bal_val - prev_b, 2)
                            if diff > 0 and abs(diff - cred_val) < 0.05:
                                deb_val = 0.0
                            elif diff < 0 and abs(abs(diff) - deb_val) < 0.05:
                                cred_val = 0.0

                    current_txn = Transaction(
                        id=f"TXN-{uuid.uuid4().hex[:8].upper()}",
                        date=std_date,
                        description=desc if desc else "Transaction",
                        debit=deb_val,
                        credit=cred_val,
                        balance=bal_val,
                        raw_text=clean_text(" ".join([w['text'] for w in r]))
                    )
                elif current_txn and desc_words and not debit_words and not credit_words:
                    current_txn.description += " " + clean_text(" ".join(desc_words))

            if current_txn:
                transactions.append(current_txn)

        return transactions

    def parse_text_stream(self, text: str) -> List[Transaction]:
        """Parses transactions from raw text lines (vital for OCR and digital layouts without strict PDF table lines)."""
        transactions: List[Transaction] = []
        lines = text.split("\n")

        date_pattern = re.compile(
            r'^(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4}|\d{1,2}-(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*-\d{2,4})\b',
            re.IGNORECASE
        )

        current_txn: Optional[Transaction] = None

        for line in lines:
            trimmed = line.strip()
            if not trimmed:
                continue

            if any(h in trimmed.lower() for h in [
                "page of", "statement of account", "transaction date", "value date",
                "opening balance", "closing balance", "total debit", "total credit",
                "generated on", "customer care", "ifsc code"
            ]):
                continue

            match = date_pattern.match(trimmed)
            if match:
                date_part = match.group(1)
                std_date, _ = parse_date(date_part)

                rest = trimmed[match.end():].strip()
                tokens = rest.split()

                tail_numbers = []
                idx = len(tokens) - 1
                while idx >= 0:
                    tok = tokens[idx]
                    amt = parse_amount(tok)
                    if amt is not None and re.search(r'\d', tok) and not re.search(r'^[A-Za-z]', tok):
                        tail_numbers.insert(0, (amt, tok))
                        idx -= 1
                        if len(tail_numbers) >= 3:
                            break
                    else:
                        break

                if tail_numbers:
                    if current_txn:
                        transactions.append(current_txn)

                    desc_candidate = clean_text(" ".join(tokens[:idx + 1]))

                    debit_val = 0.0
                    credit_val = 0.0
                    balance_val = None

                    rest_upper = rest.upper()
                    if len(tail_numbers) == 1:
                        val = tail_numbers[0][0]
                        if any(k in rest_upper for k in ["DR", "WITHDRAWAL", "DEBIT", "RENT", "BILL", "SWIGGY", "AMAZON", "ATM", "UBER", "CHARGES"]):
                            debit_val = abs(val)
                        else:
                            credit_val = abs(val)
                    elif len(tail_numbers) == 2:
                        val, raw_v = tail_numbers[0]
                        bal_val, _ = tail_numbers[1]
                        balance_val = bal_val
                        if any(k in rest_upper for k in ["CR", "CREDIT", "DEPOSIT", "SALARY", "DIVIDEND", "BONUS"]):
                            credit_val = abs(val)
                        elif any(k in rest_upper for k in ["DR", "WITHDRAWAL", "DEBIT", "RENT", "BILL", "SWIGGY", "AMAZON", "ATM", "UBER", "CHARGES"]):
                            debit_val = abs(val)
                        else:
                            if transactions and transactions[-1].balance is not None:
                                prev_b = transactions[-1].balance
                                if bal_val > prev_b:
                                    credit_val = abs(val)
                                else:
                                    debit_val = abs(val)
                            else:
                                debit_val = abs(val)
                    elif len(tail_numbers) >= 3:
                        debit_val = tail_numbers[-3][0]
                        credit_val = tail_numbers[-2][0]
                        balance_val = tail_numbers[-1][0]

                    current_txn = Transaction(
                        id=f"TXN-{uuid.uuid4().hex[:8].upper()}",
                        date=std_date or date_part,
                        description=desc_candidate if desc_candidate else "Transaction",
                        debit=debit_val,
                        credit=credit_val,
                        balance=balance_val,
                        raw_text=trimmed
                    )
            elif current_txn:
                if not re.match(r'^\d+(\.\d+)?$', trimmed) and len(trimmed) > 2:
                    current_txn.description += " " + clean_text(trimmed)

        if current_txn:
            transactions.append(current_txn)

        return transactions

    def extract_transactions(
        self,
        raw_tables: List[Dict[str, Any]],
        full_text: str,
        pages: Optional[List[Dict[str, Any]]] = None,
        opening_balance: Optional[float] = None
    ) -> List[Transaction]:
        """Combines positional column mapping, table grid parsing, and text stream parsing to get the best result."""
        txns: List[Transaction] = []

        if pages:
            pos_txns = self.parse_positional_words(pages)
            if len(pos_txns) >= 3:
                txns = pos_txns

        if not txns:
            table_txns = self.parse_tables(raw_tables)
            if len(table_txns) >= 3:
                txns = table_txns

        if not txns:
            text_txns = self.parse_text_stream(full_text)
            txns = text_txns

        # Calculate running balance if missing balance column but opening balance is known
        if txns and all(t.balance is None for t in txns) and opening_balance is not None:
            running = opening_balance
            for t in txns:
                running = round(running + (t.credit or 0.0) - (t.debit or 0.0), 2)
                t.balance = running

        return txns
