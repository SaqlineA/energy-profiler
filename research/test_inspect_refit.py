"""Run separately after installing requirements-research.txt."""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest

from inspect_refit import inspect_csv


class InspectionTests(unittest.TestCase):
    def test_reports_rows_missing_values_and_preserves_input(self):
        original = "Unix,Aggregate,Appliance1\n100,120,0\n108,130,\n116,140,50\n"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.csv"
            path.write_text(original, encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                inspect_csv(path)
            self.assertEqual(path.read_text(encoding="utf-8"), original)
        report = output.getvalue()
        self.assertIn("Rows in this file: 3", report)
        self.assertIn("First five rows", report)
        self.assertIn("Columns: ['Unix', 'Aggregate', 'Appliance1']", report)
        self.assertRegex(report, r"Appliance1\s+1")
        self.assertIn("Median interval: 8.0 seconds", report)

    def test_single_row_has_no_measurable_interval(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.csv"
            path.write_text("Unix,Aggregate\n100,120\n", encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                inspect_csv(path)
        self.assertIn("Interval: unavailable", output.getvalue())


if __name__ == "__main__":
    unittest.main()
