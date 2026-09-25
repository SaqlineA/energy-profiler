import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from cadence_comparison import run_comparison


class CadenceComparisonTests(unittest.TestCase):
    def test_fixed_protocol_scores_identical_windows_without_live_model_writes(self):
        manifest = Path('data/models/current.json')
        before = manifest.read_bytes() if manifest.exists() else None
        with TemporaryDirectory() as directory:
            reports = run_comparison(Path(directory))
            self.assertEqual(len(list(Path(directory).glob('*.json'))), 3)
            self.assertEqual(len(reports), 3)
            windows = []
            for report in reports:
                self.assertEqual(report['policy'], 'strict')
                self.assertEqual(report['cadence_seconds'], 8)
                self.assertEqual(report['window_span_seconds'], {'min': 32, 'max': 32})
                self.assertEqual(report['prediction_windows'], 663)
                self.assertEqual(report['model']['train_samples'], 2210)
                self.assertEqual(report['devices']['refrigerator']['energy_coverage_seconds'], 5280)
                windows.append([p['timestamp'] for p in report['points'] if p['predictions']])
                loaded = json.loads((Path(directory) / (report['id'] + '.json')).read_text())
                self.assertEqual(loaded['provenance']['protocol'], 'cadence-v1')
            self.assertEqual(windows[0], windows[1])
            self.assertEqual(windows[1], windows[2])
            baseline = reports[0]['devices']['refrigerator']
            self.assertEqual(baseline['estimated_kwh'], 0)
            self.assertEqual(baseline['f1'], 0)
        self.assertEqual(manifest.read_bytes() if manifest.exists() else None, before)


if __name__ == '__main__':
    unittest.main()
