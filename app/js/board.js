// Géométrie de la plaque Wish Board 106 + rendu des fils/résistances/puces (extrait tel quel de l'ancienne app)
function buildBoardGeometry() {
  const POS = {
    N1: [46, 32], T1L: [88, 74], T1R: [172, 74],
    N2: [256, 32], T2L: [298, 74], T2R: [382, 74],
    N3: [466, 32], T3L: [508, 74], T3R: [592, 74],
    N4: [676, 32]
  };
  const Y0 = 240, PAD = 8, P = 14.0, ROWS = 63, GAP = 10;

  let stripSvg = "";
  let dotsSvg = "";

  // Trous bus haut
  for (let half of ["L", "R"]) {
    for (let line = 1; line <= 2; line++) {
      for (let p = 1; p <= 25; p++) {
        const h = HOLE_MAP.get(`TOP-${half}${line}-${p}`);
        if (h) dotsSvg += `<circle cx="${h.x}" cy="${h.y}" r="2.2"/>`;
      }
    }
  }

  // Bandes et rails
  for (let [s, [x, w]] of Object.entries(POS)) {
    stripSvg += `<rect x="${x}" y="${Y0}" width="${w}" height="${2*PAD + ROWS*P}" rx="3" fill="#f1f1ee"/>`;
    if (s.startsWith("N")) {
      const my = Y0 + PAD + (ROWS - 32.5) * P;
      stripSvg += `<text x="${x + w/2}" y="${my}" font-size="10" font-weight="700" fill="#b91c1c" text-anchor="middle" font-family="Arial">W</text>`;
      stripSvg += `<text x="${x + w/2}" y="${Y0 - 6}" font-size="11" fill="#bbb" text-anchor="middle" font-family="Arial">rail ${s}</text>`;
    } else {
      const isLeft = s.endsWith("L");
      const sideLetters = isLeft ? "fghij" : "abcde";
      stripSvg += `<text x="${x + w/2}" y="${Y0 - 19}" font-size="11" fill="#bbb" text-anchor="middle" font-family="Arial">${isLeft ? "f–j" : "a–e"}</text>`;
      for (let ci = 0; ci < 5; ci++) {
        const lx = x + PAD + ci * P + P / 2.0;
        stripSvg += `<text x="${lx}" y="${Y0 - 4}" font-size="11" font-weight="700" fill="#f59e0b" text-anchor="middle" font-family="Arial">${sideLetters[ci]}</text>`;
      }
      if (isLeft) {
        for (let rr of [1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60]) {
          const ry = Y0 + PAD + (ROWS - rr) * P + P / 2.0;
          stripSvg += `<text x="${x + w + GAP/2}" y="${ry + 3}" font-size="8" font-weight="700" fill="#6b7280" text-anchor="middle" font-family="Arial">${rr}</text>`;
        }
        const xr = POS[s.slice(0, 2) + "R"][0], wr = POS[s.slice(0, 2) + "R"][1];
        stripSvg += `<text x="${(x + xr + wr)/2}" y="${Y0 - 34}" font-size="13" font-weight="700" fill="#ddd" text-anchor="middle" font-family="Arial">bloc ${s.slice(0, 2)}</text>`;
      }
    }
  }

  HOLES.forEach(h => {
    if (h.t === "strip" || h.t === "rail") dotsSvg += `<circle cx="${h.x}" cy="${h.y}" r="2.2"/>`;
  });

  // Bornes de connexion en haut
  let connSvg = "";
  const connsData = [
    { id: "BANANE_ROUGE", label: "rouge", x: 120, col: "#d62828", type: "banane" },
    { id: "BANANE_NOIRE", label: "noire", x: 180, col: "#2b2b2b", type: "banane" },
    { id: "BNC1", label: "BNC 1 (GBF)", x: 285, col: "#cfd2d6", type: "bnc" },
    { id: "BNC2", label: "BNC 2 (Oscillo)", x: 375, col: "#cfd2d6", type: "bnc" },
    { id: "VB", label: "VB (−15V)", x: 475, col: "#1d4ed8", type: "banane" },
    { id: "VC", label: "VC (+15V)", x: 575, col: "#d62828", type: "banane" },
    { id: "MASSE", label: "MASSE (0V)", x: 675, col: "#0ea5a4", type: "banane" }
  ];

  const LIVE = new Set(["BANANE_ROUGE", "BANANE_NOIRE", "BNC1", "BNC2", "VB", "VC", "MASSE"]);   // les 7 connecteurs de la plaque, tous câblables
  let connHits = "";
  connsData.forEach(c => {
    connSvg += `<circle id="anchor-${c.id}" cx="${c.x}" cy="60" r="1" fill="none"/>`;
    if (LIVE.has(c.id)) connHits += `<circle class="conn-hit" data-conn="${c.id}" cx="${c.x}" cy="60" r="${c.type === "bnc" ? 30 : 24}" fill="transparent"><title>${c.label} : clique pour brancher un câble</title></circle>`;
    if (c.type === "bnc") {
      connSvg += `<circle cx="${c.x}" cy="60" r="27" fill="#cfd2d6" stroke="#7b8087" stroke-width="3"/>`;
      connSvg += `<circle cx="${c.x}" cy="60" r="16" fill="#9aa0a6"/><circle cx="${c.x}" cy="60" r="6" fill="#222"/>`;
      connSvg += `<text x="${c.x}" y="20" font-size="11" font-weight="700" fill="#ddd" text-anchor="middle" font-family="Arial">${c.label}</text>`;
    } else {
      connSvg += `<circle cx="${c.x}" cy="60" r="19" fill="${c.col}" stroke="#ddd" stroke-width="2"/><circle cx="${c.x}" cy="60" r="7" fill="#111"/>`;
      connSvg += `<text x="${c.x}" y="20" font-size="11" font-weight="700" fill="#ddd" text-anchor="middle" font-family="Arial">${c.label}</text>`;
    }
  });

  HOLES.filter(h => h.t === "conn").forEach(h => {
    connSvg += `<circle cx="${h.x}" cy="${h.y}" r="7" fill="none" stroke="#bbb" stroke-width="3"/>`;
    if (h.id.includes("core")) connSvg += `<text x="${h.x}" y="${h.y + 20}" font-size="10" fill="#ccc" text-anchor="middle" font-family="Arial">âme</text>`;
    if (h.id.includes("shield")) connSvg += `<text x="${h.x}" y="${h.y + 20}" font-size="10" fill="#ccc" text-anchor="middle" font-family="Arial">blindage</text>`;
    if (h.id === "VB.main") connSvg += `<text x="${h.x + 12}" y="${h.y + 5}" font-size="14" font-weight="700" fill="#facc15" font-family="Arial">Vb</text>`;
    if (h.id === "VC.main") connSvg += `<text x="${h.x + 12}" y="${h.y + 5}" font-size="14" font-weight="700" fill="#facc15" font-family="Arial">Vc</text>`;
    if (h.id === "MASSE.main") connSvg += `<text x="${h.x + 12}" y="${h.y + 5}" font-size="14" font-weight="700" fill="#facc15" font-family="Arial">⏚</text>`;
  });

  document.getElementById("svg-strips").innerHTML = stripSvg;
  document.getElementById("svg-holes-dots").innerHTML = dotsSvg;
  document.getElementById("svg-connectors").innerHTML = connSvg;

  // Trous interactifs
  let targets = "";
  HOLES.forEach(h => {
    targets += `<circle cx="${h.x}" cy="${h.y}" r="6" class="h-target" data-id="${h.id}"/>`;
  });
  document.getElementById("svg-targets").innerHTML = targets + connHits;

  // Injection du SVG dans le conteneur Split
  const host = document.getElementById("board-host-split");
  const masterSvg = document.getElementById("master-board-svg");
  host.appendChild(masterSvg);
}

