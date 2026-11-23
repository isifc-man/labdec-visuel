// Colle entre l'état de l'interface et le moteur. Aucune physique ici : tout passe par Engine.
function curMontage() { return MONTAGES[state.currentMontage] || null; }
// Câbles d'appareils de l'ÉLÈVE (ceux du corrigé sont m.cables : ils ne servent que pour l'écran « attendu »)
function curCables() { return state.placedCables; }

// Le GBF affiche une amplitude « pour la charge réglée ». En « 50 Ω » il suppose une charge de 50 Ω :
// à vide (ou sur 1 MΩ) la vraie tension est ×2 (sujet TP1). En « High Z » l'affichage est la tension à vide.
function gbfEngine(g) {
  const k = g.load === "50" ? 2 : 1;
  return { f: g.f, vpp: g.vpp * k, offset: g.offset * k, wave: g.wave, on: g.on, sync: g.sync !== false };
}
function psuSrc(psu) {
  const v = {};
  [1, 2, 3].forEach(k => { const c = psu.ch[k]; v[k] = { v: c.v, i: c.i, on: !!c.on }; });
  return v;
}
function envFor(cables) { return { holes: HOLES, holeIds: HOLE_IDS, chipsLib: CHIPS_LIB, cables }; }
function wiringNow() {
  return { wires: state.placedWires, comps: state.placedComps.filter(c => c.type === "resistor" || c.type === "led"), chips: state.placedChips, dmm: state.dmm && state.dmm.v && state.dmm.com ? { v: state.dmm.v, com: state.dmm.com } : null };
}
function wiringOfSolution(m) {
  return {
    wires: (m.fils || []).map(w => ({ de: w.de, vers: w.vers })),
    comps: Object.entries(m.composants || {}).filter(([, c]) => c.type === "resistor" || c.type === "led").map(([name, c]) => ({ name, type: c.type, a: c.a, b: c.b, k: c.k, ohm: c.ohm })),
    chips: m.puces || [],
  };
}

// ---- analyses (mises en cache : un changement de câblage ou de réglage les invalide) ----
let _cache = { key: null, an: null };
function getAnalysis() {
  const ge = gbfEngine(state.gbf), ps = psuSrc(state.psu);
  const key = JSON.stringify([state.placedWires, state.placedComps, state.placedChips, state.placedCables, ge, ps, state.dmm && [state.dmm.v, state.dmm.com]]);
  if (_cache.key !== key) _cache = { key, an: Engine.analyze(wiringNow(), envFor(curCables()), { gbf: ge, psu: ps }) };
  return _cache.an;
}

// Écran « attendu » et comparaison : le câblage corrigé et le câblage de l'élève sont simulés dans les MÊMES conditions
// (réglages de départ du montage, appareils allumés), pour juger le circuit sans mélanger avec les réglages d'appareils.
const _expCache = {};
let _stuCache = { key: null, an: null };
function presetConditions() {
  const p = state.preset || { gbf: { f: 1000, vpp: 1, offset: 0, wave: "sine", load: "highz" }, psu: {}, psuI: {} };
  const ge = gbfEngine(Object.assign({ f: 1000, vpp: 1, offset: 0, wave: "sine", load: "highz" }, p.gbf || {}, { on: true }));
  const ps = {};
  [1, 2, 3].forEach(k => { const v = (p.psu || {})[k]; ps[k] = { v: v || 0, i: (p.psuI || {})[k] || 0.1, on: v != null }; });
  return { gbf: ge, psu: ps };
}
function expectedAnalysis() {
  const m = curMontage();
  if (!m) return null;
  if (!_expCache[m.id]) _expCache[m.id] = Engine.analyze(wiringOfSolution(m), envFor(m.cables), presetConditions());
  return _expCache[m.id];
}
function studentAtPreset() {
  const m = curMontage();
  if (!m) return null;
  const key = JSON.stringify([m.id, state.placedWires, state.placedComps, state.placedChips, state.placedCables]);
  if (_stuCache.key !== key) _stuCache = { key, an: Engine.analyze(wiringNow(), envFor(state.placedCables), presetConditions()) };
  return _stuCache.an;
}
// Compare les deux voies de l'oscillo (forme, niveau, phase) et les LED, sur la même base de temps.
function compareRecords(exp, st) {
  const er = exp.rec, sr = st.rec, msgs = [];
  let ok = true;
  ["ch1", "ch2"].forEach(c => {
    if (!er.ch[c]) return;
    if (!sr.ch[c]) { ok = false; msgs.push(`voie ${c.slice(2)} de l'oscillo non câblée`); return; }
    const n = er.dc ? 1 : 240, span = er.dc ? 0 : er.P;
    let d2 = 0, e2 = 0, emin = Infinity, emax = -Infinity;
    for (let i = 0; i < n; i++) {
      const t = (i + 0.5) / n * span, ve = Engine.at(er, c, t), vs = Engine.at(sr, c, t);
      d2 += (ve - vs) * (ve - vs); e2 += ve * ve; emin = Math.min(emin, ve); emax = Math.max(emax, ve);
    }
    const rms = Math.sqrt(d2 / n), scale = Math.max(emax - emin, 0.2 * Math.sqrt(e2 / n), 0.05);
    if (rms > 0.03 * scale) { ok = false; msgs.push(`voie ${c.slice(2)} différente de l'attendu (écart ${fmtV(rms)} eff.)`); }
  });
  const le = Object.values(er.leds).map(l => l.avg).sort((a, b) => a - b), ls = Object.values(sr.leds).map(l => l.avg).sort((a, b) => a - b);
  if (le.length) {
    if (ls.length < le.length) { ok = false; msgs.push(`${le.length - ls.length} LED manquante(s)`); }
    else le.forEach((v, i) => { const s = ls[ls.length - le.length + i]; if ((v > 5e-4) !== (s > 5e-4) || (v > 5e-4 && Math.abs(s / v - 1) > 0.15)) { ok = false; if (!msgs.some(x => /LED/.test(x))) msgs.push("LED : courant différent de l'attendu (sens, résistance ?)"); } });
  }
  return { ok, msgs };
}
function circuitMatch() {
  const exp = expectedAnalysis(), st = studentAtPreset();
  if (!exp || !st) return null;
  if (!exp.supported) return { status: "na", text: "Comparaison d'écran non disponible : " + exp.reasons.join(" ") };
  if (!exp.probes.ch1 && !exp.probes.ch2 && !Object.keys(exp.rec.leds).length) return { status: "na", text: "Ce montage n'a pas d'écran à comparer." };
  if (!st.supported) return { status: "bad", text: "Écran sans signal exploitable : " + st.reasons.join(" ") };
  const c = compareRecords(exp, st);
  const analog = !exp.digital && exp.gain != null && !exp.rec.dc;
  const detail = analog && st.gain != null ? `|Vs/Ve| = ${st.gain.toFixed(2)} (attendu ${exp.gain.toFixed(2)}) · phase ${st.phaseDeg.toFixed(0)}° (attendue ${exp.phaseDeg.toFixed(0)}°)` : "";
  return { status: c.ok ? "ok" : "bad", text: c.ok ? (detail || "voies de l'oscillo et LED identiques à l'attendu") : c.msgs.join(" ; ") + (detail ? " — " + detail : "") };
}

