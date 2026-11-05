import re
from typing import List, Dict, Any, Tuple, Optional
from app.schemas.statement import Transaction

class DataValidator:
    """Validates extracted transactions and flags anomalies, discrepancies, duplicates, and incomplete records."""

    @staticmethod
    def normalize_desc(desc: str) -> str:
        """Normalizes transaction description for duplicate comparison by removing noise and punctuation."""
        if not desc:
            return ""
        d = re.sub(r'[^A-Za-z0-9\s]', ' ', desc.upper())
        # Remove common numeric reference ids e.g. /1928374/
        d = re.sub(r'\b\d{6,}\b', ' ', d)
        return re.sub(r'\s+', ' ', d).strip()

    @classmethod
    def detect_duplicate_transactions(cls, transactions: List[Transaction]) -> List[Transaction]:
        """
        Identifies exact and potential overlapping transactions using date, normalized description, amount, direction, and balance.
        Never automatically deletes matches; stores warnings and flags for user decision.
        """
        seen_exact: Dict[Tuple[str, float, str, str], str] = {}
        seen_potential: Dict[Tuple[str, float, str], str] = {}

        for txn in transactions:
            deb = txn.debit or 0.0
            cred = txn.credit or 0.0
            amt = deb if deb > 0 else cred
            direction = "DEBIT" if deb > 0 else "CREDIT"
            date = txn.date or ""
            norm_desc = cls.normalize_desc(txn.description or "")

            if amt > 0 and date:
                exact_key = (date, round(amt, 2), direction, norm_desc)
                potential_key = (date, round(amt, 2), direction)

                if exact_key in seen_exact:
                    prior_id = seen_exact[exact_key]
                    txn.validation_flags.append("exact_duplicate_transaction")
                    txn.review_status = "Needs Review"
                    if not txn.explanation:
                        txn.explanation = {}
                    txn.explanation["duplicate_warning"] = (
                        f"Exact duplicate detected: identical date, amount (INR {amt:,.2f}), and description to transaction {prior_id}."
                    )
                elif potential_key in seen_potential:
                    prior_id = seen_potential[potential_key]
                    txn.validation_flags.append("potential_duplicate_transaction")
                    txn.review_status = "Needs Review"
                    if not txn.explanation:
                        txn.explanation = {}
                    txn.explanation["duplicate_warning"] = (
                        f"Potential duplicate detected: identical date and amount (INR {amt:,.2f}) to transaction {prior_id}. Verify if this is an intentional repeat or duplicate."
                    )
                else:
                    seen_exact[exact_key] = txn.id
                    seen_potential[potential_key] = txn.id

        return transactions

    @classmethod
    def correct_ocr_amounts(cls, transactions: List[Transaction], opening_balance: Optional[float] = None) -> List[Transaction]:
        """
        Safely corrects unambiguous OCR extraction anomalies verified against the running balance formula:
        Previous Balance + Credit - Debit = Current Balance.
        Never silently changes numbers: stores original OCR value, corrected value, and explanation.
        If ambiguous or multiple interpretations exist, flags for manual review without modification.
        """
        running_bal = opening_balance

        for txn in transactions:
            deb = txn.debit or 0.0
            cred = txn.credit or 0.0
            bal = txn.balance

            if running_bal is not None and bal is not None:
                expected_diff = round(bal - running_bal, 2)

                # Case 1: Simultaneous debit and credit populated (e.g. OCR column bleed or noise)
                if deb > 0 and cred > 0:
                    cand_credit_only = round(running_bal + cred, 2)
                    cand_debit_only = round(running_bal - deb, 2)

                    credit_matches = abs(cand_credit_only - bal) <= 0.05
                    debit_matches = abs(cand_debit_only - bal) <= 0.05

                    if credit_matches and not debit_matches:
                        # Unambiguous: debit was stray OCR noise
                        txn.original_ocr_value = {"debit": deb, "credit": cred, "balance": bal}
                        txn.debit = 0.0
                        txn.ocr_correction = {
                            "field": "debit",
                            "original_value": deb,
                            "corrected_value": 0.0,
                            "reason": f"Unambiguous OCR correction: Running balance confirmed credit of {cred:,.2f}; removed stray OCR debit noise {deb:,.2f}."
                        }
                    elif debit_matches and not credit_matches:
                        # Unambiguous: credit was stray OCR noise
                        txn.original_ocr_value = {"debit": deb, "credit": cred, "balance": bal}
                        txn.credit = 0.0
                        txn.ocr_correction = {
                            "field": "credit",
                            "original_value": cred,
                            "corrected_value": 0.0,
                            "reason": f"Unambiguous OCR correction: Running balance confirmed debit of {deb:,.2f}; removed stray OCR credit noise {cred:,.2f}."
                        }
                    else:
                        # Ambiguous: both or neither match, leave intact and flag for manual audit
                        txn.validation_flags.append("uncertain_ocr_amount")
                        txn.review_status = "Needs Review"

                # Case 2: Column transposition (debit placed in credit or vice-versa)
                elif deb == 0 and cred > 0 and expected_diff < 0:
                    if abs(round(running_bal - cred, 2) - bal) <= 0.05:
                        txn.original_ocr_value = {"debit": deb, "credit": cred, "balance": bal}
                        txn.debit = cred
                        txn.credit = 0.0
                        txn.ocr_correction = {
                            "field": "column_transposition",
                            "original_value": f"Credit: {cred:,.2f}",
                            "corrected_value": f"Debit: {cred:,.2f}",
                            "reason": f"Unambiguous transposition: balance decreased by {cred:,.2f}, moved amount to debit column."
                        }
                elif cred == 0 and deb > 0 and expected_diff > 0:
                    if abs(round(running_bal + deb, 2) - bal) <= 0.05:
                        txn.original_ocr_value = {"debit": deb, "credit": cred, "balance": bal}
                        txn.credit = deb
                        txn.debit = 0.0
                        txn.ocr_correction = {
                            "field": "column_transposition",
                            "original_value": f"Debit: {deb:,.2f}",
                            "corrected_value": f"Credit: {deb:,.2f}",
                            "reason": f"Unambiguous transposition: balance increased by {deb:,.2f}, moved amount to credit column."
                        }

            if txn.balance is not None:
                running_bal = txn.balance

        return transactions

    @staticmethod
    def validate_transaction(txn: Transaction, prev_balance: Optional[float] = None) -> Transaction:
        flags = []

        # 1. Date validation
        if not txn.date or txn.date.strip() == "":
            flags.append("missing_date")
        else:
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', txn.date):
                flags.append("non_standard_date_format")

        # 2. Description validation
        desc = (txn.description or "").strip()
        if not desc or len(desc) < 3 or desc.lower() in ["transaction", "na", "n/a", "-"]:
            flags.append("empty_or_vague_description")

        # 3. Debit & Credit validation
        deb = txn.debit or 0.0
        cred = txn.credit or 0.0

        if deb < 0:
            flags.append("negative_debit_value")
        if cred < 0:
            flags.append("negative_credit_value")

        if deb == 0.0 and cred == 0.0:
            flags.append("zero_amount_transaction")
        elif deb > 0 and cred > 0:
            flags.append("simultaneous_debit_credit")

        # 4. Running Balance validation
        # Formula: Previous Balance + Credit - Debit = Current Balance
        if txn.balance is not None:
            if txn.balance < 0:
                flags.append("negative_balance_overdraft")
            if prev_balance is not None:
                expected_balance = round(prev_balance + cred - deb, 2)
                diff = round(txn.balance - expected_balance, 2)
                if abs(diff) > 0.05:
                    flags.append("running_balance_mismatch")
                    if not txn.explanation:
                        txn.explanation = {}
                    txn.explanation["reconciliation_mismatch"] = {
                        "expected_balance": expected_balance,
                        "actual_balance": txn.balance,
                        "difference": diff,
                        "previous_balance": prev_balance
                    }
        else:
            flags.append("missing_running_balance")

        # Determine review status and update flags
        if txn.review_status == "Corrected":
            txn.validation_flags = flags
        else:
            txn.validation_flags = list(dict.fromkeys(txn.validation_flags + flags))
            if txn.validation_flags:
                txn.review_status = "Needs Review"
            else:
                txn.review_status = "Verified"

        return txn

    @classmethod
    def validate_all(cls, transactions: List[Transaction], opening_balance: Optional[float] = None) -> List[Transaction]:
        """Runs unambiguous OCR amount corrections, running balance validations, and duplicate checks."""
        # 1. Safe, unambiguous OCR correction
        corrected_txns = cls.correct_ocr_amounts(transactions, opening_balance=opening_balance)

        # 2. Running balance mathematical verification
        validated = []
        running_bal = opening_balance
        for txn in corrected_txns:
            val_t = cls.validate_transaction(txn, prev_balance=running_bal)
            validated.append(val_t)
            if txn.balance is not None:
                running_bal = txn.balance

        # 3. Duplicate detection
        final_txns = cls.detect_duplicate_transactions(validated)
        return final_txns
