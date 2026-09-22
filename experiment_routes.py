"""Local experiment API. No uploaded model files or client-chosen filesystem paths."""
import asyncio
import json
import re

from fastapi import HTTPException, Query
from pydantic import BaseModel
from typing import Literal

from experiments import evaluate_model, save_experiment


class ExperimentSettings(BaseModel):
    policy: Literal['strict', 'sample_window'] = 'strict'


def summary(report):
    return {key: value for key, value in report.items() if key not in ('points', 'model')}


def install_experiment_routes(app, directory):
    @app.post('/api/experiments')
    async def experiment(settings: ExperimentSettings):
        lock = app.state.training_lock
        if lock.locked():
            raise HTTPException(409, 'An experiment or training job is already running')
        async with lock:
            p = app.state.profiler
            if not p.replay_rows:
                raise HTTPException(409, 'Load a recording first')
            try:
                report = await asyncio.to_thread(evaluate_model, p.model, p.replay_rows,
                    p.replay_cadence, settings.policy, provenance=p.replay_provenance)
                report = await asyncio.to_thread(save_experiment, report, directory)
            except ValueError as exc:
                raise HTTPException(422, str(exc)) from exc
            except OSError as exc:
                raise HTTPException(500, 'Could not save experiment; check local storage') from exc
            return summary(report)

    @app.get('/api/experiments')
    async def experiments(limit: int = Query(default=20, ge=1, le=100)):
        # Files are generated only by this application, never accepted as uploads.
        paths = sorted(directory.glob('*.json'), key=lambda path: path.stat().st_mtime, reverse=True)[:limit]
        return [summary(json.loads(path.read_text(encoding='utf-8'))) for path in paths]

    @app.get('/api/experiments/{identifier}')
    async def experiment_detail(identifier: str, limit: int = Query(default=2000, ge=1, le=10000)):
        if not re.fullmatch(r'[0-9a-f]{32}', identifier):
            raise HTTPException(422, 'Invalid experiment ID')
        path = directory / f'{identifier}.json'
        if not path.is_file():
            raise HTTPException(404, 'Experiment not found')
        report = json.loads(path.read_text(encoding='utf-8'))
        report['points'] = report['points'][:limit]
        report['displayed_rows'] = len(report['points'])
        return report
