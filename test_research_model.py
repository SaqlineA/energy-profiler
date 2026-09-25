import unittest
import numpy as np

from experiments import evaluate_model
from realistic import realistic_sessions
from research_model import ResearchModel, make_features


class ResearchModelTests(unittest.TestCase):
    def test_fridge_only_models_do_not_require_other_labels(self):
        sessions = [s[::8] for s in realistic_sessions(90, 1, 400)]
        for row in sessions[0]:
            row['lamp'] = row['microwave'] = None
        for algorithm in ('always_off', 'decision_tree', 'random_forest'):
            with self.subTest(algorithm=algorithm):
                model = ResearchModel(sessions, algorithm=algorithm, cadence=8, fridge_only=True)
                report = evaluate_model(model, sessions[0], cadence=8)
                self.assertEqual(set(report['devices']), {'refrigerator'})
                self.assertEqual(report['prediction_windows'], 46)
                self.assertEqual(model.metrics['train_samples'], 46)
                self.assertEqual(set(report['points'][-1]['predictions']), {'refrigerator'})
        with self.assertRaises(ValueError):
            ResearchModel(sessions, fridge_only=True, washer=True)

    def test_single_class_training_support_is_explicit(self):
        sessions = [s[::8] for s in realistic_sessions(90, 1, 160)]
        for row in sessions[0]:
            row['refrigerator'] = 0
        model = ResearchModel(sessions, algorithm='decision_tree', cadence=8, fridge_only=True)
        self.assertEqual(model.metrics['train_class_support']['refrigerator'], {'on': 0, 'off': 16})

    def test_eight_second_training_matches_strict_evaluation(self):
        sessions = [s[::8] for s in realistic_sessions(90, 2, 160)]
        model = ResearchModel(sessions, algorithm='decision_tree', cadence=8)
        self.assertEqual(model.metrics['cadence_seconds'], 8)
        self.assertEqual(model.metrics['train_samples'], 32)
        report = evaluate_model(model, sessions[0], cadence=8)
        self.assertEqual(report['prediction_windows'], 16)
        self.assertEqual(report['window_span_seconds'], {'min': 32, 'max': 32})
        self.assertEqual(evaluate_model(model, sessions[0], cadence=1)['prediction_windows'], 0)

    def test_cadence_validation_and_training_gap_reset(self):
        sessions = [s[::8] for s in realistic_sessions(90, 1, 160)]
        for cadence in (0, -1, float('nan'), float('inf'), 3601):
            with self.subTest(cadence=cadence), self.assertRaises(ValueError):
                ResearchModel(sessions, algorithm='decision_tree', cadence=cadence)
        # Removing one sample makes a 16-second gap, larger than 1.5 * cadence.
        del sessions[0][9]
        model = ResearchModel(sessions, algorithm='decision_tree', cadence=8)
        self.assertEqual(model.metrics['train_samples'], (9 - 4) + (10 - 4))

    def test_features_are_trailing_and_window_specific(self):
        self.assertEqual(make_features([1, 2, 3, 4, 5], 'summary')[:2], [5, 1])
        self.assertEqual(make_features([1, 2, 3], 'watts'), [3])
        self.assertEqual(make_features([1, 2, 3], 'history')[-3:], [1, 2, 3])

    def test_four_device_models_and_held_out_evaluation(self):
        train = realistic_sessions(90, 2, 300, washer=True)
        test = realistic_sessions(900, 1, 200, washer=True)[0]
        model = ResearchModel(train, window=10, algorithm='decision_tree', washer=True)
        report = evaluate_model(model, test)
        self.assertEqual(report['devices']['washing_machine']['samples'], 191)
        self.assertEqual(report['prediction_windows'], 191)
        self.assertEqual(model.metrics['window'], 10)
        self.assertIn('split', model.metrics['provenance'])

    def test_always_off_baseline_is_actually_off(self):
        rows = realistic_sessions(90, 1, 100)
        model = ResearchModel(rows, algorithm='always_off')
        report = evaluate_model(model, rows[0])
        self.assertTrue(all(not v['raw_on'] and v['estimated_watts'] == 0
                            for p in report['points'] for v in p['predictions'].values()))

    def test_truth_cannot_enter_features(self):
        rows = realistic_sessions(90, 1, 100)
        model = ResearchModel(rows, algorithm='decision_tree')
        x = [model.features([r['total_watts'] for r in rows[0][:5]])]
        before = model.regressor.predict(x)
        rows[0][4]['lamp'] = 99999
        self.assertTrue(np.array_equal(before, model.regressor.predict(x)))


if __name__ == '__main__':
    unittest.main()
