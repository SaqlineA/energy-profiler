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
