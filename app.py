"""Run: .venv/Scripts/python.exe app.py, then open http://127.0.0.1:8000.

One process runs the simulator, API, SQLite storage, and dashboard.
Simulation samples represent one logical second; replay preserves recorded time.
"""

import asyncio
import csv
import io
import os
import hashlib
import hmac
import ipaddress
import json
import math
import re
import sys
import time
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, AwareDatetime, ConfigDict, ValidationError

from ml import APPLIANCES, ApplianceModel, train_recorded
from features import WINDOW
from sources import parse_csv, valid_interval, regular_interval, seconds_between, MAX_BYTES
from simulator import Appliance
from storage import Store
from events import TransitionTracker
from experiment_routes import install_experiment_routes
from realistic import RealisticHome

ROOT = Path(__file__).resolve().parent


class SimulationSettings(BaseModel):
    running: bool | None = None
    mode: Literal["auto", "manual"] | None = None
    profile: Literal['classic', 'realistic', 'expanded', 'household'] | None = None


class ApplianceSettings(BaseModel):
    is_on: bool


class TariffSettings(BaseModel):
    rate: float = Field(ge=0, le=10, allow_inf_nan=False)


class SourceSettings(BaseModel):
    source: Literal['simulator', 'replay', 'sensor']
    cadence: float = Field(default=1, gt=0, le=3600, allow_inf_nan=False)


class SensorReading(BaseModel):
    model_config = ConfigDict(extra='forbid')
    timestamp: AwareDatetime
    total_watts: float | None = Field(default=None, ge=0, le=1_000_000, allow_inf_nan=False)


class SensorBatch(BaseModel):
    # An ESP32 buffers readings during Wi-Fi drops and sends them together (ADR-004).
    model_config = ConfigDict(extra='forbid')
    readings: list[SensorReading] = Field(min_length=1, max_length=120)


SENSOR_PATHS = {'/api/sensor/readings', '/api/sensor/status'}
LOOPBACK = {'127.0.0.1', '::1'}
MIN_TOKEN_LENGTH = 24


def lan_settings(lan_host, sensor_token):
    """Validate opt-in LAN mode: a private IPv4 host and a long shared token are both required."""
    if sensor_token is not None and len(sensor_token) < MIN_TOKEN_LENGTH:
        raise ValueError(f'CURRENT_SENSOR_TOKEN must be at least {MIN_TOKEN_LENGTH} characters')
    if lan_host is None:
        return None
    if sensor_token is None:
        raise ValueError('LAN mode requires CURRENT_SENSOR_TOKEN')
    try:
        address = ipaddress.IPv4Address(lan_host)
    except ValueError as exc:
        raise ValueError('CURRENT_LAN_HOST must be an IPv4 address such as 192.168.1.20') from exc
    if not address.is_private or address.is_loopback or address.is_unspecified or address.is_link_local:
        raise ValueError('CURRENT_LAN_HOST must be a private home-network address, never public or loopback')
    return str(address)


class TrainSettings(BaseModel):
    source: Literal['synthetic', 'recorded'] = 'synthetic'


