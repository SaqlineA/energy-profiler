// Experiment names and saved data are text, never HTML or executable code.
(() => {
  let selected = null, current = null, live = [], pending = false, selectionRevision = 0;
  const element = (tag, text) => { const e = document.createElement(tag); e.textContent = text; return e; };
  const number = (value, digits = 2) => value == null ? '—' : Number(value).toFixed(digits);
  const tableRow = (values) => { const tr = document.createElement('tr'); values.forEach(v => tr.append(element('td', v))); return tr; };
  const svgElement = (tag, attrs, text) => {
    const e = document.createElementNS('http://www.w3.org/2000/svg', tag);
    Object.entries(attrs).forEach(([key, value]) => e.setAttribute(key, value));
    if (text !== undefined) e.textContent = text;
    return e;
  };

  function draw() {
    const key = $('comparison-device').value;
    const points = selected?.points ?? live.map(r => ({...r, truth: r}));
    const chart = $('comparison-chart');
    chart.replaceChildren();
    const last = points.at(-1);
    const actual = last?.truth[key], estimated = last?.predictions[key]?.estimated_watts;
    $('comparison-summary').textContent = points.length
      ? `${points.length} displayed readings · Actual ${number(actual)} W · Estimate ${number(estimated)} W · Absolute difference ${number(actual == null || estimated == null ? null : Math.abs(actual - estimated))} W`
      : 'No readings yet. Start a source or select a saved experiment.';
    if (!points.length) return;
    const firstTime = Date.parse(points[0].timestamp), lastTime = Date.parse(last.timestamp);
    const max = Math.max(10, ...points.flatMap(p => [p.truth[key] ?? 0, p.predictions[key]?.estimated_watts ?? 0]));
    const x = p => 55 + (Date.parse(p.timestamp) - firstTime) / Math.max(1, lastTime - firstTime) * 730;
    const y = v => 195 - v / max * 170;
    for (let i = 0; i <= 4; i++) {
      const value = max * i / 4;
      chart.append(svgElement('line', {x1: 55, x2: 785, y1: y(value), y2: y(value), stroke: '#dde4d7'}));
      chart.append(svgElement('text', {x: 48, y: y(value) + 4, 'text-anchor': 'end', 'font-size': 11, fill: '#46513e'}, number(value, 0)));
    }
    for (const predicted of [false, true]) {
      let path = '', connected = false;
      for (const point of points) {
        const value = predicted ? point.predictions[key]?.estimated_watts : point.truth[key];
        if (value == null) { connected = false; continue; }
        path += `${connected && point.quality !== 'gap' ? 'L' : 'M'}${x(point)},${y(value)} `;
        connected = true;
      }
      chart.append(svgElement('path', {d: path, fill: 'none', stroke: predicted ? '#995127' : '#426635',
        'stroke-width': 2, 'stroke-dasharray': predicted ? '6 4' : 'none'}));
    }
    chart.append(svgElement('text', {x: 55, y: 220, 'font-size': 11, fill: '#46513e'}, '0 source seconds'));
    chart.append(svgElement('text', {x: 785, y: 220, 'text-anchor': 'end', 'font-size': 11, fill: '#46513e'}, `${number((lastTime - firstTime) / 1000, 0)} source seconds`));
    chart.setAttribute('aria-label', `${key}: ${$('comparison-summary').textContent}. Solid measured line; dashed raw estimates. Gaps are not connected.`);
  }

  function showReport() {
    $('experiment-note').textContent = selected
      ? `${selected.provenance.name || 'Experiment'} · Model ${selected.model_version} · ${selected.timing_note} ${selected.prediction_windows}/${selected.rows} prediction windows. Showing first ${selected.points.length} rows. ${selected.limitation}`
      : 'Live session. Original model predictions require matching cadence; uncertain estimates are not confirmed detections.';
    const body = $('experiment-metrics'); body.replaceChildren();
    if (!selected) body.append(tableRow(['Select a saved experiment to inspect its metrics.', '', '', '', '', '', '']));
    else Object.entries(selected.devices).forEach(([key, m]) => body.append(tableRow([
      key, m.samples, `${m.positive_samples} / ${m.negative_samples}`, m.accuracy == null ? '—' : number(m.accuracy * 100) + '%',
      number(m.f1, 3), number(m.mae_watts), `${m.certain_samples}/${m.samples}`])));
    draw();
  }

  async function history() {
    const reports = await api('/api/experiments?limit=100');
    const view = $('experiment-view'), value = view.value;
    view.replaceChildren(new Option('Live session', ''));
    reports.forEach(r => view.append(new Option(`${r.provenance.name || r.id.slice(0, 8)} · ${r.policy}`, r.id)));
    view.value = value;
  }

  async function selectReport(id) {
    const revision = ++selectionRevision;
    const report = id ? await api(`/api/experiments/${encodeURIComponent(id)}`) : null;
    if (revision !== selectionRevision) return;
    selected = report; showReport();
  }

  async function sessions() {
    try {
      const rows = await api('/api/sessions');
      $('session-metrics').replaceChildren(...rows.map(r => tableRow([
        r.session.slice(0, 8), r.source, r.samples, number(r.covered_seconds, 1), number(r.energy_kwh, 5),
        number(r.cost_at_current_rate, 5), `${r.missing_rows} / ${r.gap_rows}`])));
      $('session-status').textContent = rows.length ? `Most recent ${rows.length} sessions. Refresh after a run or tariff change.` : 'No saved sessions yet.';
    } catch (e) { $('session-status').textContent = e.message; }
  }

  $('experiment-view').addEventListener('change', () => selectReport($('experiment-view').value).catch(e => toast(e.message)));
  $('comparison-device').addEventListener('change', draw);
  $('refresh-experiments').addEventListener('click', () => history().catch(e => toast(e.message)));
  $('refresh-sessions').addEventListener('click', sessions);
  $('simulation-profile').addEventListener('change', () => change('/api/simulation', {profile: $('simulation-profile').value}));
  $('source-sensor').addEventListener('click', () => change('/api/source', {source: 'sensor', cadence: Number($('cadence').value)}));
  $('experiment-form').addEventListener('submit', async event => {
    event.preventDefault();
    if (pending) return;
    pending = true; $('run-experiment').disabled = true;
    $('run-experiment').textContent = 'Evaluating…';
    try {
      const report = await api('/api/experiments', {policy: $('experiment-policy').value});
      await history(); $('experiment-view').value = report.id; await selectReport(report.id);
      toast('Experiment saved. Live model unchanged.');
    } catch (e) { toast(e.message); }
    finally { pending = false; $('run-experiment').textContent = 'Evaluate loaded CSV — no retraining'; renderControls(); }
  });
  function renderControls() {
    $('run-experiment').disabled = pending || !online || !current?.replay.loaded;
    $('source-sensor').disabled = !online || busy;
    $('simulation-profile').disabled = !online || busy || current?.source !== 'simulator';
  }
  window.energyResearch = {render(next, rows) {
    current = next; live = rows;
    $('simulation-profile').value = next.profile;
    const washer = next.experimental_washer;
    $('washer-status').textContent = `Experimental washer: ${number(washer?.watts)} W · Stage ${washer?.stage || 'unknown'} · ${number(washer?.energy_kwh == null ? null : washer.energy_kwh * 1000)} Wh. Original live model has no washer output; see the four-device experiment for estimates.`;
    renderControls(); if (!selected) draw();
  }};
  history().catch(e => { $('experiment-note').textContent = e.message; });
  sessions(); showReport(); renderControls();
})();
