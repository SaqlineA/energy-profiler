import unittest
from pathlib import Path

from washer_profile import cycles, profile, read, stages


class WasherProfileTests(unittest.TestCase):
    def test_cycles_join_pauses_drop_blips_and_split_on_gaps(self):
        t = 0
        readings = []
        def add(seconds, watts, step=10):
            nonlocal t
            for _ in range(seconds // step):
                readings.append((t, watts)); t += step
        add(600, 0)
        add(300, 50); add(600, 2200); add(240, 0); add(900, 150); add(300, 400)  # One 39-min cycle with a pause.
        add(3600, 0)
        add(60, 500)  # One-minute blip: ignored.
        add(3600, 0)
        found = cycles(readings)
        self.assertEqual(len(found), 1)
        self.assertEqual([s[0] for s in stages(found[0])], ['motor', 'heat', 'pause', 'motor', 'spin'])
        result = profile(readings)
        self.assertEqual((result['cycles'], result['heating_cycles'], result['idle_w_p50_p90']), (1, 1, [0, 0]))
        # A sampling gap longer than two minutes ends the cycle instead of bridging it.
        gap = [(time + (3600 if time > 1500 else 0), w) for time, w in readings]
        pieces = cycles(gap)
        self.assertEqual(len(pieces), 2)
        self.assertTrue(all(c[-1][0] - c[0][0] < 39 * 60 for c in pieces))

    def test_house5_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'retired'):
            read(Path('data/refit/washer/house5-prefix-20mb.part'), 'Appliance1')


if __name__ == '__main__':
    unittest.main()
