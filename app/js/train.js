// Entraînement : « TP4 blanc » (montage tiré au sort, corrigé masqué, chrono 1 h 45, note indicative)
// et « Trouve la panne » (montage du corrigé avec UNE erreur cachée à corriger).
const Train = (() => {
  let mode = null;          // {kind:"tp4"|"panne", id, t0, dur?, fault?, hints}
  const $ = s => document.querySelector(s);
  const esc = s => String(s == null ? "" : s).replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
  const fmtOhm = v => v >= 1e6 ? +(v / 1e6).toFixed(2) + " MΩ" : v >= 1e3 ? String(+(v / 1e3).toFixed(2)).replace(".", ",") + " kΩ" : v + " Ω";
  const ids = () => Object.keys(MONTAGES).filter(i => MONTAGES[i].noeuds && Object.keys(MONTAGES[i].noeuds).length);
  const pick = a => a[Math.floor(Math.random() * a.length)];
  const mmss = ms => { const s = Math.max(0, Math.round(ms / 1000)); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`; };

  function banner() {
    const b = $("#train-bar"); if (!b) return;
    if (!mode) { b.style.display = "none"; return; }
    b.style.display = "flex";
    const el = Date.now() - mode.t0;
    b.innerHTML = mode.kind === "tp4"
      ? `<b>🎯 TP4 blanc</b><span>${esc(MONTAGES[mode.id].titre)}</span><span class="sp"></span><span class="timer">${mmss(mode.dur - el)} restantes</span><button class="btn sm" id="tr-end">Terminer et noter</button><button class="btn sm" id="tr-quit">Abandonner</button>`
      : `<b>🔧 Trouve la panne</b><span>${esc(MONTAGES[mode.id].titre)} — une seule erreur est cachée dans le montage.</span><span class="sp"></span><span class="timer">${mmss(el)}</span><button class="btn sm" id="tr-hint">Indice</button><button class="btn sm" id="tr-quit">Voir la réponse</button>`;
    const q = $("#tr-quit"), e = $("#tr-end"), h = $("#tr-hint");
    if (q) q.onclick = () => (mode.kind === "tp4" ? finishTp4(true) : reveal());
    if (e) e.onclick = () => finishTp4(false);
    if (h) h.onclick = () => { mode.hints++; modal("Indice", `<p>${esc(mode.fault.hint)}</p>`); };
  }
  function modal(title, html) {
    let el = $("#train-modal");
    if (!el) { el = document.createElement("div"); el.id = "train-modal"; el.className = "modal"; document.body.appendChild(el); el.addEventListener("click", e => { if (e.target === el || e.target.dataset.close != null) el.classList.remove("show"); }); }
    el.innerHTML = `<div class="modal-card"><div class="modal-bar"><b>${title}</b><button class="btn sm" data-close>✕ fermer</button></div>${html}</div>`;
    el.classList.add("show");
  }

  // ---------- TP4 blanc ----------
  function startTp4() {
    const id = pick(ids());
    Lesson.load(id);
    mode = { kind: "tp4", id, t0: Date.now(), dur: 105 * 60e3, hints: 0 };
    Lesson.showTab("sujet"); Lesson.refreshSteps(); banner();
    modal("TP4 blanc", `<p>Montage tiré au sort : <b>${esc(MONTAGES[id].titre)}</b>.</p><p>Comme au TP4 : 1 h 45, tu as le sujet (ton « cahier »), mais <b>pas le corrigé</b>. Câble, règle et allume les appareils, puis « Terminer et noter ».</p><p class="mut">La note est indicative : elle juge ce que le simulateur sait vérifier (nœuds, écran, sécurité, réglages), pas ton compte rendu.</p>`);
  }
  function grade() {
    const m = MONTAGES[mode.id], nc = nodeChecklist(), cm = circuitMatch(), an = getAnalysis(), p = state.preset || {};
    const lines = [];
    const nodes = nc.total ? 8 * nc.done / nc.total : 0;
    lines.push([`Nœuds reliés : ${nc.done}/${nc.total}`, nodes, 8]);
    const ecran = cm && cm.status === "ok" ? 6 : 0;
    lines.push([`Écran conforme au montage attendu${cm && cm.status !== "ok" ? " — " + cm.text : ""}`, ecran, 6]);
    const dang = an.warnings.filter(w => /ENVERS|DÉTRUITE|grille|CC\)|court-circuitée|FLOTTANTE/.test(w));
    lines.push([dang.length ? "Sécurité : " + dang.join(" ; ") : "Sécurité : aucune erreur dangereuse", dang.length ? 0 : 3, 3]);
    let reg = 0, why = [];
    const needPsu = Object.keys(p.psu || {}).length, needGbf = m.cables.some(c => /^gbf\.out1/.test(c.de) || /^gbf\.out1/.test(c.vers));
    if (!needPsu || [1, 2, 3].every(k => p.psu[k] == null || (state.psu.ch[k].on && Math.abs(state.psu.ch[k].v - p.psu[k]) < 0.05))) reg++; else why.push("alim");
    if (!needGbf || state.gbf.on) reg++; else why.push("GBF éteint");
    if (!needGbf || !p.gbf || state.gbf.load === p.gbf.load) reg++; else why.push("charge du GBF (High Z / 50 Ω)");
    lines.push([`Réglages des appareils${why.length ? " — à revoir : " + why.join(", ") : ""}`, reg, 3]);
    const note = lines.reduce((s, l) => s + l[1], 0);
    return { note, lines };
  }
  function finishTp4(giveUp) {
    const g = grade(), el = Date.now() - mode.t0, id = mode.id;
    modal(giveUp ? "TP4 blanc abandonné" : "TP4 blanc : résultat", `<p><b>Note indicative : ${g.note.toFixed(1)} / 20</b> en ${mmss(el)}${el > mode.dur ? " (temps dépassé)" : ""}.</p><table class="placed-table"><tbody>${g.lines.map(l => `<tr><td>${esc(l[0])}</td><td>${l[1].toFixed(1)} / ${l[2]}</td></tr>`).join("")}</tbody></table><p class="mut">Le corrigé est de nouveau visible dans l'onglet Corrigé.</p>`);
    mode = null; banner(); Lesson.refreshSteps(); if (state.currentMontage !== id) Lesson.load(id);
  }

  // ---------- Trouve la panne ----------
  const FAULTS = [
    { kind: "fil décalé", hint: "Un fil est branché une rangée à côté de l'endroit prévu.", make: () => {
      const w = pick(state.placedWires.filter(w => /^T\d[a-j]\d+$/.test(w.vers)));
      if (!w) return null;
      const m = w.vers.match(/^(T\d[a-j])(\d+)$/), alt = [+m[2] + 1, +m[2] - 1].map(r => m[1] + r).find(h => HOLE_IDS.has(h));
      if (!alt) return null; const old = w.vers; w.vers = alt; return `le fil ${w.de} → ${old} était déplacé en ${alt} (une rangée à côté).`; } },
    { kind: "valeur", hint: "Une résistance n'a pas la bonne valeur : lis les étiquettes.", make: () => {
      const r = pick(state.placedComps.filter(c => c.type === "resistor"));
      if (!r) return null;
      let i = 0; E12_ALL.forEach((v, k) => { if (Math.abs(Math.log(v / r.ohm)) < Math.abs(Math.log(E12_ALL[i] / r.ohm))) i = k; });
      const nv = E12_ALL[i + 3] || E12_ALL[i - 3];
      const old = r.ohm; r.ohm = nv; r.etiquette = fmtOhm(nv); return `${r.name} valait ${fmtOhm(nv)} au lieu de ${fmtOhm(old)}.`; } },
    { kind: "fil manquant", hint: "Il manque un fil : relis le schéma nœud par nœud.", make: () => {
      if (!state.placedWires.length) return null;
      const i = Math.floor(Math.random() * state.placedWires.length), w = state.placedWires.splice(i, 1)[0]; return `le fil ${w.de} → ${w.vers} avait été retiré.`; } },
    { kind: "LED à l'envers", hint: "Un composant polarisé est retourné.", make: () => {
      const l = pick(state.placedComps.filter(c => c.type === "led"));
      if (!l) return null; [l.a, l.k] = [l.k, l.a]; return `${l.name} était montée à l'envers (anode et cathode inversées).`; } },
    { kind: "puce décalée", hint: "Regarde la position de la puce par rapport à ses fils.", make: () => {
      const c = pick(state.placedChips); if (!c) return null;
      c.rangee_broche1 += 1; return `${c.ref} était décalée d'une rangée : aucune broche n'était où il fallait.`; } },
  ];
  function startPanne() {
    for (let tries = 0; tries < 30; tries++) {
      const id = pick(ids());
      Lesson.load(id); Lesson.putSolution(MONTAGES[id]);
      if (state.gbf) state.gbf.on = true;
      [1, 2, 3].forEach(k => { if (state.preset && state.preset.psu && state.preset.psu[k] != null) state.psu.ch[k].on = true; });
      const f = pick(FAULTS), txt = f.make();
      if (!txt) continue;
      renderPlacedElements(); History.reset();
      const cm = circuitMatch(), nc = nodeChecklist();
      if (cm && cm.status === "ok" && nc.allOk) continue;        // l'erreur ne se voit pas : on en tire une autre
      mode = { kind: "panne", id, t0: Date.now(), fault: { kind: f.kind, hint: f.hint, txt }, hints: 0 };
      Lesson.showTab("etat"); Lesson.refreshSteps(); banner();
      modal("Trouve la panne", `<p>Le montage <b>${esc(MONTAGES[id].titre)}</b> est câblé et les appareils sont allumés, mais <b>une erreur</b> s'est glissée. Observe l'écran, compare au sujet, trouve-la et corrige-la.</p><p class="mut">Le corrigé est masqué. « Indice » donne le type d'erreur ; l'onglet État reste disponible.</p>`);
      return;
    }
  }
  function reveal(found) {
    const f = mode.fault, el = Date.now() - mode.t0, id = mode.id;
    modal(found ? "Panne trouvée 🎉" : "La réponse", `<p>${found ? `Corrigé en ${mmss(el)}${mode.hints ? ` (${mode.hints} indice${mode.hints > 1 ? "s" : ""})` : ""}.` : ""} La panne : ${esc(f.txt)}</p><p class="mut">Type : ${esc(f.kind)}.</p>`);
    mode = null; banner(); Lesson.refreshSteps();
    if (!found && state.currentMontage === id) { Lesson.putSolution(MONTAGES[id]); renderPlacedElements(); }
  }

  function tick() {
    if (!mode) return;
    if (state.currentMontage !== mode.id) { mode = null; banner(); return; }
    banner();
    if (mode.kind === "panne") { const cm = circuitMatch(), nc = nodeChecklist(); if (cm && cm.status === "ok" && nc.allOk) reveal(true); }
  }
  setInterval(() => { if (mode) banner(); }, 1000);
  return { startTp4, startPanne, tick, hidesCorrige: () => !!mode };
})();
