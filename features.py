"""Same causal features in training and inference; no labels or future samples."""
import numpy as np

WINDOW = 5
FEATURE_NAMES = ["watts", "delta_watts", "mean_watts", "std_watts", "min_watts", "max_watts"]


def window_features(values):
    values = np.asarray(values[-WINDOW:], dtype=float)
    if len(values) != WINDOW or not np.isfinite(values).all():
        raise ValueError(f"Need {WINDOW} consecutive finite aggregate readings")
    return [float(values[-1]), float(values[-1] - values[-2]), float(values.mean()),
            float(values.std()), float(values.min()), float(values.max())]
