"""Step 16 / ADR-004: opt-in LAN sensor ingest, batches, status and the ESP32 stand-in."""
import runpy
import tempfile
import unittest
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import create_app
from ml import ApplianceModel
from sensor_client import run

TOKEN = 'test-token-that-is-long-enough-123'
AUTH = {'Authorization': f'Bearer {TOKEN}'}


def readings(*seconds, watts=100):
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return {'readings': [{'timestamp': (start + timedelta(seconds=s)).isoformat(), 'total_watts': watts} for s in seconds]}


class LanSettingsTests(unittest.TestCase):
    def test_lan_mode_requires_private_address_and_long_token(self):
        for kwargs, message in (({'lan_host': '192.168.1.20'}, 'requires CURRENT_SENSOR_TOKEN'),
                                ({'lan_host': '8.8.8.8', 'sensor_token': TOKEN}, 'private'),
                                ({'lan_host': '127.0.0.1', 'sensor_token': TOKEN}, 'private'),
                                ({'lan_host': 'my-pc.local', 'sensor_token': TOKEN}, 'IPv4'),
                                ({'sensor_token': 'short'}, 'at least 24')):
            with self.subTest(kwargs=kwargs), patch.dict('os.environ', {'CURRENT_SENSOR_TOKEN': ''}), \
                    self.assertRaisesRegex(ValueError, message):
                create_app(tempfile.gettempdir(), ticking=False, **kwargs)

    def test_lan_flag_refuses_to_start_without_settings(self):
        with patch('uvicorn.run') as run_server, patch('sys.argv', ['app.py', '--lan']), \
                patch.dict('os.environ', {'CURRENT_LAN_HOST': '', 'CURRENT_SENSOR_TOKEN': ''}), \
                self.assertRaisesRegex(SystemExit, 'LAN mode not started'):
            runpy.run_path(str(Path(__file__).with_name('app.py')), run_name='__main__')
        run_server.assert_not_called()


class LanSensorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = ApplianceModel()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.model_patch = patch('app.ApplianceModel', return_value=self.model)
        self.model_patch.start()
        import app
        app.ApplianceModel.load.return_value = self.model
        self.app = create_app(Path(self.temp.name), ticking=False, sensor_token=TOKEN, lan_host='192.168.1.20')
        self.local = TestClient(self.app, base_url='http://127.0.0.1:8000', client=('127.0.0.1', 50000))
        self.local.__enter__()  # Runs the app lifespan once; the device client shares its state.
        self.device = TestClient(self.app, base_url='http://192.168.1.20:8000', client=('192.168.1.50', 50001))
        self.p = self.app.state.profiler

    def tearDown(self):
        self.local.__exit__(None, None, None)
        self.model_patch.stop()
        self.temp.cleanup()

    def test_network_devices_reach_only_sensor_routes_with_token(self):
        for method, path in (('get', '/'), ('get', '/api/state'), ('post', '/api/source'), ('get', '/api/export.csv')):
            with self.subTest(path=path):
                self.assertEqual(getattr(self.device, method)(path, headers=AUTH).status_code, 403)
        self.assertEqual(self.local.get('/api/state').status_code, 200)  # This computer is unaffected.
        self.assertEqual(self.local.post('/api/source', json={'source': 'sensor', 'cadence': 1}).status_code, 200)
        self.assertEqual(self.device.post('/api/sensor/readings', json=readings(0)).status_code, 401)
        self.assertEqual(self.device.post('/api/sensor/readings', json=readings(0),
                                          headers={'Authorization': 'Bearer wrong-token-wrong-token-12'}).status_code, 401)
        self.assertEqual(self.device.get('/api/sensor/status').status_code, 401)
        other_host = TestClient(self.app, base_url='http://evil.example:8000', client=('192.168.1.50', 50002))
        self.assertEqual(other_host.post('/api/sensor/readings', json=readings(0), headers=AUTH).status_code, 400)

    def test_batches_are_idempotent_and_status_reports_them(self):
        self.local.post('/api/source', json={'source': 'sensor', 'cadence': 1})
        first = self.device.post('/api/sensor/readings', json=readings(0, 1, 2), headers=AUTH)
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual((first.json()['accepted'], first.json()['duplicates']), (3, 0))
        retry = self.device.post('/api/sensor/readings', json=readings(0, 1, 2), headers=AUTH).json()
        self.assertEqual((retry['accepted'], retry['duplicates']), (0, 3))  # A resent batch changes nothing.
        overlap = self.device.post('/api/sensor/readings', json=readings(2, 3, 4), headers=AUTH).json()
        self.assertEqual((overlap['accepted'], overlap['duplicates']), (2, 1))
        self.assertEqual(overlap['latest_timestamp'], '2026-01-01T00:00:04+00:00')
        self.assertAlmostEqual(self.p.energy_kwh, 100 * 4 / 3_600_000)
        for bad in (readings(6, 5), readings(*range(10, 131)), {'readings': []},
                    {'readings': [{'timestamp': '2026-01-01T00:00:09', 'total_watts': 1}]}):
            self.assertEqual(self.device.post('/api/sensor/readings', json=bad, headers=AUTH).status_code, 422)
        status = self.device.get('/api/sensor/status', headers=AUTH).json()
        self.assertEqual({k: status[k] for k in ('active', 'accepted', 'duplicates', 'rejected', 'stale')},
                         {'active': True, 'accepted': 5, 'duplicates': 4, 'rejected': 4, 'stale': False})
        self.assertEqual(status['last_timestamp'], '2026-01-01T00:00:04+00:00')

    def test_status_is_stale_when_readings_stop(self):
        self.local.post('/api/source', json={'source': 'sensor', 'cadence': 1})
        self.assertTrue(self.local.get('/api/sensor/status', headers=AUTH).json()['stale'])  # Nothing received yet.
        self.device.post('/api/sensor/readings', json=readings(0), headers=AUTH)
        with patch('app.time.monotonic', return_value=self.p.sensor_stats['received_at'] + 5):
            self.assertTrue(self.device.get('/api/sensor/status', headers=AUTH).json()['stale'])

    def test_esp32_stand_in_sends_batches_and_retries(self):
        self.local.post('/api/source', json={'source': 'sensor', 'cadence': 1})
        clock = iter(datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=s) for s in range(100))
        calls, sleeps = [], []

        def flaky_post(url, body, token):
            calls.append(len(body['readings']))
            if len(calls) == 2:
                raise urllib.error.URLError('Wi-Fi dropped')
            response = self.device.post(url.replace('http://192.168.1.20:8000', ''), json=body,
                                        headers={'Authorization': f'Bearer {token}'})
            self.assertEqual(response.status_code, 200, response.text)
            return response.json()

        watts = iter(float(w) for w in range(100, 200))
        accepted = run(watts, 'http://192.168.1.20:8000', TOKEN, count=12, interval=1, batch=5,
                       post=flaky_post, sleep=sleeps.append, now=lambda: next(clock))
        self.assertEqual(accepted, 12)
        self.assertEqual(calls, [5, 5, 5, 2])  # The failed batch was resent whole.
        self.assertEqual(len(sleeps), 11 + 1)  # 11 sample intervals plus one backoff before the retry.
        self.assertEqual(self.p.sensor_stats['accepted'], 12)


if __name__ == '__main__':
    unittest.main()
