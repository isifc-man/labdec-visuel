// Faces avant numériques des trois appareils : mêmes touches, même disposition que sur les photos.
// Chaque élément est placé en unités de spec (x, y, w, h ou cx, cy, r) puis converti en pourcentages : la face se met à l'échelle.
// Types : btn · soft (touche sous l'écran) · knob (molette : roulette, glisser, clic = appui) · port (prise câblable) · screen (canvas) · label · deco.
// Disposition relevée sur gbf_ports.jpg, psu_ports.jpg, scope_tp2_b.jpg ; positions exactes à ajuster avec toi (version 1).
const Faces = (() => {
  const SPECS = {
    scope: { w: 1000, h: 600, title: "KEYSIGHT  DSOX1202A  ·  Digital Storage Oscilloscope  ·  70 MHz  2 GSa/s", items: [
      { t: "screen", id: "screen", x: 28, y: 60, w: 552, h: 331 },
      { t: "soft", id: "back", x: 598, y: 62, w: 44, h: 24, label: "Back", round: 1 },
      ...[0, 1, 2, 3, 4, 5].map(i => ({ t: "soft", id: "sk" + (i + 1), x: 598, y: 118 + i * 46, w: 44, h: 26 })),
      { t: "btn", id: "autoscale", x: 668, y: 64, w: 70, h: 36, label: "Auto\nScale", cls: "white" },
      { t: "btn", id: "default", x: 668, y: 108, w: 70, h: 36, label: "Default\nSetup", cls: "white" },
      { t: "label", x: 740, y: 52, label: "Horizontal", cls: "grp" },
      { t: "knob", id: "knob_horiz", cx: 790, cy: 108, r: 30, tip: "Échelle de temps (s/div) — roulette" },
      { t: "knob", id: "knob_hpos", cx: 875, cy: 108, r: 20, tip: "Position horizontale (non utilisée dans les TP)" },
      { t: "btn", id: "runstop", x: 918, y: 62, w: 64, h: 46, label: "Run\nStop", cls: "green" },
      { t: "btn", id: "single", x: 918, y: 118, w: 64, h: 36, label: "Single", cls: "gray" },
      { t: "label", x: 668, y: 170, label: "Measure", cls: "grp" },
      { t: "btn", id: "analyze", x: 668, y: 190, w: 60, h: 28, label: "Analyze", cls: "dark" },
      { t: "btn", id: "meas", x: 736, y: 190, w: 60, h: 28, label: "Meas", cls: "dark" },
      { t: "btn", id: "cursors", x: 804, y: 190, w: 60, h: 28, label: "Cursors", cls: "dark" },
      { t: "knob", id: "knob_entry", cx: 928, cy: 204, r: 22, tip: "Entry : déplace le curseur Y1 quand les curseurs sont actifs" },
      ...["Save/\nRecall", "Utility", "Display", "Quick\nAction", "Save to\nUSB"].map((l, i) => ({ t: "btn", id: "x" + i, x: 668 + i * 60, y: 228, w: 54, h: 30, label: l, cls: "dark sm", inert: 1 })),
      { t: "label", x: 668, y: 274, label: "Vertical", cls: "grp" },
      { t: "knob", id: "knob_pos1", cx: 694, cy: 330, r: 17, tip: "Position verticale voie 1" },
      { t: "knob", id: "knob_v1", cx: 752, cy: 318, r: 27, tip: "V/div voie 1 — roulette" },
      { t: "btn", id: "ch1", x: 806, y: 296, w: 46, h: 30, label: "1", cls: "orange" },
      { t: "btn", id: "ch2", x: 806, y: 336, w: 46, h: 30, label: "2", cls: "green2" },
      { t: "knob", id: "knob_v2", cx: 752, cy: 392, r: 27, tip: "V/div voie 2 — roulette" },
      { t: "knob", id: "knob_pos2", cx: 694, cy: 392, r: 17, tip: "Position verticale voie 2" },
      { t: "btn", id: "math", x: 806, y: 376, w: 46, h: 22, label: "Math", cls: "dark sm", inert: 1 },
      { t: "btn", id: "fft", x: 806, y: 404, w: 46, h: 22, label: "FFT", cls: "dark sm", inert: 1 },
      { t: "label", x: 888, y: 274, label: "Trigger", cls: "grp" },
      { t: "knob", id: "knob_trig", cx: 934, cy: 322, r: 24, tip: "Niveau de déclenchement — roulette ; clic = 50 %" },
      { t: "btn", id: "trigmenu", x: 898, y: 366, w: 70, h: 26, label: "Trigger", cls: "dark", inert: 1 },
      { t: "btn", id: "force", x: 898, y: 398, w: 70, h: 24, label: "Force", cls: "dark sm", inert: 1 },
      { t: "deco", x: 28, y: 470, w: 640, h: 60, cls: "recess" },
      { t: "label", x: 40, y: 528, label: "CH1 and CH2 inputs: 1 MΩ ≈ 16 pF · 150 V RMS", cls: "tiny" },
      { t: "port", id: "scope.ch1", cx: 700, cy: 500, r: 26, label: "1", cls: "bnc yellow", tip: "Voie 1 (BNC jaune)" },
      { t: "port", id: "scope.ch2", cx: 790, cy: 500, r: 26, label: "2", cls: "bnc green", tip: "Voie 2 (BNC verte)" },
      { t: "port", id: "scope.ext", cx: 890, cy: 500, r: 26, label: "Ext Trig", cls: "bnc blue", tip: "Entrée de déclenchement externe" },
    ] },
    gbf: { w: 1000, h: 520, title: "KEYSIGHT  EDU33211A  ·  20 MHz  ·  Waveform Generator", items: [
      { t: "screen", id: "screen", x: 28, y: 56, w: 430, h: 300 },
      { t: "soft", id: "back", x: 476, y: 40, w: 44, h: 24, label: "Back", round: 1 },
      ...[0, 1, 2, 3, 4, 5].map(i => ({ t: "soft", id: "sk" + (i + 1), x: 476, y: 78 + i * 46, w: 44, h: 26 })),
      ...["Waveform", "Parameter", "Units", "System"].map((l, i) => ({ t: "btn", id: l.toLowerCase(), x: 560 + i * 100, y: 56, w: 88, h: 34, label: l, cls: i === 0 ? "white" : "dark", inert: i >= 2 })),
      ...["Modulate", "Sweep", "Burst", "Trigger"].map((l, i) => ({ t: "btn", id: l.toLowerCase(), x: 560 + i * 100, y: 100, w: 88, h: 30, label: l, cls: "gray", inert: 1 })),
      ...[["7", 0, 0], ["8", 1, 0], ["9", 2, 0], ["4", 0, 1], ["5", 1, 1], ["6", 2, 1], ["1", 0, 2], ["2", 1, 2], ["3", 2, 2], ["0", 0, 3], [".", 1, 3], ["+/-", 2, 3]]
        .map(([l, c, r]) => ({ t: "btn", id: "k" + l, x: 560 + c * 66, y: 160 + r * 52, w: 56, h: 42, label: l, cls: "dark key" })),
      { t: "knob", id: "knob", cx: 842, cy: 232, r: 52, tip: "Molette : incrémente le paramètre en cours d'édition" },
      { t: "btn", id: "left", x: 788, y: 306, w: 56, h: 34, label: "◀", cls: "dark" },
      { t: "btn", id: "right", x: 856, y: 306, w: 56, h: 34, label: "▶", cls: "dark" },
      { t: "label", x: 800, y: 362, label: "Channel 1", cls: "grp" },
      { t: "btn", id: "setup", x: 780, y: 384, w: 64, h: 32, label: "Setup", cls: "white" },
      { t: "btn", id: "onoff", x: 858, y: 384, w: 74, h: 32, label: "On/Off", cls: "yellow" },
      { t: "deco", x: 28, y: 440, w: 944, h: 60, cls: "recess" },
      { t: "port", id: "gbf.cal", cx: 120, cy: 470, r: 20, label: "Cal", cls: "bnc", inert: 1 },
      { t: "port", id: "gbf.ext_trig", cx: 270, cy: 470, r: 20, label: "Ext Trig", cls: "bnc", inert: 1 },
      { t: "port", id: "gbf.sync_out", cx: 420, cy: 470, r: 20, label: "Sync", cls: "bnc", tip: "Sync / Trigger Out (créneau TTL)" },
      { t: "port", id: "gbf.out1", cx: 900, cy: 468, r: 24, label: "1 · 50 Ω", cls: "bnc yellowtag", tip: "Sortie 1, 50 Ω (adaptateur en T)" },
    ] },
    psu: { w: 1000, h: 600, title: "KEYSIGHT  EDU36311A  ·  Triple Output DC Power Supply  ·  6 V/5 A · 30 V/1 A · 30 V/1 A", items: [
      { t: "screen", id: "screen", x: 28, y: 60, w: 400, h: 300 },
      { t: "soft", id: "back", x: 444, y: 44, w: 44, h: 24, label: "Back", round: 1 },
      ...[0, 1, 2, 3, 4, 5].map(i => ({ t: "soft", id: "sk" + (i + 1), x: 444, y: 82 + i * 46, w: 44, h: 26 })),
      { t: "knob", id: "knob_v", cx: 580, cy: 96, r: 34, tip: "Voltage : règle la tension de la voie sélectionnée" },
      { t: "knob", id: "knob_i", cx: 710, cy: 96, r: 34, tip: "Current : règle la limite de courant" },
      { t: "label", x: 618, y: 90, label: "Voltage", cls: "tiny" },
      { t: "label", x: 748, y: 90, label: "Current", cls: "tiny" },
      { t: "btn", id: "meter", x: 520, y: 160, w: 80, h: 36, label: "Meter\nView", cls: "dark", inert: 1 },
      { t: "btn", id: "tracking", x: 624, y: 160, w: 80, h: 36, label: "Tracking", cls: "dark", inert: 1 },
      { t: "btn", id: "up", x: 570, y: 214, w: 64, h: 24, label: "▲", cls: "dark", inert: 1 },
      { t: "btn", id: "left", x: 516, y: 246, w: 44, h: 40, label: "◀", cls: "dark" },
      { t: "btn", id: "select", x: 566, y: 250, w: 66, h: 34, label: "Select", cls: "dark" },
      { t: "btn", id: "right", x: 638, y: 246, w: 44, h: 40, label: "▶", cls: "dark" },
      { t: "btn", id: "down", x: 570, y: 296, w: 64, h: 24, label: "▼", cls: "dark", inert: 1 },
      ...[["7", 0, 0], ["8", 1, 0], ["9", 2, 0], ["4", 0, 1], ["5", 1, 1], ["6", 2, 1], ["1", 0, 2], ["2", 1, 2], ["3", 2, 2], ["0", 0, 3], [".", 1, 3], ["⌫", 2, 3]]
        .map(([l, c, r]) => ({ t: "btn", id: "k" + l, x: 770 + c * 62, y: 160 + r * 50, w: 54, h: 40, label: l, cls: "dark key" })),
      { t: "btn", id: "allonoff", x: 700, y: 330, w: 84, h: 36, label: "All\nOn/Off", cls: "dark" },
      { t: "btn", id: "enter", x: 880, y: 360, w: 70, h: 36, label: "Enter", cls: "dark" },
      { t: "btn", id: "on1", x: 520, y: 380, w: 72, h: 32, label: "On", cls: "yellow" },
      { t: "btn", id: "on2", x: 620, y: 380, w: 72, h: 32, label: "On", cls: "limeon" },
      { t: "btn", id: "on3", x: 720, y: 380, w: 72, h: 32, label: "On", cls: "blueon" },
      { t: "deco", x: 24, y: 450, w: 940, h: 126, cls: "recess" },
      { t: "deco", x: 300, y: 470, w: 160, h: 70, cls: "strip s1" },
      { t: "deco", x: 480, y: 470, w: 160, h: 70, cls: "strip s2" },
      { t: "deco", x: 660, y: 470, w: 160, h: 70, cls: "strip s3" },
      { t: "port", id: "psu.gnd", cx: 100, cy: 520, r: 22, label: "⏚", cls: "banana green", inert: 1 },
      ...[1, 2, 3].flatMap(k => [
        { t: "port", id: `psu.ch${k}_plus`, cx: 335 + (k - 1) * 180, cy: 520, r: 22, label: "+", cls: "banana red", tip: `Voie ${k} +` },
        { t: "port", id: `psu.ch${k}_moins`, cx: 425 + (k - 1) * 180, cy: 520, r: 22, label: "−", cls: "banana black", tip: `Voie ${k} −` },
      ]),
    ] },
  };

  const pct = (v, T) => (v / T * 100).toFixed(3) + "%";
  const live = {};            // face -> {root, els}

  function build(name, root, handlers) {
    const spec = SPECS[name];
    root.classList.add("face", "face-" + name);
    root.style.aspectRatio = spec.w + " / " + spec.h;
    root.style.setProperty("--ar", (spec.w / spec.h).toFixed(4));
    root.ondblclick = e => { if (!e.target.closest(".it")) Zoom.toggleInst(root.closest(".inst")); };
    root.innerHTML = `<div class="face-title">${spec.title}</div>`;
    const els = {};
    spec.items.forEach(it => {
      const el = document.createElement("div");
      const x = it.cx != null ? it.cx - it.r : it.x, y = it.cy != null ? it.cy - it.r : it.y;
      const w = it.r != null ? 2 * it.r : it.w, h = it.r != null ? 2 * it.r : it.h;
      Object.assign(el.style, { left: pct(x, spec.w), top: pct(y, spec.h), width: pct(w, spec.w), height: pct(h, spec.h) });
      el.className = "it it-" + it.t + (it.cls ? " " + it.cls : "") + (it.inert ? " inert" : "");
      el.dataset.id = it.id || "";
      if (it.tip) el.title = it.tip; else if (it.inert) el.title = "Non utilisé dans les TP";
      if (it.label != null) el.innerHTML = `<span>${String(it.label).replace(/\n/g, "<br>")}</span>`;
      if (it.t === "screen") { const c = document.createElement("canvas"); c.width = Math.round(w * 1.6); c.height = Math.round(h * 1.6); el.appendChild(c); els.canvas = c; }
      if (it.t === "knob") { el.innerHTML = '<i class="mark"></i>'; el._rot = 0; }
      if (it.t === "port") el.dataset.port = it.id;
      if (it.t === "btn" || it.t === "soft") el.onclick = () => { if (!it.inert) handlers.press(it.id); };
      if (it.t === "knob") bindKnob(el, it, handlers);
      if (it.t === "port") el.onclick = () => { if (handlers.port) handlers.port(it.id); else if (typeof Cables !== "undefined") Cables.clickPort(it.id); };
      root.appendChild(el);
      els[it.id || ("_" + root.children.length)] = el;
    });
    const fit = () => root.style.setProperty("--u", (root.clientWidth / spec.w).toFixed(4) + "px");
    fit();
    if (window.ResizeObserver) new ResizeObserver(fit).observe(root);
    live[name] = { root, els, spec };
    return els;
  }

  function bindKnob(el, it, handlers) {
    const turn = d => { el._rot += d * 18; el.firstChild.style.transform = `rotate(${el._rot}deg)`; handlers.turn(it.id, d); };
    el.addEventListener("wheel", e => { e.preventDefault(); turn(e.deltaY < 0 ? 1 : -1); }, { passive: false });
    let y0 = null, moved = false;
    el.addEventListener("pointerdown", e => { y0 = e.clientY; moved = false; el.setPointerCapture(e.pointerId); });
    el.addEventListener("pointermove", e => {
      if (y0 == null) return;
      const d = y0 - e.clientY;
      if (Math.abs(d) >= 10) { moved = true; turn(d > 0 ? 1 : -1); y0 = e.clientY; }
    });
    el.addEventListener("pointerup", () => { if (!moved && handlers.press) handlers.press(it.id); y0 = null; });
    el.tabIndex = 0;
    el.addEventListener("keydown", e => { if (e.key === "ArrowUp" || e.key === "ArrowRight") turn(1); if (e.key === "ArrowDown" || e.key === "ArrowLeft") turn(-1); });
  }

  // Allume les prises câblées dans le montage courant et y colle la lettre du câble (A, B, C…)
  function updateCables() {
    const cables = (typeof curCables === "function") ? curCables() : [];
    const used = {};
    cables.forEach(cb => [cb.de, cb.vers].forEach(e => { if (e && e.indexOf(".") > 0) (used[e] = used[e] || []).push(cb.id); }));
    Object.values(live).forEach(f => {
      f.root.querySelectorAll(".it-port").forEach(p => {
        const ids = used[p.dataset.port];
        p.classList.toggle("cabled", !!ids);
        let b = p.querySelector(".badge");
        p.title = ids ? "Câble " + ids.join(", ") + " branché : clique pour en poser un autre, gomme pour retirer" : (p.title || "Clique pour poser un câble");
        if (ids) { if (!b) { b = document.createElement("em"); b.className = "badge"; p.appendChild(b); } b.textContent = ids.join(","); }
        else if (b) b.remove();
      });
    });
  }

  function setLit(name, id, on) { const f = live[name]; if (f && f.els[id]) f.els[id].classList.toggle("lit", !!on); }
  return { SPECS, build, updateCables, setLit, live };
})();

