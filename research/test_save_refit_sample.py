from pathlib import Path
import tempfile
import unittest

from save_refit_sample import save_sample


class SampleTests(unittest.TestCase):
    def test_preserves_complete_lines_and_refuses_overwrite(self):
        expected = b"Time,Unix,Aggregate,Appliance1\n" + b"time,100,10,0\n" * 10000
        with tempfile.TemporaryDirectory() as directory:
            prefix = Path(directory) / "prefix.part"
            output = Path(directory) / "sample.csv"
            prefix.write_bytes(expected + b"unfinished")
            save_sample(prefix, output)
            self.assertEqual(output.read_bytes(), expected)
            with self.assertRaises(FileExistsError):
                save_sample(prefix, output)

    def test_rejects_short_download_without_creating_output(self):
        with tempfile.TemporaryDirectory() as directory:
            prefix = Path(directory) / "prefix.part"
            output = Path(directory) / "sample.csv"
            prefix.write_bytes(b"Time,Unix,Aggregate,Appliance1\n")
            with self.assertRaises(ValueError):
                save_sample(prefix, output)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
