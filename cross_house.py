"""Leave-one-house-out fridge test across REFIT Houses 1-5 (docs/cross-house-protocol.md).

Settings are the frozen v4r ones; nothing is tuned. Refuses to run twice.
"""
import argparse
import json
from pathlib import Path

from experiments import evaluate_model, save_experiment
from final_test import CADENCE, METRICS, MODE
from fridge_development import EXTRA_TRAINING, load_house
from real_data_split import verify_split
from realistic import realistic_sessions
from research_model import ResearchModel, add_background


def house_files(manifest, extra=EXTRA_TRAINING):
    """{house: (path, sha256)} for every pinned house: split partitions plus the extra training houses."""
    manifest = Path(manifest)
    parts = verify_split(manifest)['partitions']
    files = {p['house']: (manifest.parent / p['path'], p['sha256']) for p in parts.values()}
    files.update({h: (manifest.parent / path, digest) for h, (path, digest) in extra.items()})
    return dict(sorted(files.items()))


def rules(folds):
    """The preregistered R1/R2 decision rules applied to per-house metrics."""
    n = len(folds)
    transfer = sum(f['real']['f1'] > f['always_off']['f1'] and f['real']['mae_watts'] < f['always_off']['mae_watts']
                   for f in folds.values())
    sim_wins = sum(f['simulator']['f1'] > f['real']['f1'] for f in folds.values())
    r2 = ('simulator advantage holds' if sim_wins >= n - 1 else
          'House 5 was an exception' if sim_wins <= 1 else 'mixed, no general claim')
    spread = {m: {'mean': sum(f[m]['f1'] for f in folds.values()) / n,
                  'min': min(f[m]['f1'] for f in folds.values()),
                  'max': max(f[m]['f1'] for f in folds.values())} for m in ('real', 'simulator', 'always_off')}
    return {'R1_transfer_houses': transfer, 'R1': 'holds' if transfer >= n - 1 else 'does not transfer reliably',
            'R2_simulator_wins': sim_wins, 'R2': r2, 'f1_spread': spread}


def run(manifest, reports_dir, result_path, extra=EXTRA_TRAINING):
    result_path = Path(result_path)
    if result_path.exists():
        raise ValueError('Cross-house test already run; it runs once')
    houses = {h: load_house(path, digest, CADENCE, MODE) for h, (path, digest) in house_files(manifest, extra).items()}
    simulator = ResearchModel([add_background(s[::CADENCE]) for s in realistic_sessions(42, 10, 1800)],
                              algorithm='decision_tree', cadence=CADENCE, mode=MODE,
                              fridge_only=True, profile='realistic simulator, seed 42')
    folds, reports = {}, []
    for held in houses:
        training = [rows for h, rows in houses.items() if h != held]  # One session per house.
        label = f'REFIT Houses {[h for h in houses if h != held]} training'
        models = {'real': ResearchModel(training, algorithm='decision_tree', cadence=CADENCE, mode=MODE,
                                        fridge_only=True, profile=label),
                  'simulator': simulator,
                  'always_off': ResearchModel(training, algorithm='always_off', cadence=CADENCE, mode=MODE,
                                              fridge_only=True)}
        scored = {name: evaluate_model(model, houses[held], cadence=CADENCE, policy='strict', provenance={
            'name': f'Cross-house / held-out House {held} / {name}', 'protocol': 'cross-house-v1',
            'evaluation_role': 'cross_house', 'evaluation_house': held,
            'training_houses': [h for h in houses if h != held] if name != 'simulator' else [],
            'sha256': house_files(manifest, extra)[held][1]}) for name, model in models.items()}
        stamps = [[p['timestamp'] for p in r['points'] if p['predictions']] for r in scored.values()]
        if not stamps[0] or any(s != stamps[0] for s in stamps[1:]):
            raise ValueError(f'Models must score identical nonempty windows on House {held}')
        devices = {name: r['devices']['refrigerator'] for name, r in scored.items()}
        folds[held] = {'windows': len(stamps[0]),
                       **{name: {**{k: d[k] for k in METRICS},
                                 'energy_ratio': d['estimated_kwh'] / d['true_kwh'] if d['true_kwh'] else None}
                          for name, d in devices.items()}}
        reports += scored.values()
    result = {'protocol': 'cross-house-v1', 'houses': list(houses), 'folds': folds, 'verdict': rules(folds)}
    for report in reports:
        save_experiment(report, reports_dir)
    with result_path.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=Path('data/refit/split-v1.json'))
    parser.add_argument('--output', type=Path, default=Path('data/experiments'))
    parser.add_argument('--result', type=Path, default=Path('data/holdout/cross-house-v1.json'))
    args = parser.parse_args()
    print(json.dumps(run(args.manifest, args.output, args.result), indent=2))
