"""Seeded learning simulator, not a calibrated electrical appliance model.

Each sample represents one second. Washer stages are deliberately compressed
for experiments. Background and aggregate sensor noise are never appliance truth.
"""
import random
from datetime import datetime, timedelta, timezone

WASHER = {'id': 'washing_machine', 'name': 'Washing machine', 'watts': 1800,
          'bit': 8, 'threshold': 10}


class RealisticHome:
    def __init__(self, seed=42, washer=False, start=None):
        self.rng = random.Random(seed)
        self.second = 0
        self.start = start or datetime(2020, 1, 1, tzinfo=timezone.utc)
        self.washer = washer
        self.nominal = {'lamp': self.rng.uniform(6, 30),
                        'refrigerator': self.rng.uniform(70, 220),
                        'microwave': self.rng.uniform(700, 1500)}
        self.on = {'lamp': True, 'refrigerator': True, 'microwave': False}
        self.previous_on = dict.fromkeys(self.on, False)
        self.fridge_remaining = self.rng.randint(60, 240)
        self.microwave_remaining = 0
        self.background = self.rng.uniform(20, 120)
        self.wash_start = self.rng.randint(10, 180)
        self.wash_stage = 'idle'

    def sample(self, manual=None):
        rng = self.rng
        if manual is None:
            if rng.random() < .004:
                self.on['lamp'] = not self.on['lamp']
            self.fridge_remaining -= 1
            if self.fridge_remaining <= 0:
                self.on['refrigerator'] = not self.on['refrigerator']
                self.fridge_remaining = rng.randint(90, 360)
            if self.microwave_remaining <= 0 and rng.random() < .008:
                self.microwave_remaining = rng.randint(15, 90)
            self.on['microwave'] = self.microwave_remaining > 0
            self.microwave_remaining -= 1
        else:
            self.on.update(manual)
        watts = {}
        for key, nominal in self.nominal.items():
            value = max(0, rng.gauss(nominal, nominal * .035)) if self.on[key] else 0
            if key == 'refrigerator' and self.on[key] and not self.previous_on[key]:
                value *= rng.uniform(1.8, 2.8)
            watts[key] = round(value, 2)
        if self.washer:
            age = self.second - self.wash_start
            stages = [(0, 'idle', 0), (20, 'fill', 8), (80, 'heat', 1800),
                      (170, 'wash', 100), (185, 'drain', 45), (230, 'spin', 450)]
            power, self.wash_stage = 0, 'idle'
            for end, name, stage_power in stages:
                if age < end:
                    power, self.wash_stage = stage_power, name
                    break
            if age >= 230:
                self.wash_start = self.second + rng.randint(120, 300)
            watts['washing_machine'] = round(max(0, rng.gauss(power, power * .08)), 2)
        self.background = max(5, min(200, self.background + rng.uniform(-1, 1)))
        unknown = 80 if self.second % 240 < 40 else 0
        total = round(max(0, sum(watts.values()) + self.background + unknown + rng.gauss(0, 2)), 2)
        row = {'timestamp': (self.start + timedelta(seconds=self.second)).isoformat(),
               'total_watts': total, **watts}
        self.previous_on = dict(self.on)
        self.second += 1
        return row


def realistic_sessions(seed, count, seconds=600, washer=False):
    sessions = []
    for index in range(count):
        home = RealisticHome(seed + index * 997, washer,
            datetime(2020, 1, 1, tzinfo=timezone.utc) + timedelta(days=index))
        sessions.append([home.sample() for _ in range(seconds)])
    return sessions