class EnergyProfiler:
    def __init__(self, data_dir):
        self.store = Store(data_dir / "readings.sqlite3")
        self.model_dir = data_dir / 'models'
        if (self.model_dir / 'current.json').exists():
            self.model = ApplianceModel.load(self.model_dir)
        else:
            self.model = ApplianceModel()
            self.model.save(self.model_dir)
        self.session = str(uuid4())
        self.sensor_stats = {'accepted': 0, 'duplicates': 0, 'rejected': 0, 'received_at': None}
        self.devices = {d["id"]: Appliance(d["name"], d["watts"]) for d in APPLIANCES}
        self.devices["lamp"].turn_on()
        self.devices["refrigerator"].turn_on()
        self.mode = "auto"
        self.profile = 'classic'
        self.running = True
        self.rate = self.store.get_rate()  # Saved illustrative tariff, not utility data.
        self.second = 0
        self.energy_kwh = 0
        self.device_energy = {d["id"]: 0 for d in APPLIANCES}
        self.latest = None
        self.events = []
        self.transitions = TransitionTracker()
        self.correct_predictions = 0
        self.peak_watts = 0
        self.error = None
        self.source = 'simulator'
        self.replay_rows = []
        self.replay_index = 0
        self.replay_cadence = 1.0
        self.sensor_cadence = 1.0
        self.replay_provenance = {}
        self.window = []
        self.started_at = datetime.now(timezone.utc)
        self.realistic_home = RealisticHome(start=self.started_at)
        self.washer_energy = self.washer_coverage = 0.0
        self.covered_seconds = 0.0
        self.skipped_seconds = 0.0
        self.evaluated = 0
        self.predicted_count = 0
        self.device_coverage = {d['id']: 0.0 for d in APPLIANCES}

    def reset_session(self, source):
        self.source = source
        self.session = str(uuid4())
        self.sensor_stats = {'accepted': 0, 'duplicates': 0, 'rejected': 0, 'received_at': None}
        self.second = self.replay_index = 0
        self.energy_kwh = self.covered_seconds = self.skipped_seconds = 0.0
        self.device_energy = {d['id']: 0.0 for d in APPLIANCES}
        self.device_coverage = {d['id']: 0.0 for d in APPLIANCES}
        self.latest, self.events, self.window = None, [], []
        self.transitions = TransitionTracker()
        self.correct_predictions = self.evaluated = self.predicted_count = self.peak_watts = 0
        self.started_at = datetime.now(timezone.utc)
        # expanded keeps the compressed v1 washer; household is the real-data-based demo (fridge, microwave, washer, background v2).
        self.realistic_home = RealisticHome(washer={'expanded': 'v1', 'household': 'v2'}.get(self.profile, False),
                                            start=self.started_at, fridge='v2' if self.profile == 'household' else 'v1',
                                            microwave='v2' if self.profile == 'household' else 'v1',
                                            background='v2' if self.profile == 'household' else 'v1')
        self.washer_energy = self.washer_coverage = 0.0
        self.running, self.error = True, None

    def sample(self):
        if self.source == 'sensor':
            return  # Readings arrive through the validated local input endpoint.
        if self.source == 'replay':
            if self.replay_index >= len(self.replay_rows):
                self.running = False
                return
            self.process(self.replay_rows[self.replay_index])
            self.replay_index += 1
            if self.replay_index == len(self.replay_rows):
                self.running = False
            return
        if self.profile != 'classic':
            raw = self.realistic_home.sample(None if self.mode == 'auto' else
                                           {key: d.is_on for key, d in self.devices.items()})
            for key, on in self.realistic_home.on.items():
                self.devices[key].is_on = on
            self.process(raw)
            return
        if self.mode == "auto":
            self.devices["lamp"].is_on = True
            self.devices["refrigerator"].is_on = self.second % 60 < 40
            self.devices["microwave"].is_on = 10 <= self.second % 30 < 15

        watts = {key: round(device.read_power(), 2) for key, device in self.devices.items()}
        total = round(sum(watts.values()), 2)
        timestamp = (self.started_at + timedelta(seconds=self.second)).isoformat()
        self.process({'timestamp': timestamp, 'total_watts': total, **watts})

    def process(self, raw):
        """Validate source time, infer from aggregate history, then commit and publish."""
        total = raw['total_watts']
        previous = self.latest
        cadence = 1.0 if self.source == 'simulator' else (
            self.sensor_cadence if self.source == 'sensor' else self.replay_cadence)
        dt = valid_interval(raw, previous, cadence)
        gap = previous is not None and not dt
        regular = regular_interval(raw, previous, cadence)
        window = list(self.window) if dt and regular else []
        if total is not None:
            window = (window + [total])[-WINDOW:]
        result = {'predicted_mask': None, 'confidence': None, 'predictions': {},
                  'unexplained_watts': None, 'prediction_quality': 'warming_up'}
        if total is None:
            result['prediction_quality'] = 'missing'
        elif abs(cadence - self.model.metrics['cadence_seconds']) > .001:
            result['prediction_quality'] = 'cadence_mismatch'
        elif len(window) == WINDOW:
            # ONLY aggregate values cross the inference boundary, never truth.
            result = self.model.infer(window)
        if self.source == 'simulator':
            increment = total / 3_600_000
            interval = 1.0
        else:
            increment = (total + previous['total_watts']) / 2 * dt / 3_600_000 if dt else 0
            interval = dt
        next_energy = self.energy_kwh + increment
        labeled = all(raw.get(d['id']) is not None for d in APPLIANCES)
        actual = sum(d['bit'] for d in APPLIANCES if raw[d['id']] >= d['threshold']) if labeled else None
        elapsed = self.second if self.source == 'simulator' else (
            previous['second'] + seconds_between(raw, previous) if previous else 0)
        reading = {
            "session": self.session, **raw, "second": elapsed,
            "washing_machine": raw.get('washing_machine'),
            "washing_machine_stage": raw.get('washing_machine_stage'),
            "actual_mask": actual, **result, "energy_kwh": next_energy,
            "source": self.source, "source_id": self.replay_provenance.get('sha256') if self.source == 'replay' else
                'local-sensor' if self.source == 'sensor' else f'simulator-{self.profile}',
            "quality": 'missing' if total is None else 'gap' if gap else 'irregular' if previous and not regular else 'valid',
            "interval_seconds": interval, "model_version": self.model.metrics['version'],
        }
        reading["id"] = self.store.save(reading)
        # Publish only after the database write succeeds.
        self.events = (self.transitions.update(reading) + self.events)[:20]
        if actual is not None and result['prediction_quality'] in ('estimated', 'uncertain'):
            self.evaluated += 1
            self.correct_predictions += int(result['predicted_mask'] == actual)
        self.predicted_count += int(result['predicted_mask'] is not None)
        self.peak_watts = max(self.peak_watts, total or 0)
        self.energy_kwh = next_energy
        self.covered_seconds += interval
        if gap:
            self.skipped_seconds += seconds_between(raw, previous)
        for d in APPLIANCES:
            key, value = d['id'], raw.get(d['id'])
            if value is not None and self.source == 'simulator':
                self.device_energy[key] += value / 3_600_000
                self.device_coverage[key] += 1
            elif dt and value is not None and previous.get(key) is not None:
                self.device_energy[key] += (value + previous[key]) / 2 * dt / 3_600_000
                self.device_coverage[key] += dt
        self.window = window
        washer = raw.get('washing_machine')
        if washer is not None and self.source == 'simulator':
            self.washer_energy += washer / 3_600_000
            self.washer_coverage += 1
        elif dt and washer is not None and previous.get('washing_machine') is not None:
            self.washer_energy += (washer + previous['washing_machine']) / 2 * dt / 3_600_000
            self.washer_coverage += dt
        self.latest = reading
        self.second += 1

    def state(self):
        return {
            "session": self.session, "running": self.running, "mode": self.mode,
            "profile": self.profile,
            "sensor": sensor_summary(self),
            "experimental_washer": {'watts': self.latest.get('washing_machine') if self.latest else None,
                'energy_kwh': self.washer_energy if self.washer_coverage else None,
                'stage': self.realistic_home.wash_stage if self.source == 'simulator' and self.realistic_home.washer else None,
                'model': self.realistic_home.washer if self.source == 'simulator' else None,
                'cycle_minutes': (self.realistic_home.washer_v2.cycle_seconds / 60
                                  if self.source == 'simulator' and self.realistic_home.washer_v2
                                  and self.realistic_home.washer_v2.cycle_seconds is not None else None),
                'note': 'Measured/simulated extra load; original live model has no washer output'},
            "rate": self.rate, "samples": self.second, "energy_kwh": self.energy_kwh,
            "cost": self.energy_kwh * self.rate, "latest": self.latest,
            "live_accuracy": self.correct_predictions / self.evaluated if self.evaluated else None,
            "evaluated_samples": self.evaluated,
            "prediction_coverage": self.predicted_count / self.second if self.second else 0,
            "source": self.source, "covered_seconds": self.covered_seconds, "skipped_seconds": self.skipped_seconds,
            "replay": {"loaded": len(self.replay_rows), "position": self.replay_index,
                       "cadence_seconds": self.replay_cadence, "provenance": self.replay_provenance},
            "peak_watts": self.peak_watts,
            "events": self.events, "error": self.error,
            "appliances": [
                {**device, "is_on": self.devices[device["id"]].is_on if self.source == 'simulator' else None,
                 "energy_kwh": self.device_energy[device["id"]] if self.device_coverage[device['id']] else None,
                 "coverage_seconds": self.device_coverage[device['id']]}
                for device in APPLIANCES
            ],
            "model": self.model.metrics,
        }


