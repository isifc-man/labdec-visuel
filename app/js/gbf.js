// Générateur Keysight EDU33211A : touches + écran. Les réglages alimentent la source du moteur (gbfEngine).
// Menus implémentés : Waveform (Sine/Square/Ramp), Parameter (Frequency/Amplitude/Offset, saisie au pavé + unité), Setup (charge High Z / 50 Ω), On/Off.
// Le chemin exact du menu « charge » sur TON appareil n'est pas confirmé (montages : « à vérifier ») : ici Setup → touche 1 « Output Load ».
const Gbf = (() => {
  let els = null, cv = null, ctx = null;
  const G = () => state.gbf;
  const FIELDS = {
    freq: { name: "Frequency", units: [["MHz", 1e6], ["kHz", 1e3], ["Hz", 1], ["mHz", 1e-3]], get: g => g.f, set: (g, v) => { g.f = Math.max(1e-3, Math.min(2e7, v)); } },
    // limites de l'EDU33211A : 10 Vpp et ±5 V sur 50 Ω, le double en « High Z » ; |offset| + Vpp/2 ne dépasse pas la plage
    amp: { name: "Amplitude", units: [["Vpp", 1], ["mVpp", 1e-3], ["", 1], ["", 1]], get: g => g.vpp, set: (g, v) => { const L = g.load === "50" ? 5 : 10; g.vpp = Math.max(1e-3, Math.min(2 * (L - Math.abs(g.offset)), v)); } },
    off: { name: "Offset", units: [["V", 1], ["mV", 1e-3], ["", 1], ["", 1]], get: g => g.offset, set: (g, v) => { const L = g.load === "50" ? 5 : 10; g.offset = Math.max(-(L - g.vpp / 2), Math.min(L - g.vpp / 2, v)); } },
  };

  function init(root) { els = Faces.build("gbf", root, { press, turn }); cv = els.canvas; ctx = cv.getContext("2d"); }

  function press(id) {
    const g = G();
    if (/^k[\d.]$|^k\+\/-$/.test(id) && g.field) {
      const ch = id.slice(1);
      if (ch === "+/-") g.buf = g.buf.startsWith("-") ? g.buf.slice(1) : "-" + g.buf;
      else if (ch !== "." || !g.buf.includes(".")) g.buf += ch;
    } else if ((id === "left") && g.field) g.buf = g.buf.slice(0, -1);
    else if (id === "waveform") { g.menu = "waveform"; g.field = null; g.buf = ""; }
    else if (id === "parameter") { g.menu = "param"; g.field = null; g.buf = ""; }
    else if (id === "setup") { g.menu = "setup"; g.field = null; g.buf = ""; }
    else if (id === "back") { if (g.field) { g.field = null; g.buf = ""; g.menu = "param"; } else g.menu = "home"; }
    else if (id === "onoff") g.on = !g.on;
    else if (/^sk[1-6]$/.test(id)) softkey(+id[2]);
    refreshAll();
  }

  function softkey(n) {
    const g = G();
    if (g.menu === "waveform") { if (n <= 3) g.wave = ["sine", "square", "triangle"][n - 1]; return; }
    if (g.menu === "setup") { if (n === 1) g.load = g.load === "50" ? "highz" : "50"; return; }
    if (g.menu === "param" && !g.field) { const f = ["freq", "amp", "off"][n - 1]; if (f) { g.field = f; g.buf = ""; } return; }
    if (g.field && n <= 4) {           // unité choisie : validation de la saisie
      const F = FIELDS[g.field], u = F.units[n - 1];
      if (!u || !u[0] || g.buf === "" || g.buf === "-" || isNaN(parseFloat(g.buf))) return;
      F.set(g, parseFloat(g.buf) * u[1]); g.field = null; g.buf = ""; g.menu = "param";
    }
  }

  function turn(id, d) {
    const g = G(), key = g.field || (g.menu === "param" ? "freq" : null);
    if (id !== "knob" || !key) return;
    const F = FIELDS[key], v = F.get(g), step = Math.pow(10, Math.floor(Math.log10(Math.abs(v) || 1)) - 1);
    F.set(g, +(v + d * step).toPrecision(6)); refreshAll();
  }

  function softLabels() {
    const g = G();
    if (g.menu === "waveform") return ["Sine", "Square", "Ramp", "Pulse", "Arb", "MORE 1/2"];
    if (g.menu === "setup") return ["Output Load\n" + (g.load === "50" ? "50 Ω" : "High Z"), "Polarity\nNormal", "Sync\nON", "", "", ""];
    if (g.field) return FIELDS[g.field].units.map(u => u[0]).concat(["", ""]).slice(0, 6);
    if (g.menu === "param") return ["Frequency", "Amplitude", "Offset", "Phase", "", "MORE 1/2"];
    return ["", "", "", "", "", ""];
  }

  function fmtField(key) {
    const g = G();
    if (key === "freq") return fmtHz(g.f).replace(/(\d)\.(\d{3}) /, "$1.$2 000 ");
    if (key === "amp") return (g.vpp >= 1 ? g.vpp.toFixed(4) + " Vpp" : (g.vpp * 1e3).toFixed(g.vpp * 1e3 >= 100 ? 1 : 2) + " mVpp");
    return Math.abs(g.offset) >= 1 || g.offset === 0 ? g.offset.toFixed(3) + " V" : (g.offset * 1e3).toFixed(1) + " mV";
  }

  function draw() {
    if (!ctx) return;
    const g = G(), W = cv.width, H = cv.height, u = W / 430;
    ctx.fillStyle = "#050b12"; ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = "#0e1a28"; ctx.fillRect(0, 0, W * 0.78, H);
    // en-tête de voie
    ctx.textBaseline = "middle"; ctx.font = `bold ${14 * u}px Arial`;
    ctx.fillStyle = g.on ? "#facc15" : "#94a3b8"; ctx.fillText(g.on ? "ON" : "OFF", W * 0.04, H * 0.07);
    ctx.fillStyle = "#cbd5e1"; ctx.font = `${12 * u}px Arial`; ctx.fillText(g.load === "50" ? "CH1 · 50 Ω" : "CH1 · High Z", W * 0.15, H * 0.07);
    // aperçu de forme
    const bx = W * 0.05, by = H * 0.14, bw = W * 0.68, bh = H * 0.34;
    ctx.strokeStyle = g.on ? "#22c55e" : "#4b5d52"; ctx.lineWidth = 1.5 * u; ctx.strokeRect(bx, by, bw, bh);
    ctx.beginPath();
    for (let i = 0; i <= 200; i++) {
      const ph = (i / 200 * 2) % 1;
      const v = g.wave === "square" ? (ph < 0.5 ? 1 : -1) : g.wave === "triangle" ? (ph < 0.5 ? -1 + 4 * ph : 3 - 4 * ph) : Math.sin(2 * Math.PI * ph);
      const x = bx + i / 200 * bw, y = by + bh / 2 - v * bh * 0.38;
      i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
    }
    ctx.stroke();
    // paramètres
    const rows = [["Frequency", "freq"], ["Amplitude", "amp"], ["Offset", "off"]];
    ctx.font = `${12 * u}px Arial`;
    rows.forEach(([n, k], i) => {
      const y = H * (0.58 + i * 0.1), edit = g.field === k;
      ctx.fillStyle = edit ? "#facc15" : "#94a3b8"; ctx.fillText(n, W * 0.05, y);
      ctx.fillStyle = edit ? "#facc15" : "#f1f5f9"; ctx.font = `bold ${14 * u}px Arial`;
      ctx.fillText(edit ? (g.buf === "" ? "_" : g.buf + "_") : fmtField(k), W * 0.30, y); ctx.font = `${12 * u}px Arial`;
    });
    ctx.fillStyle = "#64748b"; ctx.fillText((g.wave === "sine" ? "Sine" : g.wave === "square" ? "Square" : "Ramp") + " · " + (g.menu === "home" ? "écran principal" : g.menu), W * 0.05, H * 0.93);
    // menu de softkeys, aligné sur les 6 touches physiques
    ctx.fillStyle = "#1e3a8a"; ctx.fillRect(W * 0.8, 0, W * 0.2, H);
    const labels = softLabels(), top = (78 - 56) / 300 * H, pitch = 46 / 300 * H;
    labels.forEach((l, i) => {
      if (!l) return;
      const y = top + i * pitch;
      ctx.fillStyle = (g.menu === "waveform" && ((g.wave === "sine" && i === 0) || (g.wave === "square" && i === 1) || (g.wave === "triangle" && i === 2))) ? "#2563eb" : "#3b82c4";
      ctx.fillRect(W * 0.81, y, W * 0.18, 26 / 300 * H);
      ctx.fillStyle = "#fff"; ctx.font = `${10.5 * u}px Arial`; ctx.textAlign = "center";
      l.split("\n").forEach((t, j, a) => ctx.fillText(t, W * 0.9, y + (13 + (j - (a.length - 1) / 2) * 11) / 300 * H));
      ctx.textAlign = "left";
    });
    els.onoff.classList.toggle("lit", g.on);
  }
  return { init, draw, press, turn };
})();
