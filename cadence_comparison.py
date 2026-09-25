"""Run the fixed synthetic eight-second protocol. Never promote a live model."""
import argparse
import hashlib
import json
from pathlib import Path

from experiments import evaluate_model, save_experiment
from realistic import realistic_sessions
from research_model import ResearchModel


def run_comparison(output):
    # Subsample actual one-second simulations: do not stretch their timestamps.
    training = [session[::8] for session in realistic_sessions(42, 10, 1800)]
    testing = [session[::8] for session in realistic_sessions(70042, 3, 1800)]
    rows = [row for session in testing for row in session]
    source_hash = hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()
    reports = []
    for algorithm in ('always_off', 'decision_tree', 'random_forest'):
        model = ResearchModel(training, algorithm=algorithm, cadence=8,
                              profile='realistic; instantaneous every-eighth sample')
        report = evaluate_model(model, rows, cadence=8, policy='strict', provenance={
            'name': f'Cadence v1 / {algorithm} / synthetic 8s',
            'protocol': 'cadence-v1', 'target': 'synthetic-realistic-8s',
            'sha256': source_hash, 'training_seed': 42, 'evaluation_seed': 70042,
            'training_sessions': 10, 'evaluation_sessions': 3,
            'seconds_per_session': 1800,
            'sampling': 'Instantaneous every-eighth sample; no averaging or interpolation',
            'comparison': 'Fixed five-reading / 32-second windows; separate generated sessions and seeds',
        })
        report['limitation'] += (' Synthetic-only cadence benchmark. Compressed appliance cycles '
                                 'and missed short events limit realism; no real-house accuracy claim.')
        reports.append(report)
    # Fail rather than compare scores from different usable timestamps.
    timestamps = [[p['timestamp'] for p in r['points'] if p['predictions']] for r in reports]
    if not timestamps[0] or any(t != timestamps[0] for t in timestamps[1:]):
        raise ValueError('Candidates must score the same nonempty set of timestamps')
    return [save_experiment(report, output) for report in reports]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('data/experiments'))
    args = parser.parse_args()
    for report in run_comparison(args.output):
        print(json.dumps({'id': report['id'], 'model': report['model']['algorithm'],
                          'prediction_windows': report['prediction_windows'],
                          'devices': report['devices']}, allow_nan=False), flush=True)
