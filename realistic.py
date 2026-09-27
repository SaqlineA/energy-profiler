"""Seeded learning simulator, not a calibrated electrical appliance model.

Each sample represents one second. The v1 washer's stages are deliberately
compressed for experiments; washer v2 follows real REFIT cycles
(docs/washing-machine-design.md). Background and aggregate sensor noise are never
appliance truth.
"""
import random
from datetime import datetime, timedelta, timezone

WASHER = {'id': 'washing_machine', 'name': 'Washing machine', 'watts': 1800,
          'bit': 8, 'threshold': 10}
# The only allowed washer v2 order; off is left only when a cycle is scheduled.
WASHER_V2_NEXT = {'off': 'fill', 'fill': 'heat', 'heat': 'wash', 'wash': 'pause',
                  'pause': 'drain', 'drain': 'spin', 'spin': 'off'}


class WasherV2:
    """Multi-stage washer. Its own seeded RNG keeps every other simulated load unchanged."""
    DURATIONS = {'fill': (120, 300), 'heat': (480, 1080), 'wash': (900, 3600),
                 'pause': (60, 300), 'drain': (60, 180), 'spin': (180, 600)}
    NOISE = {'fill': .05, 'heat': .02, 'wash': .05, 'drain': .05, 'spin': .05}

    def __init__(self, seed):
        self.rng = random.Random(f'washer-v2-{seed}')
        self.heater = self.rng.uniform(2000, 2500)
        # Demo convenience: the first cycle starts 2-10 min into a session.
        self.stage, self.remaining, self.cycle_seconds = 'off', self.rng.randint(120, 600), None

    def enter(self, stage):
        rng = self.rng
        self.stage, self.age, self.burst_left, self.burst_on = stage, 0, 0, False
        if stage == 'off':
            self.remaining, self.cycle_seconds = rng.randint(36 * 3600, 120 * 3600), None
            return
        if stage == 'fill':
            self.cycle_seconds = 0
        self.length = self.remaining = rng.randint(*self.DURATIONS[stage])
        if stage == 'drain':
            self.pump = rng.uniform(30, 60)
        if stage == 'spin':
            self.peak = rng.uniform(300, 550)

    def drum(self, on_s, off_s, on_w, off_w):
        """Alternate motor bursts and rests, e.g. drum reversals during washing."""
        if self.burst_left <= 0:
            self.burst_on = not self.burst_on
            self.burst_left = self.rng.randint(*(on_s if self.burst_on else off_s))
            self.burst_power = self.rng.uniform(*(on_w if self.burst_on else off_w))
        self.burst_left -= 1
        return self.burst_power

    def sample(self):
        if self.remaining <= 0:
            self.enter(WASHER_V2_NEXT[self.stage])
        stage = self.stage
        power = {'off': 0.0, 'pause': 2.0, 'heat': self.heater}.get(stage)
        if stage == 'fill':
            power = self.drum((5, 10), (20, 40), (40, 90), (8, 12))
        elif stage == 'wash':
            power = self.drum((8, 15), (3, 8), (40, 200), (4, 6))  # Revised once from 100-250 W; see design doc.
        elif stage == 'drain':
            power = self.pump
        elif stage == 'spin':
            power = 150 + (self.peak - 150) * min(1, self.age / (self.length / 2))
        noise = self.NOISE.get(stage, 0)
        if noise:  # Bounded noise keeps every stage inside its documented range.
            power *= self.rng.uniform(1 - noise, 1 + noise)
        self.remaining -= 1
        if self.stage != 'off':
            self.age += 1
            self.cycle_seconds += 1
        return round(power, 2)


class BackgroundV2:
    """Baseload plus random unmetered loads (docs/simulator-background-v2.md). Own seeded RNG."""

    def __init__(self, seed):
        rng = self.rng = random.Random(f'background-v2-{seed}')
        self.base = self.level = rng.uniform(60, 180)
        # One documented revision (was 50-100/day, 1-30 min; 15-30/day, 1-10 min): see design doc.
        self.medium_rate = rng.uniform(60, 120) / 86400  # Lights, TV, computers.
        self.large_rate = rng.uniform(20, 35) / 86400  # Kettle, oven, toaster, iron.
        self.loads = []  # [watts, seconds left]

    def sample(self):
        rng = self.rng
        self.level = min(self.base * 1.2, max(self.base * .8, self.level + rng.uniform(-.5, .5)))
        if rng.random() < self.medium_rate:
            self.loads.append([rng.uniform(100, 600), int(60 * 10 ** rng.random())])  # Log-uniform 1-10 min.
        if rng.random() < self.large_rate:
            self.loads.append([rng.uniform(1000, 3000), int(60 * 5 ** rng.random())])  # Log-uniform 1-5 min.
        watts = self.level + sum(w for w, _ in self.loads)
        for load in self.loads:
            load[1] -= 1
        self.loads = [load for load in self.loads if load[1] > 0]
        return watts


