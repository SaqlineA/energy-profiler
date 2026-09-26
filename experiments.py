"""Evaluate a frozen model, including partially labeled recordings. Never train here."""
import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import numpy as np

from features import window_features
from ml import APPLIANCES, ApplianceModel
from sources import parse_csv, regular_interval, seconds_between, valid_interval


def device_metrics(points, device):
    key, threshold = device['id'], device['threshold']
    scored = [(p, p['predictions'][key]) for p in points
              if p['truth'].get(key) is not None and key in p['predictions']]
    truth = np.array([p['truth'][key] for p, _ in scored])
    estimated = np.array([prediction['estimated_watts'] for _, prediction in scored])
    actual = truth >= threshold
    predicted = np.array([prediction['raw_on'] for _, prediction in scored], dtype=bool)
    tp = int(np.sum(actual & predicted))
    fp = int(np.sum(~actual & predicted))
    fn = int(np.sum(actual & ~predicted))
    true_energy = estimated_energy = covered = 0.0
    for previous, current in zip(points, points[1:]):
        dt = current['interval_seconds']
        if (dt and all(p['truth'].get(key) is not None and key in p['predictions']
                       for p in (previous, current))):
            true_energy += (previous['truth'][key] + current['truth'][key]) / 2 * dt / 3_600_000
            estimated_energy += sum(p['predictions'][key]['estimated_watts'] for p in (previous, current)) / 2 * dt / 3_600_000
            covered += dt
    return {'samples': len(scored), 'positive_samples': int(actual.sum()),
            'negative_samples': int((~actual).sum()),
            'accuracy': float(np.mean(actual == predicted)) if scored else None,
            'precision': tp / (tp + fp) if tp + fp else None,
            'recall': tp / (tp + fn) if tp + fn else None,
            'f1': 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None,
            'mae_watts': float(np.abs(estimated - truth).mean()) if scored else None,
            'rmse_watts': float(np.sqrt(np.mean((estimated - truth) ** 2))) if scored else None,
            'confusion': {'tp': tp, 'fp': fp, 'fn': fn, 'tn': int(np.sum(~actual & ~predicted))},
            'certain_samples': sum(prediction['on'] is not None for _, prediction in scored),
            'energy_coverage_seconds': covered,
            'true_kwh': true_energy if covered else None,
            'estimated_kwh': estimated_energy if covered else None,
            'absolute_energy_error_kwh': abs(estimated_energy - true_energy) if covered else None}


def evaluate_model(model, rows, cadence=1, policy='strict', max_gap=16, provenance=None, min_history=0):
    if policy not in ('strict', 'sample_window'):
        raise ValueError('Unknown timing policy')
    if not all(math.isfinite(v) and 0 < v <= 3600 for v in (cadence, max_gap)):
        raise ValueError('Timing values must be finite, positive and at most 3600 seconds')
    if not 2 <= len(rows) <= 10000:
        raise ValueError('Experiments require 2–10,000 readings')
    devices = getattr(model, 'devices', APPLIANCES)
    window_size = model.metrics['window']
    required_history = max(window_size, min_history)
    compatible = abs(cadence - model.metrics['cadence_seconds']) < .001
    points, features, indices, spans = [], [], [], []
    window, times, previous = [], [], None
    for index, row in enumerate(rows):
        # Diagnostics retain native samples, but do not bridge outages.
        dt = valid_interval(row, previous, cadence if policy == 'strict' else max_gap / 1.5)
        contiguous = dt and (policy != 'strict' or regular_interval(row, previous, cadence))
        if not contiguous:
            window, times = [], []
        if row['total_watts'] is not None:
            window = (window + [row['total_watts']])[-required_history:]
            times = (times + [row])[-window_size:]
        point = {'timestamp': row['timestamp'], 'total_watts': row['total_watts'],
                 'truth': {d['id']: row.get(d['id']) for d in devices}, 'predictions': {},
                 'interval_seconds': dt, 'quality': 'missing' if row['total_watts'] is None else 'gap' if previous and not dt else 'valid'}
        points.append(point)
        if len(window) == required_history and (compatible or policy == 'sample_window'):
            features.append(model.features(window[-window_size:], row) if hasattr(model, 'features')
                            else window_features(window[-window_size:]))
            indices.append(index)
            spans.append(seconds_between(times[-1], times[0]))
        previous = row
    # Batch prediction is much faster than invoking 120 trees separately per row.
    if features:
        states = model.classifier.predict(features)
        powers = model.regressor.predict(features)
        probabilities = model.classifier.predict_proba(features)
        for j, index in enumerate(indices):
            point = points[index]
            total = point['total_watts']
            residual = float(total - sum(powers[j]))
            outside = not model.power_bounds[0] - 5 <= total <= model.power_bounds[1] * 1.10 + 5
            uncertain_load = outside or abs(residual) > max(30, total * .20)
            point['unexplained_watts'] = residual
            for i, device in enumerate(devices):
                classes = list(model.classifier.classes_[i])
                probability = float(probabilities[i][j][classes.index(1)]) if 1 in classes else 0.0
                point['predictions'][device['id']] = {
                    'raw_on': bool(states[j][i]),
                    'on': None if uncertain_load or .35 < probability < .65 else probability >= .5,
                    'estimated_watts': float(max(0, powers[j][i])), 'probability_on': probability}
    timing_note = ('Strict: original model cadence and regular windows required.' if policy == 'strict'
                   else 'Sample-window diagnostic: native irregular samples, NOT equivalent model-time windows; not live validation.')
    return {'schema': 1, 'created_at': datetime.now(timezone.utc).isoformat(),
            'model_version': model.metrics['version'], 'model': model.metrics,
            'provenance': provenance or {}, 'policy': policy, 'cadence_seconds': cadence,
            'max_gap_seconds': max_gap if policy != 'strict' else cadence * 1.5,
            'minimum_comparison_history': required_history,
            'timing_note': timing_note, 'rows': len(rows), 'prediction_windows': len(indices),
            'window_span_seconds': {'min': min(spans), 'max': max(spans)} if spans else None,
            'devices': {d['id']: device_metrics(points, d) for d in devices}, 'points': points,
            'limitation': 'Metrics score raw outputs before abstention, on known labels only. '
                          'Inspect class support and certain_samples. Short/single-house recordings do not prove generalization. '
                          'Source cleaning may already have imputed zeros.'}


def save_experiment(report, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    identifier = uuid4().hex
    report = {**report, 'id': identifier}
    temporary = directory / f'{identifier}.tmp'
    with temporary.open('x', encoding='utf-8') as handle:
        json.dump(report, handle, allow_nan=False)
    temporary.rename(directory / f'{identifier}.json')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv', type=Path)
    parser.add_argument('--model-dir', type=Path, default=Path('data/models'))
    parser.add_argument('--output', type=Path, default=Path('data/experiments'))
    parser.add_argument('--cadence', type=float, default=8)
    parser.add_argument('--policy', choices=['strict', 'sample_window'], default='strict')
    args = parser.parse_args()
    content = args.csv.read_bytes()
    report = evaluate_model(ApplianceModel.load(args.model_dir), parse_csv(content.decode('utf-8-sig')),
                            args.cadence, args.policy,
                            provenance={'name': args.csv.name, 'sha256': hashlib.sha256(content).hexdigest()})
    report = save_experiment(report, args.output)
    print(json.dumps({key: value for key, value in report.items() if key not in ('points', 'model')}, indent=2))
