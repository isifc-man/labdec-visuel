// Colle entre l'état de l'interface et le moteur. Aucune physique ici : tout passe par Engine.
function curMontage() { return MONTAGES[state.currentMontage] || null; }
// Câbles d'appareils de l'ÉLÈVE (ceux du corrigé sont m.cables : ils ne servent que pour l'écran « attendu »)
function curCables() { return state.placedCables; }

// Le GBF affiche une amplitude « pour la charge réglée ». En « 50 Ω » il suppose une charge de 50 Ω :
// à vide (ou sur 1 MΩ) la vraie tension est ×2 (sujet TP1). En « High Z » l'affichage est la tension à vide.
function gbfEngine(g) {
  const k = g.load === "50" ? 2 : 1;
  return { f: g.f, vpp: g.vpp * k, offset: g.offset * k, wave: g.wave, on: g.on };
}
function psuVolts(psu) {
  const v = {};
  [1, 2, 3].forEach(k => { v[k] = psu.ch[k].on ? psu.ch[k].v : 0; });
  return v;
}
function envFor(wiringCables, gbf, psu) {
  return { holes: HOLES, holeIds: HOLE_IDS, chipsLib: CHIPS_LIB, cables: wiringCables, gbf: { offset: gbf.offset }, psu: { on: true, v: psuVolts(psu) } };
}
function wiringNow() {
  return { wires: state.placedWires, comps: state.placedComps.filter(c => c.type === "resistor" || c.type === "led"), chips: state.placedChips };
}
function wiringOfSolution(m) {
  return {
    wires: (m.fils || []).map(w => ({ de: w.de, vers: w.vers })),
    comps: Object.entries(m.composants || {}).filter(([, c]) => c.type === "resistor" || c.type === "led").map(([name, c]) => ({ name, type: c.type, a: c.a, b: c.b, ohm: c.ohm })),
    chips: m.puces || [],
  };
}

// ---- analyses (mises en cache : un changement de câblage ou de réglage les invalide) ----
let _cache = { key: null, an: null };
function getAnalysis() {
  const ge = gbfEngine(state.gbf);
  const key = JSON.stringify([state.placedWires, state.placedComps, state.placedChips, state.placedCables, ge, psuVolts(state.psu), state.currentMontage]);
  if (_cache.key !== key) _cache = { key, an: Engine.analyze(wiringNow(), envFor(curCables(), ge, state.psu), ge) };
  return _cache.an;
}

// Écran « attendu » et comparaison : le câblage corrigé et le câblage de l'élève sont simulés dans les MÊMES conditions
// (réglages de départ du YAML), pour juger le circuit sans mélanger avec les réglages d'appareils.
const _expCache = {};
function presetConditions() {
  const p = state.preset || { gbf: { f: 1000, vpp: 1, offset: 0, wave: "sine", load: "highz" }, psu: { 1: 0, 2: 15, 3: 15 } };
  const ge = gbfEngine(Object.assign({ on: true }, p.gbf));
  const psu = { ch: {} };
  [1, 2, 3].forEach(k => { psu.ch[k] = { v: (p.psu || {})[k] || 0, on: true }; });
  return { ge, psu };
}
function expectedAnalysis() {
  const m = curMontage();
  if (!m) return null;
  if (!_expCache[m.id]) { const c = presetConditions(); _expCache[m.id] = Engine.analyze(wiringOfSolution(m), envFor(m.cables, c.ge, c.psu), c.ge); }
  return _expCache[m.id];
}
function studentAtPreset() {
  const m = curMontage();
  if (!m) return null;
  const c = presetConditions();
  return Engine.analyze(wiringNow(), envFor(state.placedCables, c.ge, c.psu), c.ge);
}
function circuitMatch() {
  const exp = expectedAnalysis(), st = studentAtPreset();
  if (!exp || !st) return null;
  if (!exp.supported) return { status: "na", text: "Comparaison d'écran non disponible : " + exp.reasons.join(" ") };
  if (!st.supported || st.gain == null) return { status: "bad", text: "Écran sans signal exploitable : " + (st.reasons.join(" ") || "câblage incomplet.") };
  const dg = Math.abs(st.gain / exp.gain - 1) * 100;
  const dph = Math.abs(((st.phaseDeg - exp.phaseDeg + 540) % 360) - 180);
  const ok = dg <= 2 && dph <= 3 && st.powered === exp.powered;
  return { status: ok ? "ok" : "bad", gain: st.gain, gainExp: exp.gain, phase: st.phaseDeg, phaseExp: exp.phaseDeg,
    text: `|Vs/Ve| = ${st.gain.toFixed(2)} (attendu ${exp.gain.toFixed(2)}) · phase ${st.phaseDeg.toFixed(0)}° (attendue ${exp.phaseDeg.toFixed(0)}°)` };
}

