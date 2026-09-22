"""Reproducible offline comparisons. Never writes data/models or promotes a model."""
import argparse
import hashlib
import json
from pathlib import Path

from experiments import evaluate_model, save_experiment
from ml import ApplianceModel, synthetic_households
from realistic import realistic_sessions
from research_model import ResearchModel
from sources import parse_csv


def run_comparisons(real_rows, output, original, source, seed=42):
    train = {'classic': synthetic_households(seed, 30),
             'realistic': realistic_sessions(seed, 10, 300)}
    held_out = [row for session in realistic_sessions(70042, 3, 300) for row in session]
    classic_test = [row for session in synthetic_households(10042, 9) for row in session]
    models = [('frozen-original', original)]
    for profile in ('classic', 'realistic'):
        for window in (5, 10, 20, 30):
            models.append((f'{profile}-rf-{window}-summary', ResearchModel(
                train[profile], window=window, seed=seed, profile=profile)))
    for mode, algorithm in [('watts', 'random_forest'), ('history', 'random_forest'),
                            ('summary', 'decision_tree'), ('summary', 'always_off')]:
        models.append((f'realistic-{algorithm}-5-{mode}', ResearchModel(
            train['realistic'], mode=mode, algorithm=algorithm, seed=seed)))
    references = []
    for name, model in models:
        for target, rows, policy, cadence in [('synthetic-classic', classic_test, 'strict', 1),
                 ('synthetic-realistic', held_out, 'strict', 1), ('REFIT', real_rows, 'sample_window', 8)]:
            report = evaluate_model(model, rows, cadence, policy, min_history=30,
                provenance={'name': f'{name} on {target}', 'target': target,
                            'origin': source if target == 'REFIT' else 'Synthetic held-out sessions',
                            'sha256': hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest(),
                            'comparison': 'Common 30-reading warmup; disjoint generated training/test seeds'})
            saved = save_experiment(report, output)
            references.append({'name': name, 'target': target, 'id': saved['id'], 'devices': saved['devices']})
            fridge = saved['devices']['refrigerator']
            print(f'{name} / {target}: n={fridge["samples"]}, F1={fridge["f1"]}, MAE={fridge["mae_watts"]}', flush=True)
    # Separate four-device experiment; it is not substituted into the live model.
    expanded = ResearchModel(realistic_sessions(seed, 10, 300, washer=True), washer=True)
    washer_test = [row for session in realistic_sessions(70042, 3, 300, washer=True) for row in session]
    saved = save_experiment(evaluate_model(expanded, washer_test, min_history=30,
        provenance={'name': 'Four-device model / held-out washer sessions', 'target': 'synthetic-washer',
                    'split': f'training seed {seed}; test seed 70042',
                    'sha256': hashlib.sha256(json.dumps(washer_test, sort_keys=True).encode()).hexdigest()}), output)
    references.append({'name': 'four-device', 'target': 'synthetic-washer', 'id': saved['id'], 'devices': saved['devices']})
    return references


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv', type=Path)
    parser.add_argument('--model-dir', type=Path, default=Path('data/models'))
    parser.add_argument('--output', type=Path, default=Path('data/experiments'))
    args = parser.parse_args()
    rows = parse_csv(args.csv.read_text(encoding='utf-8-sig'))
    run_comparisons(rows, args.output, ApplianceModel.load(args.model_dir), args.csv.name)
