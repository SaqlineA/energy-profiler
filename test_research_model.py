import unittest
import numpy as np

from experiments import evaluate_model
from realistic import realistic_sessions
from research_model import ResearchModel, make_features


class ResearchModelTests(unittest.TestCase):
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
