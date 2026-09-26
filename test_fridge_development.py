import csv
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from fridge_development import run_development
from real_data_split import freeze_split
from realistic import realistic_sessions
from sources import parse_csv, thin_to_cadence


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

    def test_thinning_keeps_real_readings_only(self):
        # House 1 style bursts: 1 s then 14 s apart, repeating.
        seconds = [0, 1, 15, 16, 30, 31, 45, None, 60]
        rows = [{'timestamp': f'2026-01-01T00:{s // 60:02d}:{s % 60:02d}+00:00' if s is not None
                 else '2026-01-01T00:00:50+00:00', 'total_watts': None if s is None else float(i)}
                for i, s in enumerate(seconds)]
        kept = thin_to_cadence(rows, 16)
        self.assertEqual([r['timestamp'][-11:-6] for r in kept], ['00:00', '00:15', '00:30', '00:45', '01:00'])
        self.assertTrue(all(r in rows for r in kept))  # Selected, never modified or created.
        self.assertTrue(all(r['total_watts'] is not None for r in kept))


if __name__ == '__main__':
    unittest.main()
