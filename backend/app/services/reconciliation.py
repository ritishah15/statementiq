from typing import List, Optional
from app.schemas.statement import Transaction, AccountDetails, ReconciliationSummary

class ReconciliationService:
    """Performs mathematical balance reconciliation and computes financial aggregates."""

    @staticmethod
    def reconcile(account: AccountDetails, transactions: List[Transaction]) -> ReconciliationSummary:
        total_txns = len(transactions)
        total_debits = sum(t.debit or 0.0 for t in transactions)
        total_credits = sum(t.credit or 0.0 for t in transactions)
        net_flow = total_credits - total_debits

        summary = ReconciliationSummary(
            total_transactions=total_txns,
            total_debits=round(total_debits, 2),
            total_credits=round(total_credits, 2),
            net_flow=round(net_flow, 2),
            opening_balance=account.opening_balance,
            closing_balance=account.closing_balance
        )

        # Check if both opening and closing balances are present
        if account.opening_balance is not None and account.closing_balance is not None:
            calc_closing = account.opening_balance + total_credits - total_debits
            summary.calculated_closing_balance = round(calc_closing, 2)
            discrepancy = round(calc_closing - account.closing_balance, 2)
            summary.discrepancy = discrepancy

            # Tolerance for rounding errors
            if abs(discrepancy) <= 0.05:
                summary.is_reconciled = True
                summary.reconciliation_status = "Reconciled"
                summary.notes = "All extracted transactions mathematically reconcile with opening and closing balances (0.00 discrepancy)."
            else:
                summary.is_reconciled = False
                summary.reconciliation_status = "Discrepancy Detected"
                summary.notes = f"Balance variance of {discrepancy:,.2f} detected between net flows and reported closing balance."
        elif account.opening_balance is None or account.closing_balance is None:
            summary.is_reconciled = False
            summary.reconciliation_status = "Missing Balance Information"
            summary.notes = "Opening or closing balance not found in document header. Direct mathematical reconciliation cannot be verified."

        return summary
