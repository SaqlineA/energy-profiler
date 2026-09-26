"""Fixed House 1 -> House 2 comparison; final-test data is never scored.

v1 uses raw eight-second strict timing. v2 first thins both recordings to 16 s
with the label-blind `thin_to_cadence` rule (see docs/fridge-development.md).
"""
import argparse
import hashlib
import json
from pathlib import Path

from experiments import evaluate_model, save_experiment
from real_data_split import verify_split
from research_model import ResearchModel
from sources import parse_csv, thin_to_cadence

PROTOCOLS = {'v1': 8, 'v2': 16}


def run_development(manifest, output, protocol='v1'):
    cadence = PROTOCOLS[protocol]
    manifest = Path(manifest)
    split = verify_split(manifest)  # Hash-only integrity check includes the reserved file.
    if (split['cadence_seconds'] != 8 or split['target'] != 'refrigerator'
            or split['final_test_status'] != 'reserved_not_scored'):
        raise ValueError('Expected the frozen eight-second fridge development protocol')
    data = {}
    for role in ('training', 'development'):
        partition = split['partitions'][role]
        content = (manifest.parent / partition['path']).read_bytes()
        if hashlib.sha256(content).hexdigest() != partition['sha256']:
            raise ValueError(f'{role} changed during loading')
        data[role] = parse_csv(content.decode('utf-8-sig'))
        if protocol != 'v1':
            data[role] = thin_to_cadence(data[role], cadence)
    reports = []
    for algorithm in ('always_off', 'decision_tree', 'random_forest'):
        model = ResearchModel([data['training']], algorithm=algorithm, cadence=cadence,
                              fridge_only=True, profile='REFIT House 1 training partition')
        report = evaluate_model(model, data['development'], cadence=cadence, policy='strict', provenance={
            'name': f'Fridge dev {protocol} / {algorithm} / House 2' + ('' if protocol == 'v1' else f' ({cadence}s thinned)'),
            'protocol': f'fridge-development-{protocol}', 'evaluation_role': 'development',
            'training_house': 1, 'evaluation_house': 2,
            'sampling': 'raw readings' if protocol == 'v1' else f'thin_to_cadence({cadence} s); no interpolation',
            'training_sha256': split['partitions']['training']['sha256'],
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
