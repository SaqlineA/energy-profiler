from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from research_model import ResearchModel
from washer_experiment import run


class WasherExperimentTests(unittest.TestCase):
    def test_small_run_scores_identical_windows_once(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            summary = root / 'summary.json'
            result = run(root / 'reports', summary, train_count=2, eval_count=2, hours=3, first_start=(600, 1800))
            self.assertEqual(len(result['candidates']), 5)
            always_off = result['candidates']['always_off_w30']
            self.assertEqual((always_off['f1'], always_off['estimated_kwh']), (0.0, 0.0))
            self.assertGreater(always_off['positive_samples'], 0)  # Each short home contains a wash.
            self.assertIn('heat', always_off['recall_by_stage'])
            self.assertEqual(len(list((root / 'reports').glob('*.json'))), 5)  # Home 1 per candidate.
            with self.assertRaisesRegex(ValueError, 'already run'):
                run(root / 'again', summary, train_count=2, eval_count=2, hours=3)
        with self.assertRaisesRegex(ValueError, 'Unknown target'):
            ResearchModel([[]], target='toaster')


if __name__ == '__main__':
    unittest.main()
