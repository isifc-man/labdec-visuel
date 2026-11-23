// Vérifications du câblage de l'élève, indépendantes de l'endroit où il a posé ses pièces sur la plaque :
//  · nœuds du montage : on compare les BORNES (puces, composants, douilles), pas les trous du corrigé ;
//    les résistances sont appariées par valeur et dans les deux sens, les puces par modèle ;
//  · contrôles physiques : deux pattes dans un même trou, composant court-circuité (moteur), etc.

// identité d'une borne dans le corrigé -> ensemble de bornes candidates chez l'élève (selon l'appariement)
function _terminalKind(t) {
  if (/^(BNC\d|VB|VC|MASSE|BANANE_ROUGE|BANANE_NOIRE)\.(core|shield|main)$/.test(t)) return "conn";
  if (/^[A-Za-z_]\w*\.(a|b|k|\d+)$/.test(t)) return "pin";
  return "hole";
}
function _studentUF() {
  const uf = new Engine.UF();
  HOLES.forEach(h => uf.u(h.id, h.net));
  state.placedChips.forEach(ch => {
    const spec = CHIPS_LIB[ch.modele];
    if (spec) for (let p = 1; p <= spec.dip; p++) uf.u(`${ch.ref}.${p}`, Engine.pinHole(ch, p, CHIPS_LIB));
  });
  state.placedComps.forEach(c => { uf.u(`${c.name}.a`, c.a); if (c.type === "led") uf.u(`${c.name}.k`, c.k); else uf.u(`${c.name}.b`, c.b); });
  state.placedWires.forEach(w => uf.u(w.de, w.vers));
  return uf;
}
function* _perms(arr) { if (arr.length <= 1) { yield arr.slice(); return; } for (let i = 0; i < arr.length; i++) { const rest = arr.slice(0, i).concat(arr.slice(i + 1)); for (const p of _perms(rest)) yield [arr[i]].concat(p); } }

// Évalue les nœuds du montage courant avec le meilleur appariement possible des pièces de l'élève.
function nodeChecklist() {
  const m = curMontage();
  if (!m || !m.noeuds) return { items: [], done: 0, total: 0, allOk: false };
  const uf = _studentUF();
  // pièces du corrigé
  const expRes = Object.entries(m.composants || {}).filter(([, c]) => c.type === "resistor").map(([n, c]) => ({ n, ohm: c.ohm }));
  const expLed = Object.entries(m.composants || {}).filter(([, c]) => c.type === "led").map(([n]) => n);
  const expChips = (m.puces || []).map(c => ({ n: c.ref, model: c.modele }));
  const stRes = state.placedComps.filter(c => c.type === "resistor"), stLed = state.placedComps.filter(c => c.type === "led");
  // candidats : résistances de même valeur, LED dans l'ordre, puces de même modèle
  const resOpts = expRes.map(r => stRes.filter(s => +s.ohm === +r.ohm).map(s => s.name));
  const chipOpts = expChips.map(c => state.placedChips.filter(s => s.modele === c.model).map(s => s.ref));
  const nodes = Object.entries(m.noeuds);
  const mapTerm = (t, map) => {
    if (_terminalKind(t) === "hole") return null;                    // trou du corrigé : l'élève peut être ailleurs
    if (_terminalKind(t) === "conn") return [t];
    const [obj, pin] = t.split(".");
    if (obj in map) { const tgt = map[obj]; if (tgt == null) return null; if (pin === "a" || pin === "b") { if (tgt.flip) return [tgt.n + "." + (pin === "a" ? "b" : "a")]; } return [tgt.n + "." + pin]; }
    return null;                                                     // pièce sans équivalent chez l'élève (ex. 20 kΩ fait de 2 × 10 kΩ)
  };
  const score = map => {
    let ok = 0; const res = nodes.map(([name, terms]) => {
      const mapped = terms.map(t => mapTerm(t, map)).filter(Boolean).map(x => x[0]);
      const good = mapped.length < 2 || mapped.slice(1).every(x => uf.c(mapped[0], x));
      if (good) ok++;
      return { name, good, shown: terms.filter(t => _terminalKind(t) !== "hole") };
    });
    return { ok, res };
  };
  // énumération bornée des appariements
  let best = null;
  const pick = (opts, i, used, acc, out) => {
    if (i === opts.length) { out.push(acc.slice()); return out.length < 400; }
    const choices = opts[i].filter(n => !used.has(n));
    if (!choices.length) { acc.push(null); const r = pick(opts, i + 1, used, acc, out); acc.pop(); return r; }
    for (const n of choices) { used.add(n); acc.push(n); const r = pick(opts, i + 1, used, acc, out); acc.pop(); used.delete(n); if (!r) return false; }
    return true;
  };
  const resMaps = []; pick(resOpts, 0, new Set(), [], resMaps);
  const chipMaps = []; pick(chipOpts, 0, new Set(), [], chipMaps);
  const nFlip = Math.min(expRes.length, 5);
  for (const rm of resMaps) for (const cm of chipMaps) for (let fl = 0; fl < (1 << nFlip); fl++) {
    const map = {};
    expRes.forEach((r, i) => { map[r.n] = rm[i] == null ? null : { n: rm[i], flip: i < nFlip && !!(fl >> i & 1) }; });
    expChips.forEach((c, i) => { map[c.n] = cm[i] == null ? null : { n: cm[i] }; });
    expLed.forEach((l, i) => { map[l] = stLed[i] ? { n: stLed[i].name } : null; });
    const s = score(map);
    if (!best || s.ok > best.ok) best = s;
    if (best.ok === nodes.length) break;
  }
  const items = best ? best.res : [];
  const done = items.filter(i => i.good).length;
  const piecesOk = expChips.every((c, i) => chipOpts[i].length) && expLed.length <= stLed.length;
  return { items, done, total: nodes.length, allOk: done === nodes.length && nodes.length > 0 && piecesOk };
}

