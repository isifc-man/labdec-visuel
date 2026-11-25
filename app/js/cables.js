// Câbles d'appareils posés PAR L'ÉLÈVE : BNC (GBF/oscillo ↔ BNC1/BNC2 de la plaque ou entre appareils) et bananes (alim ↔ VB/VC/MASSE).
// On clique une extrémité puis l'autre : une prise d'appareil (sur la face) ou une douille de la plaque.
// Un câble = {id, de, vers, nom}, mêmes champs que `cables` des fichiers montage : le moteur les lit tels quels.
const Cables = (() => {
  const NAMESPACE = "http://www.w3.org/2000/svg";
  const DEV = /^(scope|gbf|psu)\./;
  const UNUSED = { "gbf.cal": "Cal", "gbf.ext_trig": "Ext Trig", "psu.gnd": "borne ⏚ châssis" };
  const isDev = e => DEV.test(e);
  const kindOf = e => isDev(e) ? (/^psu\./.test(e) ? "banane" : "bnc") : (/^BNC/.test(e) ? "bnc" : "banane");
  const connOfHole = id => { const h = HOLE_MAP.get(id); return h && h.t === "conn" ? id.split(".")[0] : null; };
  const CONN_COL = { VB: "#3b82f6", VC: "#ef4444", MASSE: "#14b8a6", BANANE_ROUGE: "#ef4444", BANANE_NOIRE: "#1f2937" };
  const sameEnds = (a, b, c, d) => (a === c && b === d) || (a === d && b === c);
  const LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";

  function label(e) {
    const names = { "gbf.out1": "sortie 1 du GBF", "gbf.sync_out": "Sync du GBF", "scope.ch1": "voie 1 de l'oscillo", "scope.ch2": "voie 2 de l'oscillo", "scope.ext": "Ext Trig de l'oscillo" };
    if (names[e]) return names[e];
    let m = e.match(/^psu\.ch(\d)_(plus|moins)$/);
    if (m) return `alim voie ${m[1]} ${m[2] === "plus" ? "+" : "−"}`;
    return { BANANE_ROUGE: "banane rouge de la plaque (gauche)", BANANE_NOIRE: "banane noire de la plaque (gauche)", BNC1: "BNC 1 de la plaque", BNC2: "BNC 2 de la plaque", VB: "douille VB", VC: "douille VC", MASSE: "douille MASSE" }[e] || e;
  }
  function say(txt, cls) {
    const el = document.getElementById("cable-msg"); if (!el) return;
    el.textContent = txt || ""; el.className = cls || "";
  }
  function nextId() { const used = new Set(state.placedCables.map(c => c.id)); for (const l of LETTERS) if (!used.has(l)) return l; return "C" + (state.placedCables.length + 1); }
  const count = e => state.placedCables.filter(c => c.de === e || c.vers === e).length;

  function mark() {
    document.querySelectorAll(".it-port.armedcable").forEach(p => p.classList.remove("armedcable"));
    if (state.cableFirst && isDev(state.cableFirst)) document.querySelectorAll(`.it-port[data-port="${state.cableFirst}"]`).forEach(p => p.classList.add("armedcable"));
    redraw();
  }
  // Câble décroché par un double-clic pour être déplacé : on le remet tel quel si le déplacement est annulé ou refusé.
  let _moved = null;   // { c: câble d'origine, i: sa position, list: le tableau d'où on l'a sorti }
  function restore() {
    if (_moved && _moved.list === state.placedCables) state.placedCables.splice(Math.min(_moved.i, state.placedCables.length), 0, _moved.c);
    _moved = null;
  }
  function cancel() { const had = !!_moved; restore(); state.cableFirst = null; mark(); say(""); if (had) refreshAll(); }

  // Une extrémité vient d'être cliquée (prise d'appareil ou douille de la plaque)
  function pick(end) {
    if (state.tool !== "cable") { state.tool = "cable"; state.armedRef = null; document.querySelectorAll(".t-btn").forEach(b => b.classList.toggle("active", b.dataset.tool === "cable")); if (typeof syncToolbar === "function") syncToolbar(); }
    if (UNUSED[end]) { say(`« ${UNUSED[end]} » n'est utilisée dans aucun des TP.`, "warn"); return; }
    if (!state.cableFirst) {
      state.cableFirst = end; mark();
      say(`Câble ${kindOf(end) === "bnc" ? "BNC" : "banane"} : ${label(end)} → clique l'autre extrémité (Échap pour annuler).`);
      return;
    }
    const a = state.cableFirst, b = end;
    state.cableFirst = null;
    const refuse = txt => { const had = !!_moved; restore(); mark(); say(txt, "warn"); if (had) refreshAll(); };   // un déplacement refusé remet le câble d'origine
    if (a === b) { const had = !!_moved; restore(); mark(); say(""); if (had) refreshAll(); return; }
    if (!isDev(a) && !isDev(b)) { refuse("Deux douilles de la plaque ne se relient pas par un câble : utilise un fil sur la plaque."); return; }
    if (kindOf(a) !== kindOf(b)) { refuse(`Un câble BNC ne se branche pas sur une douille banane (${label(a)} / ${label(b)}).`); return; }
    if (state.placedCables.some(c => sameEnds(c.de, c.vers, a, b))) { refuse("Ce câble existe déjà."); return; }
    for (const e of [a, b]) {
      // sortie 1 du GBF : adaptateur en T (2 BNC) ; douilles banane : fiches empilables (2) ; autre BNC : 1 seul câble
      const lim = e === "gbf.out1" || kindOf(e) === "banane" ? 2 : 1;
      if (count(e) >= lim) { refuse(`${label(e)} a déjà ${lim === 2 ? "deux câbles (c'est plein)" : "un câble"} : retire-en un avec la gomme.`); return; }
    }
    const old = _moved && _moved.list === state.placedCables ? _moved.c : null;   // câble déplacé : il garde sa lettre, sa couleur et sa place dans la liste
    const id = old ? old.id : nextId(), kind = kindOf(a);
    const nc = { id, de: a, vers: b, nom: kind === "bnc" ? "câble BNC–BNC" : "câble banane" };
    nc.couleur = old ? old.couleur : state.cableColorSet ? state.wireColor : defaultColor(nc);
    if (old) state.placedCables.splice(Math.min(_moved.i, state.placedCables.length), 0, nc); else state.placedCables.push(nc);
    _moved = null;
    mark();
    say(`Câble ${id} posé : ${label(a)} ↔ ${label(b)}.${(a === "gbf.out1" || b === "gbf.out1") && count("gbf.out1") === 2 ? " (adaptateur en T sur la sortie du GBF)" : ""}`, "ok");
    refreshAll();
  }
  function clickPort(end) { if (state.tool === "delete") { if (!removeAt(end)) say("Aucun câble sur cette prise.", "warn"); else say("Câble retiré.", "ok"); } else pick(end); }
  function pickHole(hid) { const c = connOfHole(hid); if (c) pick(c); else say("Mode câble : clique une prise d'appareil ou une douille BNC / banane de la plaque (en haut ; les 2 bananes rouge et noire de gauche se câblent aussi).", "warn"); }

  function removeAt(end) {
    const n = state.placedCables.length;
    state.placedCables = state.placedCables.filter(c => c.de !== end && c.vers !== end);
    if (state.placedCables.length !== n) { mark(); refreshAll(); return true; }
    return false;
  }
  function removeIndex(i) { state.placedCables.splice(i, 1); mark(); refreshAll(); }

  // ---- câbles DESSINÉS : de la prise de l'appareil jusqu'à la vraie douille de la plaque ----
  // Une couche SVG posée sur la zone centrale (elle défile avec elle). Les bouts de câble sont lus dans la page (position réelle des prises).
  const BNC_PALETTE = ["jaune", "vert", "orange", "bleu", "turquoise", "blanc"];
  function defaultColor(c) {
    if (kindOf(c.de) === "bnc") return BNC_PALETTE[(LETTERS.indexOf(c.id) < 0 ? 0 : LETTERS.indexOf(c.id)) % BNC_PALETTE.length];
    const e = [c.de, c.vers].join(" ");
    return /_plus/.test(e) && /_moins/.test(e) ? "jaune" : /_plus/.test(e) ? "rouge" : /_moins/.test(e) ? "noir" : "rouge";
  }
  const hexOf = c => (typeof WIRE_COLORS !== "undefined" && WIRE_COLORS[c]) || "#38bdf8";

  function layer() {
    const host = document.getElementById("lv-centre"); if (!host) return null;
    let svg = document.getElementById("cable-layer");
    if (!svg) { svg = document.createElementNS(NAMESPACE, "svg"); svg.id = "cable-layer"; host.appendChild(svg); }
    return svg;
  }
  function endPt(e) {
    const el = isDev(e) ? document.querySelector(`.it-port[data-port="${e}"]`) : document.getElementById("anchor-" + e);
    const host = document.getElementById("lv-centre");
    if (!el || !host) return null;
    const r = el.getBoundingClientRect(), c = host.getBoundingClientRect();
    if (!r.width && !r.height) return null;
    return { x: r.left - c.left + host.scrollLeft + r.width / 2, y: r.top - c.top + host.scrollTop + r.height / 2 };
  }
  function curve(a, b) {
    const dy = Math.abs(b.y - a.y), d = Math.max(60, dy * 0.45), k = dy < 50 ? 1.6 : 1;
    return `M${a.x.toFixed(1)},${a.y.toFixed(1)} C${a.x.toFixed(1)},${(a.y + d * k).toFixed(1)} ${b.x.toFixed(1)},${(b.y - (dy < 50 ? -d * k : d)).toFixed(1)} ${b.x.toFixed(1)},${b.y.toFixed(1)}`;
  }
  const mid = (a, b) => { const dy = Math.abs(b.y - a.y), d = Math.max(60, dy * 0.45), k = dy < 50 ? 1.6 : 1, c1y = a.y + d * k, c2y = b.y - (dy < 50 ? -d * k : d);
    return { x: (a.x + 3 * a.x + 3 * b.x + b.x) / 8, y: (a.y + 3 * c1y + 3 * c2y + b.y) / 8 }; };
  const plug = (p, col, bnc) => `<circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="${bnc ? 8 : 6.5}" fill="${col}" stroke="#0b0e14" stroke-width="2.5"/><circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="${bnc ? 3.2 : 2.4}" fill="#0b0e14"/>`;

  let _raf = 0;
  function redraw() { if (_raf) return; _raf = requestAnimationFrame(() => { _raf = 0; render(); }); }
  function render() {
    const svg = layer(), host = document.getElementById("lv-centre"); if (!svg || !host) return;
    svg.setAttribute("width", host.scrollWidth); svg.setAttribute("height", host.scrollHeight);
    svg.classList.toggle("erasing", state.tool === "delete");
    let s = "";
    state.placedCables.forEach((c, i) => {
      const a = endPt(c.de), b = endPt(c.vers); if (!a || !b) return;
      const col = hexOf(c.couleur || defaultColor(c)), d = curve(a, b), bnc = kindOf(c.de) === "bnc", m = mid(a, b), w = bnc ? 6 : 5;
      s += `<g><path class="cab" data-i="${i}" d="${d}" fill="none" stroke="#0b0e14" stroke-width="${w + 4}" stroke-linecap="round"/>` +
           `<path d="${d}" fill="none" stroke="${col}" stroke-width="${w}" stroke-linecap="round" pointer-events="none"/>` +
           (bnc ? `<path d="${d}" fill="none" stroke="rgba(255,255,255,.28)" stroke-width="1.5" stroke-dasharray="2 9" pointer-events="none"/>` : "") +
           plug(a, col, bnc) + plug(b, col, bnc) +
           `<circle cx="${m.x.toFixed(1)}" cy="${m.y.toFixed(1)}" r="9" fill="#0b3d91" stroke="#fff" stroke-width="2"/><text x="${m.x.toFixed(1)}" y="${(m.y + 4).toFixed(1)}" font-size="11" font-weight="700" fill="#fff" text-anchor="middle" font-family="Arial">${c.id}</text></g>`;
    });
    if (state.cableFirst) {
      const f = endPt(state.cableFirst);
      if (f) { s += `<circle cx="${f.x}" cy="${f.y}" r="13" fill="none" stroke="#facc15" stroke-width="3" stroke-dasharray="4 3"/>`;
        if (_mouse) s += `<path id="rubber" d="${curve(f, _mouse)}" fill="none" stroke="#facc15" stroke-width="3" stroke-dasharray="7 6" pointer-events="none"/>`; }
    }
    svg.innerHTML = s;
    svg.querySelectorAll("path.cab").forEach(p => p.onclick = () => { if (state.tool === "delete") removeIndex(+p.dataset.i); });
  }
  let _mouse = null;
  function trackMouse(e) {
    if (!state.cableFirst) { if (_mouse) { _mouse = null; } return; }
    const host = document.getElementById("lv-centre"), c = host.getBoundingClientRect();
    _mouse = { x: e.clientX - c.left + host.scrollLeft, y: e.clientY - c.top + host.scrollTop };
    const f = endPt(state.cableFirst), r = document.getElementById("rubber");
    if (f && r) r.setAttribute("d", curve(f, _mouse)); else redraw();
  }
  function clickConn(name) { if (state.tool === "delete") { if (removeAt(name)) say("Câble retiré.", "ok"); else say("Aucun câble sur cette douille.", "warn"); } else pick(name); }

  // ---- déplacer un câble déjà posé : double-clic dessus ----
  // La couche des câbles laisse passer les clics (sinon elle masquerait les prises) : on cherche donc le câble le plus proche du clic par le calcul.
  // Le bout le plus proche du clic est décroché ; l'autre bout reste armé : un clic sur la nouvelle prise rebranche le câble (même lettre, même couleur).
  function liftAt(clientX, clientY) {
    const host = document.getElementById("lv-centre"); if (!host || state.tool === "delete") return false;
    restore();   // un autre câble était déjà décroché : on le remet avant de chercher
    const r = host.getBoundingClientRect(), p = { x: clientX - r.left + host.scrollLeft, y: clientY - r.top + host.scrollTop };
    let best = null;
    state.placedCables.forEach((c, i) => {
      const a = endPt(c.de), b = endPt(c.vers); if (!a || !b) return;
      const dy = Math.abs(b.y - a.y), d = Math.max(60, dy * 0.45), k = dy < 50 ? 1.6 : 1;
      const c1 = { x: a.x, y: a.y + d * k }, c2 = { x: b.x, y: b.y - (dy < 50 ? -d * k : d) };
      for (let t = 0; t <= 1.0001; t += 0.02) {
        const u = 1 - t, x = u * u * u * a.x + 3 * u * u * t * c1.x + 3 * u * t * t * c2.x + t * t * t * b.x, y = u * u * u * a.y + 3 * u * u * t * c1.y + 3 * u * t * t * c2.y + t * t * t * b.y;
        const dist = Math.hypot(x - p.x, y - p.y);
        if (dist < 14 && (!best || dist < best.dist)) best = { i, dist, a, b };
      }
    });
    if (!best) return false;
    const c = state.placedCables[best.i];
    const nearA = Math.hypot(p.x - best.a.x, p.y - best.a.y) <= Math.hypot(p.x - best.b.x, p.y - best.b.y);
    state.placedCables.splice(best.i, 1);
    _moved = { c, i: best.i, list: state.placedCables };
    if (state.tool !== "cable") { state.tool = "cable"; state.armedRef = null; document.querySelectorAll(".t-btn").forEach(b => b.classList.toggle("active", b.dataset.tool === "cable")); if (typeof syncToolbar === "function") syncToolbar(); }
    state.cableFirst = nearA ? c.vers : c.de;
    mark(); refreshAll();
    say(`Câble ${c.id} décroché côté ${label(nearA ? c.de : c.vers)} : clique la nouvelle prise (Échap pour le remettre).`);
    return true;
  }

  function init() {
    document.addEventListener("keydown", e => { if (e.key === "Escape" && state.cableFirst) cancel(); });
    document.getElementById("lv-centre").addEventListener("dblclick", e => {
      if (e.target.closest && e.target.closest(".it-port, .conn-hit, .h-target, .lead-hit, button, input, select, textarea")) return;
      if (!liftAt(e.clientX, e.clientY)) return;
      e.preventDefault();
      if (state.firstHole) { state.firstHole = null; ["svg-sel", "svg-rubberband"].forEach(id => { const el = document.getElementById(id); if (el) el.style.display = "none"; }); }   // le 1er clic du double-clic a pu armer un fil
    });
    document.getElementById("lv-centre").addEventListener("pointermove", trackMouse);
    window.addEventListener("resize", redraw);
  }
  return { init, liftAt, pick, pickHole, clickPort, clickConn, redraw, defaultColor, removeAt, removeIndex, cancel, render, sameEnds, label, isDev };
})();