// ---- rafraîchissement global : tout ce qui est « calculé » se redessine ici ----
function triggerScopeRedraw() { refreshAll(); }
function refreshAll() {
  const an = getAnalysis();
  if (typeof History !== "undefined") History.track();
  if (typeof Scope !== "undefined") Scope.draw(an);
  if (typeof Gbf !== "undefined") Gbf.draw();
  if (typeof Psu !== "undefined") Psu.draw(an);
  if (typeof Faces !== "undefined") Faces.updateCables();
  if (typeof Cables !== "undefined") Cables.redraw();
  if (typeof Dock !== "undefined") Dock.update();
  if (typeof Leds !== "undefined") Leds.update(an);
  if (typeof Lesson !== "undefined") Lesson.refreshSteps();
  if (typeof Dmm !== "undefined") Dmm.draw(an);
  if (typeof Train !== "undefined") Train.tick();
  const box = document.getElementById("engine-alerts");
  if (box) {
    const rows = [];
    if (!state.placedCables.length) rows.push(`<div class="alert-row alert-info">🔌 Aucun câble d'appareil posé : clique une prise du GBF / de l'oscillo / de l'alim, puis la douille de la plaque (BNC 1, BNC 2, VB, VC, MASSE).</div>`);
    const usesPsu = state.placedCables.some(c => /^psu\./.test(c.de) || /^psu\./.test(c.vers));
    if (usesPsu && ![1, 2, 3].some(k => state.psu.ch[k].on)) rows.push(`<div class="alert-row alert-info">⏻ L'alim est câblée mais ses sorties sont éteintes : vérifie le câblage, puis touches « On » des voies utilisées.</div>`);
    const usesMain = state.placedCables.some(c => c.de === "gbf.out1" || c.vers === "gbf.out1");
    if (usesMain && !state.gbf.on) rows.push(`<div class="alert-row alert-info">⏻ La sortie 1 du GBF est câblée mais éteinte : touche « On/Off » (la sortie Sync, elle, reste active : menu Trigger).</div>`);
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
  const nodesOk = typeof nodeChecklist === "function" ? nodeChecklist().allOk : false;
  const cablesOk = (m.cables || []).every(c => state.placedCables.some(x => (x.de === c.de && x.vers === c.vers) || (x.de === c.vers && x.vers === c.de)));
  let s = (placed || state.placedCables.length) ? "cur" : "todo";
  if (nodesOk && (cm ? (cm.status === "ok" || (cm.status === "na" && cablesOk)) : cablesOk)) s = "ok";
  if (state.progress[id] === "ok" && s !== "ok") return;   // « validé » est conservé ; seul « ⟲ de zéro » le remet à l'état « à faire »
  if (state.progress[id] !== s) { state.progress[id] = s; saveProgress(); if (typeof Lesson !== "undefined") Lesson.paintNav(); }
}
