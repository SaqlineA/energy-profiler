// The browser asks the API for fresh data once per second.
// It never generates readings or invents model results.
const $ = (id) => document.getElementById(id);
let state = null;
let readings = [];
let toastTimer;
let busy = false;
let online = false;
let tariffInitialized = false;
let revision = 0;
let refreshId = 0;
let loadedRange = null;
let loadedSession = null;
let training = false;

const icons = {
  lamp: '<path d="M8 14h8l3-9H5l3 9ZM12 14v6M8 21h8"/>',
  refrigerator:
    '<rect x="5" y="2" width="14" height="20" rx="2"/><path d="M5 9h14M8 5v2M8 12v4"/>',
  microwave:
    '<rect x="2" y="5" width="20" height="14" rx="2"/><rect x="5" y="8" width="10" height="8" rx="1"/><path d="M18 9h1M18 12h1M18 15h1M5 19v2M19 19v2"/>',
};

async function api(path, body) {
  const response = await fetch(path, {
    ...(body === undefined
      ? {}
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        }),
    signal: AbortSignal.timeout(path === '/api/model/train' ? 120000 : 20000),
  });
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const data = await response.json();
      if (typeof data.detail === "string") message = data.detail;
    } catch (_) {
      /* Keep status fallback. */
    }
    throw new Error(message);
  }
  return response.json();
}

function toast(message) {
  $("toast").textContent = message;
  $("toast").hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    $("toast").hidden = true;
  }, 4000);
}

function error(message) {
  $("error").textContent = message || "";
  $("error").hidden = !message;
}

function buildCards(devices) {
  // Device identifiers and names are defined in our backend, not user HTML.
  $("appliance-cards").innerHTML = devices
    .map(
      (d) => `
    <article class="appliance-card">
      <div class="device-top"><span class="device-icon"><svg viewBox="0 0 24 24" aria-hidden="true">${icons[d.id]}</svg></span><button class="toggle" id="toggle-${d.id}" role="switch" aria-checked="false" aria-label="Toggle ${d.name}"></button></div>
      <h3 class="device-name">${d.name}</h3><div class="device-description" id="description-${d.id}">Measured / estimated power</div>
      <div class="device-power"><strong><span id="watts-${d.id}">—</span><small>W</small></strong><span id="energy-${d.id}">0 Wh</span></div>
      <div class="device-bottom"><span id="actual-${d.id}">Measured: —</span><span id="prediction-${d.id}" class="prediction">ML guess: —</span></div>
    </article>`,
    )
    .join("");
  devices.forEach((d) =>
    $(`toggle-${d.id}`).addEventListener("click", () => {
      const current = state.appliances.find((item) => item.id === d.id);
      change(`/api/appliances/${d.id}`, { is_on: !current.is_on });
    }),
  );
}

function updateControls() {
  $("pause").disabled = !online || busy;
  $("auto").disabled = !online || busy || state?.source !== 'simulator';
  $("manual").disabled = !online || busy || state?.source !== 'simulator';
  $("train").disabled = !online || training;
  $("upload").disabled = !online || busy || training;
  $("source-simulator").disabled = !online || busy;
  $("source-replay").disabled = !online || busy || !state?.replay.loaded;
  $("rate-form").querySelector('button').disabled = !online || busy;
  if (state)
    state.appliances.forEach((d) => {
      $(`toggle-${d.id}`).disabled = !online || busy || !state.running || state.source !== 'simulator';
    });
}

