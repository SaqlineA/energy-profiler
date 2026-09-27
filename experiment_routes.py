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


FINAL_NAMES = {'real_v4r_decision_tree': 'Real-trained Decision Tree',
               'synthetic_decision_tree': 'Synthetic-trained Decision Tree',
               'always_off': 'Always-off baseline'}
ALGORITHMS = {'decision_tree': 'Decision Tree', 'random_forest': 'Random Forest', 'always_off': 'Always-off baseline'}


def explain(m, device='appliance'):
    """Plain-language reading of one appliance's metrics; wording bands are descriptive, not pass/fail."""
    if not m.get('samples'):
        return f'No {device} windows could be scored.'
    tp, fp = m['confusion']['tp'], m['confusion']['fp']
    if not m['positive_samples']:
        text = f'The {device} was never on in this data, so detection cannot be judged.'
    elif tp + fp == 0:
        text = f'The model never predicted the {device} ON, so it missed every ON period.'
    else:
        recall = m['recall']
        text = ('The model caught most' if recall >= .8 else 'The model caught more than half of the'
                if recall >= .5 else f'The model detected some {device} activity but missed many')
        text += f' ON periods ({recall:.0%} found).'
        if m['precision'] is not None and m['precision'] < .8:
            text += f" {1 - m['precision']:.0%} of its ON predictions were false alarms."
    if m.get('true_kwh'):
        ratio = m['estimated_kwh'] / m['true_kwh']
        text += (f' It estimated total {device} energy within {abs(ratio - 1):.0%}.' if .8 <= ratio <= 1.2 else
                 f" It {'underestimated' if ratio < 1 else 'overestimated'} total {device} energy by {abs(ratio - 1):.0%}.")
    return text


def describe(report):
    """Label data sources and give each saved report a readable name and group."""
    provenance, model = report.get('provenance', {}), report.get('model', {})
    name = provenance.get('name') or report.get('id', '')[:8]
    house = provenance.get('evaluation_house')
    real_eval = house is not None or bool(re.search(r'refit|house\d', name, re.I))
    training = str(model.get('training_source', ''))
    trained = ('none' if model.get('algorithm') == 'always_off'
               else 'real' if 'REFIT' in training else 'synthetic')
    role = provenance.get('evaluation_role')
    label = name
    if role == 'final_test':
        label = f"FINAL House {house} — {FINAL_NAMES.get(name.rsplit('/ ', 1)[-1], name)}"
    elif role == 'development':
        version = provenance.get('protocol', '').rsplit('-', 1)[-1]
        label = f"House {house} — {version} · {ALGORITHMS.get(model.get('algorithm'), model.get('algorithm'))}"
    houses = re.findall(r'\d+', training) if trained == 'real' else []
    return {'label': label, 'group': role or 'other',
            'evaluation_data': 'real' if real_eval else 'synthetic',
            'dataset': f'REFIT House {house}' if house is not None else name,
            'training_data': trained,
            'training': ('No training (fixed rule)' if trained == 'none' else
                         f"REFIT Houses {', '.join(houses)}" if houses else f'Simulator ({training or "synthetic"})'),
            'model': ALGORITHMS.get(model.get('algorithm'), model.get('algorithm') or 'Original live model'),
            'explanations': {key: explain(m, key.replace('_', ' ')) for key, m in report.get('devices', {}).items()}}


def summary(report):
    return {**{key: value for key, value in report.items() if key not in ('points', 'model')},
            'describe': describe(report)}


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
        report['describe'] = describe(report)
        return report
