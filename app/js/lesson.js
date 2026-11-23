// Menu de gauche (TP → montages), composants en bas du menu de gauche, panneau de droite (Sujet · Questions · Corrigé · État) et chargement d'un montage.
// Tout le contenu vient de MONTAGES (YAML) : aucune fiche écrite à la main ici.
const Lesson = (() => {
  const $ = s => document.querySelector(s);
  const E12 = [10, 12, 15, 18, 22, 27, 33, 39, 47, 56, 68, 82];
  const open = new Set();           // indices d'indices (corrigé) ouverts
  const ids = () => Object.keys(MONTAGES).sort();
  const esc = s => String(s == null ? "" : s).replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
  const num = s => parseFloat(String(s).replace(",", "."));

  function fmtOhm(v) { return v >= 1e6 ? +(v / 1e6).toFixed(2) + " MΩ" : v >= 1e3 ? String(+(v / 1e3).toFixed(2)).replace(".", ",") + " kΩ" : v + " Ω"; }
  function isE12(v) { for (let e = 0; e <= 5; e++) if (E12.some(m => Math.abs(m * Math.pow(10, e) - v) < 1e-6)) return true; return false; }
  function e12Palette(v) {                       // valeur du corrigé + voisines de la série E12
    const all = [];
    for (let e = 0; e <= 5; e++) E12.forEach(m => all.push(m * Math.pow(10, e)));
    const i = all.reduce((b, x, k) => Math.abs(Math.log(x / v)) < Math.abs(Math.log(all[b] / v)) ? k : b, 0);
    return [...new Set([...all.slice(Math.max(0, i - 2), i + 3), v])].sort((a, b) => a - b);
  }

  // ---------- réglages de départ lus dans le texte des YAML (« Sinus · 0,4 Vpp · 1 kHz · High Z ») ----------
  function parsePreset(m) {
    const r = m.reglages || {}, p = { gbf: null, psu: {}, psuI: {}, scope: { ch: {}, tdiv: null } };
    if (r.gbf) {
      const t = r.gbf, mf = t.match(/([\d,.]+)\s*(MHz|kHz|Hz)/i), mv = t.match(/([\d,.]+)\s*(m?)Vpp/i), mo = t.match(/offset\s*([\d,.]+)\s*V/i);
      p.gbf = { wave: /Carr/i.test(t) ? "square" : /Ramp|Triangle/i.test(t) ? "triangle" : "sine",
        f: mf ? num(mf[1]) * { mhz: 1e6, khz: 1e3, hz: 1 }[mf[2].toLowerCase()] : 1000,
        vpp: mv ? num(mv[1]) * (mv[2] ? 1e-3 : 1) : 1, offset: mo ? num(mo[1]) : 0, load: /High\s*Z/i.test(t) ? "highz" : "50" };
    }
    if (r.psu) {
      for (const x of r.psu.matchAll(/voie\s*(\d)\s*=\s*\+?([\d,.]+)\s*V/gi)) p.psu[+x[1]] = num(x[2]);
      const li = r.psu.match(/limite[^0-9]*([\d,.]+)\s*A/i);
      if (li) [1, 2, 3].forEach(k => { p.psuI[k] = num(li[1]); });
    }
    if (r.scope) {
      for (const x of r.scope.matchAll(/voie\s*(\d)\s*:?\s*[^·]*?([\d,.]+)\s*(m?)V\/div/gi)) p.scope.ch[+x[1]] = num(x[2]) * (x[3] ? 1e-3 : 1);
      const mt = r.scope.match(/([\d,.]+)\s*(µs|ms|ns|s)\/div/i);
      if (mt) p.scope.tdiv = num(mt[1]) * { "µs": 1e-6, ms: 1e-3, ns: 1e-9, s: 1 }[mt[2].toLowerCase()];
    }
    return p;
  }

  function applyPreset(p) {
    const f = factoryInstruments();
    state.gbf = f.gbf; state.psu = f.psu; state.scope = f.scope;
    if (p.gbf) Object.assign(state.gbf, p.gbf, { on: true });
    [1, 2, 3].forEach(k => { if (p.psu[k] != null) Object.assign(state.psu.ch[k], { v: p.psu[k], i: p.psuI[k] || 0.1, on: true }); });
    [1, 2].forEach(n => { if (p.scope.ch[n]) state.scope.ch[n].vdiv = p.scope.ch[n]; });
    if (p.scope.tdiv) state.scope.tdiv = p.scope.tdiv;
  }

  function prevId(m) {
    if (!m.precedent) return null;
    const tp = m.id.split("-")[0];
    return ids().find(i => i.startsWith(tp + "-") && i.split("-").slice(1).join("_") === m.precedent) || null;
  }

  // ---------- chargement d'un montage ----------
  function load(id) {
    clearWiring();
    const m = MONTAGES[id] || null;
    state.currentMontage = m ? id : null;
    for (const k in _expCache) delete _expCache[k];
    state.preset = m ? parsePreset(m) : null;
    if (m) applyPreset(state.preset); else { const f = factoryInstruments(); state.gbf = f.gbf; state.psu = f.psu; state.scope = f.scope; }
    open.clear();
    $("#cur-title").textContent = m ? m.titre : "Mode libre (câbles d'appareils du TP2)";
    paintNav(); renderAll(); Dock.setSubject(m);
    renderPlacedElements();
  }
  function clearWiring() { state.placedWires = []; state.placedComps = []; state.placedChips = []; state.placedCables = []; state.cableFirst = null; state.armedRef = null; }
  const cableOf = c => ({ id: c.id, couleur: c.couleur || Cables.defaultColor(c), de: c.de, vers: c.vers, nom: c.nom || (c.de.indexOf("psu.") === 0 || c.vers.indexOf("psu.") === 0 ? "câble banane" : "câble BNC–BNC") });
  function putSolution(m) {
    const w = wiringOfSolution(m);
    state.placedCables = (m.cables || []).map(cableOf);
    state.placedWires = (m.fils || []).map(x => ({ n: x.n, de: x.de, vers: x.vers, couleur: x.couleur || "rouge" }));
    state.placedComps = Object.entries(m.composants || {}).filter(([, c]) => c.type === "resistor").map(([name, c]) => ({ name, type: "resistor", a: c.a, b: c.b, ohm: c.ohm, etiquette: fmtOhm(c.ohm) }));
    state.placedChips = JSON.parse(JSON.stringify(m.puces || []));
    return w;
  }

  // ---------- menu de gauche ----------
  function paintNav() {
    const nav = $("#tree"), groups = {};
    ids().forEach(i => { (groups[MONTAGES[i].tp] = groups[MONTAGES[i].tp] || []).push(i); });
    nav.innerHTML = Object.keys(groups).sort().map(tp => {
      const closed = nav.dataset["c" + tp] === "1";
      return `<div class="tp${closed ? " closed" : ""}" data-tp="${tp}"><button>${closed ? "▸" : "▾"} TP${tp}</button><ul>` +
        groups[tp].map(i => {
          const s = i === state.currentMontage ? (state.progress[i] === "ok" ? "ok" : "cur") : (state.progress[i] || "todo");
          const m = MONTAGES[i];
          return `<li data-id="${i}" class="${i === state.currentMontage ? "sel" : ""}"><span class="dot ${s}">${s === "ok" ? "●" : s === "cur" ? "◐" : "○"}</span><span>${esc(shortTitle(m))}</span></li>`;
        }).join("") + "</ul></div>";
    }).join("");
    nav.querySelectorAll(".tp>button").forEach(b => b.onclick = () => { const d = b.parentNode; nav.dataset["c" + d.dataset.tp] = d.classList.contains("closed") ? "0" : "1"; paintNav(); });
    nav.querySelectorAll("li").forEach(l => l.onclick = () => load(l.dataset.id));
    const fr = $("#free"); fr.classList.toggle("sel", !state.currentMontage);
  }
  const shortTitle = m => m.titre.replace(/\s*\(.*$/, "").replace(/\s*:.*$/, "").slice(0, 44);

  // ---------- panneaux de droite ----------
  function renderAll() { renderSujet(); renderQuestions(); renderCompo(); refreshSteps(); }

  // Extraits du VRAI sujet (captures des PDF de l'école) : présents seulement si les PDF étaient là au moment du build
  const pieceList = (m, kinds) => (typeof SUJET !== "undefined" && SUJET && m && SUJET.montages[m.id] || []).map(k => [k, SUJET.pieces[k]]).filter(([, p]) => !kinds || kinds.includes(p.k));
  const figure = ([k, p]) => `<figure class="sj"><figcaption>${esc(p.t)}</figcaption><img src="${p.img}" data-piece="${k}" alt="${esc(p.t)}" loading="lazy"></figure>`;
  function bindFigures(el) { el.querySelectorAll("img[data-piece]").forEach(i => i.onclick = () => Zoom.showImage(i.src, i.alt)); }
  function renderSujet() {
    const m = curMontage(), el = $("#p-sujet");
    if (!m) { el.innerHTML = "<h3>Mode libre</h3><p>Pose des fils, des résistances (toute la série E12), des puces et des câbles d'appareils comme tu veux. Les écrans réagissent à ce que tu câbles.</p>"; return; }
    const r = m.reglages || {}, pcs = pieceList(m), hasSujet = pcs.length > 0;
    const annexes = hasSujet ? Object.values(SUJET.annexes).flat().map(k => [k, SUJET.pieces[k]]) : [];
    const head = hasSujet
      ? `<h3>${esc(m.titre)}</h3><p class="mut">Extraits du sujet de TP d'électronique (ISIFC 1A), reproduits pour l'entraînement ; clique une image pour l'agrandir. Retrait sur demande de l'établissement.</p>` + pcs.map(figure).join("") +
        `<details><summary>Annexes du sujet (GBF, oscilloscope, platine, alimentation)</summary>${annexes.map(figure).join("")}</details>` +
        `<details><summary>Texte du montage (fichier YAML)</summary><p>${esc(m.objectif)}</p></details>`
      : `<h3>${esc(m.titre)}</h3><p>${esc(m.objectif)}</p><p class="mut">Les extraits du sujet (captures) ne sont pas inclus dans cette version : texte tiré des fichiers du montage.</p>`;
    el.innerHTML = head +
      (m.description ? `<p class="mut">${esc(m.description)}</p>` : "") +
      `<h4>Réglages indiqués par le sujet</h4><ul class="reg">${["gbf:GBF", "psu:Alim", "scope:Oscillo"].map(x => { const [k, n] = x.split(":"); return r[k] ? `<li><b>${n}</b> — ${esc(r[k])}</li>` : ""; }).join("") || "<li>—</li>"}</ul>` +
      (m.etapes_montage.length ? `<h4>Consignes de montage</h4><ol>${m.etapes_montage.map(e => `<li>${esc(e)}</li>`).join("")}</ol>` : "") +
      `<h4>Si ça ne marche pas</h4><ul>${m.pannes.map(e => `<li>${esc(e)}</li>`).join("")}</ul>`;
    bindFigures(el);
  }

  function scenarioAnswer(m, sc) {
    const g = sc.gbf || {}, wave = g.kind === "square" ? "square" : g.kind === "triangle" ? "triangle" : "sine";
    const ge = { f: g.f || 1000, vpp: (g.charge === "50" ? 2 : 1) * (g.vpp || 1), offset: g.offset || 0, wave, on: true };
    const c = presetConditions(), an = Engine.analyze(wiringOfSolution(m), envFor(m.cables, ge, c.psu), ge);
    if (!an.supported) return `<span class="mut">Non simulé : ${esc(an.reasons.join(" "))}</span>`;
    const T = 1 / ge.f, w = Engine.waveforms(an, ge, niceUp(T * 3 / 10), 600);
    const sat = an.hasOpamp && w.stats.ch2.max >= an.rails.hi - 0.05;
    return `Vpp(1) = ${fmtV(w.stats.ch1.vpp)} · Vpp(2) = ${fmtV(w.stats.ch2.vpp)}<br>|Vs/Ve| = ${an.gain.toFixed(3)} · phase = ${an.phaseDeg.toFixed(0)}°` +
      (sat ? `<br><b>Sortie écrêtée à ±${an.rails.hi.toFixed(1)} V</b> (saturation)` : "") + `<br><span class="mut">Calculé par le moteur sur le câblage corrigé.</span>`;
  }
  function renderQuestions() {
    const m = curMontage(), el = $("#p-quest");
    if (!m) { el.innerHTML = "<p class='mut'>Pas de questions en mode libre.</p>"; return; }
    const qp = pieceList(m, ["q", "enonce"]).filter(([, p]) => p.k === "q");
    const qhead = qp.length ? `<h4>Questions du sujet</h4>` + qp.map(figure).join("") : "";
    if (!m.questions.length) { el.innerHTML = qhead + "<p class='mut'>Aucune question « à prédire » dans les fichiers de prédictions pour ce montage (TP3 : à écrire).</p>"; bindFigures(el); return; }
    el.innerHTML = qhead + (qp.length ? "<h4>À prédire avant de câbler</h4>" : "") + m.questions.map((q, i) => `<div class="q"><div class="mut">${esc(q.titre)}</div><b>${i + 1}. ${esc(q.q)}</b>
      <div><button class="btn" data-q="${i}">voir ce que l'écran affiche</button><div class="reveal" id="rev${i}"></div></div></div>`).join("");
    el.querySelectorAll("[data-q]").forEach(b => b.onclick = () => { const i = +b.dataset.q, r = $("#rev" + i); r.innerHTML = scenarioAnswer(m, m.questions[i]); r.style.display = "block"; });
    bindFigures(el);
  }

  // Boîte de résistances : TOUTE la série E12 (10 Ω → 1 MΩ), en quantité illimitée, + puces + câbles d'appareils
  function resistorBox() {
    const dec = [[10, 82], [100, 820], [1000, 8200], [10000, 82000], [100000, 820000]];
    return `<details open><summary><b>Boîte de résistances E12</b> (10 Ω → 1 MΩ)</summary>` +
      dec.map(([a, b]) => `<div class="row">${E12_ALL.filter(v => v >= a && v <= b).map(v => `<span class="chip" data-r="" data-v="${v}">${ohmLabel(v)}</span>`).join("")}</div>`).join("") +
      `<div class="row"><span class="chip" data-r="" data-v="1000000">1 MΩ</span></div></details>` +
      `<details><summary><b>Puces</b></summary><div class="row">${Object.keys(CHIPS_LIB).map(k => `<span class="chip" data-chip="" data-m="${k}">${k} (${CHIPS_LIB[k].dip} broches)</span>`).join("")}</div></details>` +
      `<details open><summary><b>Câbles d'appareils</b></summary><p class="mut">Clique une prise sur la face d'un appareil, puis la douille de la plaque (BNC 1, BNC 2, VB, VC, MASSE) ou une autre prise d'appareil. BNC avec BNC, banane avec banane. Le T du GBF : deux câbles sur la sortie 1.</p>` +
      `<div class="row"><button class="btn" id="btn-cable-tool">outil « Câble d'appareil »</button></div></details>`;
  }
  function bindBox(el) {
    el.querySelectorAll("[data-r]").forEach(c => c.onclick = () => arm(c.dataset.r || null, +c.dataset.v, "resistor"));
    el.querySelectorAll("[data-chip]").forEach(c => c.onclick = () => arm(c.dataset.chip || null, c.dataset.m, "chip"));
    const bt = el.querySelector("#btn-cable-tool"); if (bt) bt.onclick = () => { document.querySelector('.t-btn[data-tool="cable"]').click(); };
  }

  function renderCompo() {
    const m = curMontage(), el = $("#p-compo");
    if (!m) { el.innerHTML = "<p class='mut'>Mode libre : tout est disponible ci-dessous ; l'outil actif est celui de la barre au-dessus de la plaque.</p>" + resistorBox() + `<p class="mut" id="armed">Aucun composant armé.</p>`; bindBox(el); return; }
    const res = Object.entries(m.composants).filter(([, c]) => c.type === "resistor"), chips = m.puces || [];
    el.innerHTML = `<p class="mut">Choisis la valeur de chaque composant, puis clique les deux trous sur la plaque.</p>` +
      res.map(([name, c]) => {
        const pal = e12Palette(c.ohm), inE12 = isE12(c.ohm);
        return `<div class="cp"><b>${name}</b><div class="row">${pal.map(v => `<span class="chip" data-r="${name}" data-v="${v}">${fmtOhm(v)}</span>`).join("")}</div>` +
          (inE12 ? "" : `<div class="mut">${fmtOhm(c.ohm)} n'est pas dans la série E12 du labo : à réaliser avec deux résistances en série (le sujet impose la série E12).</div>`) + `</div>`;
      }).join("") +
      chips.map(ch => `<div class="cp"><b>${ch.ref}</b><div class="row"><span class="chip" data-chip="${ch.ref}" data-m="${ch.modele}">${ch.modele} (${CHIPS_LIB[ch.modele].dip} broches)</span></div></div>`).join("") +
      `<hr>` + resistorBox() + `<p class="mut" id="armed">Aucun composant armé.</p>`;
    bindBox(el);
  }
  function arm(ref, val, kind) {
    state.armedRef = ref;
    if (kind === "resistor") { state.resistorVal = val; state.tool = "resistor"; } else { state.chipVal = val; state.tool = "chip"; }
    Cables.cancel();
    document.querySelectorAll(".t-btn").forEach(b => b.classList.toggle("active", b.dataset.tool === state.tool));
    const who = ref ? `<b>${ref}</b>` : (kind === "resistor" ? "Une résistance" : "Une puce");
    $("#armed").innerHTML = `${who} armée${kind === "resistor" ? " = " + fmtOhm(val) : " (" + val + ")"} : ${kind === "resistor" ? "clique les deux trous" : "clique le trou de la broche 1"} sur la plaque.`;
    document.querySelectorAll("#p-compo .chip").forEach(c => c.classList.toggle("on", (ref ? c.dataset.r === ref && +c.dataset.v === val : c.dataset.r === "" && +c.dataset.v === val) || (kind === "chip" && c.dataset.chip === (ref || "") && (ref || c.dataset.m === val))));
    syncToolbar();
  }

  // ---------- corrigé pas à pas, en indirect ----------
  const sameEnds = (a, b, c, d) => (a === c && b === d) || (a === d && b === c);
  function steps(m) {
    const st = [];
    (m.puces || []).forEach(ch => st.push({ kind: "chip", ref: ch.ref, text: `Poser la puce ${ch.ref} (${ch.modele}), encoche vers le haut`, hint: `bloc ${ch.bloc}, broche 1 en rangée ${ch.rangee_broche1} (broche 1 = ${Engine.pinHole(ch, 1, CHIPS_LIB)})`,
      done: () => state.placedChips.some(c => c.ref === ch.ref && c.bloc === ch.bloc && c.rangee_broche1 === ch.rangee_broche1), put: () => { state.placedChips = state.placedChips.filter(c => c.ref !== ch.ref).concat([JSON.parse(JSON.stringify(ch))]); } }));
    Object.entries(m.composants).filter(([, c]) => c.type === "resistor").forEach(([n, c]) => st.push({ kind: "res", text: `Poser ${n} = ${fmtOhm(c.ohm)}`, hint: `${c.a} → ${c.b}`,
      done: () => state.placedComps.some(x => x.name === n && x.ohm === c.ohm && sameEnds(x.a, x.b, c.a, c.b)), put: () => { state.placedComps = state.placedComps.filter(x => x.name !== n).concat([{ name: n, type: "resistor", a: c.a, b: c.b, ohm: c.ohm, etiquette: fmtOhm(c.ohm) }]); } }));
    (m.cables || []).forEach(c => st.push({ kind: "cable", text: `Câble ${c.id} — ${c.nom || ""}` + (c.role ? ` : ${c.role}` : ""), hint: `${Cables.label(c.de)} ↔ ${Cables.label(c.vers)}` + (c.via ? " (par l'adaptateur en T)" : ""),
      done: () => state.placedCables.some(x => sameEnds(x.de, x.vers, c.de, c.vers)), put: () => { if (!state.placedCables.some(x => sameEnds(x.de, x.vers, c.de, c.vers))) state.placedCables.push(cableOf(c)); } }));
    (m.fils || []).forEach(w => st.push({ kind: "wire", text: w.role || `Fil ${w.n}`, hint: `${w.de} → ${w.vers} (${w.couleur || "—"})`,
      done: () => state.placedWires.some(x => sameEnds(x.de, x.vers, w.de, w.vers)), put: () => { if (!state.placedWires.some(x => sameEnds(x.de, x.vers, w.de, w.vers))) state.placedWires.push({ n: w.n, de: w.de, vers: w.vers, couleur: w.couleur || "rouge" }); } }));
    return st;
  }
  let _steps = [];
  function refreshSteps() {
    const m = curMontage(), el = $("#p-corr");
    if (!m) { el.innerHTML = "<p class='mut'>Pas de corrigé en mode libre.</p>"; return; }
    _steps = steps(m);
    const done = _steps.filter(s => s.done()).length, prev = prevId(m);
    el.innerHTML = `<div class="row"><button class="btn" id="btn-prev" ${prev ? "" : "disabled"}>⇤ partir de « ${prev ? esc(shortTitle(MONTAGES[prev])) : "—"} »</button></div>
      <p class="mut">${done} / ${_steps.length} étapes en place. Essaie d'abord seul : rôle → indice → poser.</p>` +
      _steps.map((s, i) => `<div class="step ${s.done() ? "done" : ""} ${open.has(i) ? "open" : ""}"><b>${s.done() ? "✓" : i + 1 + "."}</b> ${esc(s.text)}
        <div class="acts"><button class="btn sm" data-h="${i}">indice</button><button class="btn sm" data-p="${i}">poser</button></div><code>${esc(s.hint)}</code></div>`).join("") +
      `<div class="row"><button class="btn" id="btn-all">tout poser (dernier recours)</button></div>`;
    el.querySelectorAll("[data-h]").forEach(b => b.onclick = () => { open.add(+b.dataset.h); refreshSteps(); });
    el.querySelectorAll("[data-p]").forEach(b => b.onclick = () => { _steps[+b.dataset.p].put(); renderPlacedElements(); });
    $("#btn-all").onclick = () => { putSolution(m); renderPlacedElements(); };
    if (prev) $("#btn-prev").onclick = () => { clearWiring(); putSolution(MONTAGES[prev]); renderPlacedElements(); };
  }

  function init() {
    $("#free").onclick = () => load("libre");
    window.addEventListener("keydown", e => { if (e.key === "Escape") Zoom.close(); });
    $("#tabs").onclick = e => { const p = e.target.dataset.p; if (p) showTab(p); };
    $("#statusline").onclick = () => showTab("etat");
    paintNav();
  }
  function showTab(p) {
    document.querySelectorAll("#tabs button").forEach(b => b.classList.toggle("on", b.dataset.p === p));
    document.querySelectorAll(".pane").forEach(x => x.classList.toggle("on", x.id === "p-" + p));
  }
  return { init, load, paintNav, refreshSteps, putSolution, clearWiring, showTab };
})();

function syncToolbar() {
  document.getElementById("resistor-select-box").style.display = state.tool === "resistor" ? "flex" : "none";
  document.getElementById("chip-select-box").style.display = state.tool === "chip" ? "flex" : "none";
  const rv = document.getElementById("resistor-val-input"); if (rv && ![...rv.options].some(o => +o.value === state.resistorVal)) rv.add(new Option(String(state.resistorVal), state.resistorVal));
  if (rv) rv.value = state.resistorVal;
  document.getElementById("chip-val-input").value = state.chipVal;
}
