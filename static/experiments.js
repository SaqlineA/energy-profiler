// Experiment names and saved data are text, never HTML or executable code.
(() => {
  let selected = null, current = null, live = [], pending = false, selectionRevision = 0;
  const element = (tag, text) => { const e = document.createElement(tag); e.textContent = text; return e; };
  const number = (value, digits = 2) => value == null ? '—' : Number(value).toFixed(digits);
  const tableRow = (values) => { const tr = document.createElement('tr'); values.forEach(v => tr.append(element('td', v))); return tr; };
  const THRESHOLDS = {lamp: 5, refrigerator: 20, microwave: 100, washing_machine: 10};
  const BADGES = {real: 'REAL DATA', synthetic: 'SYNTHETIC DATA'};
  // Scale to the 99th percentile so one startup spike cannot flatten the chart; callers report clipping.
  const scaleTop = values => { const v = values.filter(n => n != null).map(Math.abs).sort((a, b) => a - b);
    return Math.max(10, (v[Math.floor(v.length * .99)] ?? 0) * 1.1); };
  const clippedNote = (values, top) => { const n = values.filter(v => v != null && Math.abs(v) > top).length;
    return n ? ` ${n} reading${n === 1 ? '' : 's'} beyond ±${number(top, 0)} W drawn at the chart edge.` : ''; };
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
    const values = points.flatMap(p => [p.truth[key], p.predictions[key]?.estimated_watts]);
    const max = scaleTop(values);
    const note = clippedNote(values, max);
    if (note) $('comparison-summary').textContent += '.' + note;
    const x = p => 55 + (Date.parse(p.timestamp) - firstTime) / Math.max(1, lastTime - firstTime) * 730;
    const y = v => 195 - Math.min(v, max) / max * 170;
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
    drawStates(points, key, x); drawErrors(points, key, x, lastTime - firstTime);
  }

  // Merge consecutive ON readings into bars; gaps and unknown labels break a bar.
  function drawStates(points, key, x) {
    const chart = $('state-chart'); chart.replaceChildren();
    const threshold = selected?.model?.thresholds_watts?.[key] ?? THRESHOLDS[key] ?? 1;
    const rows = [['Actual', 8, p => p.truth[key] == null ? null : p.truth[key] >= threshold, '#426635'],
                  ['Predicted', 46, p => { const m = p.predictions[key]; return m ? (m.raw_on ?? m.on ?? m.estimated_watts >= threshold) : null; }, '#995127']];
    const counts = [0, 0];
    rows.forEach(([label, top, isOn, color], row) => {
      chart.append(svgElement('rect', {x: 55, y: top, width: 730, height: 30, fill: '#eef1ec', rx: 4}));
      chart.append(svgElement('text', {x: 48, y: top + 19, 'text-anchor': 'end', 'font-size': 11, fill: '#46513e'}, label));
      let start = null;
      points.forEach((point, i) => {
        const next = points[i + 1];
        if (isOn(point) !== true) return;
        if (start === null) start = x(point);
        if (!next || next.quality === 'gap' || isOn(next) !== true) {
          const end = next && next.quality !== 'gap' && isOn(next) !== null ? x(next) : x(point) + 1;
          chart.append(svgElement('rect', {x: start, y: top, width: Math.max(1, end - start), height: 30, fill: color}));
          start = null; counts[row]++;
        }
      });
    });
    $('state-summary').textContent = `${counts[0]} actual ON period${counts[0] === 1 ? '' : 's'} vs. ${counts[1]} predicted. `
      + 'Grey means off or not scored; matching bars mean the model caught that cycle.';
    chart.setAttribute('aria-label', `${key}: ${$('state-summary').textContent}`);
  }

  function drawErrors(points, key, x, spanMs) {
    const chart = $('error-chart'); chart.replaceChildren();
    const errors = points.map(p => {
      const actual = p.truth[key], estimate = p.predictions[key]?.estimated_watts;
      return actual == null || estimate == null ? null : [p, estimate - actual];
    }).filter(Boolean);
    if (!errors.length) { $('error-summary').textContent = 'No scored predictions with known actual watts yet.'; return; }
    const limit = scaleTop(errors.map(([, e]) => e));
    const y = v => 80 - Math.max(-limit, Math.min(limit, v)) / limit * 65;
    [limit, limit / 2, 0, -limit / 2, -limit].forEach(v => {
      chart.append(svgElement('line', {x1: 55, x2: 785, y1: y(v), y2: y(v), stroke: v ? '#dde4d7' : '#8a968c'}));
      chart.append(svgElement('text', {x: 48, y: y(v) + 4, 'text-anchor': 'end', 'font-size': 11, fill: '#46513e'}, `${v > 0 ? '+' : ''}${number(v, 0)}`));
    });
    let over = '', under = '';
    errors.forEach(([p, e]) => { const seg = `M${x(p)},${y(0)}V${y(e)} `; if (e > 0) over += seg; else if (e < 0) under += seg; });
    chart.append(svgElement('path', {d: over, stroke: '#b0561f', 'stroke-width': 1.5}));
    chart.append(svgElement('path', {d: under, stroke: '#2f5f8a', 'stroke-width': 1.5}));
    chart.append(svgElement('text', {x: 55, y: 164, 'font-size': 11, fill: '#46513e'}, '0 source seconds'));
    chart.append(svgElement('text', {x: 785, y: 164, 'text-anchor': 'end', 'font-size': 11, fill: '#46513e'}, `${number(spanMs / 1000, 0)} source seconds`));
    const mean = errors.reduce((sum, [, e]) => sum + e, 0) / errors.length;
    const share = sign => errors.filter(([, e]) => sign * e > 1).length / errors.length * 100;
    const bias = Math.abs(mean) < .5 ? 'no overall bias' : `${mean < 0 ? 'underestimates' : 'overestimates'} on average`;
    $('error-summary').textContent = `Average error ${mean > 0 ? '+' : ''}${number(mean, 1)} W (${bias}). `
      + `Over by more than 1 W in ${number(share(1), 0)}% of scored readings, under in ${number(share(-1), 0)}%.`
      + clippedNote(errors.map(([, e]) => e), limit);
    chart.setAttribute('aria-label', `${key} prediction error: ${$('error-summary').textContent}`);
  }

  function showSummary(key) {
    const box = $('result-summary'), d = selected?.describe, m = selected?.devices[key];
    box.hidden = !d || !m;
    if (box.hidden) return;
    const badge = (id, kind, prefix) => { const e = $(id); e.className = `data-badge ${kind}`;
      e.textContent = kind === 'none' ? 'BASELINE · NO TRAINING' : `${prefix} ${BADGES[kind]}`; };
    badge('evaluation-badge', d.evaluation_data, 'TESTED ON');
    badge('training-badge', d.training_data, 'TRAINED ON');
    const facts = [['Dataset', d.dataset], ['Model', d.model], ['Training', d.training], ['Appliance', key.replace('_', ' ')],
      ['F1', number(m.f1, 3)], ['MAE', m.mae_watts == null ? '—' : `${number(m.mae_watts, 1)} W`],
      ['Actual energy', m.true_kwh == null ? '—' : `${number(m.true_kwh, 3)} kWh`],
      ['Predicted energy', m.estimated_kwh == null ? '—' : `${number(m.estimated_kwh, 3)} kWh`]];
    $('result-facts').replaceChildren(...facts.map(([term, value]) => {
      const wrap = document.createElement('div'); wrap.append(element('dt', term), element('dd', value)); return wrap; }));
    $('result-explanation').textContent = d.explanations[key];
  }

  function showReport() {
    const device = $('comparison-device');
    if (selected && !(device.value in selected.devices)) device.value = Object.keys(selected.devices)[0];
    $('experiment-note').textContent = selected
      ? `${selected.provenance.name || 'Experiment'} · Model ${selected.model_version} · ${selected.timing_note} ${selected.prediction_windows}/${selected.rows} prediction windows. Showing first ${selected.points.length} rows. ${selected.limitation}`
      : 'Live session. Original model predictions require matching cadence; uncertain estimates are not confirmed detections.';
    const body = $('experiment-metrics'); body.replaceChildren();
    if (!selected) body.append(tableRow(['Select a saved experiment to inspect its metrics.', '', '', '', '', '', '']));
    else Object.entries(selected.devices).forEach(([key, m]) => body.append(tableRow([
      key, m.samples, `${m.positive_samples} / ${m.negative_samples}`, m.accuracy == null ? '—' : number(m.accuracy * 100) + '%',
      number(m.f1, 3), number(m.mae_watts), `${m.certain_samples}/${m.samples}`])));
    showSummary(device.value); draw();
  }

  async function history() {
    const reports = await api('/api/experiments?limit=100');
    const view = $('experiment-view'), value = view.value;
    view.replaceChildren(new Option('Live session', ''));
    // Newest first: key groups keep only the latest report per label; "Other" keeps everything.
    const groups = [['final_test', 'Final test (held-out house, scored once)'], ['development', 'Development (House 2)'], ['other', 'Other experiments']];
    groups.forEach(([group, title]) => {
      const seen = new Set(), optgroup = document.createElement('optgroup'); optgroup.label = title;
      reports.filter(r => (r.describe?.group ?? 'other') === group).forEach(r => {
        const label = r.describe?.label ?? r.provenance.name ?? r.id.slice(0, 8);
        if (group !== 'other' && seen.has(label)) return;
        seen.add(label);
        const d = r.describe;
        const source = d ? ` · ${d.training_data === 'none' ? 'no training' : `trained on ${d.training_data} data`}, tested on ${d.evaluation_data} data` : '';
        optgroup.append(new Option(group === 'other' ? `${label} · ${r.policy}${source}` : label + source, r.id));
      });
      if (optgroup.children.length) view.append(optgroup);
    });
    view.value = value;
  }

  async function selectReport(id) {
    const revision = ++selectionRevision;
    const report = id ? await api(`/api/experiments/${encodeURIComponent(id)}?limit=10000`) : null;
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
  $('comparison-device').addEventListener('change', () => { showSummary($('comparison-device').value); draw(); });
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
    const running = washer?.stage && !['off', 'idle'].includes(washer.stage);
    $('washer-card').hidden = !washer?.model;
    $('washer-state').textContent = running ? 'Running' : 'Off';
    $('washer-phase').textContent = running ? washer.stage[0].toUpperCase() + washer.stage.slice(1) : '—';
    $('washer-watts').textContent = washer?.watts == null ? '—' : `${number(washer.watts, 0)} W`;
    $('washer-minutes').textContent = washer?.cycle_minutes == null ? '—' : `${number(washer.cycle_minutes, 1)} min`;
    $('washer-model').textContent = washer?.model === 'v2' ? 'v2 · based on REFIT cycles' : 'v1 · compressed demo';
    $('washer-status').textContent = `Experimental washer: ${number(washer?.watts)} W · Stage ${washer?.stage || 'unknown'} · ${number(washer?.energy_kwh == null ? null : washer.energy_kwh * 1000)} Wh. Original live model has no washer output; see the four-device experiment for estimates.`;
    renderControls(); if (!selected) draw();
  }};
  history().catch(e => { $('experiment-note').textContent = e.message; });
  sessions(); showReport(); renderControls();
})();
