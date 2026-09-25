import csv
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from fridge_development import run_development
from real_data_split import freeze_split
from realistic import realistic_sessions
from sources import parse_csv


class FridgeDevelopmentTests(unittest.TestCase):
    def test_only_train_and_development_are_parsed_and_live_model_is_unchanged(self):
        live = Path('data/models/current.json')
        before = live.read_bytes() if live.exists() else None
        with TemporaryDirectory() as directory:
            root = Path(directory)
            paths = []
            for index, session in enumerate(realistic_sessions(12, 3, 400)):
                path = root / f'house{index}.csv'
                with path.open('w', newline='') as handle:
                    writer = csv.DictWriter(handle, fieldnames=['timestamp', 'total_watts', 'refrigerator'], extrasaction='ignore')
                    writer.writeheader()
                    writer.writerows(session[::8])
                paths.append(path)
            manifest = root / 'split.json'
            freeze_split(*paths, manifest)
            with patch('fridge_development.parse_csv', wraps=parse_csv) as parser:
                reports = run_development(manifest, root / 'reports')
                self.assertEqual(parser.call_count, 2)
                self.assertEqual(parser.call_args_list[0].args[0], paths[0].read_bytes().decode())
                self.assertEqual(parser.call_args_list[1].args[0], paths[1].read_bytes().decode())
            self.assertEqual(len(reports), 3)
            self.assertTrue(all(r['prediction_windows'] == 46 for r in reports))
            self.assertTrue(all(set(r['devices']) == {'refrigerator'} for r in reports))
            self.assertTrue(all(r['provenance']['evaluation_role'] == 'development' for r in reports))
            # No on examples must be an explicit diagnostic, never an eligible candidate.
            text = paths[0].read_text().splitlines()
            paths[0].write_text(text[0] + '\n' + '\n'.join(line.rsplit(',', 1)[0] + ',0' for line in text[1:]) + '\n')
            second_manifest = root / 'single-class.json'
            freeze_split(*paths, second_manifest)
            diagnostics = run_development(second_manifest, root / 'diagnostics')
            self.assertTrue(all(not r['training_eligible'] for r in diagnostics))
            self.assertTrue(all(r['limitation'].startswith('INSUFFICIENT TRAINING') for r in diagnostics))
            paths[0].write_text(paths[0].read_text() + '\n')
            with self.assertRaisesRegex(ValueError, 'changed'):
                run_development(manifest, root / 'rejected')
            self.assertFalse((root / 'rejected').exists())
        self.assertEqual(live.read_bytes() if live.exists() else None, before)


if __name__ == '__main__':
    unittest.main()
