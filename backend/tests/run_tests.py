import sys
import unittest
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.test_pipeline import (
    test_pdf_detector,
    test_rule_classifier,
    test_ml_classifier,
    test_extraction_and_reconciliation,
    test_user_sample_statement_metadata,
    test_excel_and_csv_export
)

class PipelineTestSuite(unittest.TestCase):
    def test_01_pdf_detector(self):
        test_pdf_detector()

    def test_02_rule_classifier(self):
        test_rule_classifier()

    def test_03_ml_classifier(self):
        test_ml_classifier()

    def test_04_extraction_and_reconciliation(self):
        test_extraction_and_reconciliation()

    def test_05_user_sample_statement_metadata(self):
        test_user_sample_statement_metadata()

    def test_06_excel_and_csv_export(self):
        test_excel_and_csv_export()

if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(PipelineTestSuite)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(not result.wasSuccessful())
