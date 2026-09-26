"""Fixed House 1 -> House 2 comparison; final-test data is never scored.

v1 uses raw eight-second strict timing. v2 first thins both recordings to 16 s
with the label-blind `thin_to_cadence` rule. v3 is v2 with background-relative
features. v4/v4r add REFIT Houses 3 and 4 to training (v2/v3 features).
See docs/fridge-development.md.
"""
import argparse
import hashlib
import json
from pathlib import Path

from experiments import evaluate_model, save_experiment
from real_data_split import verify_split
from research_model import ResearchModel, add_background
from sources import parse_csv, thin_to_cadence

PROTOCOLS = {'v1': (8, 'summary'), 'v2': (16, 'summary'), 'v3': (16, 'relative'),
             'v4': (16, 'summary'), 'v4r': (16, 'relative')}
# Extra v4 training houses, pinned at download time (paths relative to the manifest).
EXTRA_TRAINING = {
    3: ('house3-replay-10000.csv', '7a6d59ab04873f2e1c5bb92602b49cbe1a0641c09572648664906d15e9e1c3c2'),
    4: ('house4-replay-10000.csv', 'e371a1c45ac2f30b3297b2a45ed423356af9eed4ee324fe57e9545ccb9f1d169'),
}


def run_development(manifest, output, protocol='v1'):
    cadence, mode = PROTOCOLS[protocol]
    manifest = Path(manifest)
    split = verify_split(manifest)  # Hash-only integrity check includes the reserved file.
    if (split['cadence_seconds'] != 8 or split['target'] != 'refrigerator'
            or split['final_test_status'] != 'reserved_not_scored'):
        raise ValueError('Expected the frozen eight-second fridge development protocol')
    files = {1: (split['partitions']['training']['path'], split['partitions']['training']['sha256']),
             2: (split['partitions']['development']['path'], split['partitions']['development']['sha256'])}
    if protocol.startswith('v4'):
        files.update(EXTRA_TRAINING)
    houses = {}
    for house, (path, digest) in files.items():
        content = (manifest.parent / path).read_bytes()
        if hashlib.sha256(content).hexdigest() != digest:
            raise ValueError(f'House {house} changed during loading')
        rows = parse_csv(content.decode('utf-8-sig'))
        if protocol != 'v1':
            rows = thin_to_cadence(rows, cadence)
        if mode == 'relative':
            rows = add_background(rows)
        houses[house] = rows
    development = houses.pop(2)
    training = list(houses.values())  # One session per house: windows never cross houses.
    seen = {json.dumps(r, sort_keys=True) for r in development}
    if any(json.dumps(r, sort_keys=True) in seen for rows in training for r in rows):
        raise ValueError('Training and development share exact measurements')
    reports = []
    for algorithm in ('always_off', 'decision_tree', 'random_forest'):
        model = ResearchModel(training, algorithm=algorithm, cadence=cadence, mode=mode,
                              fridge_only=True, profile=f'REFIT Houses {sorted(houses)} training')
        report = evaluate_model(model, development, cadence=cadence, policy='strict', provenance={
            'name': f'Fridge dev {protocol} / {algorithm} / House 2' + ('' if protocol == 'v1' else f' ({cadence}s thinned)'),
            'protocol': f'fridge-development-{protocol}', 'evaluation_role': 'development',
            'training_houses': sorted(houses), 'evaluation_house': 2,
            'features': mode if mode == 'summary' else 'relative to trailing 30 min aggregate minimum',
            'sampling': 'raw readings' if protocol == 'v1' else f'thin_to_cadence({cadence} s); no interpolation',
            'training_sha256': {h: files[h][1] for h in houses},
            'sha256': split['partitions']['development']['sha256'],
            'split_manifest_sha256': hashlib.sha256(manifest.read_bytes()).hexdigest(),
            'final_test': 'House 5 reserved; hashed only, not parsed or scored',
        })
        report['limitation'] += (' Development result, not final validation. Fridge-only model; '
                                 'other devices are not estimated. Residual-based certainty is '
                                 'not calibrated for a partial-appliance model.')
        support = model.metrics['train_class_support']['refrigerator']
        report['training_eligible'] = bool(support['on'] and support['off'])
        if not report['training_eligible']:
            report['limitation'] = ('INSUFFICIENT TRAINING: both on and off examples are required '
                                    'for candidate selection. These are diagnostic scores only. '
                                    + report['limitation'])
        reports.append(report)
    timestamps = [[p['timestamp'] for p in r['points'] if p['predictions']] for r in reports]
    if not timestamps[0] or any(t != timestamps[0] for t in timestamps[1:]):
        raise ValueError('Candidates need identical nonempty evaluation windows')
    return [save_experiment(report, output) for report in reports]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=Path('data/refit/split-v1.json'))
    parser.add_argument('--output', type=Path, default=Path('data/experiments'))
    parser.add_argument('--protocol', choices=PROTOCOLS, default='v1')
    args = parser.parse_args()
    for report in run_development(args.manifest, args.output, args.protocol):
        print(json.dumps({'id': report['id'], 'model': report['model']['algorithm'],
                          'training_windows': report['model']['train_samples'],
                          'training_support': report['model']['train_class_support'],
                          'training_eligible': report['training_eligible'],
                          'development_windows': report['prediction_windows'],
                          'window_span_seconds': report['window_span_seconds'],
                          'refrigerator': report['devices']['refrigerator']}, allow_nan=False))
