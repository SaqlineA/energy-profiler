import unittest

from realistic import RealisticHome, realistic_sessions


class RealisticTests(unittest.TestCase):
    def test_reproducible_sessions_and_separate_seeds(self):
        self.assertEqual(realistic_sessions(10, 2, 100), realistic_sessions(10, 2, 100))
        self.assertNotEqual(realistic_sessions(10, 1, 100), realistic_sessions(11, 1, 100))

    def test_background_overlap_and_multistage_washer(self):
        home = RealisticHome(42, washer=True)
        rows = [home.sample() for _ in range(1200)]
        self.assertGreater(len({r['washing_machine'] for r in rows}), 20)
        self.assertTrue(any(r['washing_machine'] > 1000 for r in rows))
        self.assertTrue(any(r['washing_machine'] > 50 and r['refrigerator'] > 20 for r in rows))
        self.assertTrue(any(r['total_watts'] > sum(r[k] for k in ('lamp', 'refrigerator', 'microwave', 'washing_machine')) + 20 for r in rows))
        self.assertTrue(all(r['total_watts'] >= 0 for r in rows))

    def test_fridge_v2_matches_real_cycle_targets(self):
        session = realistic_sessions(42, 1, 6 * 3600, fridge='v2')[0]
        on = [r['refrigerator'] >= 20 for r in session]
        edges = [i for i in range(1, len(on)) if on[i] != on[i - 1]]
        durations = [(b - a, on[a]) for a, b in zip(edges, edges[1:])]  # Complete runs only.
        self.assertTrue(durations)
        self.assertTrue(all(1500 <= d <= 1800 for d, state in durations if state))
        self.assertTrue(all(3600 <= d <= 7200 for d, state in durations if not state))
        running = [r['refrigerator'] for r, o in zip(session, on) if o]
        start = next(i for i in edges if on[i])
        self.assertLess(max(running), 90 * 1.4 * 1.2)  # Mild peak plus noise, never v1's 2.8x.
        self.assertGreater(session[start]['refrigerator'], session[start + 60]['refrigerator'] * 1.05)
        with self.assertRaises(ValueError):
            RealisticHome(fridge='v3')

    def test_manual_off_does_not_erase_background_load(self):
        home = RealisticHome(12)
        row = home.sample({'lamp': False, 'refrigerator': False, 'microwave': False})
        self.assertEqual(row['lamp'], 0)
        self.assertEqual(row['refrigerator'], 0)
        self.assertEqual(row['microwave'], 0)
        self.assertGreater(row['total_watts'], 0)


if __name__ == '__main__':
    unittest.main()
