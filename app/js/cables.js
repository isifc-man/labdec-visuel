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
  const CONN_COL = { VB: "#3b82f6", VC: "#ef4444", MASSE: "#14b8a6" };
  const sameEnds = (a, b, c, d) => (a === c && b === d) || (a === d && b === c);
  const LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";

  function label(e) {
    const names = { "gbf.out1": "sortie 1 du GBF", "gbf.sync_out": "Sync du GBF", "scope.ch1": "voie 1 de l'oscillo", "scope.ch2": "voie 2 de l'oscillo", "scope.ext": "Ext Trig de l'oscillo" };
    if (names[e]) return names[e];
    let m = e.match(/^psu\.ch(\d)_(plus|moins)$/);
    if (m) return `alim voie ${m[1]} ${m[2] === "plus" ? "+" : "−"}`;
    return { BNC1: "BNC 1 de la plaque", BNC2: "BNC 2 de la plaque", VB: "douille VB", VC: "douille VC", MASSE: "douille MASSE" }[e] || e;
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
    render();
  }
  function cancel() { state.cableFirst = null; mark(); say(""); }

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
    if (a === b) { mark(); say(""); return; }
    if (!isDev(a) && !isDev(b)) { mark(); say("Deux douilles de la plaque ne se relient pas par un câble : utilise un fil sur la plaque.", "warn"); return; }
    if (kindOf(a) !== kindOf(b)) { mark(); say(`Un câble BNC ne se branche pas sur une douille banane (${label(a)} / ${label(b)}).`, "warn"); return; }
    if (state.placedCables.some(c => sameEnds(c.de, c.vers, a, b))) { mark(); say("Ce câble existe déjà.", "warn"); return; }
    for (const e of [a, b]) {
      // sortie 1 du GBF : adaptateur en T (2 BNC) ; douilles banane : fiches empilables (2) ; autre BNC : 1 seul câble
      const lim = e === "gbf.out1" || kindOf(e) === "banane" ? 2 : 1;
      if (count(e) >= lim) { mark(); say(`${label(e)} a déjà ${lim === 2 ? "deux câbles (c'est plein)" : "un câble"} : retire-en un avec la gomme.`, "warn"); return; }
    }
    const id = nextId(), kind = kindOf(a);
    state.placedCables.push({ id, de: a, vers: b, nom: kind === "bnc" ? "câble BNC–BNC" : "câble banane" });
    mark();
    say(`Câble ${id} posé : ${label(a)} ↔ ${label(b)}.${(a === "gbf.out1" || b === "gbf.out1") && count("gbf.out1") === 2 ? " (adaptateur en T sur la sortie du GBF)" : ""}`, "ok");
    refreshAll();
  }
  function clickPort(end) { if (state.tool === "delete") { if (!removeAt(end)) say("Aucun câble sur cette prise.", "warn"); else say("Câble retiré.", "ok"); } else pick(end); }
  function pickHole(hid) { const c = connOfHole(hid); if (c) pick(c); else say("Mode câble : clique une prise d'appareil ou une douille BNC / banane de la plaque (en haut).", "warn"); }

  function removeAt(end) {
    const n = state.placedCables.length;
    state.placedCables = state.placedCables.filter(c => c.de !== end && c.vers !== end);
    if (state.placedCables.length !== n) { mark(); refreshAll(); return true; }
    return false;
  }
  function removeIndex(i) { state.placedCables.splice(i, 1); mark(); refreshAll(); }

  // Anneaux + lettres sur les douilles de la plaque (les mêmes lettres sont sur les prises des appareils)
  function render() {
    const svg = document.getElementById("master-board-svg"); if (!svg) return;
    let g = document.getElementById("svg-cables");
    if (!g) { g = document.createElementNS(NAMESPACE, "g"); g.id = "svg-cables"; svg.insertBefore(g, document.getElementById("svg-targets")); g.style.pointerEvents = "none"; }
    let s = "";
    const ring = (id, x, y, col, r) => `<circle cx="${x}" cy="${y}" r="${r}" fill="none" stroke="${col}" stroke-width="4"/>`;
    state.placedCables.forEach(c => [c.de, c.vers].forEach(e => {
      if (isDev(e)) return;
      const holes = HOLE_MAP.get(e + ".core") ? [e + ".core", e + ".shield"] : [e + ".main"];
      holes.forEach((hid, k) => {
        const h = HOLE_MAP.get(hid); if (!h) return;
        const col = CONN_COL[e] || "#38bdf8";
        s += ring(hid, h.x, h.y, col, 12);
        if (k === 0) s += `<circle cx="${h.x}" cy="${h.y - 24}" r="10" fill="#0b3d91" stroke="#fff" stroke-width="2"/><text x="${h.x}" y="${h.y - 20}" font-size="12" font-weight="700" fill="#fff" text-anchor="middle" font-family="Arial">${c.id}</text>`;
      });
    }));
    if (state.cableFirst && !isDev(state.cableFirst)) {
      const e = state.cableFirst; (HOLE_MAP.get(e + ".core") ? [e + ".core", e + ".shield"] : [e + ".main"]).forEach(hid => { const h = HOLE_MAP.get(hid); if (h) s += ring(hid, h.x, h.y, "#facc15", 14); });
    }
    g.innerHTML = s;
  }

  function init() {
    document.addEventListener("keydown", e => { if (e.key === "Escape" && state.cableFirst) cancel(); });
  }
  return { init, pick, pickHole, clickPort, removeAt, removeIndex, cancel, render, sameEnds, label, isDev };
})();
