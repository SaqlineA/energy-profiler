"""Integration checks run against temporary databases, never your saved readings."""

import csv
import io
import runpy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import create_app
from ml import ApplianceModel
from simulator import Appliance
from events import TransitionTracker
from concurrent.futures import ThreadPoolExecutor


class ServerStartupTests(unittest.TestCase):
    def test_entrypoint_uses_internal_scheme_for_origin_checks(self):
        with patch('uvicorn.run') as run:
            runpy.run_path(str(Path(__file__).with_name('app.py')), run_name='__main__')
        self.assertIs(run.call_args.kwargs.get('proxy_headers'), False)
        self.assertEqual(run.call_args.kwargs['host'], '127.0.0.1')


class ProjectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = ApplianceModel()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        # Reuse training across tests; model fitting has its own explicit check.
        self.model_patch = patch('app.ApplianceModel', return_value=self.model)
        self.model_patch.start()
        # Loading must return a real model too when the app class is mocked.
        import app
        app.ApplianceModel.load.return_value = self.model
        self.app = create_app(Path(self.temp.name), ticking=False)
        self.client = TestClient(self.app)
        self.client.__enter__()
        self.profiler = self.app.state.profiler

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.model_patch.stop()
        self.temp.cleanup()

    def test_household_profile_runs_saves_and_exports_washer_v2(self):
        self.assertEqual(self.client.post('/api/simulation', json={'profile': 'household'}).status_code, 200)
        home = self.profiler.realistic_home
        self.assertEqual((home.washer, home.microwave, home.background_v2 is not None), ('v2', 'v2', True))
        for _ in range(700):  # The first v2 cycle starts 2-10 minutes in.
            self.profiler.sample()
        washer = self.client.get('/api/state').json()['experimental_washer']
        self.assertEqual(washer['model'], 'v2')
        self.assertNotIn(washer['stage'], ('off', 'idle'))
        self.assertGreater(washer['cycle_minutes'], 0)
        exported = list(csv.DictReader(io.StringIO(self.client.get('/api/export.csv').text)))
        stages = [row['washing_machine_stage'] for row in exported]
        self.assertEqual(stages[0], 'off')
        self.assertEqual(stages[-1], washer['stage'])
        self.assertAlmostEqual(float(exported[-1]['washing_machine']), washer['watts'])

    def test_original_appliance_still_works(self):
        lamp = Appliance('Lamp', 10)
        self.assertEqual(lamp.read_power(), 0)
        lamp.turn_on()
        self.assertTrue(8 <= lamp.read_power() <= 12)
        lamp.turn_off()
        self.assertEqual(lamp.read_power(), 0)

    def test_auto_cycle_saved_totals_energy_and_export(self):
        for _ in range(65):
            self.profiler.sample()
        rows = self.client.get('/api/readings').json()
        self.assertEqual(len(rows), 65)
        for row in rows:
            second = row['second']
            self.assertEqual(row['actual_mask'] & 4 > 0, 10 <= second % 30 < 15)
            self.assertEqual(row['actual_mask'] & 2 > 0, second % 60 < 40)
            self.assertAlmostEqual(row['total_watts'], row['lamp'] + row['refrigerator'] + row['microwave'], places=2)
        state = self.client.get('/api/state').json()
        self.assertAlmostEqual(state['energy_kwh'], sum(r['total_watts'] for r in rows) / 3_600_000)
        self.assertAlmostEqual(state['cost'], state['energy_kwh'] * 0.16)
        response = self.client.get('/api/export.csv')
        self.assertIn('attachment', response.headers['content-disposition'])
        exported = list(csv.DictReader(io.StringIO(response.text)))
        self.assertEqual(len(exported), 65)
        self.assertEqual(float(exported[-1]['total_watts']), rows[-1]['total_watts'])

    def test_manual_controls_and_validation(self):
        response = self.client.post('/api/appliances/microwave', json={'is_on': True})
        self.assertEqual(response.json()['mode'], 'manual')
        self.profiler.sample()
        self.assertEqual(self.profiler.latest['actual_mask'], 7)
        self.assertEqual(self.client.post('/api/appliances/toaster', json={'is_on': True}).status_code, 404)
        self.assertEqual(self.client.post('/api/simulation', json={'mode': 'invalid'}).status_code, 422)
        self.assertEqual(self.client.post('/api/tariff', json={'rate': -1}).status_code, 422)
        self.assertEqual(self.client.get('/api/readings?limit=999999').status_code, 422)
        self.client.post('/api/tariff', json={'rate': 0.25})
        state = self.client.get('/api/state').json()
        self.assertAlmostEqual(state['cost'], state['energy_kwh'] * 0.25)

    def test_pause_resume_and_mode(self):
        self.client.post('/api/simulation', json={'running': False, 'mode': 'manual'})
        self.assertFalse(self.client.get('/api/state').json()['running'])
        self.client.post('/api/simulation', json={'running': True, 'mode': 'auto'})
        state = self.client.get('/api/state').json()
        self.assertTrue(state['running'])
        self.assertEqual(state['mode'], 'auto')

    def test_model_receives_only_total_power(self):
        with patch.object(self.profiler.model, 'infer', wraps=self.profiler.model.infer) as predict:
            for _ in range(5):
                self.profiler.sample()
            rows = self.profiler.store.history(self.profiler.session)
            predict.assert_called_once_with([row['total_watts'] for row in rows])
            self.assertIsNone(rows[0]['predicted_mask'])

    def test_model_evaluation_and_retrain(self):
        metrics = self.model.metrics
        self.assertEqual(sum(map(sum, metrics['confusion_matrix'])), metrics['test_samples'])
        self.assertEqual(metrics['test_samples'], 1920)
        self.assertTrue(0 <= metrics['accuracy'] <= 1)
        self.assertGreater(metrics['accuracy'], 0.6)
        self.assertEqual(self.model.predict(0)[0], 0)
        self.assertEqual(self.model.predict(10)[0], 1)
        self.model_patch.stop()
        response = self.client.post('/api/model/train')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['seed'], metrics['seed'] + 1)

    def test_restart_retains_export_but_starts_new_session(self):
        self.profiler.sample()
        other_app = create_app(Path(self.temp.name), ticking=False)
        with TestClient(other_app) as other:
            self.assertNotEqual(other.get('/api/state').json()['session'], self.profiler.session)
            self.assertEqual(other.get('/api/readings').json(), [])
            self.assertEqual(len(list(csv.DictReader(io.StringIO(other.get('/api/export.csv').text)))), 1)

    def test_web_assets_and_docs(self):
        self.assertIn('Your home, in watts.', self.client.get('/').text)
        self.assertEqual(self.client.get('/static/app.js').status_code, 200)
        self.assertEqual(self.client.get('/static/style.css').status_code, 200)
        self.assertEqual(self.client.get('/docs').status_code, 200)
        self.assertEqual(self.client.get('/static/../app.py').status_code, 404)

    def test_incremental_snapshot_and_stale_session(self):
        self.profiler.sample()
        first = self.client.get('/api/dashboard').json()
        cursor = first['readings'][-1]['id']
        session = first['state']['session']
        self.profiler.sample()
        query = f'/api/dashboard?after_id={cursor}&session={session}'
        delta = self.client.get(query).json()
        self.assertEqual(len(delta['readings']), 1)
        self.assertEqual(delta['readings'][0], delta['state']['latest'])
        reset = self.client.get('/api/dashboard?after_id=999999&session=old').json()
        self.assertEqual(len(reset['readings']), 2)
        self.assertEqual(self.client.get('/api/dashboard?after_id=-1').status_code, 422)

    def test_rate_survives_restart(self):
        self.client.post('/api/tariff', json={'rate': 0.25})
        with TestClient(create_app(Path(self.temp.name), ticking=False)) as other:
            self.assertEqual(other.get('/api/state').json()['rate'], 0.25)

    def test_export_can_change_threads_while_sampling_continues(self):
        self.profiler.sample()
        self.profiler.sample()
        rows = self.profiler.store.export_rows()
        first = next(rows)
        try:
            # Reading transaction stays open while another connection writes.
            self.profiler.sample()
            with ThreadPoolExecutor(max_workers=1) as pool:
                second = pool.submit(next, rows).result(timeout=3)
            self.assertGreater(second['id'], first['id'])
        finally:
            rows.close()

    def test_live_metrics_and_failed_write(self):
        for _ in range(5):
            self.profiler.sample()
        rows = self.client.get('/api/readings').json()
        before = self.client.get('/api/state').json()
        eligible = [r for r in rows if r['prediction_quality'] in ('estimated', 'uncertain')]
        self.assertEqual(before['live_accuracy'], sum(r['predicted_mask'] == r['actual_mask'] for r in eligible) / len(eligible))
        self.assertEqual(before['peak_watts'], max(r['total_watts'] for r in rows))
        with patch.object(self.profiler.store, 'save', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                self.profiler.sample()
        after = self.client.get('/api/state').json()
        for key in ['samples', 'energy_kwh', 'latest', 'live_accuracy', 'events']:
            self.assertEqual(before[key], after[key])

    def test_event_filter_rejects_flicker_and_confirms_real_change(self):
        tracker = TransitionTracker()
        def feed(mask, second):
            return tracker.update({'predicted_mask': mask, 'total_watts': mask * 10,
                                   'second': second, 'timestamp': '2026-01-01T00:00:00Z'})
        self.assertEqual(feed(0, 0), [])
        self.assertEqual(feed(1, 1), [])
        self.assertEqual(feed(0, 2), [])
        self.assertEqual(feed(1, 3), [])
        self.assertEqual(feed(1, 4), [])
        events = feed(1, 5)
        self.assertEqual(len(events), 1)
        self.assertTrue(events[0]['is_on'])
        self.assertEqual(events[0]['delta'], 10)
        self.assertEqual(feed(1, 6), [])
        feed(0, 7)
        feed(0, 8)
        self.assertFalse(feed(0, 9)[0]['is_on'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
