"""Describe real REFIT washing-machine cycles (Houses 1-4 only). No training.

A cycle is a run of active readings (>10 W) joined across pauses of up to
15 minutes. Power bands approximate stages; they are labels for description,
not ground-truth washer phases.
"""
import argparse
import csv
import json
from pathlib import Path
from statistics import median

ACTIVE_W = 10  # Same threshold as the simulator's washer.
MAX_PAUSE_S = 15 * 60  # Soak/pause gaps shorter than this stay inside one cycle.
MAX_INTERVAL_S = 120  # Longer sampling gaps are not integrated or treated as continuous.
MIN_CYCLE_S, MIN_PEAK_W = 10 * 60, 100  # Ignore standby blips.
MIN_STAGE_S = 60  # A band must last this long to count as a stage.
BANDS = ((0, 'pause'), (ACTIVE_W, 'motor'), (300, 'spin'), (1000, 'heat'))
# Washer channels from NILMTK REFIT metadata (meter N = REFIT Appliance N-1).
CHANNELS = {1: ['Appliance5'], 2: ['Appliance2'], 3: ['Appliance6'], 4: ['Appliance5', 'Appliance6']}


def band(watts):
    return [name for low, name in BANDS if watts >= low][-1]


def pct(values, q):
    values = sorted(values)
    return round(values[min(len(values) - 1, int(q * len(values)))], 1) if values else None


def read(path, column):
    """Complete rows only: a byte-range prefix can end midway through a line."""
    path = Path(path)
    if 'holdout' in path.resolve().parts or 'House5' in path.name or 'house5' in path.name:
        raise ValueError('House 5 is retired; do not profile it')
    with path.open(newline='', encoding='utf-8') as handle:
        lines = handle.read().splitlines(keepends=True)
    if lines and not lines[-1].endswith('\n'):
        lines.pop()
    return [(int(r['Unix']), float(r[column])) for r in csv.DictReader(lines)]


def cycles(readings):
    found, current, last_active = [], None, None
    for index, (t, w) in enumerate(readings):
        gap = index and t - readings[index - 1][0] > MAX_INTERVAL_S
        if current and (gap or (w > ACTIVE_W and t - last_active > MAX_PAUSE_S)):
            found.append(current)
            current = None
        if w > ACTIVE_W:
            if current is None:
                current = []
            last_active = t
        if current is not None:
            current.append((t, w))
    if current:
        found.append(current)
    # Trim trailing pause readings and drop blips.
    result = []
    for c in found:
        while c and c[-1][1] <= ACTIVE_W:
            c.pop()
        if c and c[-1][0] - c[0][0] >= MIN_CYCLE_S and max(w for _, w in c) >= MIN_PEAK_W:
            result.append(c)
    return result


def stages(cycle):
    """Merge consecutive readings into bands; bands shorter than a minute join the previous stage."""
    runs = []
    for (t, w), nxt in zip(cycle, cycle[1:] + [None]):
        end = nxt[0] if nxt else t
        name = band(w)
        if runs and runs[-1][0] == name:
            runs[-1][2] = end
        else:
            runs.append([name, t, end])
    merged = []
    for name, start, end in runs:
        if merged and (end - start < MIN_STAGE_S or merged[-1][0] == name):
            merged[-1][2] = end
        else:
            merged.append([name, start, end])
    return merged


def profile(readings):
    span_days = (readings[-1][0] - readings[0][0]) / 86400
    found = cycles(readings)
    inside = {t for c in found for t, _ in c}
    idle = [w for t, w in readings if t not in inside]
    rows = []
    for c in found:
        energy = sum((a[1] + b[1]) / 2 * (b[0] - a[0]) for a, b in zip(c, c[1:])
                     if b[0] - a[0] <= MAX_INTERVAL_S) / 3.6e6
        steps = [abs(b[1] - a[1]) for a, b in zip(c, c[1:])]
        seq = stages(c)
        time_in = {name: sum(e - s for n, s, e in seq if n == name) / 60 for _, name in BANDS}
        rows.append({'minutes': round((c[-1][0] - c[0][0]) / 60, 1), 'peak_w': max(w for _, w in c),
                     'median_active_w': median(w for _, w in c if w > ACTIVE_W), 'kwh': round(energy, 3),
                     'stages': len(seq), 'sequence': ' > '.join(n for n, _, _ in seq),
                     'minutes_by_band': {k: round(v, 1) for k, v in time_in.items()},
                     'median_step_w': median(steps), 'max_step_w': max(steps)})
    key = lambda k: [r[k] for r in rows]
    return {
        'days': round(span_days, 1), 'cycles': len(rows),
        'cycles_per_day': round(len(rows) / span_days, 2) if span_days else None,
        'idle_w_p50_p90': [pct(idle, .5), pct(idle, .9)],
        'cycle_minutes_p10_p50_p90': [pct(key('minutes'), q) for q in (.1, .5, .9)],
        'peak_w_p10_p50_p90': [pct(key('peak_w'), q) for q in (.1, .5, .9)],
        'median_active_w_p50': pct(key('median_active_w'), .5),
        'kwh_per_cycle_p50': pct(key('kwh'), .5),
        'stages_p10_p50_p90': [pct(key('stages'), q) for q in (.1, .5, .9)],
        'heating_cycles': sum(r['minutes_by_band']['heat'] > 0 for r in rows),
        'minutes_by_band_p50': {name: pct([r['minutes_by_band'][name] for r in rows], .5) for _, name in BANDS},
        'median_step_w_p50': pct(key('median_step_w'), .5), 'max_step_w_p50': pct(key('max_step_w'), .5),
        'examples': [r['sequence'] for r in rows[:3]],
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder', type=Path, default=Path('data/refit/washer'))
    args = parser.parse_args()
    result = {f'house{h}_{column}': profile(read(args.folder / f'house{h}-prefix-20mb.part', column))
              for h, columns in CHANNELS.items() for column in columns}
    print(json.dumps(result, indent=2))
