"""Stand-in for the future ESP32: send live readings to Current over HTTP (ADR-004).

It behaves like the planned device: it stamps each reading with the current UTC
time (a real ESP32 gets this from NTP), buffers readings, sends them in batches,
and resends the same batch after a failure. The server skips anything already
stored, so retries never duplicate data. Nothing here measures real electricity.

    python sensor_client.py --start                        # simulated home, this computer
    python sensor_client.py --url http://192.168.1.20:8000  # from another device on the LAN
"""
import argparse
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from itertools import cycle
from pathlib import Path

MAX_BUFFER = 120  # Same as the server's batch limit.


def simulated_watts(seed=42):
    from realistic import RealisticHome
    home = RealisticHome(seed, washer='v2', fridge='v2', microwave='v2', background='v2')
    while True:
        yield home.sample()['total_watts']


def csv_watts(path):
    from sources import parse_csv
    rows = parse_csv(Path(path).read_text(encoding='utf-8-sig'))
    return cycle(row['total_watts'] for row in rows)  # Watts only; timestamps are re-stamped live.


def http_post(url, body, token, timeout=5):
    request = urllib.request.Request(url, data=json.dumps(body).encode(), method='POST',
                                     headers={'Content-Type': 'application/json',
                                              **({'Authorization': f'Bearer {token}'} if token else {})})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read())


def send(buffer, post, url, token, sleep, attempts=3):
    """Send the whole buffer as one batch, retrying with backoff. Returns the reply or None."""
    for attempt in range(attempts):
        try:
            return post(f'{url}/api/sensor/readings', {'readings': buffer}, token)
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403, 409, 413, 422):  # Retrying cannot fix these; report and stop.
                raise SystemExit(f'Server refused the batch ({exc.code}): {exc.read().decode(errors="replace")}')
            error = exc
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            error = exc
        if attempt < attempts - 1:
            print(f'Send failed ({error}); retrying in {2 ** attempt} s')
            sleep(2 ** attempt)
    print(f'Send failed ({error}); keeping {len(buffer)} readings buffered for the next attempt')
    return None


def run(watts, url, token, count, interval, batch, post=http_post, sleep=time.sleep, now=None):
    """Sample `count` readings every `interval` s and send them in batches of `batch`."""
    now = now or (lambda: datetime.now(timezone.utc))
    buffer, sent = [], 0
    for index in range(count):
        buffer.append({'timestamp': now().isoformat(), 'total_watts': round(next(watts), 2)})
        if len(buffer) > MAX_BUFFER:
            buffer.pop(0)  # ponytail: drops the oldest reading on long outages; add flash storage on the device if that matters.
            print('Buffer full: oldest reading dropped')
        if len(buffer) >= batch or index == count - 1:
            reply = send(buffer, post, url, token, sleep)
            if reply is not None:
                sent += reply['accepted']
                print(f"Sent {len(buffer)}: accepted {reply['accepted']}, already stored {reply['duplicates']}")
                buffer = []
        if index < count - 1:
            sleep(interval)
    return sent


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--url', default='http://127.0.0.1:8000')
    parser.add_argument('--token', default=os.environ.get('CURRENT_SENSOR_TOKEN'), help='Defaults to CURRENT_SENSOR_TOKEN')
    parser.add_argument('--csv', help='Replay watts from this CSV instead of the simulated home')
    parser.add_argument('--count', type=int, default=120, help='Readings to send')
    parser.add_argument('--interval', type=float, default=1.0, help='Seconds between readings')
    parser.add_argument('--batch', type=int, default=5, help='Readings per request (1-120)')
    parser.add_argument('--start', action='store_true', help='First switch the dashboard to sensor mode (this computer only)')
    args = parser.parse_args()
    if not 1 <= args.batch <= MAX_BUFFER:
        parser.error('--batch must be 1-120')
    if args.start:
        http_post(f'{args.url}/api/source', {'source': 'sensor', 'cadence': args.interval}, None)
    source = csv_watts(args.csv) if args.csv else simulated_watts()
    total = run(source, args.url.rstrip('/'), args.token, args.count, args.interval, args.batch)
    print(f'Done: {total} readings accepted.')
