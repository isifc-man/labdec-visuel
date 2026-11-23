// Alimentation Keysight EDU36311A : 3 voies flottantes (6 V/5 A, 30 V/1 A, 30 V/1 A — ordre des voies supposé, cf. behavior.yaml).
// Écran « Meter View » : tension et courant mesurés de chaque voie. Le courant vient du solveur (courant de la source) :
// la consommation propre du TL081 (~1,4 mA par rail réel) n'est pas modélisée.
const Psu = (() => {
  let els = null, cv = null, ctx = null;
  const P = () => state.psu;
  const COL = { 1: "#facc15", 2: "#4ade80", 3: "#60a5fa" };
  const LIM = { 1: { v: 6, i: 5 }, 2: { v: 30, i: 1 }, 3: { v: 30, i: 1 } };

  function init(root) { els = Faces.build("psu", root, { press, turn }); cv = els.canvas; ctx = cv.getContext("2d"); }

  function press(id) {
    const p = P();
    if (/^k[\d.⌫]$/.test(id)) {
      const ch = id.slice(1);
      if (ch === "⌫") p.buf = p.buf.slice(0, -1);
      else if (ch !== "." || !p.buf.includes(".")) p.buf += ch;
    } else if (id === "enter") {
      const v = parseFloat(p.buf);
      if (!isNaN(v)) { const c = p.ch[p.sel]; if (p.field === "v") c.v = Math.min(LIM[p.sel].v, Math.max(0, v)); else c.i = Math.min(LIM[p.sel].i, Math.max(0.001, v)); }
      p.buf = "";
    } else if (id === "left") { p.sel = p.sel === 1 ? 3 : p.sel - 1; p.buf = ""; }
    else if (id === "right") { p.sel = p.sel === 3 ? 1 : p.sel + 1; p.buf = ""; }
    else if (id === "select") { p.field = p.field === "v" ? "i" : "v"; p.buf = ""; }
    else if (id === "knob_v") { p.field = "v"; }
    else if (id === "knob_i") { p.field = "i"; }
    else if (/^on[123]$/.test(id)) { const k = +id[2]; p.sel = k; p.ch[k].on = !p.ch[k].on; }
    else if (id === "allonoff") { const any = [1, 2, 3].some(k => p.ch[k].on); [1, 2, 3].forEach(k => { p.ch[k].on = !any; }); }
    refreshAll();
  }

  function turn(id, d) {
    const p = P(), c = p.ch[p.sel];
    if (id === "knob_v") { c.v = Math.min(LIM[p.sel].v, Math.max(0, +(c.v + d * 0.1).toFixed(3))); p.field = "v"; }
    else if (id === "knob_i") { c.i = Math.min(LIM[p.sel].i, Math.max(0.001, +(c.i + d * 0.01).toFixed(3))); p.field = "i"; }
    else return;
    refreshAll();
  }

  function draw(an) {
    if (!ctx) return;
    const p = P(), W = cv.width, H = cv.height, u = W / 400;
    ctx.fillStyle = "#06101c"; ctx.fillRect(0, 0, W, H);
    const colW = W * 0.8 / 3;
    [1, 2, 3].forEach(k => {
      const x = 4 + (k - 1) * colW, c = p.ch[k], sel = p.sel === k;
      ctx.fillStyle = "#0b1b2e"; ctx.fillRect(x, 6, colW - 6, H - 40 * u);
      if (sel) { ctx.strokeStyle = "#e2e8f0"; ctx.lineWidth = 2 * u; ctx.strokeRect(x, 6, colW - 6, H - 40 * u); }
      ctx.fillStyle = COL[k]; ctx.fillRect(x, 6, colW - 6, 18 * u);
      ctx.fillStyle = "#04101c"; ctx.font = `bold ${12 * u}px Arial`; ctx.textBaseline = "middle"; ctx.fillText("CH" + k, x + 8 * u, 15 * u);
      const iOut = c.on && an && an.psuI && an.psuI[k] != null ? Math.max(0, an.psuI[k]) : 0;
      const cc = c.on && iOut >= c.i - 1e-6;
      ctx.textAlign = "right";
      ctx.fillStyle = c.on ? "#f8fafc" : "#475569"; ctx.font = `bold ${19 * u}px Arial`;
      ctx.fillText((c.on ? c.v : 0).toFixed(3) + " V", x + colW - 12 * u, 56 * u);
      ctx.font = `${15 * u}px Arial`; ctx.fillText(iOut.toFixed(3) + " A", x + colW - 12 * u, 88 * u);
      ctx.textAlign = "left"; ctx.font = `${10.5 * u}px Arial`;
      ctx.fillStyle = c.on ? (cc ? "#f87171" : "#4ade80") : "#64748b"; ctx.fillText(c.on ? (cc ? "CC" : "CV") : "OFF", x + 8 * u, 40 * u);
      ctx.fillStyle = sel && p.field === "v" ? "#facc15" : "#94a3b8"; ctx.fillText("Réglé : " + c.v.toFixed(3) + " V", x + 8 * u, 118 * u);
      ctx.fillStyle = sel && p.field === "i" ? "#facc15" : "#94a3b8"; ctx.fillText("Limite : " + c.i.toFixed(3) + " A", x + 8 * u, 134 * u);
      if (sel && p.buf) { ctx.fillStyle = "#facc15"; ctx.fillText("Saisie : " + p.buf + "_", x + 8 * u, 154 * u); }
    });
    // menu de softkeys (maquette fidèle aux libellés de la photo)
    ctx.fillStyle = "#1e3a8a"; ctx.fillRect(W * 0.84, 0, W * 0.16, H);
    ["Source\nSettings", "Output\nSettings", "Store/\nRecall", "Utilities", "", "Lock"].forEach((l, i) => {
      if (!l) return; const y = (82 - 60) / 300 * H + i * 46 / 300 * H;
      ctx.fillStyle = "#3b82c4"; ctx.fillRect(W * 0.85, y, W * 0.14, 26 / 300 * H);
      ctx.fillStyle = "#fff"; ctx.font = `${9.5 * u}px Arial`; ctx.textAlign = "center";
      l.split("\n").forEach((t, j, a) => ctx.fillText(t, W * 0.92, y + (13 + (j - (a.length - 1) / 2) * 10) / 300 * H)); ctx.textAlign = "left";
    });
    if (an && an.warnings.some(w => /FLOTTANTE/.test(w))) { ctx.fillStyle = "#facc15"; ctx.font = `${11 * u}px Arial`; ctx.fillText("⚠ 0 V non relié à la plaque", 10 * u, H - 14 * u); }
    [1, 2, 3].forEach(k => els["on" + k].classList.toggle("lit", p.ch[k].on));
  }
  return { init, draw, press, turn };
})();