// 2. RENDU DES ÉLÉMENTS DE CÂBLAGE SUR LA PLAQUE
function wirePath(p1, p2) {
  const dx = p2.x - p1.x;
  const dy = p2.y - p1.y;
  let c1, c2;
  if (Math.abs(dx) < 60) {
    const bulge = -(24 + 0.05 * Math.abs(dy));
    c1 = { x: p1.x + bulge, y: p1.y };
    c2 = { x: p2.x + bulge, y: p2.y };
  } else {
    c1 = { x: p1.x, y: p1.y - 70 };
    c2 = { x: p2.x, y: p2.y - 70 };
  }
  const d = `M ${p1.x.toFixed(1)},${p1.y.toFixed(1)} C ${c1.x.toFixed(1)},${c1.y.toFixed(1)} ${c2.x.toFixed(1)},${c2.y.toFixed(1)} ${p2.x.toFixed(1)},${p2.y.toFixed(1)}`;
  const mid = {
    x: (p1.x + 3 * c1.x + 3 * c2.x + p2.x) / 8.0,
    y: (p1.y + 3 * c1.y + 3 * c2.y + p2.y) / 8.0
  };
  return { d, mid };
}

function renderPlacedElements() {
  // Fils
  let wSvg = "";
  state.placedWires.forEach((w, idx) => {
    const h1 = HOLE_MAP.get(w.de), h2 = HOLE_MAP.get(w.vers);
    if (!h1 || !h2) return;
    const { d, mid } = wirePath(h1, h2);
    const col = WIRE_COLORS[w.couleur] || "#999";
    wSvg += `<path d="${d}" fill="none" stroke="#fff" stroke-width="8" stroke-linecap="round" opacity=".85"/>`;
    wSvg += `<path d="${d}" fill="none" stroke="${col}" stroke-width="5" stroke-linecap="round"/>`;
    wSvg += `<circle cx="${h1.x}" cy="${h1.y}" r="5" fill="${col}" stroke="#fff" stroke-width="1.5"/>`;
    wSvg += `<circle cx="${h2.x}" cy="${h2.y}" r="5" fill="${col}" stroke="#fff" stroke-width="1.5"/>`;
    wSvg += `<circle cx="${mid.x}" cy="${mid.y}" r="10" fill="#0b3d91" stroke="#fff" stroke-width="2"/>`;
    wSvg += `<text x="${mid.x}" y="${mid.y + 4}" font-size="11" font-weight="700" fill="#fff" text-anchor="middle" font-family="Arial">${idx + 1}</text>`;
  });
  document.getElementById("svg-wires").innerHTML = wSvg;

  // Résistances
  let rSvg = "";
  state.placedComps.filter(c => c.type === "led").forEach(l => {
    const h1 = HOLE_MAP.get(l.a), h2 = HOLE_MAP.get(l.k);
    if (!h1 || !h2) return;
    const mx = (h1.x + h2.x) / 2.0, my = (h1.y + h2.y) / 2.0, id = String(l.name).replace(/[^\w-]/g, "_");
    rSvg += `<line x1="${h1.x}" y1="${h1.y}" x2="${mx}" y2="${my}" stroke="#bbb" stroke-width="3"/><line x1="${mx}" y1="${my}" x2="${h2.x}" y2="${h2.y}" stroke="#888" stroke-width="2"/>`;
    rSvg += `<circle id="led-glow-${id}" class="led-glow" cx="${mx}" cy="${my}" r="17" fill="#ff2a2a" opacity="0"/>`;
    rSvg += `<circle id="led-body-${id}" cx="${mx}" cy="${my}" r="8" fill="#7f1d1d" stroke="#fecaca" stroke-width="1.5"/>`;
    rSvg += `<text x="${h1.x + (h1.x <= h2.x ? -9 : 9)}" y="${h1.y + 4}" font-size="11" font-weight="700" fill="#fca5a5" text-anchor="middle" font-family="Arial">+</text>`;
    rSvg += `<text x="${Math.max(h1.x, h2.x) + 14}" y="${my + 4}" font-size="11" font-weight="700" fill="#fca5a5" font-family="Arial">${l.name}</text>`;
    rSvg += `<circle cx="${h1.x}" cy="${h1.y}" r="4" fill="#333" stroke="#fff" stroke-width="1.5"/><circle cx="${h2.x}" cy="${h2.y}" r="4" fill="#333" stroke="#fff" stroke-width="1.5"/>`;
  });
  state.placedComps.filter(c => c.type !== "led").forEach(r => {
    const h1 = HOLE_MAP.get(r.a), h2 = HOLE_MAP.get(r.b);
    if (!h1 || !h2) return;
    const mx = (h1.x + h2.x) / 2.0, my = (h1.y + h2.y) / 2.0;
    const ang = Math.atan2(h2.y - h1.y, h2.x - h1.x) * 180 / Math.PI;
    const ln = Math.hypot(h2.x - h1.x, h2.y - h1.y);

    rSvg += `<line x1="${h1.x}" y1="${h1.y}" x2="${h2.x}" y2="${h2.y}" stroke="#888" stroke-width="3"/>`;
    rSvg += `<g transform="translate(${mx},${my}) rotate(${ang})"><rect x="${-ln * 0.3}" y="-6" width="${ln * 0.6}" height="12" rx="4" fill="#d9b77e" stroke="#8a6d3b" stroke-width="1.5"/></g>`;
    rSvg += `<text x="${Math.max(h1.x, h2.x) + 12}" y="${my + 4}" font-size="11" font-weight="700" fill="#facc15" font-family="Arial">${r.name} (${r.etiquette})</text>`;
    rSvg += `<circle cx="${h1.x}" cy="${h1.y}" r="4" fill="#333" stroke="#fff" stroke-width="1.5"/>`;
    rSvg += `<circle cx="${h2.x}" cy="${h2.y}" r="4" fill="#333" stroke="#fff" stroke-width="1.5"/>`;
  });
  document.getElementById("svg-resistors").innerHTML = rSvg;

  // Puces
  let cSvg = "";
  state.placedChips.forEach(ch => {
    const spec = CHIPS_LIB[ch.modele];
    if (!spec) return;
    const n = spec.dip, half = Math.floor(n / 2);
    const blk = ch.bloc, r1 = ch.rangee_broche1;
    const pins = {};
    for (let p = 1; p <= n; p++) {
      let letCode = p <= half ? "j" : "a";
      let rowCode = p <= half ? r1 - (p - 1) : r1 - (half - 1) + (p - half - 1);
      const h = HOLE_MAP.get(`${blk}${letCode}${rowCode}`);
      if (h) pins[p] = h;
    }
    const xs = Object.values(pins).map(h => h.x), ys = Object.values(pins).map(h => h.y);
    if (!xs.length) return;
    const x0 = Math.min(...xs) - 10, x1 = Math.max(...xs) + 10;
    const y0 = Math.min(...ys) - 10, y1 = Math.max(...ys) + 10;
    const cx = (x0 + x1) / 2.0, cy = (y0 + y1) / 2.0;

    cSvg += `<rect x="${x0}" y="${y0}" width="${x1 - x0}" height="${y1 - y0}" rx="3" fill="#2b2f36" stroke="#0b0c0e" stroke-width="2"/>`;
    cSvg += `<path d="M ${cx - 7},${y0} a 7,7 0 0 0 14,0 z" fill="#17191c"/>`;
    cSvg += `<text transform="translate(${cx},${cy}) rotate(-90)" font-size="12" font-weight="700" fill="#e5e7eb" text-anchor="middle" font-family="Arial">${ch.ref} ${ch.modele}</text>`;
    for (let [p, h] of Object.entries(pins)) {
      const left = h.x < cx;
      cSvg += `<circle cx="${h.x}" cy="${h.y}" r="3.4" fill="#e5e7eb"/>`;
      cSvg += `<text x="${h.x + (left ? -5 : 5)}" y="${h.y + 3}" font-size="8" font-weight="700" fill="#fde68a" text-anchor="${left ? 'end' : 'start'}" font-family="Arial">${p}</text>`;
    }
  });
  document.getElementById("svg-chips").innerHTML = cSvg;

  renderLeads();
  updatePlacedTable();
  updateElectricalChecklist();
  triggerScopeRedraw();
}


