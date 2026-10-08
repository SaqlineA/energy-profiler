// Current project site. Plain JS, no build step. Content is visible without it.
(() => {
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const NS = 'http://www.w3.org/2000/svg';
  const el = (tag, attrs = {}, text) => {
    const node = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
    if (text !== undefined) node.textContent = text;
    return node;
  };

  // Illustrative appliance signals (not measured data), 120 steps each.
  const STEPS = 120;
  const signals = [
    { name: 'Fridge', note: 'cycles on and off', img: 'img/refrigerator.webp',
      at: i => (i % 40 < 14 ? 85 : 0) },
    { name: 'Lamp', note: 'steady while on', img: 'img/lamp.webp',
      at: i => (i < 18 ? 0 : 20) },
    { name: 'Washer', note: 'heats, then washes and spins', img: 'img/washing_machine.webp',
      at: i => i < 30 ? 0 : i < 38 ? (i % 3 ? 60 : 10) : i < 60 ? 2050 : i < 100 ? (i % 4 < 2 ? 160 : 40)
        : i < 112 ? 300 + (i - 100) * 18 : 0 },
  ];
  const total = Array.from({ length: STEPS }, (_, i) => 120 + signals.reduce((sum, s) => sum + s.at(i), 0));

  function trace(values, x0, x1, yBase, height) {
    const max = Math.max(...values) || 1;
    return values.map((v, i) => {
      const x = x0 + (x1 - x0) * i / (values.length - 1);
      const y = yBase - (v / max) * height;
      return `${i ? 'L' : 'M'}${x.toFixed(1)},${y.toFixed(1)}`;
    }).join('');
  }

  // Two compositions of the same idea: side by side on wide screens, stacked on phones.
  const LAYOUTS = {
    wide: { viewBox: '0 0 1100 430', rows: [70, 215, 360], thumb: 64, labelX: 78, trace: [230, 560], traceH: 56,
      route: (y, m) => `M566,${y + 20} C640,${y + 20} 650,${m.y} ${m.x - 26},${m.y}`, meter: { x: 712, y: 215 },
      total: { x0: 760, x1: 1090, base: 330, h: 220, titleY: 70 } },
    stacked: { viewBox: '0 0 360 650', rows: [44, 134, 224], thumb: 40, labelX: 48, trace: [168, 352], traceH: 40,
      route: (y, m) => `M352,${y + 20} C352,${y + 110} ${m.x + 40},${m.y - 60} ${m.x},${m.y - 26}`, meter: { x: 180, y: 380 },
      total: { x0: 0, x1: 352, base: 630, h: 120, titleY: 470 } },
  };
  const phone = matchMedia('(max-width: 620px)');

  function buildWire(svg, animate) {
    const L = LAYOUTS[phone.matches ? 'stacked' : 'wide'], meter = L.meter;
    svg.setAttribute('viewBox', L.viewBox);
    [...svg.children].forEach(node => { if (!['title', 'desc'].includes(node.nodeName)) node.remove(); });
    const add = (tag, attrs, text, step) => {
      const node = el(tag, attrs, text);
      if (step !== undefined) node.style.cssText += `--delay:${step * 0.6}s;--step:${step};`;
      svg.append(node);
      return node;
    };
    signals.forEach((s, r) => {
      const y = L.rows[r], step = 0.3 * r;
      add('image', { href: s.img, x: 0, y: y - L.thumb * 0.72, width: L.thumb, height: L.thumb, class: 'fade' }, undefined, step);
      add('text', { x: L.labelX, y: y - 14, class: 'label fade' }, s.name, step);
      add('text', { x: L.labelX, y: y + 4, class: 'sub fade' }, s.note, step);
      const values = Array.from({ length: STEPS }, (_, i) => s.at(i));
      add('line', { x1: L.trace[0], x2: L.trace[1], y1: y + 20, y2: y + 20, stroke: 'var(--hairline)' });
      add('path', { d: trace(values, L.trace[0], L.trace[1], y + 20, L.traceH), class: 'trace draw', stroke: 'var(--green)' }, undefined, step);
      add('path', { d: L.route(y, meter), class: 'route draw', stroke: 'var(--green)' }, undefined, 1.4 + 0.2 * r);
    });
    add('circle', { cx: meter.x, cy: meter.y, r: 26, class: 'meter fade' }, undefined, 2.2);
    add('path', { d: `M${meter.x + 3},${meter.y - 13} l-9,14 h7 l-3,12 l11,-16 h-7 z`, fill: 'var(--green)', class: 'fade' }, undefined, 2.2);
    add('text', { x: meter.x, y: meter.y + 50, 'text-anchor': 'middle', class: 'sub fade' }, 'the meter', 2.2);
    const T = L.total;
    add('line', { x1: T.x0, x2: T.x1, y1: T.base, y2: T.base, stroke: 'var(--hairline)' });
    add('path', { d: trace(total, T.x0, T.x1, T.base, T.h), class: 'total draw' }, undefined, 2.6);
    add('text', { x: T.x0, y: T.titleY, class: 'label fade' }, 'What the model gets', 2.6);
    add('text', { x: T.x0, y: T.titleY + 20, class: 'sub fade' }, 'one total line, every appliance mixed in', 2.6);
    if (animate) svg.querySelectorAll('.draw').forEach(path => path.style.setProperty('--len', Math.ceil(path.getTotalLength())));
  }

  const wire = document.querySelector('#wire');
  if (wire) {
    const svg = wire.querySelector('svg');
    const scrollDriven = !reduced && CSS.supports('animation-timeline: view()');
    const animate = !reduced && (scrollDriven || 'IntersectionObserver' in window);
    buildWire(svg, animate);
    phone.addEventListener('change', () => buildWire(svg, animate));
    if (scrollDriven) {
      wire.classList.add('armed', 'scroll'); // Drawing follows the scroll position.
    } else if (animate) {
      wire.classList.add('armed');
      new IntersectionObserver((entries, observer) => {
        if (entries.some(e => e.isIntersecting)) { wire.classList.add('play'); observer.disconnect(); }
      }, { threshold: 0.35 }).observe(wire);
    }
  }

  // Paper: render report.md, one section per heading, with a pinned figure beside each.
  const paper = document.querySelector('#paper');
  if (!paper) return;
  const figures = {
    abstract: { img: 'img/hero.webp', alt: 'Illustration of a house whose appliances share one meter', cap: 'One meter, many appliances. (Illustration.)' },
    background: { wire: true, cap: 'The NILM problem: separate signals become one total line. (Illustration, not measured data.)' },
    system: { img: 'img/dashboard.webp', alt: 'The Current dashboard', cap: "Current's dashboard: live power, appliance cards and the experiment workbench." },
    method: { svg: splitDiagram, cap: 'Which REFIT house did what. House 5 stayed sealed until the single final test.' },
    development: { svg: () => bars([
      ['v2 · absolute · RF', 0.406], ['v3 · relative · RF', 0.181], ['v4 · absolute · RF', 0.132],
      ['v4r · relative · RF', 0.439], ['v4r · relative · DT', 0.781, true], ['Always off', 0]], 'F1 on the development house (House 2)'),
      cap: 'Table 1 as a chart. Only one change per run; the v4r Decision Tree was chosen before House 5 was opened.' },
    'final-test': { img: 'img/house5-figure.webp', alt: 'House 5: 36 real fridge ON periods above 257 short predicted bursts, and the prediction error', cap: 'House 5, scored once: 36 real fridge cycles vs 257 short guesses, and the error over about 17 hours.' },
    'cross-house': { svg: () => bars([
      ['House 1 · real', 0.358], ['House 1 · simulator', 0.280, false, true],
      ['House 2 · real', 0.520], ['House 2 · simulator', 0.874, false, true],
      ['House 3 · real', 0.377], ['House 3 · simulator', 0.631, false, true],
      ['House 4 · real', 0.339], ['House 4 · simulator', 0.360, false, true],
      ['House 5 · real', 0.450], ['House 5 · simulator', 0.686, false, true]], 'F1 with each house held out once'),
      cap: 'Table 3 as a chart. Violet marks the simulator-trained model; it detected the fridge better in 4 of 5 houses.' },
    discussion: { svg: () => bars([
      ['Development house, real training', 0.781], ['Sealed house, real training', 0.297, true], ['Sealed house, simulator training', 0.686, false, true]],
      'F1: the development score did not transfer'), cap: 'Violet marks a model trained on simulated homes.' },
    'next-steps': { trio: true, cap: 'Next: more homes, a published baseline, a fresh sealed house, and safely collected data of my own.' },
  };
  const ids = ['abstract', 'background', 'system', 'method', 'development', 'final-test', 'cross-house', 'discussion', 'next-steps', 'references'];

  function svgBox(viewBox, label) {
    const svg = el('svg', { viewBox, role: 'img', 'aria-label': label });
    return svg;
  }
  function bars(rows, label) {
    const height = 46 * rows.length + 30;
    const svg = svgBox(`0 0 520 ${height}`, label);
    svg.append(el('text', { x: 0, y: 16, class: 'sub', style: 'font:600 13px var(--font, system-ui);fill:var(--quiet)' }, label));
    rows.forEach(([name, value, strong, sim], i) => {
      const y = 36 + i * 46;
      svg.append(el('text', { x: 0, y: y + 12, style: `font:${strong ? 700 : 500} 13px system-ui;fill:var(--ink)` }, name));
      svg.append(el('rect', { x: 0, y: y + 20, width: 440, height: 10, rx: 5, fill: 'var(--fill)' }));
      svg.append(el('rect', { x: 0, y: y + 20, width: Math.max(0.5, 440 * value), height: 10, rx: 5, fill: sim ? '#6e3fa3' : 'var(--green)', opacity: strong || sim ? 1 : 0.55 }));
      svg.append(el('text', { x: 520, y: y + 30, 'text-anchor': 'end', style: 'font:700 15px system-ui;fill:var(--ink);font-variant-numeric:tabular-nums' }, value.toFixed(3)));
    });
    return svg;
  }
  function splitDiagram() {
    const svg = svgBox('0 0 520 250', 'REFIT houses 1, 3 and 4 for training, house 2 for development, house 5 sealed for the final test');
    const houses = [['1', 'Training', 'var(--green)', 1], ['3', 'Training', 'var(--green)', 1], ['4', 'Training', 'var(--green)', 1],
      ['2', 'Development', 'var(--green)', 0.45], ['5', 'Sealed test', 'var(--ink)', 0]];
    houses.forEach(([n, role, color, fill], i) => {
      const x = 8 + i * 102, y = 60;
      svg.append(el('path', { d: `M${x},${y + 40} L${x + 44},${y} L${x + 88},${y + 40} V${y + 110} H${x} Z`,
        fill: fill ? color : 'var(--surface)', 'fill-opacity': fill || 1, stroke: color, 'stroke-width': 2.5, 'stroke-linejoin': 'round' }));
      svg.append(el('text', { x: x + 44, y: y + 88, 'text-anchor': 'middle', style: `font:700 26px system-ui;fill:${fill === 1 ? '#fff' : 'var(--ink)'}` }, n));
      svg.append(el('text', { x: x + 44, y: y + 140, 'text-anchor': 'middle', style: 'font:600 12px system-ui;fill:var(--quiet)' }, role));
    });
    svg.append(el('text', { x: 8, y: 30, style: 'font:600 13px system-ui;fill:var(--quiet)' }, 'REFIT houses, ~10,000 readings each'));
    return svg;
  }
  function figureNode(spec) {
    const fig = document.createElement('figure');
    const plate = document.createElement('div');
    plate.className = 'plate';
    if (spec.img) {
      const img = document.createElement('img');
      Object.assign(img, { src: spec.img, alt: spec.alt });
      plate.append(img);
    } else if (spec.wire) {
      const svg = el('svg', { role: 'img', 'aria-label': 'Three appliance signals merging into one total line' });
      plate.classList.add('wire');
      buildWire(svg, false);
      plate.append(svg);
    } else if (spec.svg) {
      plate.append(spec.svg());
    } else if (spec.trio) {
      const row = document.createElement('div');
      row.style.cssText = 'display:grid;grid-template-columns:repeat(3,1fr);gap:12px;align-items:end';
      for (const name of ['refrigerator', 'lamp', 'washing_machine']) {
        const img = document.createElement('img');
        Object.assign(img, { src: `img/${name}.webp`, alt: '' });
        img.style.cssText = 'max-height:160px;width:100%;object-fit:contain';
        row.append(img);
      }
      plate.append(row);
    }
    const cap = document.createElement('figcaption');
    cap.textContent = spec.cap;
    fig.append(plate, cap);
    return fig;
  }

  const article = paper.querySelector('article');
  const pinned = paper.querySelector('.pinned');
  article.setAttribute('aria-busy', 'true');
  fetch('report.md').then(r => { if (!r.ok) throw new Error(r.status); return r.text(); }).then(md => {
    const body = md.slice(md.indexOf('\n## '));
    const html = window.marked.parse(body);
    const holder = document.createElement('div');
    holder.innerHTML = html;
    article.replaceChildren();
    let section = null, index = -1;
    for (const node of [...holder.childNodes]) {
      if (node.nodeName === 'H2') {
        index += 1;
        section = document.createElement('section');
        section.id = ids[index] || `section-${index}`;
        section.append(node);
        const spec = figures[section.id];
        if (spec) {
          const inline = figureNode(spec);
          inline.className = 'inline-figure';
          section.append(inline);
        }
        article.append(section);
      } else if (section) {
        section.append(node);
      }
    }
    let current = null;
    const show = id => {
      const spec = figures[id];
      if (!spec || id === current) return;
      current = id;
      pinned.classList.add('swap');
      setTimeout(() => { pinned.replaceChildren(figureNode(spec)); pinned.classList.remove('swap'); }, reduced ? 0 : 180);
    };
    show('abstract');
    const observer = new IntersectionObserver(entries => {
      for (const entry of entries) if (entry.isIntersecting) show(entry.target.id);
    }, { rootMargin: '-35% 0px -60% 0px' });
    article.querySelectorAll('section').forEach(s => observer.observe(s));
    article.removeAttribute('aria-busy');
    if (location.hash) document.querySelector(location.hash)?.scrollIntoView();
  }).catch(() => {
    article.removeAttribute('aria-busy');
    article.innerHTML = '<p>The paper could not load here. Read <a href="report.md">report.md</a> or download the <a href="report.pdf">PDF</a>.</p>';
  });
})();
