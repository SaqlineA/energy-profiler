import csv
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from final_test import run_final
from real_data_split import freeze_split
from realistic import realistic_sessions


class FinalTestTests(unittest.TestCase):
    def test_runs_once_on_identical_windows(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            paths = []
            for index, session in enumerate(realistic_sessions(12, 5, 1600)):
                path = root / f'house{index}.csv'
                with path.open('w', newline='') as handle:
                    writer = csv.DictWriter(handle, fieldnames=['timestamp', 'total_watts', 'refrigerator'], extrasaction='ignore')
                    writer.writeheader()
                    writer.writerows(session[::8])
                paths.append(path)
            manifest = root / 'split.json'
            freeze_split(*paths[:3], manifest)
            extra = {h: (p.name, hashlib.sha256(p.read_bytes()).hexdigest()) for h, p in zip((3, 4), paths[3:])}
            result_path = root / 'final.json'
            with self.assertRaisesRegex(ValueError, 'preregistered'):
                run_final(manifest, root / 'reports', result_path, extra, real_version='0' * 16)
            self.assertFalse(result_path.exists())
            result = run_final(manifest, root / 'reports', result_path, extra, real_version=None)
            self.assertGreater(result['windows'], 0)
            self.assertEqual(set(result['metrics']), {'real_v4r_decision_tree', 'synthetic_decision_tree', 'always_off'})
            self.assertEqual(result['metrics']['always_off']['f1'], 0)
            self.assertIn('passes', result['verdict'])
            with self.assertRaisesRegex(ValueError, 'once'):
                run_final(manifest, root / 'again', result_path, extra, real_version=None)
            self.assertFalse((root / 'again').exists())


if __name__ == '__main__':
    unittest.main()
