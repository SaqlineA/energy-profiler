import csv
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from cross_house import rules, run
from real_data_split import freeze_split
from realistic import realistic_sessions


class CrossHouseTests(unittest.TestCase):
    def test_every_house_held_out_once_and_runs_once(self):
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
            result_path = root / 'cross.json'
            result = run(manifest, root / 'reports', result_path, extra)
            self.assertEqual(sorted(result['folds']), [1, 2, 3, 4, 5])
            for fold in result['folds'].values():
                self.assertGreater(fold['windows'], 0)
                self.assertEqual(fold['always_off']['f1'], 0)
            self.assertIn(result['verdict']['R2'], ('simulator advantage holds', 'House 5 was an exception',
                                                    'mixed, no general claim'))
            with self.assertRaisesRegex(ValueError, 'once'):
                run(manifest, root / 'again', result_path, extra)

    def test_rules_follow_the_protocol(self):
        fold = lambda real, sim: {'real': {'f1': real, 'mae_watts': 10}, 'simulator': {'f1': sim},
                                  'always_off': {'f1': 0, 'mae_watts': 20}}
        verdict = rules({h: fold(.5, .6 if h <= 4 else .4) for h in range(1, 6)})
        self.assertEqual((verdict['R1'], verdict['R2']), ('holds', 'simulator advantage holds'))
        verdict = rules({h: fold(.5, .6 if h <= 2 else .4) for h in range(1, 6)})
        self.assertEqual(verdict['R2'], 'mixed, no general claim')
        verdict = rules({h: fold(0 if h <= 2 else .5, 0) for h in range(1, 6)})
        self.assertEqual(verdict['R1'], 'does not transfer reliably')
        self.assertEqual(verdict['R2'], 'House 5 was an exception')


if __name__ == '__main__':
    unittest.main()
