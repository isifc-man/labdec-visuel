// Multimètre (TP1 B : comparer l'oscilloscope et le multimètre quand la forme et la fréquence changent).
// Le modèle exact du multimètre de la salle n'est pas connu (hardware/behavior.yaml) : ses réglages sont donc
// exposés et marqués « hypothèse » : TRMS ou valeur moyenne, bande passante du mode alternatif.
// Les deux pointes se posent sur des trous de la plaque ; 10 MΩ d'entrée sont ajoutés au circuit simulé.
const Dmm = (() => {
  const BWS = [1e3, 1e5, 1e6];
  const fmtBw = b => b >= 1e6 ? (b / 1e6) + " MHz" : b >= 1e3 ? (b / 1e3) + " kHz" : b + " Hz";
  function fmtReading(v) {
    const a = Math.abs(v);
    if (a < 1) return (v * 1e3).toFixed(a < 0.1 ? 2 : 1) + " mV";
    return v.toFixed(a < 10 ? 4 : 3) + " V";
  }
  function reading(an) {
    const d = state.dmm, r = an && an.rec && an.rec.dmm;
    if (!d.v || !d.com) return { txt: "- - - -", note: "Pose les deux pointes (V puis COM) sur la plaque." };
    if (!r) return { txt: "- - - -", note: an && !an.supported ? "Calcul impossible." : "" };
    if (d.mode === "dc") return { txt: fmtReading(r.dc), note: "V⎓ : valeur moyenne de la tension." };
    const f = an.rec.dc ? 0 : (an.rec.T ? 1 / an.rec.T : 0), k = 1 / Math.sqrt(1 + Math.pow(f / d.bw, 2));
    const raw = d.type === "trms" ? r.acRms : 1.1107 * r.acAvgAbs;     // 1,1107 = π / (2√2) : appareil étalonné pour un sinus
    return { txt: fmtReading(raw * k), note: (d.type === "trms" ? "V~ TRMS : valeur efficace vraie" : "V~ « moyenne » : valeur moyenne redressée × 1,11 (juste pour un sinus seulement)") +
      (f > d.bw / 3 ? ` — ⚠ ${fmtBw(f)} : au-delà de la bande passante supposée (${fmtBw(d.bw)}), la lecture chute.` : "") };
  }
  function draw(an) {
    const el = document.getElementById("dmm-panel"); if (!el) return;
    const d = state.dmm, r = reading(an);
    el.innerHTML = `<div class="cap">MULTIMÈTRE <span class="mut">(modèle de la salle inconnu : réglages = hypothèses)</span></div>
      <div class="dmm-body"><div class="dmm-lcd">${r.txt}<small>${d.mode === "dc" ? "DC" : "AC"}</small></div>
      <div class="dmm-keys">
        <button class="btn sm${d.mode === "dc" ? " on" : ""}" data-dmm="dc">V⎓</button><button class="btn sm${d.mode === "ac" ? " on" : ""}" data-dmm="ac">V~</button>
        <button class="btn sm" data-dmm="type" title="Multimètre TRMS (valeur efficace vraie) ou à valeur moyenne">${d.type === "trms" ? "TRMS" : "moyenne"}</button>
        <button class="btn sm" data-dmm="bw" title="Bande passante supposée du mode alternatif">BP ${fmtBw(d.bw)}</button>
        <button class="btn sm${state.tool === "dmmv" ? " on" : ""}" data-dmm="pv" style="border-color:#ef4444">pointe V ${d.v ? "✓" : ""}</button>
        <button class="btn sm${state.tool === "dmmcom" ? " on" : ""}" data-dmm="pc">pointe COM ${d.com ? "✓" : ""}</button>
        <button class="btn sm" data-dmm="off">retirer</button></div></div>
      <div class="mut dmm-note">${r.note}</div>`;
    el.querySelectorAll("[data-dmm]").forEach(b => b.onclick = () => press(b.dataset.dmm));
  }
  function press(k) {
    const d = state.dmm;
    if (k === "dc" || k === "ac") d.mode = k;
    else if (k === "type") d.type = d.type === "trms" ? "avg" : "trms";
    else if (k === "bw") d.bw = BWS[(BWS.indexOf(d.bw) + 1) % BWS.length];
    else if (k === "pv" || k === "pc") { state.tool = k === "pv" ? "dmmv" : "dmmcom"; if (typeof syncToolbar === "function") syncToolbar(); }
    else if (k === "off") { d.v = d.com = null; renderPlacedElements(); return; }
    refreshAll();
  }
  function placeProbe(hid) {
    if (state.tool === "dmmv") state.dmm.v = hid; else state.dmm.com = hid;
    state.tool = "wire"; if (typeof syncToolbar === "function") syncToolbar();
    renderPlacedElements();
  }
  return { draw, placeProbe, reading };
})();
