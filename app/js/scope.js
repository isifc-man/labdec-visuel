// Oscilloscope Keysight DSOX1202A : touches + écran calculé à partir de l'enregistrement du moteur.
// Comme le vrai appareil : mesures sur la fenêtre affichée (avec la pleine résolution de l'enregistrement),
// affichage min/max par colonne (bande « pleine » quand le signal est trop rapide pour la base de temps, jamais de faux signal),
// déclenchement sur la voie choisie, front montant ou descendant ; niveau hors du signal → image instable (« Auto »).
const Scope = (() => {
  let els = null, cv = null, ctx = null;
  const CH_COL = { 1: "#facc15", 2: "#22c55e" };
  const MEAS_PAGES = [
    [["Moy - PE(1):", 1, "mean"], ["Fréq(1):", 1, "freq"], ["Max(1):", 1, "max"], ["Max(2):", 2, "max"]],
    [["Cr-cr(1):", 1, "vpp"], ["Cr-cr(2):", 2, "vpp"], ["Phase(2→1):", 2, "phase"], ["Fréq(1):", 1, "freq"]],
    [["Min(1):", 1, "min"], ["Min(2):", 2, "min"], ["Moy - PE(2):", 2, "mean"], ["Fréq(2):", 2, "freq"]],
  ];
  const NCOL = 520;

  function init(root) {
    els = Faces.build("scope", root, { press, turn });
    cv = els.canvas; ctx = cv.getContext("2d");
    setInterval(() => { const s = S(); if (s.running && current && !current.trig && current.moving) { draw(getAnalysis()); if (typeof Dock !== "undefined") Dock.update(); } }, 160);
  }

  const S = () => state.scope;

  function press(id) {
    const s = S();
    switch (id) {
      case "autoscale": autoscale(); break;
      case "default": Object.assign(state.scope, factoryInstruments().scope); break;
      case "runstop": s.running = !s.running; s.frozen = s.running ? null : (current || null); break;
      case "single": s.running = false; s.frozen = current && current.trig ? current : null; break;
      case "meas": s.menu = s.menu === "meas" ? "home" : "meas"; break;
      case "trigmenu": s.menu = s.menu === "trig" ? "home" : "trig"; break;
      case "cursors": s.cursors = !s.cursors; s.menu = s.cursors ? "curs" : "home"; break;
      case "back": s.menu = "home"; break;
      case "sk1": case "sk2": case "sk3": case "sk4": case "sk5": case "sk6": softkey(+id[2]); break;
      case "ch1": case "ch2": {
        const n = id === "ch1" ? 1 : 2, c = s.ch[n];
        if (!c.on) { c.on = true; s.selCh = n; } else if (s.selCh !== n) s.selCh = n; else c.on = false;
        break;
      }
      case "knob_trig": { const an = getAnalysis(); if (an.rec && an.rec.ch["ch" + s.trigSrc]) { const st = an.rec.stats["ch" + s.trigSrc]; s.trigLevel = +((st.max + st.min) / 2).toFixed(4); } break; }
      default: return;
    }
    refreshAll();
  }
  function softkey(n) {
    const s = S();
    if (s.menu === "trig") { if (n === 1) s.trigSrc = s.trigSrc === 1 ? 2 : 1; if (n === 2) s.trigSlope = s.trigSlope > 0 ? -1 : 1; if (n === 3) s.trigMode = s.trigMode === "normal" ? "auto" : "normal"; }
    else if (s.menu === "meas") { if (n === 1) s.measPage = (s.measPage + 1) % MEAS_PAGES.length; }
    else if (s.menu === "curs") { if (n === 1) s.cursSel = (s.cursSel + 1) % 4; }
  }

  function turn(id, d) {
    const s = S();
    if (id === "knob_v1" || id === "knob_v2") { const c = s.ch[id === "knob_v1" ? 1 : 2]; c.vdiv = nextSeq(c.vdiv, -d); }
    else if (id === "knob_pos1" || id === "knob_pos2") { const c = s.ch[id === "knob_pos1" ? 1 : 2]; c.pos = Math.max(-4, Math.min(4, +(c.pos + d * 0.2).toFixed(2))); }
    else if (id === "knob_horiz") s.tdiv = Math.max(5e-9, Math.min(50, nextSeq(s.tdiv, -d)));
    else if (id === "knob_hpos") s.hpos = +(s.hpos + d * 0.5 * s.tdiv).toPrecision(6);
    else if (id === "knob_trig") s.trigLevel = +(s.trigLevel + d * 0.1 * s.ch[s.trigSrc].vdiv).toFixed(4);
    else if (id === "knob_entry" && s.cursors) { const k = ["x1", "x2", "y1", "y2"][s.cursSel]; s.curs[k] = Math.max(-5, Math.min(5, +(s.curs[k] + d * 0.1).toFixed(2))); }
    else return;
    refreshAll();
  }

  // Auto Scale : base de temps ≈ 3 périodes du signal de déclenchement, voie 1 dans le haut, voie 2 dans le bas
  function autoscale() {
    const an = getAnalysis(), s = S(), rec = an.rec;
    if (!rec || rec.dc) return;
    const src = rec.ch.ch1 ? "ch1" : rec.ch.ch2 ? "ch2" : null; if (!src) return;
    const m = Engine.measure(rec, src, 0, 2 * rec.P + 1e-15) || {};
    const T = m.freq ? 1 / m.freq : rec.T;
    s.tdiv = niceUp(T * 3 / 10); s.hpos = 0;
    let shown = 0;
    [1, 2].forEach(n => { const k = "ch" + n; if (!rec.ch[k]) return; const st = rec.stats[k]; s.ch[n].on = true; s.ch[n].vdiv = niceUp(Math.max(st.max - st.min, 0.01) / 3); shown++;
      s.ch[n].pos = 0; });
    if (shown === 2) [1, 2].forEach(n => { const st = rec.stats["ch" + n], mid = (st.max + st.min) / 2; s.ch[n].pos = +((n === 1 ? 2 : -2) - mid / s.ch[n].vdiv).toFixed(2); });
    else [1, 2].forEach(n => { if (rec.ch["ch" + n]) { const st = rec.stats["ch" + n]; s.ch[n].pos = +(-(st.max + st.min) / 2 / s.ch[n].vdiv).toFixed(2); } });
    s.trigSrc = src === "ch1" ? 1 : 2; s.trigSlope = 1;
    const st = rec.stats[src]; s.trigLevel = +((st.max + st.min) / 2).toFixed(4);
  }

  let current = null, lastTrig = null;       // dernière acquisition affichée / dernière acquisition déclenchée
  function acquire(an) {
    const s = S();
    if (!s.running && s.frozen) return s.frozen;
    const rec = an.rec, win = 10 * s.tdiv;
    if (!rec) return { rec: null, t0: 0, win, trig: false, moving: false };
    let tc = 0, trig = false, moving = false;
    const key = "ch" + s.trigSrc;
    if (!rec.dc && rec.ch[key]) {
      const c = Engine.crossings(rec, key, s.trigLevel, s.trigSlope, 0, rec.P, 1);
      if (c.length) { tc = c[0]; trig = true; }
      else { tc = Math.random() * rec.P; moving = true; }        // pas de déclenchement : chaque acquisition tombe au hasard
    } else if (!rec.dc) { tc = Math.random() * rec.P; moving = true; }
    const t0 = tc - win / 2 + (s.hpos || 0);
    // mode Normal : sans déclenchement, l'écran garde la dernière acquisition déclenchée (ou reste vide)
    if (!trig && s.trigMode === "normal" && !rec.dc) return lastTrig ? Object.assign({}, lastTrig, { waiting: true }) : { rec: null, t0: 0, win, trig: false, moving: false, waiting: true };
    const acq = { rec, t0, win, trig, moving };
    if (trig) lastTrig = acq;
    return acq;
  }

  // ---------- mesures ----------
  const sig3 = v => { const a = Math.abs(v); return a >= 100 ? v.toFixed(0) : a >= 10 ? v.toFixed(1) : a >= 1 ? v.toFixed(2) : v.toFixed(3); };
  function fmtM(v) { const a = Math.abs(v); if (a >= 1 || a < 5e-7) return sig3(a < 5e-7 ? 0 : v) + "V"; if (a >= 1e-3) return sig3(v * 1e3) + "mV"; return sig3(v * 1e6) + "µV"; }
  const fmtF = f => f >= 1e6 ? sig3(f / 1e6) + "MHz" : f >= 1e3 ? sig3(f / 1e3) + "kHz" : sig3(f) + "Hz";
  function measure(kind, ch, acq) {
    const s = S(), key = "ch" + ch;
    if (!acq.rec || !acq.rec.ch[key] || !s.ch[ch].on) return "Aucun signal";
    if (kind === "phase") { const p = Engine.phase(acq.rec); return p == null || !acq.rec.ch.ch1 ? "Aucun signal" : (Math.abs(p) < 0.05 ? 0 : p).toFixed(1) + "°"; }
    const m = Engine.measure(acq.rec, key, acq.t0, acq.t0 + acq.win);
    if (kind === "mean") return fmtM(m.mean);
    if (kind === "max") return fmtM(m.max);
    if (kind === "min") return fmtM(m.min);
    if (kind === "vpp") return fmtM(m.vpp);
    if (kind === "freq") return m.freq ? fmtF(m.freq) : "Aucun front";
    return "";
  }

  // ---------- dessin ----------
  function draw(an) {
    if (!ctx) return;
    const s = S(), acq = acquire(an);
    current = acq;
    const W = cv.width, H = cv.height, u = W / 800;
    ctx.fillStyle = "#020b16"; ctx.fillRect(0, 0, W, H);
    const gx = 0.03 * W, gy = 0.095 * H, gw = 0.72 * W, gh = 0.72 * H, dx = gw / 10, dy = gh / 8, cx = gx + gw / 2, cy = gy + gh / 2;

    ctx.strokeStyle = "rgba(70,120,190,.55)"; ctx.lineWidth = 1; ctx.beginPath();
    for (let i = 0; i <= 10; i++) { ctx.moveTo(gx + i * dx, gy); ctx.lineTo(gx + i * dx, gy + gh); }
    for (let j = 0; j <= 8; j++) { ctx.moveTo(gx, gy + j * dy); ctx.lineTo(gx + gw, gy + j * dy); }
    ctx.stroke();
    ctx.strokeStyle = "rgba(120,170,235,.85)"; ctx.beginPath(); ctx.moveTo(cx, gy); ctx.lineTo(cx, gy + gh); ctx.moveTo(gx, cy); ctx.lineTo(gx + gw, cy); ctx.stroke();
    ctx.lineWidth = 1; ctx.beginPath();
    for (let i = 0; i <= 50; i++) { const x = gx + i * dx / 5; ctx.moveTo(x, cy - 3 * u); ctx.lineTo(x, cy + 3 * u); }
    for (let j = 0; j <= 40; j++) { const y = gy + j * dy / 5; ctx.moveTo(cx - 3 * u, y); ctx.lineTo(cx + 3 * u, y); }
    ctx.stroke();

    // bandeau du haut
    ctx.font = `${13 * u}px Arial`; ctx.textBaseline = "middle";
    const ty = gy * 0.52;
    [1, 2].forEach(n => { const c = s.ch[n]; ctx.fillStyle = c.on ? CH_COL[n] : "#556"; ctx.fillText(`${n}  ${fmtVdiv(c.vdiv)}/`, gx + (n - 1) * 95 * u, ty); });
    ctx.fillStyle = "#e5e7eb";
    ctx.fillText(fmtT(s.hpos || 0).replace(" ", ""), cx - 60 * u, ty);
    ctx.fillText(fmtT(s.tdiv).replace(" ", "") + "/", cx + 5 * u, ty);
    ctx.fillStyle = !s.running ? "#f87171" : acq.trig ? "#e5e7eb" : "#fb923c";
    ctx.fillText(!s.running ? "Stop" : acq.waiting ? "Trig?" : acq.trig ? "Trig'd" : "Auto", cx + 80 * u, ty);
    ctx.fillStyle = CH_COL[s.trigSrc]; ctx.fillText(`${s.trigSlope > 0 ? "↑" : "↓"} ${s.trigSrc}  ${fmtM(s.trigLevel)}`, gx + gw - 95 * u, ty);

    // traces : min/max par colonne
    ctx.save(); ctx.beginPath(); ctx.rect(gx, gy, gw, gh); ctx.clip();
    if (acq.rec) [1, 2].forEach(n => {
      const c = s.ch[n], key = "ch" + n; if (!c.on || !acq.rec.ch[key]) return;
      const v = Engine.view(acq.rec, key, acq.t0, acq.t0 + acq.win, NCOL), Y = val => cy - (val / c.vdiv + c.pos) * dy;
      ctx.strokeStyle = CH_COL[n]; ctx.lineWidth = 1.6 * u; ctx.lineJoin = "round"; ctx.beginPath();
      for (let j = 0; j < NCOL; j++) {
        const x = gx + (j + 0.5) / NCOL * gw, lo = Y(v.max[j]), hi = Y(v.min[j]), st = Y(v.start[j]);
        if (j === 0) ctx.moveTo(x, st);
        if (Math.abs(st - lo) < Math.abs(st - hi)) { ctx.lineTo(x, lo); ctx.lineTo(x, hi); } else { ctx.lineTo(x, hi); ctx.lineTo(x, lo); }
      }
      ctx.stroke();
    });
    // niveau de déclenchement
    ctx.strokeStyle = "rgba(250,204,21,.7)"; ctx.setLineDash([3 * u, 5 * u]); ctx.beginPath();
    const tc = s.ch[s.trigSrc], ty1 = cy - (s.trigLevel / tc.vdiv + tc.pos) * dy; ctx.moveTo(gx, ty1); ctx.lineTo(gx + gw, ty1); ctx.stroke(); ctx.setLineDash([]);
    if (s.cursors) {
      ctx.strokeStyle = "#f97316"; ctx.setLineDash([5 * u, 4 * u]); ctx.beginPath();
      [s.curs.x1, s.curs.x2].forEach(x => { ctx.moveTo(cx + x * dx, gy); ctx.lineTo(cx + x * dx, gy + gh); });
      [s.curs.y1, s.curs.y2].forEach(y => { ctx.moveTo(gx, cy - y * dy); ctx.lineTo(gx + gw, cy - y * dy); });
      ctx.stroke(); ctx.setLineDash([]);
    }
    ctx.restore();

    [1, 2].forEach(n => {
      const c = s.ch[n]; if (!c.on) return;
      const y = Math.max(gy, Math.min(gy + gh, cy - c.pos * dy));
      ctx.fillStyle = CH_COL[n]; ctx.fillRect(gx - 12 * u, y - 7 * u, 12 * u, 14 * u);
      ctx.fillStyle = "#000"; ctx.font = `bold ${10 * u}px Arial`; ctx.textAlign = "center"; ctx.fillText(String(n), gx - 6 * u, y); ctx.textAlign = "left";
    });

    // menu bleu de droite (touches de côté = sk1…sk6)
    const mx = gx + gw + 0.012 * W, mw = W - mx - 0.008 * W;
    ctx.fillStyle = "#143e7a"; ctx.fillRect(mx, gy, mw, gh);
    ctx.fillStyle = "#e11d48"; ctx.font = `bold ${12 * u}px Arial`; ctx.fillText("▲▼ KEYSIGHT", mx + 8 * u, gy + 14 * u);
    const head = (t, y) => { ctx.fillStyle = "#38bdf8"; ctx.fillRect(mx + 4 * u, y, mw - 8 * u, 15 * u); ctx.fillStyle = "#04101c"; ctx.font = `bold ${11 * u}px Arial`; ctx.textAlign = "center"; ctx.fillText(t, mx + mw / 2, y + 8 * u); ctx.textAlign = "left"; };
    const line = (t, y, col) => { ctx.fillStyle = col || "#dbeafe"; ctx.font = `${11 * u}px Arial`; ctx.fillText(t, mx + 10 * u, y); };
    if (s.menu === "curs" || s.cursors) {
      head("Curseurs", gy + 34 * u);
      const dT = Math.abs(s.curs.x2 - s.curs.x1) * s.tdiv, dV = Math.abs(s.curs.y2 - s.curs.y1) * s.ch[s.selCh].vdiv;
      line("ΔX " + fmtT(dT), gy + 62 * u); line("1/ΔX " + (dT > 0 ? fmtHz(1 / dT) : "—"), gy + 80 * u); line(`ΔY(${s.selCh}) ` + fmtM(dV), gy + 98 * u);
      const y1v = (s.curs.y1 - s.ch[s.selCh].pos) * s.ch[s.selCh].vdiv, y2v = (s.curs.y2 - s.ch[s.selCh].pos) * s.ch[s.selCh].vdiv;
      line(`Y1 ${fmtM(y1v)}  Y2 ${fmtM(y2v)}`, gy + 116 * u, CH_COL[s.selCh]);
      line("Touche 1 : curseur actif", gy + 150 * u, "#93c5fd"); line("→ " + ["X1", "X2", "Y1", "Y2"][s.cursSel] + " (molette Entry)", gy + 166 * u, "#facc15");
    } else if (s.menu === "trig") {
      head("Déclenchement", gy + 34 * u);
      line("1 : Source  voie " + s.trigSrc, gy + 62 * u, CH_COL[s.trigSrc]); line("2 : Front  " + (s.trigSlope > 0 ? "montant ↑" : "descendant ↓"), gy + 80 * u);
      line("3 : Mode  " + (s.trigMode === "normal" ? "Normal" : "Auto"), gy + 98 * u); line("Niveau " + fmtM(s.trigLevel), gy + 116 * u);
      line(acq.trig ? "Déclenché" : "Niveau hors du signal :", gy + 150 * u, acq.trig ? "#86efac" : "#fdba74"); if (!acq.trig) line("image instable", gy + 166 * u, "#fdba74");
    } else if (s.menu === "meas") {
      head("Mesures", gy + 34 * u); line(`Page ${s.measPage + 1}/${MEAS_PAGES.length}`, gy + 62 * u); line("Touche 1 : page suivante", gy + 80 * u, "#93c5fd");
    } else {
      head("Acquisition", gy + 34 * u); line("Normal", gy + 62 * u); line("2.00GSa/s", gy + 78 * u);
      head("Voies", gy + 96 * u); line("DC    1.00:1", gy + 124 * u, CH_COL[1]); line("DC    1.00:1", gy + 140 * u, CH_COL[2]);
      line("Trigger / Meas / Cursors :", gy + 176 * u, "#93c5fd"); line("menus à droite", gy + 192 * u, "#93c5fd");
    }

    // barre du bas : 4 mesures
    ctx.fillStyle = "#0a0f18"; ctx.fillRect(0, H * 0.862, W, H * 0.138);
    MEAS_PAGES[s.measPage].forEach(([label, ch, kind], i) => {
      const x = W * (0.03 + i * 0.205), col = CH_COL[ch];
      ctx.fillStyle = col; ctx.font = `${12 * u}px Arial`; ctx.fillText(label, x, H * 0.9);
      ctx.fillStyle = "#f1f5f9"; ctx.fillText(measure(kind, ch, acq), x + 12 * u, H * 0.955);
    });
    Faces.setLit("scope", "ch1", s.ch[1].on); Faces.setLit("scope", "ch2", s.ch[2].on);
    els.runstop.classList.toggle("stopped", !s.running);
    els.cursors.classList.toggle("lit", s.cursors);
    if (els.trigmenu) els.trigmenu.classList.toggle("lit", s.menu === "trig");
    if (els.meas) els.meas.classList.toggle("lit", s.menu === "meas");
    els.ch1.classList.toggle("sel", s.selCh === 1); els.ch2.classList.toggle("sel", s.selCh === 2);
  }

  const fmtVdiv = v => v >= 1 ? v.toFixed(2).replace(/\.?0+$/, "") + "V" : (v * 1e3).toFixed(0) + "mV";
  return { init, draw, press, turn, measureText: (k, ch) => measure(k, ch, current || acquire(getAnalysis())) };
})();
