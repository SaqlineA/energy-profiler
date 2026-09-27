"""Synthetic washing-machine detection experiment v1 (docs/washer-experiment.md). One run, no tuning."""
import argparse
import json
from pathlib import Path

from experiments import evaluate_model, save_experiment
from realistic import realistic_sessions
from research_model import ResearchModel, add_background

CADENCE, TARGET, THRESHOLD = 16, 'washing_machine', 10
V2 = dict(washer='v2', fridge='v2', microwave='v2', background='v2')
CANDIDATES = [('always_off', 30), ('decision_tree', 5), ('decision_tree', 30),
              ('random_forest', 5), ('random_forest', 30)]
LABELLED = ('lamp', 'refrigerator', 'microwave', 'washing_machine')


def homes(seed, count, hours, first_start):
    """Simulate at 1 s, keep every 16th reading, then add the trailing background."""
    return [add_background(s[::CADENCE]) for s in realistic_sessions(
        seed, count, hours * 3600, washer_first_start=first_start, **V2)]


def pooled(reports, sessions):
    """Sum counts and energy over homes; add recall by stage and kettle-confusion share."""
    total = {'tp': 0, 'fp': 0, 'fn': 0, 'tn': 0}
    true_kwh = estimated_kwh = abs_error = 0.0
    by_stage, fp_big = {}, 0
    for report, rows in zip(reports, sessions):
        device = report['devices'][TARGET]
        for key in total:
            total[key] += device['confusion'][key]
        true_kwh += device['true_kwh'] or 0
        estimated_kwh += device['estimated_kwh'] or 0
        abs_error += device['mae_watts'] * device['samples']
        by_time = {row['timestamp']: row for row in rows}
        for point in report['points']:
            prediction = point['predictions'].get(TARGET)
            if not prediction:
                continue
            row = by_time[point['timestamp']]
            actual = row[TARGET] >= THRESHOLD
            if actual:
                hit = by_stage.setdefault(row['washing_machine_stage'], [0, 0])
                hit[0] += prediction['raw_on']
                hit[1] += 1
            elif prediction['raw_on']:
                fp_big += row['total_watts'] - sum(row[k] for k in LABELLED) >= 1000
    tp, fp, fn, tn = (total[k] for k in ('tp', 'fp', 'fn', 'tn'))
    samples = tp + fp + fn + tn
    return {'confusion': total, 'samples': samples, 'positive_samples': tp + fn,
            'f1': 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0,
            'precision': tp / (tp + fp) if tp + fp else None, 'recall': tp / (tp + fn) if tp + fn else None,
            'accuracy': (tp + tn) / samples, 'mae_watts': abs_error / samples,
            'true_kwh': true_kwh, 'estimated_kwh': estimated_kwh,
            'recall_by_stage': {stage: {'found': h, 'on_windows': n, 'recall': h / n} for stage, (h, n) in sorted(by_stage.items())},
            'false_positives_during_unmetered_1kw': {'count': fp_big, 'share': fp_big / fp if fp else None}}


def run(output, summary_path, train_count=20, eval_count=20, hours=36, first_start=(3600, 86400)):
    summary_path = Path(summary_path)
    if summary_path.exists():
        raise ValueError('Washer experiment v1 already run; keep its result instead of re-running')
    train = homes(42, train_count, hours, first_start)
    evaluation = homes(70042, eval_count, hours, first_start)
    result = {'protocol': 'washer-experiment-v1', 'cadence_seconds': CADENCE, 'target': TARGET,
              'train_homes': train_count, 'eval_homes': eval_count, 'hours_per_home': hours,
              'washer_first_start_seconds': list(first_start), 'candidates': {}}
    for algorithm, window in CANDIDATES:
        model = ResearchModel(train, window=window, mode='relative', algorithm=algorithm, cadence=CADENCE,
                              target=TARGET, profile='realistic v2 simulator (all components)')
        reports = [evaluate_model(model, rows, cadence=CADENCE, min_history=30, provenance={
            'name': f'Washer v1 / {algorithm} w{window} / sim home {index + 1}', 'protocol': 'washer-experiment-v1',
            'evaluation_role': 'synthetic_evaluation'}) for index, rows in enumerate(evaluation)]
        stamps = [[p['timestamp'] for p in r['points'] if p['predictions']] for r in reports]
        name = f'{algorithm}_w{window}'
        result['candidates'][name] = {'model_version': model.metrics['version'],
                                      'train_windows': model.metrics['train_samples'],
                                      'train_support': model.metrics['train_class_support'][TARGET],
                                      'scored_windows_per_home': [len(s) for s in stamps],
                                      **pooled(reports, evaluation)}
        result['candidates'][name]['stamps'] = stamps  # Checked below, removed before saving.
        save_experiment(reports[0], output)  # Home 1 only, for the dashboard charts.
    all_stamps = [c.pop('stamps') for c in result['candidates'].values()]
    if any(s != all_stamps[0] for s in all_stamps[1:]):
        raise ValueError('Candidates must score identical windows')
    f1 = {k: v['f1'] for k, v in result['candidates'].items()}
    mae = {k: v['mae_watts'] for k, v in result['candidates'].items()}
    helps = all(f1[f'{a}_w30'] - f1[f'{a}_w5'] >= .05 and mae[f'{a}_w30'] <= mae[f'{a}_w5']
                for a in ('decision_tree', 'random_forest'))
    result['longer_window_helps'] = helps
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('data/experiments'))
    parser.add_argument('--summary', type=Path, default=Path('data/washer-experiment/v1.json'))
    args = parser.parse_args()
    result = run(args.output, args.summary)
    for name, c in result['candidates'].items():
        print(f"{name:18} F1 {c['f1']:.3f}  P {c['precision'] or 0:.3f}  R {c['recall'] or 0:.3f}  "
              f"acc {c['accuracy']:.3f}  MAE {c['mae_watts']:.1f} W  kWh {c['estimated_kwh']:.2f}/{c['true_kwh']:.2f}  "
              f"FP@kettle {c['false_positives_during_unmetered_1kw']['share']}")
        print('   recall by stage:', {s: round(v['recall'], 2) for s, v in c['recall_by_stage'].items()})
    print('longer window helps:', result['longer_window_helps'])
