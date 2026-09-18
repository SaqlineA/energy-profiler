"""Offline training/evaluation. Does not change the running server's model.

python evaluate.py --csv recording.csv --cadence 8 --output data/experiment
Optionally --test-csv different-household.csv for a separate-household holdout.
No user data is transmitted. Obtain and convert public datasets under their terms.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

from ml import ApplianceModel, train_recorded
from sources import parse_csv


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', type=Path)
    parser.add_argument('--test-csv', type=Path)
    parser.add_argument('--cadence', type=float, default=1)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--output', type=Path, default=Path('data/experiment'))
    args = parser.parse_args()
    if not math.isfinite(args.cadence) or not 0 < args.cadence <= 3600:
        parser.error('cadence must be finite, positive, and at most 3600 seconds')
    if args.test_csv and not args.csv:
        parser.error('--test-csv requires --csv')
    try:
        if args.csv:
            content = args.csv.read_bytes()
            rows = parse_csv(content.decode('utf-8-sig'))
            provenance = {'name': args.csv.name, 'sha256': hashlib.sha256(content).hexdigest()}
            if args.test_csv:
                test_content = args.test_csv.read_bytes()
                test = parse_csv(test_content.decode('utf-8-sig'))
                digest = hashlib.sha256(test_content).hexdigest()
                if digest == provenance['sha256']:
                    parser.error('training and held-out files must differ')
                # Also reject duplicated measurements, even if the CSV formatting differs.
                train_rows = {json.dumps(r, sort_keys=True) for r in rows}
                if any(json.dumps(r, sort_keys=True) in train_rows for r in test):
                    parser.error('held-out file contains duplicate training measurements')
                provenance.update(test_sha256=digest, test_name=args.test_csv.name,
                                  split='separate user-declared household/session files')
                model = ApplianceModel(args.seed, [rows], [test], args.cadence, provenance)
            else:
                model = train_recorded(rows, args.cadence, args.seed, provenance)
        else:
            model = ApplianceModel(args.seed)
        model.save(args.output)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps(model.metrics, indent=2))


if __name__ == '__main__':
    main()
