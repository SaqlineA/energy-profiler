# Sending sensor readings to Current (Step 16)

This is the software side of connecting a future ESP32 (or any device) to
Current. It is **ready and tested without hardware**. No physical sensor,
calibration or mains wiring has been validated; that work stays with the builder
(Steps 17–19). The design and its security trade-offs are in
[ADR-004](decisions/0004-lan-sensor-ingest.md).

## 1. Try it on this computer (no hardware)

`sensor_client.py` stands in for the ESP32. It sends a simulated home's power
(or a CSV's watts) over HTTP, stamped with the current time, in batches.

```powershell
.\.venv\Scripts\python.exe app.py
# In a second terminal:
.\.venv\Scripts\python.exe sensor_client.py --start --count 120 --interval 1 --batch 5
```

`--start` switches the dashboard to sensor mode first; you can also click
**Data source & import → Wait for local sensor**. The dashboard's source line
shows *"Sensor: N readings received · last X s ago"*. It adds *"no recent
readings"* when nothing has arrived for three sample intervals.

## 2. Accept readings from a device on your home Wi-Fi

LAN mode is **off by default** and only starts when both settings exist:

```powershell
ipconfig                                   # find this PC's IPv4 address, e.g. 192.168.1.20
$env:CURRENT_LAN_HOST = "192.168.1.20"
$env:CURRENT_SENSOR_TOKEN = .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(32))"
.\.venv\Scripts\python.exe app.py --lan
```

- **Windows Firewall** asks whether to allow Python on networks. Allow
  **Private networks** only.
- **The dashboard stays at `http://127.0.0.1:8000`** on this computer. Other
  devices get **403** for everything except the two sensor routes below.
- **Check the address.** LAN mode refuses to start if the address is public,
  loopback or not an IPv4 address, or if the token is shorter than 24 characters.
- **Keep the token secret.** Put it in the device's configuration, never in Git.
  It travels over plain HTTP, so use this only on a trusted home network, never
  the internet.

Test from another computer on the same Wi-Fi:

```powershell
python sensor_client.py --url http://192.168.1.20:8000 --token <token> --count 30
```

## 3. The device contract

**Send readings:** `POST http://<LAN host>:8000/api/sensor/readings`, with
`Authorization: Bearer <token>` and `Content-Type: application/json`.

```json
{"readings": [
  {"timestamp": "2026-09-28T12:00:00Z", "total_watts": 231.4},
  {"timestamp": "2026-09-28T12:00:01Z", "total_watts": null}
]}
```

- **1–120 readings per batch,** at most 16 KB. A single reading object without
  `readings` also works (8 KB limit).
- **`timestamp`** must include a timezone. Sync the device clock with NTP, and
  never send local time without an offset.
- **Timestamps must strictly increase** within a batch.
- **`total_watts`** is active power in watts, 0–1,000,000, or `null` for a
  missed sample. Blank means unknown, not zero.
- **No other fields** are accepted yet. Voltage, current and power factor wait
  for the hardware choice.

**Reply (200):**

```json
{"session": "…", "accepted": 2, "duplicates": 0, "latest_timestamp": "2026-09-28T12:00:01+00:00"}
```

**Retrying is safe.** Readings at or before the last stored timestamp are
counted as `duplicates` and skipped. If a request times out, resend the same
batch. The stand-in client does this with 1 s and 2 s backoff, and keeps up
to 120 readings buffered during outages.

| Status | Meaning | Device should |
|---|---|---|
| 200 | Batch processed | Clear its buffer |
| 401 | Missing or wrong token | Stop and fix its configuration |
| 403 | Route not allowed from the network | Use `/api/sensor/…` only |
| 409 | No active sensor session, or the session changed | Wait; start sensor mode on the dashboard |
| 413 | Body too large | Send smaller batches |
| 422 | Invalid reading, or timestamps out of order in the batch | Fix the data; do not resend unchanged |
| 5xx / timeout | Server problem or Wi-Fi drop | Keep the buffer and retry with backoff |

**Check health:** `GET /api/sensor/status` with the same token returns:
- `active` and `running`;
- `cadence_seconds`;
- `accepted`, `duplicates` and `rejected` for this session;
- `last_timestamp` and `seconds_since_last`;
- `stale`.

## What this does not do yet

- There is no firmware, no electrical sensing, and no calibration against a
  reference meter (Steps 17–19).
- Sensor mode feeds only the aggregate. The live three-appliance model was
  trained on 1 s synthetic data, so its predictions from a real sensor are
  unvalidated.
- There is no TLS and no user login. The planned public read-only demo
  (PRODUCT.md) is separate work.