// 3. PETITS CÂBLES DE LA PLAQUE : sous chaque âme / blindage / douille, un cordon pend déjà ; il suffit d'enficher son bout dans un trou.
// Clic sur le bout qui pend, puis clic sur le trou : le fil est posé avec la couleur du cordon (le cordon disparaît tant qu'un fil part de ce trou).
const LEADS = {
  "BANANE_ROUGE.main": { dx: -10, col: "rouge", nom: "banane rouge (gauche)" }, "BANANE_NOIRE.main": { dx: 10, col: "noir", nom: "banane noire (gauche)" },
  "BNC1.core": { dx: -16, col: "rouge", nom: "âme BNC 1" }, "BNC1.shield": { dx: 16, col: "noir", nom: "blindage BNC 1" },
  "BNC2.core": { dx: -16, col: "orange", nom: "âme BNC 2" }, "BNC2.shield": { dx: 16, col: "noir", nom: "blindage BNC 2" },
  "VB.main": { dx: 0, col: "bleu", nom: "douille VB (−15 V)" }, "VC.main": { dx: 0, col: "rouge", nom: "douille VC (+15 V)" }, "MASSE.main": { dx: 0, col: "turquoise", nom: "douille MASSE (0 V)" },
};
function renderLeads() {
  const svg = document.getElementById("master-board-svg"); if (!svg) return;
  let g = document.getElementById("svg-leads");
  if (!g) { g = document.createElementNS("http://www.w3.org/2000/svg", "g"); g.id = "svg-leads"; svg.appendChild(g); }
  let s = "";
  Object.entries(LEADS).forEach(([hid, L]) => {
    const h = HOLE_MAP.get(hid); if (!h) return;
    if (state.placedWires.some(w => w.de === hid || w.vers === hid)) return;
    const col = WIRE_COLORS[L.col], ex = h.x + L.dx, ey = h.y + 56;
    const d = `M ${h.x},${h.y} C ${h.x},${h.y + 22} ${ex + L.dx * 1.2},${h.y + 22} ${ex},${ey}`;
    s += `<g class="lead"><path d="${d}" fill="none" stroke="#0b0e14" stroke-width="7" stroke-linecap="round"/><path d="${d}" fill="none" stroke="${col}" stroke-width="4.5" stroke-linecap="round"/>` +
         `<circle cx="${ex}" cy="${ey}" r="6" fill="${col}" stroke="#fff" stroke-width="1.8"/>` +
         `<circle class="lead-hit" data-lead="${hid}" cx="${ex}" cy="${ey}" r="11" fill="transparent"><title>${L.nom} : clique ce bout, puis le trou de la plaque où l'enficher</title></circle></g>`;
  });
  g.innerHTML = s;
}

