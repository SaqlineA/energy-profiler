"""Experimental models are separate from the live three-appliance baseline."""
import hashlib
import json
import math

import numpy as np
import sklearn
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor

from ml import APPLIANCES
from realistic import WASHER
from sources import regular_interval, valid_interval


def make_features(values, mode='summary'):
    v = np.asarray(values, dtype=float)
    if len(v) < 2 or not np.isfinite(v).all():
        raise ValueError('Features require at least two finite values')
    if mode == 'watts':
        return [float(v[-1])]
    summary = [float(v[-1]), float(v[-1] - v[-2]), float(v.mean()),
               float(v.std()), float(v.min()), float(v.max())]
    if mode == 'summary':
        return summary
    if mode == 'history':
        return summary + v.tolist()
    raise ValueError('Unknown feature mode')


class ResearchModel:
    def __init__(self, sessions, window=5, mode='summary', algorithm='random_forest',
                 washer=False, seed=42, profile='realistic', cadence=1):
        if not math.isfinite(cadence) or not 0 < cadence <= 3600:
            raise ValueError('Cadence must be finite, positive and at most 3600 seconds')
        if window not in (5, 10, 20, 30) or mode not in ('watts', 'summary', 'history'):
            raise ValueError('Unsupported feature configuration')
        self.mode = mode
        self.devices = (*APPLIANCES, WASHER) if washer else APPLIANCES
        x, y, power = [], [], []
        for session in sessions:
            history, previous = [], None
            for row in session:
                if not valid_interval(row, previous, cadence) or not regular_interval(row, previous, cadence):
                    history = []
                if row['total_watts'] is not None:
                    history = (history + [row['total_watts']])[-window:]
                if len(history) == window and all(row.get(d['id']) is not None for d in self.devices):
                    x.append(self.features(history))
                    power.append([row[d['id']] for d in self.devices])
                    y.append([int(row[d['id']] >= d['threshold']) for d in self.devices])
                previous = row
        if not x:
            raise ValueError('No complete labeled training windows')
        if algorithm == 'random_forest':
            self.classifier = RandomForestClassifier(n_estimators=40, max_depth=12, min_samples_leaf=3, random_state=seed)
            self.regressor = RandomForestRegressor(n_estimators=40, max_depth=12, min_samples_leaf=3, random_state=seed)
        elif algorithm == 'decision_tree':
            self.classifier = DecisionTreeClassifier(max_depth=8, min_samples_leaf=5, random_state=seed)
            self.regressor = DecisionTreeRegressor(max_depth=8, min_samples_leaf=5, random_state=seed)
        elif algorithm == 'always_off':
            self.classifier = DummyClassifier(strategy='constant', constant=[0] * len(self.devices))
            self.regressor = DummyRegressor(strategy='constant', constant=[0] * len(self.devices))
        else:
            raise ValueError('Unknown algorithm')
        # This comparator is a fixed rule, even if a device never turns off in training.
        self.classifier.fit(x, np.zeros_like(y) if algorithm == 'always_off' else y)
        self.regressor.fit(x, power)
        self.power_bounds = (min(v[0] for v in x), max(v[0] for v in x))
        self.metrics = {'algorithm': algorithm, 'window': window, 'feature': mode,
                        'cadence_seconds': cadence, 'seed': seed, 'train_samples': len(x),
                        'sklearn_version': sklearn.__version__,
                        'training_source': profile, 'experimental': True,
                        'thresholds_watts': {d['id']: d['threshold'] for d in self.devices},
                        'provenance': {'split': 'separate generated sessions; evaluation supplied separately',
                                       'train_sessions': len(sessions),
                                       'training_sha256': hashlib.sha256(json.dumps(sessions, sort_keys=True).encode()).hexdigest()}}
        self.metrics['version'] = hashlib.sha256(json.dumps(self.metrics, sort_keys=True).encode()).hexdigest()[:16]

    def features(self, values):
        return make_features(values, self.mode)