def create_app(data_dir=None, ticking=True, sensor_token=None, lan_host=None):
    data_dir = Path(data_dir or os.environ.get("ENERGY_DATA_DIR", ROOT / "data"))
    sensor_token = sensor_token or os.environ.get('CURRENT_SENSOR_TOKEN') or None
    lan_host = lan_settings(lan_host, sensor_token)

    @asynccontextmanager
    async def lifespan(app):
        profiler = EnergyProfiler(data_dir)
        app.state.profiler = profiler
        app.state.training_lock = asyncio.Lock()

        async def collect():
            while True:
                if profiler.running:
                    try:
                        profiler.sample()
                    except Exception:
                        import logging
                        logging.exception("Could not collect a reading")
                        profiler.error = "Collection stopped. Check the server terminal for details."
                        profiler.running = False
                await asyncio.sleep(1)

        task = asyncio.create_task(collect()) if ticking else None
        try:
            yield
        finally:
            if task:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task

    app = FastAPI(title="Energy Profiler", lifespan=lifespan)
    install_experiment_routes(app, data_dir / 'experiments')

    # Only this Codespace's private preview is permitted, never a wildcard host.
    # https://docs.github.com/en/codespaces/developing-in-a-codespace/default-environment-variables-for-your-codespace
    cloud_origin = None
    render_host = 'current-energy-profiler.onrender.com'
    allowed_hosts = ['localhost', '127.0.0.1', 'testserver', render_host]
    if lan_host:
        allowed_hosts.append(lan_host)  # Exact home-network address only, never a wildcard.
    if os.environ.get('CODESPACES') == 'true':
        name = os.environ.get('CODESPACE_NAME', '')
        domain = os.environ.get('GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN', '')
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', name) or domain != 'app.github.dev':
            raise ValueError('Invalid or unsupported Codespaces preview configuration')
        host = f'{name}-8000.{domain}'
        allowed_hosts.append(host)
        cloud_origin = f'https://{host}'

    # Reject DNS-rebinding hostnames and cross-site writes. This is not authentication.
    # https://fastapi.tiangolo.com/advanced/middleware/#trustedhostmiddleware
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

    # https://fastapi.tiangolo.com/tutorial/middleware/#create-a-middleware
    @app.middleware('http')
    async def local_browser_boundary(request: Request, call_next):
        origin = request.headers.get('origin')
        expected = f'{request.url.scheme}://{request.headers.get("host", "")}'
        if (request.method not in ('GET', 'HEAD', 'OPTIONS') and origin is not None
                and origin != expected and origin != cloud_origin):
            return JSONResponse({'detail': 'Cross-origin writes are not allowed'}, status_code=403)
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'no-referrer'
        return response

    if lan_host:
        # Network devices may only send readings and check sensor status (ADR-004).
        @app.middleware('http')
        async def lan_boundary(request: Request, call_next):
            client = request.client.host if request.client else ''
            if client not in LOOPBACK and request.url.path not in SENSOR_PATHS:
                return JSONResponse({'detail': 'Only sensor routes are available from the network'}, status_code=403)
            return await call_next(request)

    def require_sensor_token(request: Request):
        if sensor_token is None:
            return
        supplied = request.headers.get('authorization', '')
        if not hmac.compare_digest(supplied.encode(), f'Bearer {sensor_token}'.encode()):
            raise HTTPException(401, 'Missing or invalid sensor token', headers={'WWW-Authenticate': 'Bearer'})

    @app.get("/api/state")
    async def state():
        return app.state.profiler.state()

    @app.get("/api/readings")
    async def readings(limit: int = Query(default=300, ge=1, le=3600)):
        p = app.state.profiler
        return p.store.history(p.session, limit)

    @app.get('/api/sessions')
    async def sessions(limit: int = Query(default=20, ge=1, le=100)):
        p = app.state.profiler
        return [{**row, 'cost_at_current_rate': row['energy_kwh'] * p.rate,
                 'current_rate': p.rate} for row in p.store.sessions(limit)]

    @app.get("/api/dashboard")
    async def dashboard(limit: int = Query(default=300, ge=1, le=3600),
                        after_id: int = Query(default=0, ge=0), session: str | None = None):
        p = app.state.profiler
        # A new server session needs a fresh chart, even with an old client cursor.
        rows = p.store.history(p.session, limit, after_id if session == p.session else 0)
        return {"state": p.state(), "readings": rows}

    @app.post("/api/simulation")
    async def simulation(settings: SimulationSettings):
        p = app.state.profiler
        if p.source != 'simulator' and (settings.mode is not None or settings.profile is not None):
            raise HTTPException(409, 'Switch to simulator before changing appliance mode')
        if settings.profile is not None and settings.profile != p.profile:
            p.profile = settings.profile
            p.reset_session('simulator')
        if p.source == 'replay' and settings.running and p.replay_index >= len(p.replay_rows):
            raise HTTPException(409, 'Replay complete. Select Replay CSV to restart it.')
        if settings.running is not None:
            p.running = settings.running
            if settings.running:
                p.error = None
        if settings.mode is not None:
            p.mode = settings.mode
        return p.state()

    @app.post("/api/appliances/{device_id}")
    async def set_appliance(device_id: str, settings: ApplianceSettings):
        p = app.state.profiler
        if device_id not in p.devices:
            raise HTTPException(404, "Unknown appliance")
        if p.source != 'simulator':
            raise HTTPException(409, 'Appliance switches are only available in the simulator')
        p.mode = "manual"
        p.devices[device_id].is_on = settings.is_on
        return p.state()

    @app.post("/api/tariff")
    async def set_tariff(settings: TariffSettings):
        p = app.state.profiler
        p.store.set_rate(settings.rate)
        p.rate = settings.rate
        return p.state()

    @app.post("/api/model/train")
    async def train(settings: TrainSettings = TrainSettings()):
        lock = app.state.training_lock
        if lock.locked():
            raise HTTPException(409, "Training is already in progress")
        async with lock:
            p = app.state.profiler
            # Build off the event loop; sampling can continue with the old model.
            seed = p.model.metrics['seed'] + 1
            try:
                if settings.source == 'recorded':
                    if not p.replay_rows:
                        raise HTTPException(409, 'Upload a labeled CSV first')
                    rows, cadence, provenance = p.replay_rows, p.replay_cadence, p.replay_provenance
                    model = await asyncio.to_thread(train_recorded, rows, cadence, seed, provenance)
                else:
                    model = await asyncio.to_thread(ApplianceModel, seed)
                await asyncio.to_thread(model.save, p.model_dir)
            except ValueError as exc:
                raise HTTPException(422, str(exc)) from exc
            p.model = model
            p.window = []
            p.transitions = TransitionTracker()
            return model.metrics

    @app.post('/api/replay')
    async def upload_replay(request: Request, cadence: float = Query(default=1, gt=0, le=3600),
                            name: str = Query(default='recording.csv', max_length=120)):
        if not math.isfinite(cadence):
            raise HTTPException(422, 'Cadence must be finite')
        content = bytearray()
        async for chunk in request.stream():
            content.extend(chunk)
            if len(content) > MAX_BYTES:
                raise HTTPException(413, 'CSV exceeds the 5 MB limit')
        try:
            rows = await asyncio.to_thread(parse_csv, content.decode('utf-8-sig'))
        except (ValueError, UnicodeError) as exc:
            raise HTTPException(422, str(exc)) from exc
        p = app.state.profiler
        p.replay_rows, p.replay_cadence = rows, cadence
        p.replay_provenance = {'name': name, 'sha256': hashlib.sha256(content).hexdigest(),
                               'rows': len(rows), 'cadence_seconds': cadence,
                               'origin': 'User-supplied recording; not independently verified'}
        # Upload does not interrupt the current source. Source selection is explicit.
        if p.source == 'replay':
            p.reset_session('replay')
            p.running = False
        return p.state()

    @app.post('/api/source')
    async def source(settings: SourceSettings):
        p = app.state.profiler
        if settings.source == 'replay' and not p.replay_rows:
            raise HTTPException(409, 'Upload a CSV first')
        p.reset_session(settings.source)
        if settings.source == 'sensor':
            p.sensor_cadence = settings.cadence
        return p.state()

    @app.post('/api/sensor/readings', openapi_extra={'requestBody': {
        'required': True, 'content': {'application/json': {'schema': SensorReading.model_json_schema()}}
    }})
    async def sensor_reading(request: Request):
        require_sensor_token(request)
        p = app.state.profiler
        session = p.session
        if p.source != 'sensor' or not p.running:
            raise HTTPException(409, 'Start an unpaused sensor session first')
        content = bytearray()
        async for chunk in request.stream():
            content.extend(chunk)
            if len(content) > 16384:
                raise HTTPException(413, 'Sensor JSON exceeds 16 KB')
        try:
            is_batch = isinstance(parsed := json.loads(content), dict) and 'readings' in parsed
        except ValueError:
            is_batch = False
        if not is_batch and len(content) > 8192:
            raise HTTPException(413, 'Sensor JSON exceeds 8 KB')
        try:
            readings = (SensorBatch.model_validate_json(content).readings if is_batch
                        else [SensorReading.model_validate_json(content)])
        except ValidationError as exc:
            p.sensor_stats['rejected'] += 1
            raise HTTPException(422, 'Require timezone-aware timestamp and finite nonnegative total_watts (or null); '
                                     'no extra fields; batches hold 1-120 readings') from exc
        rows = [{'timestamp': r.timestamp.astimezone(timezone.utc).isoformat(),
                 'total_watts': r.total_watts, 'lamp': None, 'refrigerator': None, 'microwave': None} for r in readings]
        if any(seconds_between(b, a) <= 0 for a, b in zip(rows, rows[1:])):
            p.sensor_stats['rejected'] += 1
            raise HTTPException(422, 'Timestamps must strictly increase within a batch')
        if p.session != session or p.source != 'sensor' or not p.running:
            raise HTTPException(409, 'Sensor session changed while receiving the reading; retry in the current session')
        if not is_batch:
            if p.latest and seconds_between(rows[0], p.latest) <= 0:
                p.sensor_stats['duplicates'] += 1
                raise HTTPException(409, 'Duplicate or out-of-order timestamp; reading not added')
            p.process(rows[0])
            p.sensor_stats['accepted'] += 1
            p.sensor_stats['received_at'] = time.monotonic()
            return p.state()
        accepted = duplicates = 0
        for raw in rows:
            # Already stored (e.g. a retried batch): skip instead of failing, so resending is safe.
            if p.latest and seconds_between(raw, p.latest) <= 0:
                duplicates += 1
                continue
            p.process(raw)
            accepted += 1
        p.sensor_stats['accepted'] += accepted
        p.sensor_stats['duplicates'] += duplicates
        if accepted:
            p.sensor_stats['received_at'] = time.monotonic()
        return {'session': p.session, 'accepted': accepted, 'duplicates': duplicates,
                'latest_timestamp': p.latest['timestamp'] if p.latest else None}

    @app.get('/api/sensor/status')
    async def sensor_status(request: Request):
        require_sensor_token(request)
        return sensor_summary(app.state.profiler)

    @app.get('/api/model/report')
    async def model_report():
        return app.state.profiler.model.metrics

    @app.get("/api/export.csv")
    async def export():
        store = app.state.profiler.store

        def generate():
            buffer = io.StringIO(newline="")
            writer = csv.writer(buffer)
            columns = ["id", "session", "timestamp", "second", "total_watts", "lamp",
                       "refrigerator", "microwave", "actual_mask", "predicted_mask",
                       "confidence", "energy_kwh", "source", "quality", "prediction_quality",
                       "interval_seconds", "model_version", "source_id", "unexplained_watts", "predictions", "washing_machine", "washing_machine_stage"]
            writer.writerow(columns)
            yield buffer.getvalue()
            for row in store.export_rows():
                buffer.seek(0)
                buffer.truncate(0)
                writer.writerow([json.dumps(row[column]) if isinstance(row[column], dict) else row[column]
                                 for column in columns])
                yield buffer.getvalue()

        return StreamingResponse(generate(), media_type="text/csv", headers={
            "Content-Disposition": 'attachment; filename="energy-readings.csv"',
        })

    @app.get("/")
    async def index():
        return FileResponse(ROOT / "static" / "index.html")

    app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
    return app


