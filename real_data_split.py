"""Freeze REFIT 1/2/5 recording identities without fitting or scoring a model."""
import argparse
import hashlib
import json
import os
from pathlib import Path

from sources import parse_csv

ROLES = {'training': 1, 'development': 2, 'final_test': 5}


def freeze_split(training, development, final_test, output):
    output = Path(output)
    partitions, seen_rows, seen_files = {}, set(), set()
    for (role, house), filename in zip(ROLES.items(), (training, development, final_test)):
        path = Path(filename).resolve()
        content = path.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        if digest in seen_files:
            raise ValueError('Partitions contain duplicate files')
        rows = parse_csv(content.decode('utf-8-sig'))
        if len(rows) > 10000:
            raise ValueError('Protocol v1 allows at most 10,000 readings per partition')
        identities = {json.dumps(row, sort_keys=True) for row in rows}
        if identities & seen_rows:
            raise ValueError('Partitions overlap in exact normalized measurements')
        seen_files.add(digest)
        seen_rows.update(identities)
        partitions[role] = {
            'house': house, 'path': os.path.relpath(path, output.resolve().parent),
            'sha256': digest, 'rows': len(rows),
            'first_timestamp': rows[0]['timestamp'], 'last_timestamp': rows[-1]['timestamp'],
            'source': f'https://zenodo.org/records/5063428/files/CLEAN_House{house}.csv',
            'mapping': {'timestamp': 'Unix', 'total_watts': 'Aggregate', 'refrigerator': 'Appliance1'},
        }
    report = {'protocol': 'refit-split-v1', 'cadence_seconds': 8,
              'target': 'refrigerator', 'final_test_status': 'reserved_not_scored',
              'partitions': partitions,
              'limitation': 'House identities and channel mappings are declared, not inferred from CSV values. '
                            'Exact-duplicate checks cannot detect all near-duplicates or mislabeled houses. '
                            'Reservation is a workflow rule, not access control.'}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as handle:
        json.dump(report, handle, indent=2, allow_nan=False)
    return report


def verify_split(manifest):
    """Read file bytes only: verification never computes final-test statistics."""
    manifest = Path(manifest)
    report = json.loads(manifest.read_text(encoding='utf-8'))
    if report['protocol'] != 'refit-split-v1' or set(report['partitions']) != set(ROLES):
        raise ValueError('Unsupported split protocol or roles')
    for role, house in ROLES.items():
        partition = report['partitions'][role]
        if partition['house'] != house:
            raise ValueError('Declared house assignment changed')
        content = (manifest.parent / partition['path']).read_bytes()
        if hashlib.sha256(content).hexdigest() != partition['sha256']:
            raise ValueError(f'{role} recording changed since the split was frozen')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--training', type=Path)
    parser.add_argument('--development', type=Path)
    parser.add_argument('--final-test', type=Path)
    parser.add_argument('--output', type=Path, default=Path('data/refit/split-v1.json'))
    parser.add_argument('--verify', type=Path, help='Verify an existing manifest without scoring')
    args = parser.parse_args()
    if args.verify:
        verify_split(args.verify)
        print('All three recording hashes match; no model evaluation performed.')
    else:
        if not all((args.training, args.development, args.final_test)):
            parser.error('Provide --training, --development and --final-test, or --verify')
        freeze_split(args.training, args.development, args.final_test, args.output)
        print(f'Split frozen at {args.output}; final test reserved, not scored.')
