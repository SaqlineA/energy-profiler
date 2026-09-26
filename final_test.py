"""Step 11: score the preregistered models on House 5 ONCE (docs/final-test.md).

Refuses to run if a final result already exists. Nothing is tuned here.
"""
import argparse
import json
from pathlib import Path

from experiments import evaluate_model, save_experiment
from fridge_development import EXTRA_TRAINING, load_house
from real_data_split import verify_split
from realistic import realistic_sessions
from research_model import ResearchModel, add_background

CADENCE, MODE = 16, 'relative'
REAL_VERSION = '92d52feba60f9800'  # v4r Decision Tree scored on House 2.
METRICS = ('f1', 'precision', 'recall', 'accuracy', 'mae_watts', 'true_kwh', 'estimated_kwh',
           'positive_samples', 'negative_samples', 'energy_coverage_seconds')


def verdict(real, synthetic, off):
    ratio = lambda d: d['estimated_kwh'] / d['true_kwh']
    passed = {'f1_beats_always_off': real['f1'] > off['f1'],
              'mae_beats_always_off': real['mae_watts'] < off['mae_watts'],
              'energy_ratio_0.5_to_1.5': .5 <= ratio(real) <= 1.5}
    better = (real['f1'] > synthetic['f1'] and real['mae_watts'] < synthetic['mae_watts']
              and abs(ratio(real) - 1) < abs(ratio(synthetic) - 1))
    return {**passed, 'passes': all(passed.values()), 'better_than_synthetic': better,
            'energy_ratio': {'real': ratio(real), 'synthetic': ratio(synthetic)}}


def run_final(manifest, reports_dir, result_path, extra=EXTRA_TRAINING, real_version=REAL_VERSION):
    manifest, result_path = Path(manifest), Path(result_path)
    if result_path.exists():
        raise ValueError('Final test already run; House 5 is scored once only')
    split = verify_split(manifest)
    partitions = split['partitions']
    training = [load_house(manifest.parent / partitions['training']['path'], partitions['training']['sha256'], CADENCE, MODE)]
    training += [load_house(manifest.parent / path, digest, CADENCE, MODE) for path, digest in extra.values()]
    real = ResearchModel(training, algorithm='decision_tree', cadence=CADENCE, mode=MODE,
                         fridge_only=True, profile='REFIT Houses [1, 3, 4] training')  # Must match v4r for the version hash.
    if real_version and real.metrics['version'] != real_version:
        raise ValueError(f"Retrained model {real.metrics['version']} is not the preregistered {real_version}")
    synthetic = ResearchModel([add_background(s[::CADENCE]) for s in realistic_sessions(42, 10, 1800)],
                              algorithm='decision_tree', cadence=CADENCE, mode=MODE,
                              fridge_only=True, profile='realistic simulator, seed 42')
    off = ResearchModel(training, algorithm='always_off', cadence=CADENCE, mode=MODE, fridge_only=True)
    # House 5 is parsed only here, after every model is frozen.
    final = partitions['final_test']
    house5 = load_house(manifest.parent / final['path'], final['sha256'], CADENCE, MODE)
    reports = {}
    for name, model in (('real_v4r_decision_tree', real), ('synthetic_decision_tree', synthetic), ('always_off', off)):
        reports[name] = evaluate_model(model, house5, cadence=CADENCE, policy='strict', provenance={
            'name': f'FINAL House 5 / {name}', 'protocol': 'final-test-v1', 'evaluation_role': 'final_test',
            'evaluation_house': 5, 'sha256': final['sha256']})
    stamps = [[p['timestamp'] for p in r['points'] if p['predictions']] for r in reports.values()]
    if not stamps[0] or any(s != stamps[0] for s in stamps[1:]):
        raise ValueError('Models must score identical nonempty House 5 windows')
    devices = {name: r['devices']['refrigerator'] for name, r in reports.items()}
    result = {'protocol': 'final-test-v1', 'windows': len(stamps[0]),
              'model_versions': {name: r['model_version'] for name, r in reports.items()},
              'metrics': {name: {k: d[k] for k in METRICS} for name, d in devices.items()},
              'confusion': {name: d['confusion'] for name, d in devices.items()},
              'verdict': verdict(devices['real_v4r_decision_tree'], devices['synthetic_decision_tree'],
                                 devices['always_off'])}
    for report in reports.values():
        save_experiment(report, reports_dir)
    with result_path.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=Path('data/refit/split-v1.json'))
    parser.add_argument('--output', type=Path, default=Path('data/experiments'))
    parser.add_argument('--result', type=Path, default=Path('data/holdout/final-test-v1.json'))
    args = parser.parse_args()
    print(json.dumps(run_final(args.manifest, args.output, args.result), indent=2))
