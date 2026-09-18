"""Confirm each predicted switch over three readings to reduce alert flicker.

Raw model predictions remain untouched; only the event feed is filtered.
Confirmation delays alerts by two simulated seconds and can miss shorter events.
"""
from ml import APPLIANCES


class TransitionTracker:
    def __init__(self):
        self.stable = None
        self.pending = {}
        self.previous_watts = 0

    def update(self, reading):
        mask = reading['predicted_mask']
        if mask is None or reading.get('quality') in ('gap', 'missing'):
            self.stable = None
            self.pending.clear()
            self.previous_watts = reading['total_watts'] or 0
            return []
        events = []
        if self.stable is None:
            self.stable = mask
        for device in APPLIANCES:
            bit = device['bit']
            if bool(mask & bit) == bool(self.stable & bit):
                self.pending.pop(bit, None)
                continue
            count, delta = self.pending.get(bit, (0, round(reading['total_watts'] - self.previous_watts, 2)))
            count += 1
            if count >= 3:
                self.stable ^= bit
                self.pending.pop(bit, None)
                events.append({
                    'appliance': device['name'], 'is_on': bool(mask & bit),
                    'second': reading['second'], 'timestamp': reading['timestamp'],
                    'delta': delta,
                })
            else:
                self.pending[bit] = (count, delta)
        self.previous_watts = reading['total_watts']
        return events
