// Oscilloscope Keysight DSOX1202A : touches + écran calculé à partir du montage (Engine).
// Mise en page de l'écran relevée sur scope_screen_empty.jpg et scope_tp2_b.jpg :
//   bandeau du haut (V/div des voies, 0.0s, temps/div, Auto, ⚡ niveau) · grille 10 × 8 · menu bleu à droite · barre de mesures en bas.
const Scope = (() => {
  let els = null, cv = null, ctx = null;
  const CH_COL = { 1: "#facc15", 2: "#22c55e" };
  const MEAS_PAGES = [
    [["Moy - PE(1):", 1, "mean"], ["Fréq(1):", 1, "freq"], ["Max(1):", 1, "max"], ["Max(2):", 2, "max"]],
    [["Cr-cr(1):", 1, "vpp"], ["Cr-cr(2):", 2, "vpp"], ["Phase(2→1):", 2, "phase"], ["Fréq(1):", 1, "freq"]],
  ];

  function init(root) {
    els = Faces.build("scope", root, { press, turn });
    cv = els.canvas; ctx = cv.getContext("2d");
  }

  const S = () => state.scope;

  function press(id) {
    const s = S();
    switch (id) {
      case "autoscale": autoscale(); break;
      case "default": Object.assign(state.scope, factoryInstruments().scope); break;
      case "runstop": s.running = !s.running; s.frozen = s.running ? null : (current || null); break;
      case "single": s.running = false; s.frozen = current || null; break;
      case "meas": s.measPage = (s.measPage + 1) % MEAS_PAGES.length; break;
      case "cursors": s.cursors = !s.cursors; break;
      case "ch1": case "ch2": {
        const n = id === "ch1" ? 1 : 2, c = s.ch[n];
        if (!c.on) { c.on = true; s.selCh = n; } else if (s.selCh !== n) s.selCh = n; else c.on = false;
        break;
      }
      case "knob_trig": { if (current && current.w && current.w.hasCh1) s.trigLevel = (current.w.stats.ch1.max + current.w.stats.ch1.min) / 2; break; }
      default: return;
    }
    refreshAll();
  }

  function turn(id, d) {
    const s = S();
    if (id === "knob_v1" || id === "knob_v2") { const c = s.ch[id === "knob_v1" ? 1 : 2]; c.vdiv = nextSeq(c.vdiv, -d); }
    else if (id === "knob_pos1" || id === "knob_pos2") { const c = s.ch[id === "knob_pos1" ? 1 : 2]; c.pos = Math.max(-4, Math.min(4, +(c.pos + d * 0.2).toFixed(2))); }
    else if (id === "knob_horiz") s.tdiv = nextSeq(s.tdiv, -d);
    else if (id === "knob_trig") s.trigLevel = +(s.trigLevel + d * 0.1 * s.ch[1].vdiv).toFixed(4);
    else if (id === "knob_entry" && s.cursors) s.curs.y1 = Math.max(-4, Math.min(4, +(s.curs.y1 + d * 0.1).toFixed(2)));
    else return;
    refreshAll();
  }

  // Auto Scale : voie 1 dans la bande du haut, voie 2 dans celle du bas (offsets ≈ ±2 carreaux, notes de scope.yaml)
  function autoscale() {
    const an = getAnalysis(), g = gbfEngine(state.gbf), s = S();
    if (!an.probes.ch1 || !state.gbf.on) return;
    const T = 1 / g.f;
    s.tdiv = niceUp(T * 3 / 10);
    const w = Engine.waveforms(an, g, s.tdiv, 400);
    [[1, w.stats.ch1, w.hasCh1], [2, w.stats.ch2, w.hasCh2]].forEach(([n, st, ok]) => {
      if (ok && st.vpp > 1e-9) { s.ch[n].on = true; s.ch[n].vdiv = niceUp(st.vpp / 3); }
    });
    s.ch[1].pos = 2; s.ch[2].pos = -2;
    s.trigLevel = 0;
  }

  let current = null;       // dernière acquisition affichée {w, shift, trig}

  function acquire(an) {
    const s = S();
    if (!s.running && s.frozen) return s.frozen;
    const g = gbfEngine(state.gbf);
    const shift = Engine.trigShift(an, g, s.trigLevel);
    const w = Engine.waveforms(an, g, s.tdiv, 900, shift == null ? 0 : shift);
    return { w, trig: shift != null, tdiv: s.tdiv, an };
  }

  // ---------- mesures ---------------------------------------------------------------
  function freqOf(arr, t, mid) {
    const cr = [];
    for (let i = 1; i < arr.length; i++) if (arr[i - 1] < mid && arr[i] >= mid) cr.push(t[i - 1] + (mid - arr[i - 1]) / (arr[i] - arr[i - 1]) * (t[i] - t[i - 1]));
    return cr.length >= 2 ? (cr.length - 1) / (cr[cr.length - 1] - cr[0]) : null;
  }
  const sig3 = v => { const a = Math.abs(v); return a >= 100 ? v.toFixed(0) : a >= 10 ? v.toFixed(1) : a >= 1 ? v.toFixed(2) : v.toFixed(3); };
  function fmtM(v) { const a = Math.abs(v); if (a >= 1) return sig3(v) + "V"; if (a >= 1e-3) return sig3(v * 1e3) + "mV"; return sig3(v * 1e6) + "µV"; }
  function measure(kind, ch, acq, an) {
    const w = acq.w, has = ch === 1 ? w.hasCh1 : w.hasCh2, on = S().ch[ch].on;
    if (!has || !on) return "Aucun signal";
    const arr = ch === 1 ? w.v1 : w.v2, st = ch === 1 ? w.stats.ch1 : w.stats.ch2;
    if (kind === "mean") return fmtM(st.mean);
    if (kind === "max") return fmtM(st.max);
    if (kind === "vpp") return fmtM(st.vpp);
    if (kind === "freq") { const f = st.vpp > 1e-9 ? freqOf(arr, w.t, (st.max + st.min) / 2) : null; return f ? (f >= 1e3 ? sig3(f / 1e3) + "kHz" : sig3(f) + "Hz") : "Aucun signal"; }
    if (kind === "phase") return an.phaseDeg == null || !w.hasCh1 ? "Aucun signal" : an.phaseDeg.toFixed(1) + "°";
    return "";
  }

  // ---------- dessin ------------------------------------------------------------------
  function draw(an) {
    if (!ctx) return;
    const s = S(), acq = acquire(an);
    current = acq;
    const W = cv.width, H = cv.height, u = W / 800;
    ctx.fillStyle = "#020b16"; ctx.fillRect(0, 0, W, H);
    const gx = 0.03 * W, gy = 0.095 * H, gw = 0.72 * W, gh = 0.72 * H, dx = gw / 10, dy = gh / 8, cx = gx + gw / 2, cy = gy + gh / 2;

    // grille
    ctx.strokeStyle = "rgba(70,120,190,.55)"; ctx.lineWidth = 1; ctx.beginPath();
    for (let i = 0; i <= 10; i++) { ctx.moveTo(gx + i * dx, gy); ctx.lineTo(gx + i * dx, gy + gh); }
    for (let j = 0; j <= 8; j++) { ctx.moveTo(gx, gy + j * dy); ctx.lineTo(gx + gw, gy + j * dy); }
    ctx.stroke();
    ctx.strokeStyle = "rgba(120,170,235,.85)"; ctx.beginPath(); ctx.moveTo(cx, gy); ctx.lineTo(cx, gy + gh); ctx.moveTo(gx, cy); ctx.lineTo(gx + gw, cy); ctx.stroke();
    ctx.lineWidth = 1; ctx.beginPath();                                   // graduations fines sur les axes centraux
    for (let i = 0; i <= 50; i++) { const x = gx + i * dx / 5; ctx.moveTo(x, cy - 3 * u); ctx.lineTo(x, cy + 3 * u); }
    for (let j = 0; j <= 40; j++) { const y = gy + j * dy / 5; ctx.moveTo(cx - 3 * u, y); ctx.lineTo(cx + 3 * u, y); }
    ctx.stroke();

    // bandeau du haut
    ctx.font = `${13 * u}px Arial`; ctx.textBaseline = "middle";
    const ty = gy * 0.52;
    [1, 2].forEach(n => {
      const c = s.ch[n]; ctx.fillStyle = c.on ? CH_COL[n] : "#556";
      ctx.fillText(`${n}  ${fmtVdiv(c.vdiv)}/`, gx + (n - 1) * 95 * u, ty);
    });
    ctx.fillStyle = "#e5e7eb";
    ctx.fillText("0.0s", cx - 55 * u, ty);
    ctx.fillText(fmtT(s.tdiv).replace(" ", "") + "/", cx + 5 * u, ty);
    ctx.fillStyle = s.running ? "#e5e7eb" : "#f87171";
    ctx.fillText(s.running ? (acq.trig ? "Trig'd" : "Auto") : "Stop", cx + 80 * u, ty);
    ctx.fillStyle = "#facc15"; ctx.fillText(`⚡ 1  ${fmtM(s.trigLevel)}`, gx + gw - 95 * u, ty);

    // traces (zone de grille seulement)
    const w = acq.w;
    ctx.save(); ctx.beginPath(); ctx.rect(gx, gy, gw, gh); ctx.clip();
    [[1, w.v1, w.hasCh1], [2, w.v2, w.hasCh2 || (an.probes.ch2 && true)]].forEach(([n, arr]) => {
      const c = s.ch[n];
      if (!c.on || !arr || (n === 1 && !w.hasCh1) || (n === 2 && !an.probes.ch2)) return;
      ctx.strokeStyle = CH_COL[n]; ctx.lineWidth = 2 * u; ctx.beginPath();
      for (let i = 0; i < arr.length; i++) {
        const x = gx + i / (arr.length - 1) * gw, y = cy - (arr[i] / c.vdiv + c.pos) * dy;
        i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
      }
      ctx.stroke();
    });
    // niveau de déclenchement
    ctx.strokeStyle = "rgba(250,204,21,.7)"; ctx.setLineDash([3 * u, 5 * u]); ctx.beginPath();
    const ty1 = cy - (s.trigLevel / s.ch[1].vdiv + s.ch[1].pos) * dy; ctx.moveTo(gx, ty1); ctx.lineTo(gx + gw, ty1); ctx.stroke(); ctx.setLineDash([]);
    if (s.cursors) {
      ctx.strokeStyle = "#f97316"; ctx.setLineDash([5 * u, 4 * u]); ctx.beginPath();
      [s.curs.x1, s.curs.x2].forEach(x => { ctx.moveTo(cx + x * dx, gy); ctx.lineTo(cx + x * dx, gy + gh); });
      [s.curs.y1, s.curs.y2].forEach(y => { ctx.moveTo(gx, cy - y * dy); ctx.lineTo(gx + gw, cy - y * dy); });
      ctx.stroke(); ctx.setLineDash([]);
    }
    ctx.restore();

    // fanions de niveau zéro de chaque voie (à gauche, à la hauteur du 0 V)
    [1, 2].forEach(n => {
      const c = s.ch[n]; if (!c.on) return;
      const y = cy - c.pos * dy;
      ctx.fillStyle = CH_COL[n]; ctx.fillRect(gx - 12 * u, y - 7 * u, 12 * u, 14 * u);
      ctx.fillStyle = "#000"; ctx.font = `bold ${10 * u}px Arial`; ctx.textAlign = "center"; ctx.fillText(String(n), gx - 6 * u, y); ctx.textAlign = "left";
    });

    // menu bleu de droite
    const mx = gx + gw + 0.012 * W, mw = W - mx - 0.008 * W;
    ctx.fillStyle = "#143e7a"; ctx.fillRect(mx, gy, mw, gh);
    ctx.fillStyle = "#e11d48"; ctx.font = `bold ${12 * u}px Arial`; ctx.fillText("▲▼ KEYSIGHT", mx + 8 * u, gy + 14 * u);
    const head = (t, y) => { ctx.fillStyle = "#38bdf8"; ctx.fillRect(mx + 4 * u, y, mw - 8 * u, 15 * u); ctx.fillStyle = "#04101c"; ctx.font = `bold ${11 * u}px Arial`; ctx.textAlign = "center"; ctx.fillText(t, mx + mw / 2, y + 8 * u); ctx.textAlign = "left"; };
    const line = (t, y, col) => { ctx.fillStyle = col || "#dbeafe"; ctx.font = `${11 * u}px Arial`; ctx.fillText(t, mx + 10 * u, y); };
    if (s.cursors) {
      head("Curseurs", gy + 34 * u);
      const dT = Math.abs(s.curs.x2 - s.curs.x1) * s.tdiv, dV = Math.abs(s.curs.y2 - s.curs.y1) * s.ch[1].vdiv;
      line("ΔX " + fmtT(dT), gy + 62 * u); line("1/ΔX " + (dT > 0 ? fmtHz(1 / dT) : "—"), gy + 80 * u); line("ΔY(1) " + fmtM(dV), gy + 98 * u);
    } else {
      head("Acquisition", gy + 34 * u); line("Normal", gy + 62 * u); line("2.00GSa/s", gy + 78 * u);
      head("Voies", gy + 96 * u); line("DC    1.00:1", gy + 124 * u, CH_COL[1]); line("DC    1.00:1", gy + 140 * u, CH_COL[2]);
      head("Math", gy + 156 * u); line("Ch1 + Ch2", gy + 184 * u); line(fmtVdiv(s.ch[1].vdiv) + "/", gy + 200 * u);
    }

    // barre du bas : 4 mesures
    ctx.fillStyle = "#0a0f18"; ctx.fillRect(0, H * 0.862, W, H * 0.138);
    MEAS_PAGES[s.measPage].forEach(([label, ch, kind], i) => {
      const x = W * (0.03 + i * 0.205), col = kind === "phase" ? CH_COL[2] : CH_COL[ch];
      ctx.fillStyle = col; ctx.font = `${12 * u}px Arial`; ctx.fillText(label, x, H * 0.9);
      ctx.fillStyle = "#f1f5f9"; ctx.fillText(measure(kind, ch, acq, an), x + 12 * u, H * 0.955);
    });
    // état des touches
    Faces.setLit("scope", "ch1", s.ch[1].on); Faces.setLit("scope", "ch2", s.ch[2].on);
    els.runstop.classList.toggle("stopped", !s.running);
    els.cursors.classList.toggle("lit", s.cursors);
    els.ch1.classList.toggle("sel", s.selCh === 1); els.ch2.classList.toggle("sel", s.selCh === 2);
  }

  const fmtVdiv = v => v >= 1 ? v.toFixed(2).replace(/\.?0+$/, "") + "V" : (v * 1e3).toFixed(0) + "mV";
  return { init, draw, press, turn };
})();
