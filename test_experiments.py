"""Offline evaluation must not turn unknown truth or abstention into 'off'."""
import unittest
from copy import deepcopy

from ml import ApplianceModel, synthetic_households
from experiments import evaluate_model


class ExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = ApplianceModel()

    def test_partial_truth_and_model_are_preserved(self):
        rows = synthetic_households(71, 1)[0]
        for row in rows:
            row['lamp'] = row['microwave'] = None
        before = deepcopy(rows)
        version = self.model.metrics['version']
        report = evaluate_model(self.model, rows, cadence=1)
        self.assertEqual(report['devices']['lamp']['samples'], 0)
        self.assertIsNone(report['devices']['lamp']['accuracy'])
        self.assertEqual(report['devices']['refrigerator']['samples'], 96)
        self.assertEqual(rows, before)
        self.assertEqual(self.model.metrics['version'], version)
        self.assertEqual(report['prediction_windows'], 96)

    def test_strict_cadence_mismatch_abstains(self):
        report = evaluate_model(self.model, synthetic_households(71, 1)[0], cadence=8)
        self.assertEqual(report['prediction_windows'], 0)
        self.assertIsNone(report['devices']['refrigerator']['f1'])

    def test_diagnostic_is_explicit_and_never_bridges_gaps(self):
        rows = synthetic_households(71, 1)[0][:10]
        rows[5]['total_watts'] = None
        report = evaluate_model(self.model, rows, cadence=8, policy='sample_window')
        self.assertEqual(report['prediction_windows'], 1)
        self.assertIn('diagnostic', report['timing_note'])
        self.assertEqual(report['points'][5]['predictions'], {})

    def test_common_warmup_and_future_data_cannot_change_past(self):
        rows = synthetic_households(71, 1)[0]
        report = evaluate_model(self.model, rows, min_history=30)
        self.assertEqual(report['prediction_windows'], 71)
        self.assertEqual(report['points'][28]['predictions'], {})
        before = report['points'][:50]
        for row in rows[50:]:
            row['total_watts'] = 99999
        self.assertEqual(evaluate_model(self.model, rows, min_history=30)['points'][:50], before)

    def test_zero_positive_support_is_visible(self):
        rows = synthetic_households(71, 1)[0]
        for row in rows:
            row['refrigerator'] = 0
        metrics = evaluate_model(self.model, rows)['devices']['refrigerator']
        self.assertEqual(metrics['positive_samples'], 0)
        self.assertIsNone(metrics['recall'])


if __name__ == '__main__':
    unittest.main()


class DescribeTests(unittest.TestCase):
    def test_labels_sources_and_plain_explanations(self):
        from experiment_routes import describe
        device = {'samples': 10, 'positive_samples': 5, 'negative_samples': 5, 'recall': .2, 'precision': .5,
                  'confusion': {'tp': 1, 'fp': 1, 'fn': 4, 'tn': 4}, 'true_kwh': 1.0, 'estimated_kwh': .6}
        real = describe({'provenance': {'name': 'FINAL House 5 / real_v4r_decision_tree', 'evaluation_role': 'final_test',
                                        'evaluation_house': 5},
                         'model': {'algorithm': 'decision_tree', 'training_source': 'REFIT Houses [1, 3, 4] training'},
                         'devices': {'refrigerator': device}})
        self.assertEqual(real['label'], 'FINAL House 5 — Real-trained Decision Tree')
        self.assertEqual((real['evaluation_data'], real['training_data'], real['training']), ('real', 'real', 'REFIT Houses 1, 3, 4'))
        self.assertEqual(real['explanations']['refrigerator'],
                         'The model detected some refrigerator activity but missed many ON periods (20% found). '
                         '50% of its ON predictions were false alarms. It underestimated total refrigerator energy by 40%.')
        synthetic = describe({'provenance': {'name': 'Cadence v1 / always_off / synthetic 8s'},
                              'model': {'algorithm': 'always_off', 'training_source': 'realistic'},
                              'devices': {'lamp': {**device, 'confusion': {'tp': 0, 'fp': 0, 'fn': 5, 'tn': 5}, 'true_kwh': None}}})
        self.assertEqual((synthetic['evaluation_data'], synthetic['training_data'], synthetic['group']), ('synthetic', 'none', 'other'))
        self.assertIn('never predicted the lamp ON', synthetic['explanations']['lamp'])
