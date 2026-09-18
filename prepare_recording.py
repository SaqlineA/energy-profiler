"""Convert a selected slice of a CSV into the replay contract, without pandas.

No download, guessed device mappings, missing-value filling, or resampling.
Outputs are created exclusively: existing files are never overwritten.
"""
import argparse
import csv
import hashlib
import io
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from sources import DEVICE_IDS, MAX_ROWS, parse_csv


def convert(path, timestamp_column, mains_column, mapping, timestamp_format='iso',
            scale=1.0, start=0, limit=MAX_ROWS):
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError('Power scale must be finite and positive')
    if start < 0 or not 2 <= limit <= MAX_ROWS:
        raise ValueError('Start must be nonnegative and limit between 2 and 50,000')
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=['timestamp', 'total_watts', *DEVICE_IDS])
    writer.writeheader()
    with Path(path).open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        required = {timestamp_column, mains_column, *(value for value in mapping.values() if value)}
        if not required <= set(reader.fieldnames or []):
            raise ValueError(f'Missing columns: {sorted(required - set(reader.fieldnames or []))}')
        for index, row in enumerate(reader):
            if index < start:
                continue
            if index >= start + limit:
                break
            timestamp = row[timestamp_column]
            if timestamp_format == 'unix':
                timestamp = datetime.fromtimestamp(float(timestamp), timezone.utc).isoformat()
            selected = {'timestamp': timestamp}
            for key, column in {'total_watts': mains_column, **mapping}.items():
                value = row.get(column) if column else None
                selected[key] = '' if value is None or not value.strip() else float(value) * scale
            writer.writerow(selected)
    content = output.getvalue()
    parse_csv(content)  # Validate before creating any output files.
    return content


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--timestamp', default='timestamp', help='Source timestamp column')
    parser.add_argument('--mains', default='total_watts', help='Source aggregate power column')
    parser.add_argument('--timestamp-format', choices=['iso', 'unix'], default='iso')
    parser.add_argument('--scale', type=float, default=1, help='Multiply every power column by this (e.g. 1000 for kW)')
    parser.add_argument('--start', type=int, default=0, help='Zero-based data row offset')
    parser.add_argument('--limit', type=int, default=MAX_ROWS)
    parser.add_argument('--origin', required=True, help='Dataset source/reference and household identifier')
    for key in DEVICE_IDS:
        parser.add_argument('--' + key, help='Source submeter column; omit if unknown')
    args = parser.parse_args()
    mapping = {key: getattr(args, key) for key in DEVICE_IDS}
    sidecar = args.output.with_suffix(args.output.suffix + '.metadata.json')
    try:
        if args.output.exists() or sidecar.exists():
            raise ValueError('Output or metadata already exists; choose a new output name')
        content = convert(args.input, args.timestamp, args.mains, mapping,
                          args.timestamp_format, args.scale, args.start, args.limit)
        metadata = {'origin': args.origin, 'input_name': args.input.name, 'mapping': mapping,
                    'mains': args.mains, 'timestamp': args.timestamp, 'timestamp_format': args.timestamp_format,
                    'power_scale': args.scale, 'start_row': args.start, 'row_limit': args.limit,
                    'normalized_sha256': hashlib.sha256(content.encode()).hexdigest()}
        with args.output.open('x', encoding='utf-8', newline='') as handle:
            handle.write(content)
        with sidecar.open('x', encoding='utf-8') as handle:
            json.dump(metadata, handle, indent=2)
    except (OSError, ValueError, OverflowError) as exc:
        parser.error(str(exc))
    print(f'Prepared {args.output}; source mapping saved in {sidecar}')


if __name__ == '__main__':
    main()
