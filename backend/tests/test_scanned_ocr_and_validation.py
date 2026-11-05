import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.schemas.statement import Transaction, AccountDetails
from app.services.pdf_extractor import PDFExtractor
from app.services.transaction_parser import TransactionParser
from app.services.data_validator import DataValidator
from app.services.reconciliation import ReconciliationService
from app.utils.helpers import parse_amount, parse_date

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_statements"

class TestScannedOCRandValidation(unittest.TestCase):
    def setUp(self):
        self.extractor = PDFExtractor()
        self.parser = TransactionParser()

    def test_01_scanned_hdfc_statement_extraction(self):
        """Test OCR extraction accuracy on scanned HDFC bank statement."""
        scanned_pdf = SAMPLE_DIR / "scanned_statement.pdf"
        self.assertTrue(scanned_pdf.exists(), "scanned_statement.pdf must exist")

        res = self.extractor.extract_content(str(scanned_pdf))
        self.assertTrue(res["is_scanned"], "Should be detected as scanned")
        self.assertGreaterEqual(len(res["pages"]), 2, "Should have 2 scanned pages")

        acc = self.parser.extract_account_details(res["full_text"])
        self.assertEqual(acc.bank_name, "HDFC Bank")
        self.assertEqual(acc.account_holder, "VIKRAMADITYA SINGHANIA")
        self.assertEqual(acc.opening_balance, 45200.0)
        self.assertEqual(acc.closing_balance, 128450.0)

        txns = self.parser.extract_transactions(res["raw_tables"], res["full_text"], pages=res.get("pages", []))
        self.assertEqual(len(txns), 17, f"Expected 17 transactions, got {len(txns)}")

        validated = DataValidator.validate_all(txns, opening_balance=acc.opening_balance)

        # 1. No simultaneous debit and credit
        simultaneous = [t for t in validated if t.debit > 0 and t.credit > 0]
        self.assertEqual(len(simultaneous), 0, f"Found simultaneous debit & credit: {[t.description for t in simultaneous]}")

        # 2. No running balance mismatches
        mismatches = [t for t in validated if "running_balance_mismatch" in t.validation_flags]
        self.assertEqual(len(mismatches), 0, f"Found running balance mismatches: {[t.description for t in mismatches]}")

        # 3. Check specific transactions mentioned in prompt
        t_salary = next(t for t in validated if "SALARY" in t.description.upper())
        self.assertEqual(t_salary.credit, 120000.0, "Salary must be credit 120,000.00")
        self.assertEqual(t_salary.debit, 0.0, "Salary must have 0.0 debit")
        self.assertEqual(t_salary.balance, 165200.0, "Salary balance must be 165,200.00")
        self.assertEqual(t_salary.review_status, "Verified")

        t_swiggy = next(t for t in validated if "SWIGGY" in t.description.upper())
        self.assertEqual(t_swiggy.debit, 650.0, "Swiggy must be debit 650.00")
        self.assertEqual(t_swiggy.credit, 0.0, "Swiggy must have 0.0 credit")
        self.assertEqual(t_swiggy.balance, 139550.0, "Swiggy balance must be 139,550.00")
        self.assertEqual(t_swiggy.review_status, "Verified")

        t_bescom = next(t for t in validated if "BESCOM" in t.description.upper())
        self.assertEqual(t_bescom.debit, 2400.0, "Bescom bill must be debit 2,400.00")
        self.assertEqual(t_bescom.credit, 0.0, "Bescom must have 0.0 credit")
        self.assertEqual(t_bescom.balance, 137150.0, "Bescom balance must be 137,150.00")
        self.assertEqual(t_bescom.review_status, "Verified")

        t_amazon = next(t for t in validated if "AMAZON" in t.description.upper())
        self.assertEqual(t_amazon.debit, 4200.0, "Amazon retail must be debit 4,200.00")
        self.assertEqual(t_amazon.credit, 0.0, "Amazon must have 0.0 credit")
        self.assertEqual(t_amazon.balance, 132950.0, "Amazon balance must be 132,950.00")
        self.assertEqual(t_amazon.review_status, "Verified")

        t_dividend = next(t for t in validated if "DIVIDEND" in t.description.upper())
        self.assertEqual(t_dividend.credit, 3125.0, "Dividend must be credit 3,125.00")
        self.assertEqual(t_dividend.debit, 0.0, "Dividend must have 0.0 debit")
        self.assertEqual(t_dividend.balance, 110607.30, "Dividend balance must be 110,607.30")
        self.assertIn("500", t_dividend.description, "500 SHARES must remain in description, not amounts")

        # 4. Reconciliation
        recon = ReconciliationService.reconcile(acc, validated)
        self.assertTrue(recon.is_reconciled, "Scanned statement must reconcile perfectly")
        self.assertAlmostEqual(recon.total_credits, 173125.0, places=2)
        self.assertAlmostEqual(recon.total_debits, 89875.0, places=2)

    def test_02_text_based_statement_extraction(self):
        """Test extraction on digital text-based HDFC statement."""
        dig_pdf = SAMPLE_DIR / "hdfc_digital_statement.pdf"
        res = self.extractor.extract_content(str(dig_pdf))
        acc = self.parser.extract_account_details(res["full_text"])
        txns = self.parser.extract_transactions(res["raw_tables"], res["full_text"], pages=res.get("pages", []))
        self.assertEqual(len(txns), 17)
        validated = DataValidator.validate_all(txns, opening_balance=acc.opening_balance)
        recon = ReconciliationService.reconcile(acc, validated)
        self.assertTrue(recon.is_reconciled)

    def test_03_indian_numeric_formatting_and_ocr_noise(self):
        """Test parse_amount() with Indian formatting and OCR noise artifacts."""
        self.assertEqual(parse_amount("1,20,000.00"), 120000.0)
        self.assertEqual(parse_amount("1.65.200.00"), 165200.0)
        self.assertEqual(parse_amount("2.400.00"), 2400.0)
        self.assertEqual(parse_amount("4.200.00"), 4200.0)
        self.assertEqual(parse_amount("1,08.757.30"), 108757.3)
        self.assertEqual(parse_amount("84.437.30"), 84437.3)
        self.assertEqual(parse_amount("1.39,550.00"), 139550.0)
        self.assertEqual(parse_amount("17.70"), 17.70)
        self.assertEqual(parse_amount("INR 45,200.00"), 45200.0)
        self.assertEqual(parse_amount("(500.00)"), -500.0)
        self.assertEqual(parse_amount("Nil"), 0.0)
        self.assertEqual(parse_amount("-"), 0.0)

    def test_04_simultaneous_debit_credit_validation(self):
        """Test detection and flagging of transactions with both debit and credit."""
        t_bad = Transaction(
            id="T1",
            date="2024-05-01",
            description="SUSPICIOUS TRANSACTION",
            debit=120000.0,
            credit=1.65,
            balance=200.0
        )
        val = DataValidator.validate_transaction(t_bad, prev_balance=45200.0)
        self.assertIn("simultaneous_debit_credit", val.validation_flags)
        self.assertIn("running_balance_mismatch", val.validation_flags)
        self.assertEqual(val.review_status, "Needs Review")

    def test_05_running_balance_formula_validation(self):
        """Test running balance validation: Prev + Cr - Dr = Current."""
        t1 = Transaction(id="T1", date="2024-05-01", description="SALARY", debit=0.0, credit=50000.0, balance=75000.0)
        val1 = DataValidator.validate_transaction(t1, prev_balance=25000.0)
        self.assertEqual(val1.review_status, "Verified")
        self.assertEqual(val1.validation_flags, [])

        # Balance mismatch
        t2 = Transaction(id="T2", date="2024-05-02", description="GROCERIES", debit=1000.0, credit=0.0, balance=72000.0)
        val2 = DataValidator.validate_transaction(t2, prev_balance=75000.0)
        self.assertIn("running_balance_mismatch", val2.validation_flags)
        self.assertEqual(val2.review_status, "Needs Review")

    def test_06_manual_correction_workflow(self):
        """Test recalculating validation and reconciliation after manual user correction."""
        acc = AccountDetails(bank_name="Test Bank", opening_balance=10000.0, closing_balance=14000.0)
        txns = [
            Transaction(id="T1", date="2024-05-01", description="BAD EXTRACTION", debit=1000.0, credit=5000.0, balance=14000.0)
        ]
        val1 = DataValidator.validate_all(txns, opening_balance=acc.opening_balance)
        self.assertEqual(val1[0].review_status, "Needs Review")

        # User corrects debit to 0.0 and credit to 5000.0, but opening + 5000 - 1000 = 14000? 10000 + 4000 = 14000
        # If user fixes debit=0.0, credit=4000.0:
        txns[0].debit = 0.0
        txns[0].credit = 4000.0
        txns[0].review_status = "Corrected"

        val2 = DataValidator.validate_all(txns, opening_balance=acc.opening_balance)
        self.assertEqual(val2[0].review_status, "Corrected")
        self.assertEqual(val2[0].validation_flags, [])

        recon = ReconciliationService.reconcile(acc, val2)
        self.assertTrue(recon.is_reconciled)

if __name__ == "__main__":
    unittest.main()
