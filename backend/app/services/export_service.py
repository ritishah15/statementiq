import io
import csv
from typing import List, Dict, Any, Optional, Tuple
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from app.schemas.statement import AccountDetails, Transaction, ReconciliationSummary
from app.utils.helpers import sanitize_spreadsheet_value


class ExportService:
    """Generates styled multi-sheet Excel (.xlsx) workbooks and CSV exports with formula injection protection."""

    # FinTech Styling constants
    HEADER_FILL = PatternFill(start_color="172B4D", end_color="172B4D", fill_type="solid")  # Deep Navy
    SUB_FILL = PatternFill(start_color="0D9488", end_color="0D9488", fill_type="solid")     # Teal Accent
    ACCENT_FILL = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")  # Light Slate
    TOTAL_FILL = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")   # Total Bar Fill
    HEADER_FONT = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    TITLE_FONT = Font(name="Calibri", size=14, bold=True, color="172B4D")
    BOLD_FONT = Font(name="Calibri", size=11, bold=True)
    REGULAR_FONT = Font(name="Calibri", size=11)
    THIN_BORDER = Border(
        left=Side(style='thin', color='E2E8F0'),
        right=Side(style='thin', color='E2E8F0'),
        top=Side(style='thin', color='E2E8F0'),
        bottom=Side(style='thin', color='E2E8F0')
    )
    TOTAL_BORDER = Border(
        top=Side(style='thin', color='94A3B8'),
        bottom=Side(style='double', color='172B4D')
    )

    @classmethod
    def generate_excel(
        cls,
        account: AccountDetails,
        transactions: List[Transaction],
        reconciliation: ReconciliationSummary,
        source_filename: Optional[str] = None
    ) -> io.BytesIO:
        """
        Generates a 7-sheet comprehensive financial report in Excel:
        1. Account Details
        2. Transactions (with totals row)
        3. Summary (financial audit & formula verification)
        4. Income by Category
        5. Expense by Category
        6. Review Flags
        7. Classification Explanations
        """
        wb = openpyxl.Workbook()

        # ----------------- SHEET 1: Account Details -----------------
        ws_account = wb.active
        ws_account.title = "Account Details"
        ws_account.views.sheetView[0].showGridLines = True

        ws_account["A1"] = "StatementIQ – Bank Account Details"
        ws_account["A1"].font = cls.TITLE_FONT

        if source_filename:
            ws_account["A2"] = f"Source Document: {sanitize_spreadsheet_value(source_filename)}"
            ws_account["A2"].font = Font(name="Calibri", size=10, italic=True, color="64748B")

        account_rows = [
            ("Bank Name", sanitize_spreadsheet_value(account.bank_name or "Not Found")),
            ("Account Holder Name", sanitize_spreadsheet_value(account.account_holder or "Not Found")),
            ("Account Number", sanitize_spreadsheet_value(account.account_number or "Not Found")),
            ("Masked Account Number", sanitize_spreadsheet_value(account.masked_account_number or "Not Found")),
            ("IFSC / Routing Code", sanitize_spreadsheet_value(account.ifsc_code or "Not Found")),
            ("Statement Period Start", sanitize_spreadsheet_value(account.statement_period_start or "Not Found")),
            ("Statement Period End", sanitize_spreadsheet_value(account.statement_period_end or "Not Found")),
            ("Opening Balance", account.opening_balance if account.opening_balance is not None else "Not Found"),
            ("Closing Balance", account.closing_balance if account.closing_balance is not None else "Not Found"),
            ("Currency", sanitize_spreadsheet_value(account.currency or "INR"))
        ]

        start_row = 4
        ws_account[f"A{start_row}"] = "Account Field"
        ws_account[f"B{start_row}"] = "Extracted Value"
        ws_account[f"A{start_row}"].font = cls.HEADER_FONT
        ws_account[f"A{start_row}"].fill = cls.HEADER_FILL
        ws_account[f"B{start_row}"].font = cls.HEADER_FONT
        ws_account[f"B{start_row}"].fill = cls.HEADER_FILL

        for idx, (label, val) in enumerate(account_rows, start=start_row + 1):
            ws_account[f"A{idx}"] = label
            ws_account[f"A{idx}"].font = cls.BOLD_FONT
            ws_account[f"A{idx}"].border = cls.THIN_BORDER
            ws_account[f"B{idx}"] = val
            ws_account[f"B{idx}"].border = cls.THIN_BORDER
            if isinstance(val, (int, float)):
                ws_account[f"B{idx}"].number_format = '#,##0.00'
                ws_account[f"B{idx}"].alignment = Alignment(horizontal="right")

        # ----------------- SHEET 2: Transactions -----------------
        ws_txns = wb.create_sheet(title="Transactions")
        ws_txns.views.sheetView[0].showGridLines = True

        txn_headers = [
            "Transaction ID", "Date", "Description", "Debit", "Credit",
            "Balance", "Category", "Classification Method", "Confidence", "Review Status"
        ]

        for col_idx, h in enumerate(txn_headers, start=1):
            cell = ws_txns.cell(row=1, column=col_idx, value=h)
            cell.font = cls.HEADER_FONT
            cell.fill = cls.HEADER_FILL
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = cls.THIN_BORDER

        total_debits = 0.0
        total_credits = 0.0

        for r_idx, t in enumerate(transactions, start=2):
            deb = float(t.debit) if (t.debit is not None and t.debit > 0) else 0.0
            crd = float(t.credit) if (t.credit is not None and t.credit > 0) else 0.0
            total_debits += deb
            total_credits += crd

            row_data = [
                sanitize_spreadsheet_value(t.id),
                sanitize_spreadsheet_value(t.date),
                sanitize_spreadsheet_value(t.description),
                deb,
                crd,
                float(t.balance) if t.balance is not None else "",
                sanitize_spreadsheet_value(t.category),
                sanitize_spreadsheet_value(t.classification_method),
                f"{int(t.confidence * 100)}%" if t.confidence is not None else "N/A",
                sanitize_spreadsheet_value(t.review_status)
            ]

            for c_idx, val in enumerate(row_data, start=1):
                cell = ws_txns.cell(row=r_idx, column=c_idx, value=val)
                cell.border = cls.THIN_BORDER
                cell.font = cls.REGULAR_FONT
                if c_idx in [4, 5]:  # Debit, Credit
                    cell.number_format = '#,##0.00'
                    cell.alignment = Alignment(horizontal="right")
                elif c_idx == 6 and isinstance(val, (int, float)):
                    cell.number_format = '#,##0.00'
                    cell.alignment = Alignment(horizontal="right")
                elif c_idx in [1, 2, 8, 9, 10]:
                    cell.alignment = Alignment(horizontal="center")

        # Total Row for Sheet 2
        total_row_idx = len(transactions) + 2
        ws_txns.cell(row=total_row_idx, column=1, value="Total")
        ws_txns.cell(row=total_row_idx, column=1).font = cls.BOLD_FONT
        ws_txns.cell(row=total_row_idx, column=1).alignment = Alignment(horizontal="center")
        ws_txns.cell(row=total_row_idx, column=1).border = cls.TOTAL_BORDER
        ws_txns.cell(row=total_row_idx, column=1).fill = cls.TOTAL_FILL

        for c in range(2, 4):
            c_cell = ws_txns.cell(row=total_row_idx, column=c, value="")
            c_cell.border = cls.TOTAL_BORDER
            c_cell.fill = cls.TOTAL_FILL

        deb_cell = ws_txns.cell(row=total_row_idx, column=4, value=round(total_debits, 2))
        deb_cell.number_format = '#,##0.00'
        deb_cell.font = cls.BOLD_FONT
        deb_cell.alignment = Alignment(horizontal="right")
        deb_cell.border = cls.TOTAL_BORDER
        deb_cell.fill = cls.TOTAL_FILL

        crd_cell = ws_txns.cell(row=total_row_idx, column=5, value=round(total_credits, 2))
        crd_cell.number_format = '#,##0.00'
        crd_cell.font = cls.BOLD_FONT
        crd_cell.alignment = Alignment(horizontal="right")
        crd_cell.border = cls.TOTAL_BORDER
        crd_cell.fill = cls.TOTAL_FILL

        for c in range(6, len(txn_headers) + 1):
            c_cell = ws_txns.cell(row=total_row_idx, column=c, value="")
            c_cell.border = cls.TOTAL_BORDER
            c_cell.fill = cls.TOTAL_FILL

        # ----------------- SHEET 3: Summary -----------------
        ws_summary = wb.create_sheet(title="Summary")
        ws_summary.views.sheetView[0].showGridLines = True

        ws_summary["A1"] = "StatementIQ – Reconciliation & Audit Summary"
        ws_summary["A1"].font = cls.TITLE_FONT

        summary_rows = [
            ("Total Transactions Processed", reconciliation.total_transactions),
            ("Total Debits (Withdrawals)", reconciliation.total_debits),
            ("Total Credits (Deposits)", reconciliation.total_credits),
            ("Net Liquidity Flow (Credits - Debits)", reconciliation.net_flow),
            ("Opening Balance", reconciliation.opening_balance if reconciliation.opening_balance is not None else "Not Found"),
            ("Reported Closing Balance", account.closing_balance if account.closing_balance is not None else "Not Found"),
            ("Calculated Closing Balance (Opening + Credits - Debits)", reconciliation.calculated_closing_balance if reconciliation.calculated_closing_balance is not None else "N/A"),
            ("Discrepancy Amount", reconciliation.discrepancy if reconciliation.discrepancy is not None else 0.0),
            ("Reconciliation Status", sanitize_spreadsheet_value(reconciliation.reconciliation_status)),
            ("Mathematical Formula Verified", "Opening Balance + Total Credits - Total Debits = Closing Balance"),
            ("Reconciliation Notes", sanitize_spreadsheet_value(reconciliation.notes))
        ]

        ws_summary["A3"] = "Reconciliation & Financial Metric"
        ws_summary["B3"] = "Calculated Value"
        ws_summary["A3"].font = cls.HEADER_FONT
        ws_summary["A3"].fill = cls.SUB_FILL
        ws_summary["B3"].font = cls.HEADER_FONT
        ws_summary["B3"].fill = cls.SUB_FILL

        for s_idx, (s_label, s_val) in enumerate(summary_rows, start=4):
            ws_summary[f"A{s_idx}"] = s_label
            ws_summary[f"A{s_idx}"].font = cls.BOLD_FONT
            ws_summary[f"A{s_idx}"].border = cls.THIN_BORDER
            ws_summary[f"B{s_idx}"] = s_val
            ws_summary[f"B{s_idx}"].border = cls.THIN_BORDER
            if isinstance(s_val, (int, float)):
                ws_summary[f"B{s_idx}"].number_format = '#,##0.00'
                ws_summary[f"B{s_idx}"].alignment = Alignment(horizontal="right")

        # ----------------- SHEET 4: Income by Category -----------------
        ws_income = wb.create_sheet(title="Income by Category")
        ws_income.views.sheetView[0].showGridLines = True

        ws_income["A1"] = "StatementIQ – Income Breakdown by Category"
        ws_income["A1"].font = cls.TITLE_FONT

        income_headers = ["Category", "Transaction Count", "Total Income (Credits)", "% of Total Income"]
        for c_idx, h in enumerate(income_headers, start=1):
            cell = ws_income.cell(row=3, column=c_idx, value=h)
            cell.font = cls.HEADER_FONT
            cell.fill = cls.SUB_FILL
            cell.alignment = Alignment(horizontal="center")
            cell.border = cls.THIN_BORDER

        income_map: Dict[str, Dict[str, Any]] = {}
        credit_txns = [t for t in transactions if t.credit and t.credit > 0]
        sum_credits = sum(t.credit for t in credit_txns) if credit_txns else 0.0

        for t in credit_txns:
            cat = t.category or "Other Income"
            if cat not in income_map:
                income_map[cat] = {"count": 0, "amount": 0.0}
            income_map[cat]["count"] += 1
            income_map[cat]["amount"] += t.credit

        # Sort categories by income descending
        sorted_income = sorted(income_map.items(), key=lambda x: x[1]["amount"], reverse=True)

        curr_r = 4
        for cat, data in sorted_income:
            pct = (data["amount"] / sum_credits * 100.0) if sum_credits > 0 else 0.0
            row_vals = [
                sanitize_spreadsheet_value(cat),
                data["count"],
                round(data["amount"], 2),
                f"{pct:.1f}%"
            ]
            for c_idx, v in enumerate(row_vals, start=1):
                cell = ws_income.cell(row=curr_r, column=c_idx, value=v)
                cell.border = cls.THIN_BORDER
                if c_idx == 1:
                    cell.font = cls.BOLD_FONT
                elif c_idx == 2:
                    cell.alignment = Alignment(horizontal="center")
                elif c_idx == 3:
                    cell.number_format = '#,##0.00'
                    cell.alignment = Alignment(horizontal="right")
                elif c_idx == 4:
                    cell.alignment = Alignment(horizontal="right")
            curr_r += 1

        # Income Total Row
        if not sorted_income:
            ws_income.cell(row=curr_r, column=1, value="No credit transactions detected.")
            curr_r += 1

        ws_income.cell(row=curr_r, column=1, value="Total Income")
        ws_income.cell(row=curr_r, column=1).font = cls.BOLD_FONT
        ws_income.cell(row=curr_r, column=1).fill = cls.TOTAL_FILL
        ws_income.cell(row=curr_r, column=1).border = cls.TOTAL_BORDER

        ws_income.cell(row=curr_r, column=2, value=len(credit_txns))
        ws_income.cell(row=curr_r, column=2).font = cls.BOLD_FONT
        ws_income.cell(row=curr_r, column=2).alignment = Alignment(horizontal="center")
        ws_income.cell(row=curr_r, column=2).fill = cls.TOTAL_FILL
        ws_income.cell(row=curr_r, column=2).border = cls.TOTAL_BORDER

        tot_inc_cell = ws_income.cell(row=curr_r, column=3, value=round(sum_credits, 2))
        tot_inc_cell.font = cls.BOLD_FONT
        tot_inc_cell.number_format = '#,##0.00'
        tot_inc_cell.alignment = Alignment(horizontal="right")
        tot_inc_cell.fill = cls.TOTAL_FILL
        tot_inc_cell.border = cls.TOTAL_BORDER

        pct_inc_cell = ws_income.cell(row=curr_r, column=4, value="100.0%")
        pct_inc_cell.font = cls.BOLD_FONT
        pct_inc_cell.alignment = Alignment(horizontal="right")
        pct_inc_cell.fill = cls.TOTAL_FILL
        pct_inc_cell.border = cls.TOTAL_BORDER

        # ----------------- SHEET 5: Expense by Category -----------------
        ws_expense = wb.create_sheet(title="Expense by Category")
        ws_expense.views.sheetView[0].showGridLines = True

        ws_expense["A1"] = "StatementIQ – Expense Breakdown by Category"
        ws_expense["A1"].font = cls.TITLE_FONT

        expense_headers = ["Category", "Transaction Count", "Total Expense (Debits)", "% of Total Expense"]
        for c_idx, h in enumerate(expense_headers, start=1):
            cell = ws_expense.cell(row=3, column=c_idx, value=h)
            cell.font = cls.HEADER_FONT
            cell.fill = cls.HEADER_FILL
            cell.alignment = Alignment(horizontal="center")
            cell.border = cls.THIN_BORDER

        expense_map: Dict[str, Dict[str, Any]] = {}
        debit_txns = [t for t in transactions if t.debit and t.debit > 0]
        sum_debits = sum(t.debit for t in debit_txns) if debit_txns else 0.0

        for t in debit_txns:
            cat = t.category or "Other Expenses"
            if cat not in expense_map:
                expense_map[cat] = {"count": 0, "amount": 0.0}
            expense_map[cat]["count"] += 1
            expense_map[cat]["amount"] += t.debit

        sorted_expense = sorted(expense_map.items(), key=lambda x: x[1]["amount"], reverse=True)

        curr_r = 4
        for cat, data in sorted_expense:
            pct = (data["amount"] / sum_debits * 100.0) if sum_debits > 0 else 0.0
            row_vals = [
                sanitize_spreadsheet_value(cat),
                data["count"],
                round(data["amount"], 2),
                f"{pct:.1f}%"
            ]
            for c_idx, v in enumerate(row_vals, start=1):
                cell = ws_expense.cell(row=curr_r, column=c_idx, value=v)
                cell.border = cls.THIN_BORDER
                if c_idx == 1:
                    cell.font = cls.BOLD_FONT
                elif c_idx == 2:
                    cell.alignment = Alignment(horizontal="center")
                elif c_idx == 3:
                    cell.number_format = '#,##0.00'
                    cell.alignment = Alignment(horizontal="right")
                elif c_idx == 4:
                    cell.alignment = Alignment(horizontal="right")
            curr_r += 1

        if not sorted_expense:
            ws_expense.cell(row=curr_r, column=1, value="No debit transactions detected.")
            curr_r += 1

        ws_expense.cell(row=curr_r, column=1, value="Total Expense")
        ws_expense.cell(row=curr_r, column=1).font = cls.BOLD_FONT
        ws_expense.cell(row=curr_r, column=1).fill = cls.TOTAL_FILL
        ws_expense.cell(row=curr_r, column=1).border = cls.TOTAL_BORDER

        ws_expense.cell(row=curr_r, column=2, value=len(debit_txns))
        ws_expense.cell(row=curr_r, column=2).font = cls.BOLD_FONT
        ws_expense.cell(row=curr_r, column=2).alignment = Alignment(horizontal="center")
        ws_expense.cell(row=curr_r, column=2).fill = cls.TOTAL_FILL
        ws_expense.cell(row=curr_r, column=2).border = cls.TOTAL_BORDER

        tot_exp_cell = ws_expense.cell(row=curr_r, column=3, value=round(sum_debits, 2))
        tot_exp_cell.font = cls.BOLD_FONT
        tot_exp_cell.number_format = '#,##0.00'
        tot_exp_cell.alignment = Alignment(horizontal="right")
        tot_exp_cell.fill = cls.TOTAL_FILL
        tot_exp_cell.border = cls.TOTAL_BORDER

        pct_exp_cell = ws_expense.cell(row=curr_r, column=4, value="100.0%")
        pct_exp_cell.font = cls.BOLD_FONT
        pct_exp_cell.alignment = Alignment(horizontal="right")
        pct_exp_cell.fill = cls.TOTAL_FILL
        pct_exp_cell.border = cls.TOTAL_BORDER

        # ----------------- SHEET 6: Review Flags -----------------
        ws_flags = wb.create_sheet(title="Review Flags")
        ws_flags.views.sheetView[0].showGridLines = True

        ws_flags["A1"] = "StatementIQ – Audit Exceptions & Flagged Transactions"
        ws_flags["A1"].font = cls.TITLE_FONT

        flag_headers = [
            "Transaction ID", "Date", "Description", "Debit", "Credit",
            "Category", "Review Status", "Validation Flags", "OCR Correction", "Reconciliation Issue"
        ]
        for c_idx, h in enumerate(flag_headers, start=1):
            cell = ws_flags.cell(row=3, column=c_idx, value=h)
            cell.font = cls.HEADER_FONT
            cell.fill = cls.HEADER_FILL
            cell.alignment = Alignment(horizontal="center")
            cell.border = cls.THIN_BORDER

        flagged_txns = [
            t for t in transactions
            if t.review_status == "Needs Review"
            or t.validation_flags
            or t.ocr_correction
            or (t.explanation and (t.explanation.get("duplicate_warning") or t.explanation.get("reconciliation_mismatch")))
        ]

        curr_r = 4
        if flagged_txns:
            for t in flagged_txns:
                val_flags_str = ", ".join(t.validation_flags) if t.validation_flags else "None"
                ocr_str = str(t.ocr_correction.get("action", "")) if t.ocr_correction else "None"
                recon_mismatch = t.explanation.get("reconciliation_mismatch") if t.explanation else None
                recon_str = f"Expected: {recon_mismatch.get('expected_balance')}, Diff: {recon_mismatch.get('difference')}" if recon_mismatch else "OK"

                row_vals = [
                    sanitize_spreadsheet_value(t.id),
                    sanitize_spreadsheet_value(t.date),
                    sanitize_spreadsheet_value(t.description),
                    t.debit if t.debit else 0.0,
                    t.credit if t.credit else 0.0,
                    sanitize_spreadsheet_value(t.category),
                    sanitize_spreadsheet_value(t.review_status),
                    sanitize_spreadsheet_value(val_flags_str),
                    sanitize_spreadsheet_value(ocr_str),
                    sanitize_spreadsheet_value(recon_str)
                ]

                for c_idx, v in enumerate(row_vals, start=1):
                    cell = ws_flags.cell(row=curr_r, column=c_idx, value=v)
                    cell.border = cls.THIN_BORDER
                    if c_idx in [4, 5]:
                        cell.number_format = '#,##0.00'
                        cell.alignment = Alignment(horizontal="right")
                    elif c_idx in [1, 2, 7]:
                        cell.alignment = Alignment(horizontal="center")
                curr_r += 1
        else:
            ws_flags.cell(row=curr_r, column=1, value="No review flags or audit exceptions found across all transactions.")
            ws_flags.merge_cells(start_row=curr_r, start_column=1, end_row=curr_r, end_column=len(flag_headers))

        # ----------------- SHEET 7: Classification Explanations -----------------
        ws_explain = wb.create_sheet(title="Classification Explanations")
        ws_explain.views.sheetView[0].showGridLines = True

        ws_explain["A1"] = "StatementIQ – Explainable Classification Intelligence (Non-LLM)"
        ws_explain["A1"].font = cls.TITLE_FONT

        explain_headers = [
            "Transaction ID", "Date", "Description", "Assigned Category",
            "Classification Method", "Confidence", "Matched Rule / Keyword", "Explanation Reason", "Model Probabilities"
        ]
        for c_idx, h in enumerate(explain_headers, start=1):
            cell = ws_explain.cell(row=3, column=c_idx, value=h)
            cell.font = cls.HEADER_FONT
            cell.fill = cls.SUB_FILL
            cell.alignment = Alignment(horizontal="center")
            cell.border = cls.THIN_BORDER

        for r_idx, t in enumerate(transactions, start=4):
            exp = t.explanation or {}
            kw = exp.get("matched_keyword") or "N/A"
            reason = exp.get("reason") or ("Deterministic rule match" if t.classification_method == "Rule-Based" else "TF-IDF + Naive Bayes prediction")
            probs = exp.get("model_probabilities")
            if isinstance(probs, list):
                prob_str = ", ".join([f"{item.get('category')}: {int(item.get('probability', 0)*100)}%" for item in probs[:3] if isinstance(item, dict)])
            elif isinstance(probs, dict):
                prob_str = ", ".join([f"{k}: {int(v*100)}%" for k, v in list(probs.items())[:3]])
            else:
                prob_str = "N/A"

            row_vals = [
                sanitize_spreadsheet_value(t.id),
                sanitize_spreadsheet_value(t.date),
                sanitize_spreadsheet_value(t.description),
                sanitize_spreadsheet_value(t.category),
                sanitize_spreadsheet_value(t.classification_method),
                f"{int(t.confidence * 100)}%" if t.confidence is not None else "N/A",
                sanitize_spreadsheet_value(kw),
                sanitize_spreadsheet_value(reason),
                sanitize_spreadsheet_value(prob_str)
            ]

            for c_idx, v in enumerate(row_vals, start=1):
                cell = ws_explain.cell(row=r_idx, column=c_idx, value=v)
                cell.border = cls.THIN_BORDER
                if c_idx in [1, 2, 5, 6]:
                    cell.alignment = Alignment(horizontal="center")

        # Autofit column widths across all sheets
        for sheet in wb.worksheets:
            for col in sheet.columns:
                max_len = 0
                for cell in col:
                    val_str = str(cell.value or '')
                    if len(val_str) > max_len:
                        max_len = len(val_str)
                col_letter = get_column_letter(col[0].column)
                sheet.column_dimensions[col_letter].width = min(max(max_len + 3, 14), 50)

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output

    @classmethod
    def generate_combined_excel(cls, statements_data: List[Dict[str, Any]]) -> io.BytesIO:
        """
        Exports multiple processed bank statements together into a single master workbook:
        1. Statement Summaries (overview of each processed statement)
        2. Combined Transactions (all transactions with statement identifier, totals row)
        3. Combined Income (aggregated credits by category across all statements)
        4. Combined Expenses (aggregated debits by category across all statements)
        5. Flagged Review Items (review flags aggregated across all statements)
        6. Classification Explanations (explanations across all statements)
        """
        wb = openpyxl.Workbook()

        # ----------------- SHEET 1: Statement Summaries -----------------
        ws_overview = wb.active
        ws_overview.title = "Statement Summaries"
        ws_overview.views.sheetView[0].showGridLines = True

        ws_overview["A1"] = "StatementIQ – Multi-Statement Portfolio Summary"
        ws_overview["A1"].font = cls.TITLE_FONT

        overview_headers = [
            "Statement ID", "Filename", "Bank Name", "Account Holder",
            "Account Number", "Transactions", "Total Debits", "Total Credits",
            "Net Flow", "Reconciliation Status", "Pipeline Stage"
        ]

        for c_idx, h in enumerate(overview_headers, start=1):
            cell = ws_overview.cell(row=3, column=c_idx, value=h)
            cell.font = cls.HEADER_FONT
            cell.fill = cls.HEADER_FILL
            cell.alignment = Alignment(horizontal="center")
            cell.border = cls.THIN_BORDER

        all_txns: List[Tuple[str, str, Transaction]] = []  # (stmt_id, filename, txn)

        for s_idx, s in enumerate(statements_data, start=4):
            meta = s.get("metadata")
            acc = s.get("account_details")
            recon = s.get("reconciliation")
            txns = s.get("transactions", [])

            stmt_id = getattr(meta, "statement_id", "") or s.get("statement_id", "")
            fname = getattr(meta, "filename", "") or s.get("filename", "")
            bank = getattr(acc, "bank_name", "") or "Not Found"
            holder = getattr(acc, "account_holder", "") or "Not Found"
            acc_num = getattr(acc, "masked_account_number", "") or "Not Found"
            tot_txns = len(txns)
            tot_deb = getattr(recon, "total_debits", 0.0) if recon else sum(t.debit or 0.0 for t in txns)
            tot_crd = getattr(recon, "total_credits", 0.0) if recon else sum(t.credit or 0.0 for t in txns)
            net = getattr(recon, "net_flow", 0.0) if recon else (tot_crd - tot_deb)
            recon_status = getattr(recon, "reconciliation_status", "N/A") if recon else "N/A"
            stage = getattr(meta, "stage_name", "") or "Completed"

            for t in txns:
                all_txns.append((stmt_id, fname, t))

            row_vals = [
                sanitize_spreadsheet_value(stmt_id),
                sanitize_spreadsheet_value(fname),
                sanitize_spreadsheet_value(bank),
                sanitize_spreadsheet_value(holder),
                sanitize_spreadsheet_value(acc_num),
                tot_txns,
                round(tot_deb, 2),
                round(tot_crd, 2),
                round(net, 2),
                sanitize_spreadsheet_value(recon_status),
                sanitize_spreadsheet_value(stage)
            ]

            for c_idx, v in enumerate(row_vals, start=1):
                cell = ws_overview.cell(row=s_idx, column=c_idx, value=v)
                cell.border = cls.THIN_BORDER
                if c_idx in [7, 8, 9]:
                    cell.number_format = '#,##0.00'
                    cell.alignment = Alignment(horizontal="right")
                elif c_idx in [1, 6, 10, 11]:
                    cell.alignment = Alignment(horizontal="center")

        # ----------------- SHEET 2: Combined Transactions -----------------
        ws_all_txns = wb.create_sheet(title="Combined Transactions")
        ws_all_txns.views.sheetView[0].showGridLines = True

        comb_headers = [
            "Statement ID", "Source Statement Filename", "Transaction ID", "Date",
            "Description", "Debit", "Credit", "Balance", "Category",
            "Classification Method", "Confidence", "Review Status", "Duplicate Warning"
        ]

        for c_idx, h in enumerate(comb_headers, start=1):
            cell = ws_all_txns.cell(row=1, column=c_idx, value=h)
            cell.font = cls.HEADER_FONT
            cell.fill = cls.HEADER_FILL
            cell.alignment = Alignment(horizontal="center")
            cell.border = cls.THIN_BORDER

        total_deb = 0.0
        total_crd = 0.0

        for r_idx, (stmt_id, fname, t) in enumerate(all_txns, start=2):
            deb = float(t.debit) if (t.debit is not None and t.debit > 0) else 0.0
            crd = float(t.credit) if (t.credit is not None and t.credit > 0) else 0.0
            total_deb += deb
            total_crd += crd

            dup_warn = ""
            if t.explanation and t.explanation.get("duplicate_warning"):
                dup_warn = t.explanation.get("duplicate_warning")
            elif "exact_duplicate_transaction" in (t.validation_flags or []):
                dup_warn = "Exact duplicate transaction"
            elif "potential_duplicate_transaction" in (t.validation_flags or []):
                dup_warn = "Potential overlapping transaction"

            row_data = [
                sanitize_spreadsheet_value(stmt_id),
                sanitize_spreadsheet_value(fname),
                sanitize_spreadsheet_value(t.id),
                sanitize_spreadsheet_value(t.date),
                sanitize_spreadsheet_value(t.description),
                deb,
                crd,
                float(t.balance) if t.balance is not None else "",
                sanitize_spreadsheet_value(t.category),
                sanitize_spreadsheet_value(t.classification_method),
                f"{int(t.confidence * 100)}%" if t.confidence is not None else "N/A",
                sanitize_spreadsheet_value(t.review_status),
                sanitize_spreadsheet_value(dup_warn)
            ]

            for c_idx, val in enumerate(row_data, start=1):
                cell = ws_all_txns.cell(row=r_idx, column=c_idx, value=val)
                cell.border = cls.THIN_BORDER
                cell.font = cls.REGULAR_FONT
                if c_idx in [6, 7]:  # Debit, Credit
                    cell.number_format = '#,##0.00'
                    cell.alignment = Alignment(horizontal="right")
                elif c_idx == 8 and isinstance(val, (int, float)):
                    cell.number_format = '#,##0.00'
                    cell.alignment = Alignment(horizontal="right")
                elif c_idx in [1, 3, 4, 10, 11, 12]:
                    cell.alignment = Alignment(horizontal="center")

        # Total row for Combined Transactions
        tot_row = len(all_txns) + 2
        ws_all_txns.cell(row=tot_row, column=1, value="Total")
        ws_all_txns.cell(row=tot_row, column=1).font = cls.BOLD_FONT
        ws_all_txns.cell(row=tot_row, column=1).alignment = Alignment(horizontal="center")
        ws_all_txns.cell(row=tot_row, column=1).border = cls.TOTAL_BORDER
        ws_all_txns.cell(row=tot_row, column=1).fill = cls.TOTAL_FILL

        for c in range(2, 6):
            c_cell = ws_all_txns.cell(row=tot_row, column=c, value="")
            c_cell.border = cls.TOTAL_BORDER
            c_cell.fill = cls.TOTAL_FILL

        ws_all_txns.cell(row=tot_row, column=6, value=round(total_deb, 2)).font = cls.BOLD_FONT
        ws_all_txns.cell(row=tot_row, column=6).number_format = '#,##0.00'
        ws_all_txns.cell(row=tot_row, column=6).alignment = Alignment(horizontal="right")
        ws_all_txns.cell(row=tot_row, column=6).border = cls.TOTAL_BORDER
        ws_all_txns.cell(row=tot_row, column=6).fill = cls.TOTAL_FILL

        ws_all_txns.cell(row=tot_row, column=7, value=round(total_crd, 2)).font = cls.BOLD_FONT
        ws_all_txns.cell(row=tot_row, column=7).number_format = '#,##0.00'
        ws_all_txns.cell(row=tot_row, column=7).alignment = Alignment(horizontal="right")
        ws_all_txns.cell(row=tot_row, column=7).border = cls.TOTAL_BORDER
        ws_all_txns.cell(row=tot_row, column=7).fill = cls.TOTAL_FILL

        for c in range(8, len(comb_headers) + 1):
            c_cell = ws_all_txns.cell(row=tot_row, column=c, value="")
            c_cell.border = cls.TOTAL_BORDER
            c_cell.fill = cls.TOTAL_FILL

        # ----------------- SHEET 3: Combined Income -----------------
        ws_comb_inc = wb.create_sheet(title="Combined Income")
        ws_comb_inc.views.sheetView[0].showGridLines = True
        ws_comb_inc["A1"] = "StatementIQ – Aggregated Income by Category"
        ws_comb_inc["A1"].font = cls.TITLE_FONT

        inc_map: Dict[str, Dict[str, Any]] = {}
        credit_txns = [item for item in all_txns if item[2].credit and item[2].credit > 0]
        sum_crd = sum(item[2].credit for item in credit_txns) if credit_txns else 0.0

        for stmt_id, fname, t in credit_txns:
            cat = t.category or "Other Income"
            if cat not in inc_map:
                inc_map[cat] = {"count": 0, "amount": 0.0}
            inc_map[cat]["count"] += 1
            inc_map[cat]["amount"] += t.credit

        for c_idx, h in enumerate(["Category", "Transaction Count", "Total Income", "% of Total Income"], start=1):
            cell = ws_comb_inc.cell(row=3, column=c_idx, value=h)
            cell.font = cls.HEADER_FONT
            cell.fill = cls.SUB_FILL
            cell.alignment = Alignment(horizontal="center")
            cell.border = cls.THIN_BORDER

        curr_r = 4
        for cat, data in sorted(inc_map.items(), key=lambda x: x[1]["amount"], reverse=True):
            pct = (data["amount"] / sum_crd * 100.0) if sum_crd > 0 else 0.0
            row_vals = [sanitize_spreadsheet_value(cat), data["count"], round(data["amount"], 2), f"{pct:.1f}%"]
            for c_idx, v in enumerate(row_vals, start=1):
                cell = ws_comb_inc.cell(row=curr_r, column=c_idx, value=v)
                cell.border = cls.THIN_BORDER
                if c_idx == 3:
                    cell.number_format = '#,##0.00'
                    cell.alignment = Alignment(horizontal="right")
                elif c_idx in [2, 4]:
                    cell.alignment = Alignment(horizontal="right")
            curr_r += 1

        # ----------------- SHEET 4: Combined Expenses -----------------
        ws_comb_exp = wb.create_sheet(title="Combined Expenses")
        ws_comb_exp.views.sheetView[0].showGridLines = True
        ws_comb_exp["A1"] = "StatementIQ – Aggregated Expense by Category"
        ws_comb_exp["A1"].font = cls.TITLE_FONT

        exp_map: Dict[str, Dict[str, Any]] = {}
        debit_txns = [item for item in all_txns if item[2].debit and item[2].debit > 0]
        sum_deb = sum(item[2].debit for item in debit_txns) if debit_txns else 0.0

        for stmt_id, fname, t in debit_txns:
            cat = t.category or "Other Expenses"
            if cat not in exp_map:
                exp_map[cat] = {"count": 0, "amount": 0.0}
            exp_map[cat]["count"] += 1
            exp_map[cat]["amount"] += t.debit

        for c_idx, h in enumerate(["Category", "Transaction Count", "Total Expense", "% of Total Expense"], start=1):
            cell = ws_comb_exp.cell(row=3, column=c_idx, value=h)
            cell.font = cls.HEADER_FONT
            cell.fill = cls.HEADER_FILL
            cell.alignment = Alignment(horizontal="center")
            cell.border = cls.THIN_BORDER

        curr_r = 4
        for cat, data in sorted(exp_map.items(), key=lambda x: x[1]["amount"], reverse=True):
            pct = (data["amount"] / sum_deb * 100.0) if sum_deb > 0 else 0.0
            row_vals = [sanitize_spreadsheet_value(cat), data["count"], round(data["amount"], 2), f"{pct:.1f}%"]
            for c_idx, v in enumerate(row_vals, start=1):
                cell = ws_comb_exp.cell(row=curr_r, column=c_idx, value=v)
                cell.border = cls.THIN_BORDER
                if c_idx == 3:
                    cell.number_format = '#,##0.00'
                    cell.alignment = Alignment(horizontal="right")
                elif c_idx in [2, 4]:
                    cell.alignment = Alignment(horizontal="right")
            curr_r += 1

        # ----------------- SHEET 5: Flagged Review Items -----------------
        ws_all_flags = wb.create_sheet(title="Flagged Review Items")
        ws_all_flags.views.sheetView[0].showGridLines = True
        ws_all_flags["A1"] = "StatementIQ – All Flagged Review Items"
        ws_all_flags["A1"].font = cls.TITLE_FONT

        flag_headers = [
            "Statement ID", "Source Filename", "Transaction ID", "Date",
            "Description", "Debit", "Credit", "Category", "Review Status", "Validation Flags"
        ]
        for c_idx, h in enumerate(flag_headers, start=1):
            cell = ws_all_flags.cell(row=3, column=c_idx, value=h)
            cell.font = cls.HEADER_FONT
            cell.fill = cls.HEADER_FILL
            cell.alignment = Alignment(horizontal="center")
            cell.border = cls.THIN_BORDER

        curr_r = 4
        for stmt_id, fname, t in all_txns:
            if t.review_status == "Needs Review" or t.validation_flags or t.ocr_correction:
                row_vals = [
                    sanitize_spreadsheet_value(stmt_id),
                    sanitize_spreadsheet_value(fname),
                    sanitize_spreadsheet_value(t.id),
                    sanitize_spreadsheet_value(t.date),
                    sanitize_spreadsheet_value(t.description),
                    t.debit if t.debit else 0.0,
                    t.credit if t.credit else 0.0,
                    sanitize_spreadsheet_value(t.category),
                    sanitize_spreadsheet_value(t.review_status),
                    sanitize_spreadsheet_value(", ".join(t.validation_flags or []))
                ]
                for c_idx, v in enumerate(row_vals, start=1):
                    cell = ws_all_flags.cell(row=curr_r, column=c_idx, value=v)
                    cell.border = cls.THIN_BORDER
                    if c_idx in [6, 7]:
                        cell.number_format = '#,##0.00'
                        cell.alignment = Alignment(horizontal="right")
                    elif c_idx in [1, 3, 4, 9]:
                        cell.alignment = Alignment(horizontal="center")
                curr_r += 1

        # Autofit column widths across all sheets
        for sheet in wb.worksheets:
            for col in sheet.columns:
                max_len = 0
                for cell in col:
                    val_str = str(cell.value or '')
                    if len(val_str) > max_len:
                        max_len = len(val_str)
                col_letter = get_column_letter(col[0].column)
                sheet.column_dimensions[col_letter].width = min(max(max_len + 3, 14), 50)

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output

    @classmethod
    def generate_csv(
        cls,
        transactions: List[Transaction],
        source_filename: Optional[str] = None,
        statement_id: Optional[str] = None
    ) -> str:
        """
        Generates clean, formula-injection-safe CSV export for transactions of a statement.
        """
        output = io.StringIO()
        writer = csv.writer(output)
        has_metadata = bool(source_filename or statement_id)

        if has_metadata:
            writer.writerow([
                "Statement ID",
                "Source Filename",
                "Transaction ID",
                "Date",
                "Description",
                "Debit",
                "Credit",
                "Balance",
                "Category",
                "Classification Method",
                "Confidence",
                "Review Status"
            ])
        else:
            writer.writerow([
                "Date",
                "Description",
                "Debit",
                "Credit",
                "Balance",
                "Category",
                "Classification Method"
            ])

        for t in transactions:
            deb_str = f"{t.debit:.2f}" if (t.debit is not None and t.debit > 0) else "0.00"
            crd_str = f"{t.credit:.2f}" if (t.credit is not None and t.credit > 0) else "0.00"
            bal_str = f"{t.balance:.2f}" if t.balance is not None else ""
            conf_str = f"{int(t.confidence * 100)}%" if t.confidence is not None else "N/A"

            if has_metadata:
                writer.writerow([
                    sanitize_spreadsheet_value(statement_id or ""),
                    sanitize_spreadsheet_value(source_filename or ""),
                    sanitize_spreadsheet_value(t.id),
                    sanitize_spreadsheet_value(t.date),
                    sanitize_spreadsheet_value(t.description),
                    deb_str,
                    crd_str,
                    bal_str,
                    sanitize_spreadsheet_value(t.category),
                    sanitize_spreadsheet_value(t.classification_method),
                    conf_str,
                    sanitize_spreadsheet_value(t.review_status)
                ])
            else:
                writer.writerow([
                    sanitize_spreadsheet_value(t.date),
                    sanitize_spreadsheet_value(t.description),
                    deb_str,
                    crd_str,
                    bal_str,
                    sanitize_spreadsheet_value(t.category),
                    sanitize_spreadsheet_value(t.classification_method)
                ])

        return output.getvalue()

    @classmethod
    def generate_combined_csv(cls, statements_data: List[Dict[str, Any]]) -> str:
        """
        Generates combined CSV containing all transactions across multiple bank statements.
        Includes source statement information and does not silently merge duplicate records.
        """
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Statement ID",
            "Source Filename",
            "Transaction ID",
            "Date",
            "Description",
            "Debit",
            "Credit",
            "Balance",
            "Category",
            "Classification Method",
            "Confidence",
            "Review Status",
            "Duplicate Warning"
        ])

        for s in statements_data:
            meta = s.get("metadata")
            stmt_id = getattr(meta, "statement_id", "") or s.get("statement_id", "")
            fname = getattr(meta, "filename", "") or s.get("filename", "")
            txns = s.get("transactions", [])

            for t in txns:
                deb_str = f"{t.debit:.2f}" if (t.debit is not None and t.debit > 0) else "0.00"
                crd_str = f"{t.credit:.2f}" if (t.credit is not None and t.credit > 0) else "0.00"
                bal_str = f"{t.balance:.2f}" if t.balance is not None else ""
                conf_str = f"{int(t.confidence * 100)}%" if t.confidence is not None else "N/A"

                dup_warn = ""
                if t.explanation and t.explanation.get("duplicate_warning"):
                    dup_warn = t.explanation.get("duplicate_warning")
                elif "exact_duplicate_transaction" in (t.validation_flags or []):
                    dup_warn = "Exact duplicate transaction"
                elif "potential_duplicate_transaction" in (t.validation_flags or []):
                    dup_warn = "Potential duplicate transaction"

                writer.writerow([
                    sanitize_spreadsheet_value(stmt_id),
                    sanitize_spreadsheet_value(fname),
                    sanitize_spreadsheet_value(t.id),
                    sanitize_spreadsheet_value(t.date),
                    sanitize_spreadsheet_value(t.description),
                    deb_str,
                    crd_str,
                    bal_str,
                    sanitize_spreadsheet_value(t.category),
                    sanitize_spreadsheet_value(t.classification_method),
                    conf_str,
                    sanitize_spreadsheet_value(t.review_status),
                    sanitize_spreadsheet_value(dup_warn)
                ])

        return output.getvalue()