function render() {
  if (!state) return;
  if (!$("appliance-cards").children.length) buildCards(state.appliances);
  const r = state.latest;
  if (loadedSession !== state.session) readings = [];
  $("source-badge").textContent = state.source === 'simulator' ? 'SIMULATED DATA' : state.source === 'sensor' ? 'LOCAL SENSOR INPUT' : 'RECORDED CSV';
  $("replay-status").textContent = state.replay.loaded
    ? `${state.replay.provenance.name} · ${state.replay.position}/${state.replay.loaded} rows · ${state.replay.cadence_seconds}s interval`
    : 'No recording loaded.';
  $("power").textContent = r?.total_watts != null
    ? r.total_watts.toLocaleString(undefined, { maximumFractionDigits: 1 })
    : "—";
  $("power-note").textContent = state.running
    ? (state.source === 'simulator' ? "Live simulated consumption" : state.source === 'sensor' ? "Local sensor input" : "Recorded-data replay")
    : "Paused · showing last reading";
  $("energy").textContent = state.energy_kwh.toFixed(4);
  $("duration").textContent =
    `${state.covered_seconds.toFixed(1)}s covered · ${state.skipped_seconds.toFixed(1)}s skipped`;
  $("cost").textContent = `$${state.cost.toFixed(4)}`;
  $("tariff-note").textContent =
    `Illustrative rate · $${state.rate.toFixed(3)} / kWh`;
  $("active").textContent = r?.predicted_mask != null
    ? state.appliances.filter((d) => r.predicted_mask & d.bit).length
    : "—";
  $("score").textContent = r
    ? `${r.prediction_quality.replaceAll('_', ' ')}${r.confidence == null ? '' : ` · ${Math.round(r.confidence * 100)}% uncalibrated score`}`
    : "Waiting for a reading";
  $("pause").textContent = state.running
    ? "Ⅱ  Pause collection"
    : "▷  Resume collection";
  $("auto").setAttribute("aria-pressed", state.mode === "auto");
  $("manual").setAttribute("aria-pressed", state.mode === "manual");
  $("mode-description").textContent =
    state.source === 'sensor' ? 'Waiting for POST /api/sensor/readings. Loopback only; no physical hardware has been verified.' : state.source === 'replay' ? 'Replay preserves source time. Gaps are not counted as zero consumption. Appliance switches are disabled.' : state.profile === 'household' ? 'Fridge and washing machine timings follow real REFIT homes: the fridge runs 25-30 min, the microwave is used a few times a day, other household loads (lights, TV, kettle) come and go, and a full wash (fill, heat, wash, pause, drain, spin) takes about an hour. The first wash starts within 10 minutes; later ones days apart.' : state.profile !== 'classic' ? 'Seeded cycles, varying wattage, startup spikes, unknown background and measurement noise. Washer stages are compressed demo timings.' : state.mode === "auto"
      ? "The lamp stays on. The refrigerator cycles, and the microwave runs in short bursts."
      : "Use the appliance switches below. Try combining loads to see when the model gets confused.";
  if (!tariffInitialized) {
    $("rate").value = state.rate;
    tariffInitialized = true;
  }
  state.appliances.forEach((d) => {
    const prediction = r?.predictions[d.id];
    const predicted = prediction?.on;
    const actual = r?.[d.id] == null ? null : r[d.id] >= d.threshold;
    $(`toggle-${d.id}`).setAttribute("aria-checked", Boolean(d.is_on));
    $(`watts-${d.id}`).textContent = r?.[d.id] != null ? r[d.id].toFixed(1) : "—";
    $(`description-${d.id}`).textContent = prediction
      ? `ML estimate ${prediction.estimated_watts.toFixed(1)} W · ${predicted == null ? 'uncertain' : 'not measured'}`
      : `${d.watts.toLocaleString()} W demo nominal · measured watts below`;
    $(`energy-${d.id}`).textContent = d.energy_kwh == null ? 'Energy unknown' : `${(d.energy_kwh * 1000).toFixed(2)} Wh measured`;
    $(`actual-${d.id}`).textContent = actual != null
      ? `Measured: ${actual ? "on" : "off"}`
      : "Measured: unknown";
    $(`prediction-${d.id}`).textContent = predicted != null
      ? `ML: ${predicted ? "on" : "off"} ${actual == null ? '' : predicted === actual ? "✓" : "≠"}`
      : "ML: unknown";
    $(`prediction-${d.id}`).classList.toggle(
      "mismatch",
      predicted != null && actual != null && predicted !== actual,
    );
  });
  const model = state.model;
  $("accuracy").textContent = `${(model.accuracy * 100).toFixed(1)}%`;
  $("training-count").textContent = model.train_samples.toLocaleString();
  $("live-metrics").textContent = state.live_accuracy === null
    ? `No labeled predictions to evaluate yet · ${(state.prediction_coverage * 100).toFixed(1)}% prediction coverage`
    : `Session: ${(state.live_accuracy * 100).toFixed(1)}% correct across ${state.evaluated_samples} labeled windows (abstentions count as wrong) · ${(state.prediction_coverage * 100).toFixed(1)}% prediction coverage. Includes all session models; replay may include training rows, so this is not a held-out score.`;
  $("evaluation").textContent =
    `${model.training_source} · ${model.test_samples.toLocaleString()} held-out windows.`;
  $("model-provenance").textContent = `Model ${model.version} · ${model.cadence_seconds}s interval · ${model.provenance.split} · seed ${model.seed}. Energy metrics cover ${model.energy_coverage_seconds}s of scored intervals.`;
  $("baselines").textContent = `Same-test baselines: single-watt joint model ${(model.baselines.single_watt_joint_accuracy * 100).toFixed(1)}%; always off ${(model.baselines.always_off_accuracy * 100).toFixed(1)}%. Unexplained load: ${r?.unexplained_watts == null ? '—' : `${r.unexplained_watts.toFixed(1)} W (heuristic residual)`}.`;
  $("metric-rows").innerHTML = state.appliances.map(d => {
    const m = model.device_metrics[d.id];
    return `<tr><th>${d.name}</th><td>${m.precision.toFixed(2)}</td><td>${m.recall.toFixed(2)}</td><td>${m.f1.toFixed(2)}</td><td>${m.mae_watts.toFixed(1)}</td><td>${(m.absolute_energy_error_kwh * 1000).toFixed(2)}</td></tr>`;
  }).join('');
  $("limitation").textContent = model.limitation;
  $("per-device").innerHTML = state.appliances
    .map(
      (d) =>
        `<span>${d.name} ${(model.per_appliance[d.id] * 100).toFixed(1)}%</span>`,
    )
    .join("");
  $("event-count").textContent = `${state.events.length} recent events`;
  $("events").innerHTML = state.events.length
    ? state.events
        .map(
          (e) => `
    <li class="event"><span class="event-icon ${e.is_on ? "" : "off"}">${e.is_on ? "↗" : "↘"}</span><div class="event-body"><strong>${e.appliance} predicted ${e.is_on ? "on" : "off"}</strong><small>Second ${e.second} · ${new Date(e.timestamp).toLocaleTimeString()}</small></div><span class="event-delta">${e.delta > 0 ? "+" : ""}${e.delta.toFixed(1)} W</span></li>`,
        )
        .join("")
    : '<li class="empty-event">Waiting for the first switch.<br>Try turning on the microwave.</li>';
  error(state.error);
  updateControls();
  drawChart();
  window.energyResearch?.render(state, readings);
}

