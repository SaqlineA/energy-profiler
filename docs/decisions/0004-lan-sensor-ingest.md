# ADR-004: Opt-in LAN sensor ingest (Step 16)

Status: Accepted — implemented in software; no physical sensor has been connected.
Date: 2026-09-27

## Context

A future ESP32 on the home Wi-Fi cannot reach the loopback-only server
(`127.0.0.1`). The existing sensor endpoint accepts one reading per request,
has no authentication, and replies with the whole dashboard state. A
microcontroller on flaky Wi-Fi needs to buffer readings, retry safely, and get
a small reply. The app has no login and exposes write controls (source, upload,
retraining), so it must never be reachable from the network as a whole.
PRODUCT.md plans a public read-only demo later; this decision does not create
one.

## Decision

- **LAN mode is off by default.** `python app.py --lan` binds to all interfaces
  only when two things are set:
  - `CURRENT_SENSOR_TOKEN`, at least 24 characters;
  - `CURRENT_LAN_HOST`, this computer's **private** IPv4 address.

  Otherwise it refuses to start. Public, loopback and malformed addresses are
  rejected. The LAN address is added to the trusted-host list explicitly,
  never as a wildcard.
- **Network clients reach two routes only:** `POST /api/sensor/readings` and
  `GET /api/sensor/status`. Everything else, including the dashboard, returns
  403 to any client that is not loopback. Loopback use is unchanged.
- **Token:** when a token is configured, every sensor request (read or write)
  needs `Authorization: Bearer <token>`, compared in constant time. Without a
  token (local learning mode) the sensor routes behave as before.
- **Batches:** `{"readings": [...]}` carries 1–120 readings, up to 16 KB.
  - The batch is validated as a whole, and timestamps must strictly increase
    within it.
  - Readings at or before the last accepted timestamp are counted as
    `duplicates` and skipped, so resending a batch after a timeout is safe.
  - The reply is small: accepted, duplicates, latest timestamp and session.
- **The single-reading form is kept unchanged,** including its full-state reply
  and its 409 on duplicates, for compatibility.
- **`GET /api/sensor/status`** reports:
  - whether a sensor session is active, and its cadence;
  - accepted, duplicate and rejected counts for the session;
  - the last reading timestamp and seconds since it arrived;
  - `stale`, true when nothing arrived for more than three sample intervals.
- **`sensor_client.py`** is a stand-in for the ESP32. It sends simulated or CSV
  readings over HTTP with the token, batching and retries, so the whole path can
  be tested without hardware.
- Readings keep the existing contract: timezone-aware timestamps (the device
  must sync with NTP), finite non-negative active watts or null, no extra fields.

## Alternatives and tradeoffs

- **Binding only to the LAN address** would make the dashboard unreachable at
  `127.0.0.1` while sensing. Binding to all interfaces with a client-address gate
  keeps local use working.
- **A separate sensor microservice** would duplicate the timing, energy and
  storage path (ADR-003 rejected this already).
- **Server-side timestamps** (the time of arrival) would hide buffering delay and
  make batches meaningless. The device's NTP time is required instead.
- **TLS on the LAN** is not added. The token travels in plain HTTP on the home
  network. It is suitable for a trusted home Wi-Fi, never the internet.
- **Voltage, current and power-factor fields** for calibration are deferred until
  the sensing hardware is chosen.

## Consequences

- Windows will ask to allow Python through the firewall the first time LAN mode
  starts. The user decides.
- Anyone on the LAN who learns the token can post readings, but cannot change
  sources, upload files, retrain or read the dashboard.
- Hardware, calibration and mains safety remain the builder's responsibility,
  and nothing here validates a real sensor.