// LED allumées : luminosité ∝ courant. En dessous de ~25 Hz la LED clignote en temps réel (comme sur la table) ;
// au-dessus, l'œil ne voit plus le clignotement : on affiche la luminosité moyenne.
const Leds = (() => {
  let an = null, raf = 0, t0 = performance.now();
  const lum = i => Math.max(0, Math.min(1, i / 0.01));        // 10 mA = pleine luminosité
  function paint(name, i) {
    const id = String(name).replace(/[^\w-]/g, "_"), g = document.getElementById("led-glow-" + id), b = document.getElementById("led-body-" + id);
    if (!g || !b) return;
    const L = i > 3e-4 ? 0.25 + 0.75 * lum(i) : 0;
    g.setAttribute("opacity", (0.85 * L).toFixed(3)); b.setAttribute("fill", L ? `rgb(${Math.round(150 + 105 * L)},${Math.round(30 + 60 * L)},${Math.round(30 + 60 * L)})` : "#7f1d1d");
  }
  function frame() {
    raf = 0; if (!an || !an.rec) return;
    const rec = an.rec, slow = !rec.dc && rec.P > 0 && rec.T >= 1 / 25;
    Object.entries(rec.leds).forEach(([n, l]) => {
      if (!slow) { paint(n, l.avg); return; }
      const tm = ((performance.now() - t0) / 1000) % rec.P, t = rec.t; let k = 0, hi = t.length - 1;
      while (hi - k > 1) { const m = (k + hi) >> 1; if (t[m] <= tm) k = m; else hi = m; }
      paint(n, l.i[k]);
    });
    if (slow && Object.keys(rec.leds).length) raf = requestAnimationFrame(frame);
  }
  function update(a) { an = a; if (raf) cancelAnimationFrame(raf); raf = 0; frame(); }
  return { update };
})();