def sensor_summary(p):
    """Small health view for a sensor session; `stale` means no reading for 3 sample intervals."""
    stats = p.sensor_stats
    since = time.monotonic() - stats['received_at'] if stats['received_at'] is not None else None
    active = p.source == 'sensor'
    return {'active': active, 'running': p.running, 'cadence_seconds': p.sensor_cadence,
            'accepted': stats['accepted'], 'duplicates': stats['duplicates'], 'rejected': stats['rejected'],
            'last_timestamp': p.latest['timestamp'] if active and p.latest else None,
            'seconds_since_last': since, 'stale': active and (since is None or since > 3 * p.sensor_cadence)}


app = create_app()

if __name__ == "__main__":
    import argparse
    import uvicorn
    parser = argparse.ArgumentParser(description='Run Current locally.')
    parser.add_argument('--lan', action='store_true',
                        help='Also accept sensor readings from the home network (needs CURRENT_SENSOR_TOKEN and CURRENT_LAN_HOST)')
    args, _ = parser.parse_known_args(sys.argv[1:])
    if args.lan:
        lan_host = os.environ.get('CURRENT_LAN_HOST')
        try:
            lan_app = create_app(lan_host=lan_host or '')
        except ValueError as exc:
            sys.exit(f'LAN mode not started: {exc}')
        print(f'Dashboard: http://127.0.0.1:8000 (this computer only). '
              f'Sensor endpoint for devices: http://{lan_host}:8000/api/sensor/readings')
        uvicorn.run(lan_app, host="0.0.0.0", port=8000, proxy_headers=False)
    else:
        # Codespaces rewrites Host/Origin to HTTP localhost. Keep that internal scheme
        # instead of mixing it with X-Forwarded-Proto; external HTTPS stays at GitHub.
        uvicorn.run(app, host="127.0.0.1", port=8000, proxy_headers=False)