class RealisticHome:
    def __init__(self, seed=42, washer=False, start=None, fridge='v1', microwave='v1', background='v1'):
        if fridge not in ('v1', 'v2'):
            raise ValueError('Unknown fridge model')
        if background not in ('v1', 'v2'):
            raise ValueError('Unknown background model')
        if microwave not in ('v1', 'v2'):
            raise ValueError('Unknown microwave model')
        if washer not in (False, True, 'v1', 'v2'):
            raise ValueError('Unknown washer model')
        self.rng = random.Random(seed)
        self.second = 0
        self.start = start or datetime(2020, 1, 1, tzinfo=timezone.utc)
        self.washer = 'v1' if washer in (True, 'v1') else washer  # True keeps meaning v1.
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
        self.fridge = fridge
        self.fridge_age = 0
        if fridge == 'v2':
            # Drawn after every v1 value so v1 seeds reproduce exactly.
            # Targets from REFIT Houses 1-4: docs/simulator-fridge-v2.md.
            self.nominal['refrigerator'] = self.rng.uniform(80, 90)
            self.on['refrigerator'] = self.rng.random() < .25
            self.fridge_remaining = self.rng.randint(1, self.fridge_cycle())
        self.washer_v2 = WasherV2(seed) if washer == 'v2' else None
        self.background_v2 = BackgroundV2(seed) if background == 'v2' else None
        self.microwave = microwave
        if microwave == 'v2':
            # Own RNG: REFIT Houses 2-4 use a microwave 1-6 times a day (docs/simulator-microwave-v2.md).
            self.microwave_rng = random.Random(f'microwave-v2-{seed}')
            self.nominal['microwave'] = self.microwave_rng.uniform(1000, 1400)
            self.microwave_rate = self.microwave_rng.uniform(1, 6) / 86400

    def sample(self, manual=None):
        rng = self.rng
        if manual is None:
            if rng.random() < .004:
                self.on['lamp'] = not self.on['lamp']
            self.fridge_remaining -= 1
            if self.fridge_remaining <= 0:
                self.on['refrigerator'] = not self.on['refrigerator']
                self.fridge_remaining = self.fridge_cycle() if self.fridge == 'v2' else rng.randint(90, 360)
            if self.microwave == 'v2':
                if self.microwave_remaining <= 0 and self.microwave_rng.random() < self.microwave_rate:
                    self.microwave_remaining = int(20 * 15 ** self.microwave_rng.random())  # Log-uniform 20-300 s.
            elif self.microwave_remaining <= 0 and rng.random() < .008:
                self.microwave_remaining = rng.randint(15, 90)
            self.on['microwave'] = self.microwave_remaining > 0
            self.microwave_remaining -= 1
        else:
            self.on.update(manual)
        watts = {}
        for key, nominal in self.nominal.items():
            value = max(0, rng.gauss(nominal, nominal * .035)) if self.on[key] else 0
            if key == 'refrigerator' and self.fridge == 'v2':
                if self.on[key] and not self.previous_on[key]:
                    self.fridge_age, self.startup = 0, rng.uniform(1.1, 1.4)
                if self.on[key] and self.fridge_age < 10:  # Mild peak over the first 10 s.
                    value *= self.startup
                self.fridge_age += 1
            elif key == 'refrigerator' and self.on[key] and not self.previous_on[key]:
                value *= rng.uniform(1.8, 2.8)
            watts[key] = round(value, 2)
        if self.washer == 'v1':
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
        elif self.washer_v2:
            watts['washing_machine'] = self.washer_v2.sample()
            self.wash_stage = self.washer_v2.stage
        self.background = max(5, min(200, self.background + rng.uniform(-1, 1)))
        unknown = 80 if self.second % 240 < 40 else 0
        # v2 keeps the v1 draw above so every labelled appliance matches v1 exactly.
        other = self.background_v2.sample() if self.background_v2 else self.background + unknown
        total = round(max(0, sum(watts.values()) + other + rng.gauss(0, 2)), 2)
        row = {'timestamp': (self.start + timedelta(seconds=self.second)).isoformat(),
               'total_watts': total, **watts}
        if self.washer_v2:
            row['washing_machine_stage'] = self.wash_stage
        self.previous_on = dict(self.on)
        self.second += 1
        return row

    def fridge_cycle(self):
        # 25-30 min on, 1-2 h off (seconds).
        return self.rng.randint(1500, 1800) if self.on['refrigerator'] else self.rng.randint(3600, 7200)


def realistic_sessions(seed, count, seconds=600, washer=False, fridge='v1', microwave='v1', background='v1'):
    sessions = []
    for index in range(count):
        home = RealisticHome(seed + index * 997, washer,
            datetime(2020, 1, 1, tzinfo=timezone.utc) + timedelta(days=index), fridge, microwave, background)
        sessions.append([home.sample() for _ in range(seconds)])
    return sessions
