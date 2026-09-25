import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from real_data_split import freeze_split, verify_split


class RealDataSplitTests(unittest.TestCase):
    def fixtures(self, directory):
        paths = []
        for day in (1, 2, 3):
            path = Path(directory) / f'house-{day}.csv'
            path.write_text('timestamp,total_watts,refrigerator\n'
                            f'2020-01-0{day}T00:00:00Z,100,80\n'
                            f'2020-01-0{day}T00:00:08Z,120,90\n', encoding='utf-8')
            paths.append(path)
        return paths

    def test_freeze_verify_and_refuse_overwrite_or_modified_data(self):
        with TemporaryDirectory() as directory:
            paths = self.fixtures(directory)
            output = Path(directory) / 'split.json'
            report = freeze_split(*paths, output)
            self.assertEqual(report['partitions']['final_test']['house'], 5)
            self.assertEqual(verify_split(output), report)
            self.assertNotIn('f1', json.dumps(report))
            with self.assertRaises(FileExistsError):
                freeze_split(*paths, output)
            paths[0].write_text(paths[0].read_text().replace(',100,', ',101,'))
            with self.assertRaisesRegex(ValueError, 'changed'):
                verify_split(output)

    def test_rejects_duplicate_and_overlapping_recordings_before_saving(self):
        with TemporaryDirectory() as directory:
            paths = self.fixtures(directory)
            output = Path(directory) / 'split.json'
            with self.assertRaisesRegex(ValueError, 'duplicate|overlap'):
                freeze_split(paths[0], paths[0], paths[2], output)
            paths[1].write_text(paths[0].read_text() + '2020-01-01T00:00:16Z,130,95\n')
            with self.assertRaisesRegex(ValueError, 'overlap'):
                freeze_split(*paths, output)
            self.assertFalse(output.exists())

    def test_formatting_changes_do_not_hide_duplicate_measurements(self):
        with TemporaryDirectory() as directory:
            paths = self.fixtures(directory)
            paths[1].write_text(paths[0].read_text().replace(',100,', ',100.0,'))
            with self.assertRaisesRegex(ValueError, 'overlap'):
                freeze_split(*paths, Path(directory) / 'split.json')

    def test_verification_rejects_changed_house_assignment(self):
        with TemporaryDirectory() as directory:
            paths = self.fixtures(directory)
            output = Path(directory) / 'split.json'
            report = freeze_split(*paths, output)
            report['partitions']['final_test']['house'] = 2
            output.write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError, 'assignment changed'):
                verify_split(output)


if __name__ == '__main__':
    unittest.main()
