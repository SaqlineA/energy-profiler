"""Per-appliance forests, causal windows, fixed evaluation, saved provenance.

Only load trusted local joblib files, NEVER uploaded model files.
"""
import hashlib
import json
import random
from datetime import datetime, timezone, timedelta
from pathlib import Path

import joblib
import numpy as np
import sklearn
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support

from features import WINDOW, FEATURE_NAMES, window_features
from sources import DEVICE_IDS, valid_interval, regular_interval

APPLIANCES = (
    {"id": "lamp", "name": "Lamp", "watts": 10, "bit": 1, "threshold": 5},
    {"id": "refrigerator", "name": "Refrigerator", "watts": 150, "bit": 2, "threshold": 20},
    {"id": "microwave", "name": "Microwave", "watts": 1200, "bit": 4, "threshold": 100},
)
SCHEMA = 2
TEST_SEED = 10042


def synthetic_households(seed, count):
    rng = random.Random(seed)
    result = []
    for household in range(count):
        powers = [d["watts"] * rng.uniform(.97, 1.03) for d in APPLIANCES]
        rows = []
        start = datetime(2020, 1, 1, tzinfo=timezone.utc) + timedelta(days=household)
        mask = rng.randrange(8)
        for second in range(100):
            if second % 10 == 0:
                mask = rng.randrange(8)
            watts = {d["id"]: round(max(0, p + rng.uniform(-2, 2)), 2)
                     if mask & d["bit"] else 0.0 for d, p in zip(APPLIANCES, powers)}
            rows.append({"timestamp": (start + timedelta(seconds=second)).isoformat(),
                         "total_watts": round(sum(watts.values()), 2), **watts})
        result.append(rows)
    return result


def dataset(sessions, cadence):
    x, y, power, weights = [], [], [], []
    for rows in sessions:
        window, previous, previous_scored = [], None, None
        for row in rows:
            dt = valid_interval(row, previous, cadence)
            if not dt or not regular_interval(row, previous, cadence):
                window = []
            if row["total_watts"] is not None:
                window = (window + [row["total_watts"]])[-WINDOW:]
            labeled = all(row.get(key) is not None for key in DEVICE_IDS)
            if len(window) == WINDOW and labeled:
                x.append(window_features(window))
                p = [row[key] for key in DEVICE_IDS]
                power.append(p)
                y.append([int(value >= d["threshold"]) for value, d in zip(p, APPLIANCES)])
                weights.append(0.0)
                # Trapezoidal energy over adjacent scored valid intervals only.
                if previous_scored is previous and dt:
                    weights[-1] += dt / 2
                    weights[-2] += dt / 2
                previous_scored = row
            else:
                previous_scored = None
            previous = row
    if not x:
        raise ValueError("No fully labeled, gap-free five-reading windows available")
    return np.asarray(x), np.asarray(y), np.asarray(power), np.asarray(weights)


def masks(labels):
    return np.asarray(labels, dtype=int) @ np.array([d["bit"] for d in APPLIANCES])