// ---- interface attendue par checks.js (union-find « nommé » : R1.a, U1.2, VB.main, TOP_L_1…) ----
function evaluateCircuit() {
  const uf = new Engine.UF();
  HOLES.forEach(h => uf.u(h.id, h.net));
  state.placedChips.forEach(ch => {
    const spec = CHIPS_LIB[ch.modele];
    if (spec) for (let p = 1; p <= spec.dip; p++) uf.u(`${ch.ref}.${p}`, Engine.pinHole(ch, p, CHIPS_LIB));
  });
  state.placedComps.forEach(c => { uf.u(`${c.name}.a`, c.a); uf.u(`${c.name}.b`, c.b); if (c.k) uf.u(`${c.name}.k`, c.k); });
  state.placedWires.forEach(w => uf.u(w.de, w.vers));
  const an = getAnalysis();
  return { uf, isPowered: an.powered, isGndConnected: uf.c("MASSE.main", "TOP_L_1") };
}

// ---- rafraîchissement global : tout ce qui est « calculé » se redessine ici ----
function triggerScopeRedraw() { refreshAll(); }
function refreshAll() {
  const an = getAnalysis();
  if (typeof Scope !== "undefined") Scope.draw(an);
  if (typeof Gbf !== "undefined") Gbf.draw();
  if (typeof Psu !== "undefined") Psu.draw(an);
  if (typeof Faces !== "undefined") Faces.updateCables();
  if (typeof Cables !== "undefined") Cables.redraw();
  if (typeof Dock !== "undefined") Dock.update();
  if (typeof Lesson !== "undefined") Lesson.refreshSteps();
  const box = document.getElementById("engine-alerts");
  if (box) {
    const rows = [];
    if (!state.placedCables.length) rows.push(`<div class="alert-row alert-info">🔌 Aucun câble d'appareil posé : clique une prise du GBF / de l'oscillo / de l'alim, puis la douille de la plaque (BNC 1, BNC 2, VB, VC, MASSE).</div>`);
    an.warnings.forEach(w => rows.push(`<div class="alert-row alert-warn">⚠️ ${w}</div>`));
    if (!an.supported) an.reasons.forEach(r => rows.push(`<div class="alert-row alert-info">ℹ️ ${r}</div>`));
    an.notes.forEach(n => rows.push(`<div class="alert-row alert-info">ℹ️ ${n}</div>`));
    const cm = circuitMatch();
    if (cm) rows.push(`<div class="alert-row ${cm.status === "ok" ? "alert-ok" : cm.status === "bad" ? "alert-err" : "alert-info"}">${cm.status === "ok" ? "✅ Écran conforme : " : cm.status === "bad" ? "❌ Écran différent de l'attendu : " : ""}${cm.text}</div>`);
    box.innerHTML = rows.join("");
    updateProgress(cm);
  }
}

function updateProgress(cm) {
  const id = state.currentMontage, m = curMontage();
  if (!id || !m) return;
  const placed = state.placedWires.length + state.placedComps.length + state.placedChips.length;
  const { uf } = evaluateCircuit();
  const nodes = Object.values(m.noeuds || {});
  const nodesOk = nodes.length > 0 && nodes.every(e => e.slice(1).every(x => uf.c(e[0], x)));
  const cablesOk = (m.cables || []).every(c => state.placedCables.some(x => (x.de === c.de && x.vers === c.vers) || (x.de === c.vers && x.vers === c.de)));
  let s = (placed || state.placedCables.length) ? "cur" : "todo";
  if (nodesOk && (cm ? (cm.status === "ok" || (cm.status === "na" && cablesOk)) : cablesOk)) s = "ok";
  if (state.progress[id] === "ok" && s !== "ok") return;   // « validé » est conservé ; seul « ⟲ de zéro » le remet à l'état « à faire »
  if (state.progress[id] !== s) { state.progress[id] = s; saveProgress(); if (typeof Lesson !== "undefined") Lesson.paintNav(); }
}
