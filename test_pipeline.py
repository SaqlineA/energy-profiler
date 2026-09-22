"""Regression tests for replay, missing data, causal features, and persistence."""
import csv
import io
import json
import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import numpy as np
from fastapi.testclient import TestClient

from app import create_app
from features import window_features
from ml import ApplianceModel, dataset, train_recorded, synthetic_households, TEST_SEED
from sources import parse_csv
from storage import Store
from prepare_recording import convert


def recording(count=50, cadence=1, labels=True):
    rows = synthetic_households(500, 1)[0][:count]
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for i, row in enumerate(rows):
        row['timestamp'] = (start + timedelta(seconds=i * cadence)).isoformat()
        if not labels:
            for key in ('lamp', 'refrigerator', 'microwave'):
                row[key] = None
    return rows


def csv_text(rows):
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=['timestamp', 'total_watts', 'lamp', 'refrigerator', 'microwave'])
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = ApplianceModel()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.mock = patch('app.ApplianceModel', return_value=self.model)
        mocked = self.mock.start()
        mocked.load.return_value = self.model
        self.app = create_app(self.directory, ticking=False)
        self.client = TestClient(self.app)
        self.client.__enter__()
        self.p = self.app.state.profiler

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.mock.stop()
        self.temp.cleanup()

    def upload(self, rows, cadence=1):
        response = self.client.post(f'/api/replay?cadence={cadence}&name=test.csv',
                                    content=csv_text(rows), headers={'Content-Type': 'text/csv'})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.client.post('/api/source', json={'source': 'replay'}).status_code, 200)

    def test_unlabeled_replay_preserves_time_and_finishes(self):
        rows = recording(8, labels=False)
        self.upload(rows)
        for _ in rows:
            self.p.sample()
        saved = self.client.get('/api/readings').json()
        self.assertEqual(saved[0]['timestamp'], rows[0]['timestamp'])
        self.assertIsNone(saved[-1]['actual_mask'])
        self.assertIsNone(saved[-1]['lamp'])
        self.assertIsNone(self.p.state()['live_accuracy'])
        self.assertIsNone(self.p.state()['appliances'][0]['energy_kwh'])
        self.assertFalse(self.p.running)
        self.assertEqual(self.p.covered_seconds, 7)
        expected = sum((rows[i]['total_watts'] + rows[i-1]['total_watts']) / 2 for i in range(1, len(rows))) / 3_600_000
        self.assertAlmostEqual(self.p.energy_kwh, expected)
        self.assertEqual(self.client.post('/api/simulation', json={'running': True}).status_code, 409)
        self.assertEqual(self.client.post('/api/appliances/lamp', json={'is_on': True}).status_code, 409)
        self.assertEqual(self.client.post('/api/simulation', json={'mode': 'auto'}).status_code, 409)

    def test_missing_and_gaps_reset_window_and_skip_energy(self):
        rows = recording(12)
        rows[5]['total_watts'] = None
        for i in range(8, 12):
            rows[i]['timestamp'] = (datetime.fromisoformat(rows[i]['timestamp']) + timedelta(seconds=100)).isoformat()
        self.upload(rows)
        for _ in rows:
            self.p.sample()
        saved = self.p.store.history(self.p.session)
        self.assertEqual(saved[5]['quality'], 'missing')
        self.assertEqual(saved[6]['quality'], 'gap')
        self.assertEqual(saved[8]['quality'], 'gap')
        self.assertIsNone(saved[8]['predicted_mask'])
        self.assertIsNone(saved[11]['predicted_mask'])
        self.assertEqual(saved[8]['energy_kwh'], saved[7]['energy_kwh'])
        self.assertEqual(self.p.covered_seconds, 8)
        self.assertEqual(self.p.skipped_seconds, 103)

    def test_validation_is_atomic_and_bounded(self):
        self.p.sample()
        session = self.p.session
        for body in ['timestamp,total_watts\n2026-01-01,10\n2026-01-02,20',
                     'timestamp,total_watts\n2026-01-01T00:00:00Z,nan\n2026-01-01T00:00:01Z,0',
                     csv_text([recording(2)[0]] * 2),
                     'timestamp,total_watts\n2026-01-01T00:00:00Z,-1\n2026-01-01T00:00:01Z,0']:
            self.assertEqual(self.client.post('/api/replay', content=body).status_code, 422)
        self.assertEqual(self.client.post('/api/replay', content='x' * 5_000_001).status_code, 413)
        self.assertEqual(self.p.session, session)
        self.assertEqual(self.p.second, 1)
        self.assertEqual(self.client.post('/api/source', json={'source': 'replay'}).status_code, 409)

    def test_csv_parser_errors_and_extreme_power_are_validation_errors(self):
        for value in ['x' * 140_000, '1e300']:
            body = f'timestamp,total_watts\n2026-01-01T00:00:00Z,{value}\n2026-01-01T00:00:01Z,0'
            with self.subTest(value=value[:10]):
                with self.assertRaises(ValueError):
                    parse_csv(body)

    def test_converter_preserves_measurements_and_missing_labels(self):
        fixture = Path(__file__).parent / 'examples' / 'replay-demo.csv'
        content = convert(fixture, 'timestamp', 'total_watts',
                          {'lamp': 'lamp', 'refrigerator': 'refrigerator', 'microwave': 'microwave'})
        self.assertEqual(parse_csv(content), parse_csv(fixture.read_text()))
        scaled = parse_csv(convert(fixture, 'timestamp', 'total_watts', {}, scale=.5))
        self.assertEqual(scaled[0]['total_watts'], 80)
        self.assertIsNone(scaled[0]['lamp'])
        self.assertIsNone(scaled[5]['total_watts'])

    def test_different_feature_schema_rejects_saved_model(self):
        folder = self.directory / 'features'
        self.model.save(folder)
        with patch('ml.WINDOW', 9):
            with self.assertRaisesRegex(ValueError, 'feature'):
                ApplianceModel.load(folder)

    def test_cadence_mismatch_prevents_misleading_predictions(self):
        rows = recording(8, cadence=8)
        self.upload(rows, cadence=8)
        for _ in rows:
            self.p.sample()
        self.assertEqual(self.p.latest['prediction_quality'], 'cadence_mismatch')
        self.assertIsNone(self.p.latest['predicted_mask'])
        self.assertEqual(self.p.covered_seconds, 56)

    def test_model_round_trip_checksum_and_metadata(self):
        folder = self.directory / 'roundtrip'
        self.model.save(folder)
        loaded = ApplianceModel.load(folder)
        self.assertEqual(self.model.infer([160] * 5), loaded.infer([160] * 5))
        manifest = json.loads((folder / 'current.json').read_text())
        self.assertEqual(manifest['test_seed'], TEST_SEED)
        with patch('ml.hashlib.sha256') as digest:
            digest.return_value.hexdigest.return_value = 'tampered'
            with self.assertRaisesRegex(ValueError, 'checksum'):
                ApplianceModel.load(folder)

    def test_fixed_test_set_and_baselines(self):
        other = ApplianceModel(seed=43)
        self.assertEqual(other.metrics['test_seed'], self.model.metrics['test_seed'])
        self.assertEqual(other.metrics['test_samples'], 1920)
        for device in self.model.metrics['device_metrics']:
            self.assertEqual(other.metrics['device_metrics'][device]['support'],
                             self.model.metrics['device_metrics'][device]['support'])
        self.assertIn('single_watt_joint_accuracy', other.metrics['baselines'])

    def test_feature_causality_label_isolation_and_split(self):
        rows = recording()
        x, _, _, _ = dataset([rows], 1)
        self.assertEqual(x[0].tolist(), window_features([r['total_watts'] for r in rows[:5]]))
        changed = [{**r, 'lamp': 999} for r in rows]
        self.assertTrue(np.array_equal(x, dataset([changed], 1)[0]))
        model = train_recorded(rows, 1)
        self.assertEqual(model.metrics['train_samples'], 31)
        self.assertEqual(model.metrics['test_samples'], 11)
        self.assertEqual(model.metrics['provenance']['split_timestamp'], rows[35]['timestamp'])
        self.assertEqual(model.metrics['energy_coverage_seconds'], 10)

    def test_recorded_training_endpoint_and_null_export(self):
        self.upload(recording())
        response = self.client.post('/api/model/train', json={'source': 'recorded'})
        self.assertEqual(response.status_code, 200, response.text)
        report = self.client.get('/api/model/report').json()
        self.assertIn('sha256', report['provenance'])
        self.assertEqual(report['test_samples'], 11)
        self.p.sample()
        exported = list(csv.DictReader(io.StringIO(self.client.get('/api/export.csv').text)))
        self.assertEqual(exported[-1]['predicted_mask'], '')
        self.assertEqual(exported[-1]['model_version'], report['version'])

    def test_unknown_load_abstains(self):
        result = self.model.infer([9000] * 5)
        self.assertIsNone(result['predicted_mask'])
        self.assertTrue(all(d['on'] is None for d in result['predictions'].values()))
        self.assertGreater(result['unexplained_watts'], 1000)

    def test_local_browser_write_boundary(self):
        body = csv_text(recording(8))
        denied = self.client.post('/api/replay', content=body,
                                  headers={'Origin': 'https://unrelated.example'})
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(self.p.replay_rows, [])
        allowed = self.client.post('/api/replay', content=body,
                                   headers={'Origin': 'http://testserver'})
        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(self.client.get('/api/state', headers={'Host': 'unrelated.example'}).status_code, 400)

    def test_unlabeled_training_rejected(self):
        self.upload(recording(labels=False))
        version = self.p.model.metrics['version']
        response = self.client.post('/api/model/train', json={'source': 'recorded'})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.p.model.metrics['version'], version)

    def test_frozen_experiment_history_and_safe_ids(self):
        self.upload(recording(12, labels=False))
        version = self.p.model.metrics['version']
        response = self.client.post('/api/experiments', json={'policy': 'strict'})
        self.assertEqual(response.status_code, 200, response.text)
        report = response.json()
        self.assertEqual(report['prediction_windows'], 8)
        self.assertIsNone(report['devices']['refrigerator']['accuracy'])
        self.assertEqual(self.p.model.metrics['version'], version)
        history = self.client.get('/api/experiments').json()
        self.assertEqual(history[0]['id'], report['id'])
        detail = self.client.get('/api/experiments/' + report['id']).json()
        self.assertEqual(len(detail['points']), 12)
        self.assertEqual(self.client.get('/api/experiments/not-an-id').status_code, 422)

    def test_sensor_mode_uses_source_time_and_rejects_duplicates(self):
        self.assertEqual(self.client.post('/api/sensor/readings', json={
            'timestamp': '2026-01-01T00:00:00Z', 'total_watts': 100}).status_code, 409)
        self.assertEqual(self.client.post('/api/source', json={'source': 'sensor', 'cadence': 1}).status_code, 200)
        self.p.sample()
        self.assertEqual(self.p.second, 0)
        for i in (0, 1):
            response = self.client.post('/api/sensor/readings', json={
                'timestamp': f'2026-01-01T00:00:0{i}Z', 'total_watts': 100})
            self.assertEqual(response.status_code, 200, response.text)
        self.assertAlmostEqual(self.p.energy_kwh, 100 / 3_600_000)
        self.assertIsNone(self.p.latest['lamp'])
        self.assertEqual(self.client.post('/api/sensor/readings', json={
            'timestamp': '2026-01-01T00:00:01Z', 'total_watts': 100}).status_code, 409)
        self.assertEqual(self.client.post('/api/sensor/readings', json={
            'timestamp': '2026-01-01T00:00:02', 'total_watts': 100}).status_code, 422)
        self.assertEqual(self.p.second, 2)

    def test_200_row_replay_energy_and_cost(self):
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        rows = [{'timestamp': (start + timedelta(seconds=i * 8)).isoformat(),
                 'total_watts': 100 + i, 'lamp': None, 'refrigerator': 50, 'microwave': None}
                for i in range(200)]
        response = self.client.post('/api/replay?cadence=8', content=csv_text(rows))
        self.assertEqual(response.status_code, 200)
        self.client.post('/api/source', json={'source': 'replay'})
        for _ in rows:
            self.p.sample()
        expected = (100 + 299) / 2 * (199 * 8) / 3_600_000
        self.assertAlmostEqual(self.p.energy_kwh, expected)
        self.assertAlmostEqual(self.p.state()['cost'], expected * self.p.rate)
        self.assertEqual(self.p.covered_seconds, 199 * 8)
        self.assertEqual(self.p.latest['timestamp'], rows[-1]['timestamp'])
        self.assertEqual(self.p.latest['prediction_quality'], 'cadence_mismatch')

    def test_sensor_limits_and_session_summary(self):
        self.client.post('/api/source', json={'source': 'sensor', 'cadence': 1})
        invalid = [
            {'timestamp': '2026-01-01T00:00:00Z', 'total_watts': -1},
            {'timestamp': '2026-01-01T00:00:00Z', 'total_watts': 10, 'lamp': 10},
        ]
        for body in invalid:
            self.assertEqual(self.client.post('/api/sensor/readings', json=body).status_code, 422)
        self.assertEqual(self.client.post('/api/sensor/readings', content=' ' * 8193).status_code, 413)
        for second in (0, 1, 5):
            self.client.post('/api/sensor/readings', json={
                'timestamp': f'2026-01-01T00:00:0{second}Z', 'total_watts': 100})
        row = self.client.get('/api/sessions').json()[0]
        self.assertEqual(row['samples'], 3)
        self.assertEqual(row['covered_seconds'], 1)
        self.assertEqual(row['gap_rows'], 1)
        self.assertAlmostEqual(row['energy_kwh'], 100 / 3_600_000)
        self.assertAlmostEqual(row['cost_at_current_rate'], row['energy_kwh'] * self.p.rate)
        self.assertEqual(self.client.get('/api/sessions?limit=101').status_code, 422)

    def test_realistic_profile_and_expanded_washer(self):
        response = self.client.post('/api/simulation', json={'profile': 'expanded'})
        self.assertEqual(response.status_code, 200, response.text)
        self.p.sample()
        self.assertIn('washing_machine', self.p.latest)
        self.assertGreater(self.p.latest['total_watts'], sum(self.p.latest[k] for k in ('lamp', 'refrigerator', 'microwave', 'washing_machine')))
        self.assertEqual(self.p.store.history(self.p.session)[0]['washing_machine'], self.p.latest['washing_machine'])

    def test_private_codespace_preview_boundary(self):
        host = 'my-learning-space-123-8000.app.github.dev'
        environment = {'CODESPACES': 'true', 'CODESPACE_NAME': 'my-learning-space-123',
                       'GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN': 'app.github.dev'}
        with patch.dict(os.environ, environment):
            cloud_app = create_app(self.directory, ticking=False)
        with TestClient(cloud_app, base_url=f'http://{host}') as client:
            self.assertEqual(client.get('/api/state').status_code, 200)
            self.assertEqual(client.post('/api/simulation', json={'running': False},
                             headers={'Origin': f'https://{host}'}).status_code, 200)
            self.assertFalse(client.get('/api/state').json()['running'])
            for origin in ('https://other-8000.app.github.dev', 'null', 'https://evil.example'):
                self.assertEqual(client.post('/api/simulation', json={'running': True},
                                 headers={'Origin': origin}).status_code, 403)
            self.assertEqual(client.get('/api/state', headers={
                'Host': 'other-8000.app.github.dev'}).status_code, 400)

    def test_codespace_config_is_explicit_and_fail_closed(self):
        environment = {'CODESPACES': 'false', 'CODESPACE_NAME': 'example',
                       'GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN': 'app.github.dev'}
        with patch.dict(os.environ, environment):
            local_app = create_app(self.directory, ticking=False)
        with TestClient(local_app) as client:
            self.assertEqual(client.get('/api/state', headers={
                'Host': 'example-8000.app.github.dev'}).status_code, 400)
        environment['CODESPACES'] = 'true'
        for name in ('', '*', 'example/evil', 'example.example'):
            with patch.dict(os.environ, {**environment, 'CODESPACE_NAME': name}):
                with self.assertRaises(ValueError):
                    create_app(self.directory, ticking=False)

    def test_additive_database_migration_preserves_ids(self):
        path = self.directory / 'legacy.sqlite3'
        with closing(sqlite3.connect(path)) as db, db:
            db.execute('CREATE TABLE readings (id INTEGER PRIMARY KEY, session TEXT, timestamp TEXT, second INTEGER, total_watts REAL, lamp REAL, refrigerator REAL, microwave REAL, actual_mask INTEGER, predicted_mask INTEGER, confidence REAL, energy_kwh REAL)')
            db.execute("INSERT INTO readings VALUES (41,'old','2026-01-01T00:00:00Z',0,10,10,0,0,1,1,1,0.1)")
        store = Store(path)
        self.assertEqual(store.history('old')[0]['id'], 41)
        Store(path)  # Running the migration twice must not duplicate old readings.
        self.assertEqual(len(list(store.export_rows())), 1)
        with closing(sqlite3.connect(path)) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM readings').fetchone()[0], 1)


if __name__ == '__main__':
    unittest.main()