class ApplianceModel:
    def __init__(self, seed=42, train_sessions=None, test_sessions=None, cadence=1.0, provenance=None):
        synthetic = train_sessions is None
        train_sessions = synthetic_households(seed, 60) if synthetic else train_sessions
        test_sessions = synthetic_households(TEST_SEED, 20) if synthetic else test_sessions
        train_x, train_y, train_p, _ = dataset(train_sessions, cadence)
        test_x, test_y, test_p, weights = dataset(test_sessions, cadence)
        self.classifier = RandomForestClassifier(n_estimators=60, max_depth=12,
                                                 min_samples_leaf=3, random_state=seed)
        self.regressor = RandomForestRegressor(n_estimators=60, max_depth=12,
                                               min_samples_leaf=3, random_state=seed)
        self.classifier.fit(train_x, train_y)
        self.regressor.fit(train_x, train_p)
        self.power_bounds = (float(train_x[:, 0].min()), float(train_x[:, 0].max()))
        predicted = self.classifier.predict(test_x)
        estimated = self.regressor.predict(test_x)
        baseline = RandomForestClassifier(n_estimators=60, max_depth=10,
                                           min_samples_leaf=6, random_state=seed)
        baseline.fit(train_x[:, :1], masks(train_y))
        baseline_pred = baseline.predict(test_x[:, :1])
        precision, recall, f1, support = precision_recall_fscore_support(
            test_y, predicted, average=None, zero_division=0)
        per_device = {}
        for i, d in enumerate(APPLIANCES):
            true_kwh = float(test_p[:, i] @ weights / 3_600_000)
            estimated_kwh = float(estimated[:, i] @ weights / 3_600_000)
            per_device[d["id"]] = {
                "precision": float(precision[i]), "recall": float(recall[i]), "f1": float(f1[i]),
                "support": int(support[i]), "mae_watts": float(np.abs(estimated[:, i] - test_p[:, i]).mean()),
                "true_kwh": true_kwh, "estimated_kwh": estimated_kwh,
                "absolute_energy_error_kwh": abs(true_kwh - estimated_kwh),
            }
        self.metrics = {
            "schema": SCHEMA, "algorithm": "Per-appliance state and power random forests",
            "feature": ", ".join(FEATURE_NAMES), "window": WINDOW, "cadence_seconds": cadence,
            "prediction_alignment": "Latest timestamp; trailing window; no future readings",
            "train_samples": len(train_y), "test_samples": len(test_y),
            "train_households": len(train_sessions), "test_households": len(test_sessions),
            "accuracy": float(accuracy_score(masks(test_y), masks(predicted))),
            "per_appliance": {d["id"]: float(accuracy_score(test_y[:, i], predicted[:, i]))
                              for i, d in enumerate(APPLIANCES)},
            "device_metrics": per_device,
            "baselines": {"single_watt_joint_accuracy": float(accuracy_score(masks(test_y), baseline_pred)),
                          "always_off_accuracy": float(np.mean(masks(test_y) == 0))},
            "confusion_matrix": confusion_matrix(masks(test_y), masks(predicted), labels=list(range(8))).tolist(),
            "trained_at": datetime.now(timezone.utc).isoformat(), "seed": seed,
            "test_seed": TEST_SEED if synthetic else None,
            "training_source": "synthetic" if synthetic else "recorded CSV (origin not independently verified)",
            "provenance": provenance or {"generator": "sustained-households-v2", "split": "separate households"},
            "thresholds_watts": {d["id"]: d["threshold"] for d in APPLIANCES},
            "sklearn_version": sklearn.__version__, "energy_coverage_seconds": float(weights.sum()),
            "limitation": "Synthetic results are not real-household validation. Scores are uncalibrated. "
                          "Uncertainty and unexplained power are heuristics, not reliable unknown-appliance detection. "
                          "Metrics score raw predictions before abstention; absent positive labels make recall uninformative.",
        }
        self.metrics["version"] = hashlib.sha256(json.dumps(self.metrics, sort_keys=True).encode()).hexdigest()[:16]

    def infer(self, values):
        x = [window_features(values)]
        probabilities = self.classifier.predict_proba(x)
        estimated = self.regressor.predict(x)[0]
        devices, mask, confidence = {}, 0, 1.0
        outside = not self.power_bounds[0] - 5 <= values[-1] <= self.power_bounds[1] * 1.10 + 5
        residual = float(values[-1] - sum(estimated))
        unexplained = abs(residual) > max(30, values[-1] * .20)
        for i, d in enumerate(APPLIANCES):
            classes = list(self.classifier.classes_[i])
            p = float(probabilities[i][0][classes.index(1)]) if 1 in classes else 0.0
            on = None if outside or unexplained or .35 < p < .65 else p >= .5
            devices[d["id"]] = {"on": on, "probability_on": round(p, 4),
                                    "estimated_watts": round(float(max(0, estimated[i])), 2)}
            mask += d["bit"] if on else 0
            confidence = min(confidence, max(p, 1 - p))
        uncertain = any(d["on"] is None for d in devices.values())
        return {"predicted_mask": None if uncertain else mask, "confidence": round(confidence, 4),
                "predictions": devices, "unexplained_watts": round(residual, 2),
                "prediction_quality": "uncertain" if uncertain else "estimated"}

    def predict(self, total_watts):
        """Legacy helper. The live pipeline instead supplies a genuine window."""
        result = self.infer([total_watts] * WINDOW)
        return result["predicted_mask"], result["confidence"]

    def save(self, directory):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        name = self.metrics["version"] + ".joblib"
        joblib.dump(self, directory / name)
        digest = hashlib.sha256((directory / name).read_bytes()).hexdigest()
        manifest = {"artifact": name, "sha256": digest, **self.metrics}
        temporary = directory / "current.tmp"
        temporary.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        temporary.replace(directory / "current.json")

    @classmethod
    def load(cls, directory):
        directory = Path(directory)
        manifest = json.loads((directory / "current.json").read_text(encoding="utf-8"))
        if manifest["schema"] != SCHEMA or manifest["sklearn_version"] != sklearn.__version__:
            raise ValueError("Saved model is incompatible; retrain with this environment")
        if (manifest['window'] != WINDOW or manifest['feature'] != ', '.join(FEATURE_NAMES)
                or manifest['thresholds_watts'] != {d['id']: d['threshold'] for d in APPLIANCES}):
            raise ValueError('Saved model feature/threshold contract changed; retrain before loading')
        name = manifest["artifact"]
        if Path(name).name != name:
            raise ValueError("Invalid artifact name")
        artifact = directory / name
        if hashlib.sha256(artifact.read_bytes()).hexdigest() != manifest["sha256"]:
            raise ValueError("Saved model checksum mismatch")
        return joblib.load(artifact)  # Our trusted local directory only.


def train_recorded(rows, cadence, seed=42, provenance=None):
    """Split raw time BEFORE windows: none straddles the held-out boundary."""
    split = int(len(rows) * .7)
    train, test = rows[:split], rows[split:]
    if min(len(train), len(test)) < WINDOW * 2:
        raise ValueError("Recorded training needs at least 34 rows; more is strongly recommended")
    metadata = {**(provenance or {}), "split": "chronological 70/30; raw rows split before windows",
                "split_timestamp": test[0]["timestamp"], "train_rows": len(train), "test_rows": len(test)}
    return ApplianceModel(seed, [train], [test], cadence, metadata)
