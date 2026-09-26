"""Describe refrigerator behaviour in simulators vs REFIT Houses 1/2. No training.

Uses fridge labels for description only. Final-test (holdout) files are refused.
"""
import argparse
import json
from pathlib import Path
from statistics import median, pstdev

from ml import synthetic_households
from realistic import realistic_sessions
from sources import parse_csv, seconds_between

THRESHOLD = 20  # Same on/off threshold as the fridge experiments.
MAX_GAP = 60  # A run touching a longer gap is censored, never bridged.


def pct(values, q):
    values = sorted(values)
    return round(values[min(len(values) - 1, int(q * len(values)))], 1) if values else None


def runs(session):
    """Split one recording into on/off runs; `complete` means both ends were observed."""
    out, current = [], None
    for previous, row in zip([None] + session, session):
        if row['refrigerator'] is None or row['total_watts'] is None:
            if current:
                current['complete'] = False
            current = None
            continue
        on = row['refrigerator'] >= THRESHOLD
        gap = previous is not None and seconds_between(row, previous) > MAX_GAP
        if current and (gap or current['on'] != on):
            if gap:
                current['complete'] = False
            else:
                current['next'] = row
            current = None
        if current is None:
            current = {'on': on, 'rows': [], 'complete': bool(out) and not gap
                       and previous is not None and previous['refrigerator'] is not None,
                       'previous': previous}
            out.append(current)
        current['rows'].append(row)
    if current:
        current['complete'] = False
    return out


def profile(sessions):
    on_w, off_w, on_s, off_s, cv, startup, fridge_step, total_step = [], [], [], [], [], [], [], []
    for session in sessions:
        for run in runs(session):
            watts = [r['refrigerator'] for r in run['rows']]
            (on_w if run['on'] else off_w).extend(watts)
            if run['complete'] and 'next' in run:
                (on_s if run['on'] else off_s).append(seconds_between(run['next'], run['rows'][0]))
            if run['on'] and len(watts) >= 3:
                steady = median(watts)
                cv.append(pstdev(watts) / steady)
                start = [r['refrigerator'] for r in run['rows'] if seconds_between(r, run['rows'][0]) <= 30]
                startup.append(max(start) / steady)
            if run['on'] and run['previous'] is not None and run['complete']:
                first, prev = run['rows'][0], run['previous']
                fridge_step.append(first['refrigerator'] - prev['refrigerator'])
                total_step.append(first['total_watts'] - prev['total_watts'])
    rows = [r for s in sessions for r in s]
    intervals = [seconds_between(b, a) for s in sessions for a, b in zip(s, s[1:])]
    return {
        'readings': len(rows), 'median_interval_s': median(intervals),
        'duty_cycle': round(len(on_w) / (len(on_w) + len(off_w)), 3),
        'on_watts_p10_p50_p90': [pct(on_w, .1), pct(on_w, .5), pct(on_w, .9)],
        'off_watts_p50_p90': [pct(off_w, .5), pct(off_w, .9)],
        'complete_on_cycles': len(on_s),
        'on_cycle_minutes_p10_p50_p90': [pct([s / 60 for s in on_s], q) for q in (.1, .5, .9)],
        'off_cycle_minutes_p10_p50_p90': [pct([s / 60 for s in off_s], q) for q in (.1, .5, .9)],
        'startup_peak_over_median_p50_p90': [pct(startup, .5), pct(startup, .9)],
        'within_run_variation_cv_p50': pct(cv, .5),
        'switch_on_fridge_step_w_p50': pct(fridge_step, .5),
        'switch_on_aggregate_step_w_p10_p50_p90': [pct(total_step, q) for q in (.1, .5, .9)],
        'aggregate_watts_p10_p50_p90': [pct([r['total_watts'] for r in rows if r['total_watts'] is not None], q)
                                        for q in (.1, .5, .9)],
    }


def load(path):
    path = Path(path)
    if 'holdout' in path.resolve().parts:
        raise ValueError('Final-test data is reserved; do not profile it')
    return parse_csv(path.read_text(encoding='utf-8-sig'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--real', nargs='*', type=Path,
                        default=[Path('data/refit/house1-replay-10000.csv'), Path('data/refit/house2-replay-10000.csv')])
    args = parser.parse_args()
    result = {
        # Live model generator (current.json provenance) and research simulator (cadence v1 seeds).
        'live_generator_synthetic_households': profile(synthetic_households(43, 60)),
        'research_simulator_realistic': profile(realistic_sessions(42, 10, 1800)),
        **{path.stem: profile([load(path)]) for path in args.real},
    }
    print(json.dumps(result, indent=2))