// Deux pattes (fil, composant, broche de puce) dans le même trou : impossible sur une vraie plaque
function doubleHoles() {
  const use = new Map(), add = (h, who) => { if (!h || /\.(core|shield|main)$/.test(h)) return; (use.get(h) || use.set(h, []).get(h)).push(who); };
  state.placedWires.forEach((w, i) => { add(w.de, "fil " + (i + 1)); add(w.vers, "fil " + (i + 1)); });
  state.placedComps.forEach(c => { add(c.a, c.name); add(c.type === "led" ? c.k : c.b, c.name); });
  state.placedChips.forEach(ch => { const spec = CHIPS_LIB[ch.modele]; if (spec) for (let p = 1; p <= spec.dip; p++) add(Engine.pinHole(ch, p, CHIPS_LIB), `${ch.ref} broche ${p}`); });
  return [...use.entries()].filter(([, w]) => w.length > 1);
}

function updateElectricalChecklist() {
  const m = MONTAGES[state.currentMontage];
  const checklistBox = document.getElementById("checklist-box");
  const scoreTag = document.getElementById("score-tag");
  const alertsBox = document.getElementById("alerts-box");
  const alerts = [];
  doubleHoles().forEach(([h, w]) => alerts.push(`<div class='alert-row alert-warn'>⚠️ Trou ${h} : ${w.join(" + ")} — une seule patte par trou sur une vraie plaque.</div>`));

  if (!m || !m.noeuds) {
    checklistBox.innerHTML = "<div style='font-size:11px;color:var(--text-muted);'>Mode libre actif.</div>";
    scoreTag.textContent = "Libre"; scoreTag.style.background = "#0284c7";
    alertsBox.innerHTML = alerts.join("") || "<div class='alert-row alert-info'>Mode libre : les alertes du moteur sont dans « Moteur » ci-dessus.</div>";
    return;
  }
  const r = nodeChecklist();
  checklistBox.innerHTML = r.items.map(it => it.good
    ? `<div class="checklist-item done"><span>✓</span><div><b>Nœud ${it.name}</b> <span style="font-size:10px;opacity:0.8">${it.shown.slice(0, 3).join(", ")}${it.shown.length > 3 ? "…" : ""}</span></div></div>`
    : `<div class="checklist-item missing"><span>○</span><div><b>Nœud ${it.name}</b> <span style="font-size:10px;color:var(--text-muted)">Relier : ${it.shown.join(" — ")}</span></div></div>`).join("") +
    `<div class="mut" style="font-size:10px;margin-top:4px">Les nœuds se jugent sur les bornes (puces, composants, douilles), où que tu les aies posés sur la plaque.</div>`;
  scoreTag.textContent = `${r.done} / ${r.total}`;
  scoreTag.style.background = r.allOk ? "var(--ok)" : "#0284c7";
  const cm = circuitMatch();
  if (r.allOk && cm && cm.status === "ok" && !alerts.length) alerts.push("<div class='alert-row alert-ok'>🎉 Montage validé : nœuds reliés et écran conforme.</div>");
  else if (!alerts.length) alerts.push("<div class='alert-row alert-info'>Contrôles physiques (courts-circuits, alimentation, puces) : voir « Moteur » ci-dessus.</div>");
  alertsBox.innerHTML = alerts.join("");
}

function updatePlacedTable() {
  let rows = "", idx = 1;
  state.placedChips.forEach((ch, i) => {
    rows += `<tr><td>${idx++}</td><td>Puce ${ch.ref}</td><td>${ch.modele}</td><td>R.${ch.rangee_broche1}</td><td><button class="wire-del" onclick="delChip(${i})">×</button></td></tr>`;
  });
  state.placedComps.forEach((c, i) => {
    rows += `<tr><td>${idx++}</td><td>${c.name} ${c.etiquette || ""}</td><td>${c.a}</td><td>${c.type === "led" ? c.k : c.b}</td><td><button class="wire-del" onclick="delComp(${i})">×</button></td></tr>`;
  });
  state.placedCables.forEach((c, i) => {
    rows += `<tr><td>${idx++}</td><td>Câble ${c.id}</td><td>${Cables.label(c.de)}</td><td>${Cables.label(c.vers)}</td><td><button class="wire-del" onclick="Cables.removeIndex(${i})">×</button></td></tr>`;
  });
  state.placedWires.forEach((w, i) => {
    rows += `<tr><td>${idx++}</td><td>Fil</td><td>${w.de}</td><td>${w.vers}</td><td><button class="wire-del" onclick="delWire(${i})">×</button></td></tr>`;
  });
  document.getElementById("placed-tbody").innerHTML = rows;
  document.getElementById("placed-num").textContent = (idx - 1);
}

window.delWire = i => { state.placedWires.splice(i, 1); renderPlacedElements(); };
window.delComp = i => { state.placedComps.splice(i, 1); renderPlacedElements(); };
window.delChip = i => { state.placedChips.splice(i, 1); renderPlacedElements(); };