function drawChart() {
  const canvas = $("chart");
  const box = canvas.getBoundingClientRect();
  if (!box.width) return;
  const scale = window.devicePixelRatio || 1;
  canvas.width = Math.round(box.width * scale);
  canvas.height = Math.round(box.height * scale);
  const ctx = canvas.getContext("2d");
  ctx.scale(scale, scale);
  const w = box.width,
    h = box.height;
  const left = 43,
    top = 18,
    right = w - 12,
    bottom = h - 30;
  const peak = readings.length
    ? Math.max(...readings.map((r) => r.total_watts))
    : 0;
  const maxY = Math.max(200, Math.ceil(peak / 200) * 200);
  ctx.font = "9px system-ui";
  for (let i = 0; i <= 4; i++) {
    const y = bottom - ((bottom - top) * i) / 4;
    ctx.strokeStyle = "#edf0e7";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(left, y);
    ctx.lineTo(right, y);
    ctx.stroke();
    ctx.fillStyle = "#939d86";
    ctx.textAlign = "right";
    ctx.fillText(`${Math.round((maxY * i) / 4)}`, left - 9, y + 3);
  }
  $("chart-empty").hidden = readings.length > 0;
  $("peak").textContent = readings.length
    ? `Peak ${peak.toFixed(1)} W`
    : "Peak — W";
  $("chart-count").textContent = `${readings.length} readings in view`;
  if (!readings.length) return;
  const first = readings[0].second,
    last = readings[readings.length - 1].second;
  const span = Math.max(1, last - first);
  const x = (r) => left + ((r.second - first) / span) * (right - left);
  const y = (r) => bottom - (r.total_watts / maxY) * (bottom - top);
  ctx.beginPath();
  let connected = false;
  readings.forEach((r) => {
    if (r.total_watts == null) { connected = false; return; }
    if (!connected || r.quality === 'gap') ctx.moveTo(x(r), y(r));
    else ctx.lineTo(x(r), y(r));
    connected = true;
  });
  ctx.strokeStyle = "#6c8c50";
  ctx.lineWidth = 2;
  ctx.lineJoin = "round";
  ctx.stroke();
  const latest = readings[readings.length - 1];
  ctx.beginPath();
  if (latest.total_watts != null) ctx.arc(x(latest), y(latest), 3, 0, Math.PI * 2);
  ctx.fillStyle = "#426635";
  ctx.fill();
  ctx.fillStyle = "#939d86";
  const ticks = Math.min(5, readings.length);
  for (let i = 0; i < ticks; i++) {
    const r =
      readings[
        Math.round((i * (readings.length - 1)) / Math.max(1, ticks - 1))
      ];
    ctx.textAlign = i === 0 ? "left" : i === ticks - 1 ? "right" : "center";
    ctx.fillText(`${r.second}s`, x(r), h - 8);
  }
  canvas.setAttribute(
    "aria-label",
    `Total power over ${readings.length} readings. Latest ${latest.total_watts?.toFixed(1) ?? 'unknown'} watts, peak ${peak.toFixed(1)} watts.`,
  );
}

