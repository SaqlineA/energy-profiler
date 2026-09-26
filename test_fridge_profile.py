import unittest
from pathlib import Path

from fridge_profile import load, profile


class FridgeProfileTests(unittest.TestCase):
    def test_complete_cycles_steps_and_holdout_refusal(self):
        # 10 s cadence: off 60 s, on 120 s, off 60 s, on 30 s (open at the end).
        pattern = [0] * 6 + [100] * 12 + [0] * 6 + [100] * 3
        rows = [{'timestamp': f'2026-01-01T00:{i * 10 // 60:02d}:{i * 10 % 60:02d}+00:00',
                 'total_watts': 50 + w, 'refrigerator': w} for i, w in enumerate(pattern)]
        result = profile([rows])
        # Edge runs are censored; only the fully observed on/off runs are timed.
        self.assertEqual(result['complete_on_cycles'], 1)
        self.assertEqual(result['on_cycle_minutes_p10_p50_p90'], [2.0, 2.0, 2.0])
        self.assertEqual(result['off_cycle_minutes_p10_p50_p90'], [1.0, 1.0, 1.0])
        self.assertEqual(result['switch_on_aggregate_step_w_p10_p50_p90'], [100, 100, 100])
        # A gap longer than 60 s censors the runs around it instead of bridging it.
        del rows[8:15]
        self.assertEqual(profile([rows])['complete_on_cycles'], 0)
        with self.assertRaisesRegex(ValueError, 'reserved'):
            load(Path('data/holdout/house5-replay-10000.csv'))


if __name__ == '__main__':
    unittest.main()