async function refresh() {
  // Skip polling while a user command is pending so old responses cannot undo it.
  if (busy) return;
  const requestedRevision = revision;
  const requestId = ++refreshId;
  const requestedRange = $("range").value;
  const cursor = loadedRange === requestedRange && readings.length
    ? readings[readings.length - 1].id : 0;
  try {
    const snapshot = await api(`/api/dashboard?limit=${requestedRange}&after_id=${cursor}&session=${encodeURIComponent(loadedSession || '')}`);
    const next = snapshot.state;
    const history = snapshot.readings;
    if (busy || requestedRevision !== revision || requestId !== refreshId)
      return;
    const sameSession = loadedSession === next.session;
    readings = (sameSession && cursor ? readings.concat(history) : history).slice(-Number(requestedRange));
    loadedRange = requestedRange;
    loadedSession = next.session;
    if (!sameSession) tariffInitialized = false;
    state = next;
    online = true;
    $("connection").textContent = state.running
      ? `Live · ${state.source}`
      : "Connected · paused";
    $("connection").className = "connection online";
    render();
  } catch (e) {
    if (busy || requestedRevision !== revision || requestId !== refreshId)
      return;
    online = false;
    $("connection").textContent = "Disconnected";
    $("connection").className = "connection offline";
    $("power-note").textContent = "Disconnected · last received reading";
    error(
      "Cannot reach the local server. Keep app.py running; this page will reconnect automatically.",
    );
    updateControls();
  }
}

async function change(path, body) {
  if (busy) return;
  revision += 1;
  busy = true;
  updateControls();
  try {
    state = await api(path, body);
    render();
  } catch (e) {
    toast(e.message);
  } finally {
    busy = false;
    updateControls();
    await refresh();
  }
}

$("pause").addEventListener("click", () => {
  if (state) change("/api/simulation", { running: !state.running });
});
$("auto").addEventListener("click", () =>
  change("/api/simulation", { mode: "auto" }),
);
$("manual").addEventListener("click", () =>
  change("/api/simulation", { mode: "manual" }),
);
$("range").addEventListener("change", refresh);
$("rate-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  await change("/api/tariff", { rate: Number($("rate").value) });
});
$("train").addEventListener("click", async () => {
  training = true;
  $("train").disabled = true;
  $("train").textContent = "Training…";
  try {
    await api("/api/model/train", { source: $("train-source").value });
    toast("Model saved and evaluated against its fixed held-out split.");
    await refresh();
  } catch (e) {
    toast(e.message);
  } finally {
    training = false;
    updateControls();
    $("train").textContent = "↻ Retrain model";
  }
});
$("source-simulator").addEventListener('click', () => change('/api/source', {source: 'simulator'}));
$("source-replay").addEventListener('click', () => change('/api/source', {source: 'replay'}));
$("replay-form").addEventListener('submit', async (event) => {
  event.preventDefault();
  if (busy) return;
  const file = $("csv-file").files[0];
  if (!file) return;
  if (file.size > 5000000) { toast('CSV exceeds 5 MB limit'); return; }
  busy = true;
  revision += 1;
  updateControls();
  try {
    const response = await fetch(`/api/replay?cadence=${encodeURIComponent($("cadence").value)}&name=${encodeURIComponent(file.name)}`, {
      method: 'POST', headers: {'Content-Type': 'text/csv'}, body: file, signal: AbortSignal.timeout(20000),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'Invalid recording or interval');
    state = result;
    render();
    toast('Recording loaded. Select Replay CSV to start.');
  } catch (e) { toast(e.message); }
  finally { busy = false; updateControls(); await refresh(); }
});
new ResizeObserver(drawChart).observe($("chart").parentElement);
async function poll() {
  await refresh();
  setTimeout(poll, 1000);
}
updateControls();
poll();
