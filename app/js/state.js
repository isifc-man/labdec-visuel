// État global de l'application (une seule source de vérité ; tout le reste le lit).
const HOLE_MAP = new Map(HOLES.map(h => [h.id, h]));
const HOLE_IDS = new Set(HOLES.map(h => h.id));
const WIRE_COLORS = { rouge: "#ef4444", noir: "#1f2937", bleu: "#3b82f6", jaune: "#eab308", orange: "#f97316", vert: "#22c55e", blanc: "#f8fafc", turquoise: "#14b8a6" };

// Valeurs d'usine : NON vérifiées pour le GBF (1 kHz / 100 mVpp supposés) ; sorties éteintes comme sur un banc qu'on vient d'allumer.
function factoryInstruments() {
  return {
    gbf: { on: false, sync: true, wave: "sine", f: 1000, vpp: 0.1, offset: 0, load: "50", menu: "home", page: 1, field: null, buf: "" },
    psu: { sel: 1, field: "v", buf: "", ch: { 1: { v: 0, i: 0.1, on: false }, 2: { v: 0, i: 0.1, on: false }, 3: { v: 0, i: 0.1, on: false } } },
    scope: { running: true, frozen: null, selCh: 1, tdiv: 1e-3, hpos: 0, trigLevel: 0, trigSrc: 1, trigSlope: 1, measPage: 0, cursors: false, cursSel: 0, trigMode: "auto", menu: "home",
      ch: { 1: { on: true, vdiv: 1, pos: 0 }, 2: { on: true, vdiv: 1, pos: 0 } }, curs: { x1: -1.5, x2: 1.5, y1: 2, y2: -2 } },
  };
}

const state = Object.assign({
  currentMontage: null,
  tool: "wire", wireColor: "rouge", resistorVal: 1000, chipVal: "TL081", armedRef: null,
  firstHole: null, placedWires: [], placedComps: [], placedChips: [],
  placedCables: [], cableFirst: null,   // câbles d'appareils (BNC / bananes) posés par l'élève
  preset: null,            // réglages de départ lus dans le YAML du montage (sert à comparer)
  progress: {},            // montage -> "todo" | "cur" | "ok"
}, factoryInstruments());

try { Object.assign(state.progress, JSON.parse(localStorage.getItem("labdec.progress") || "{}")); } catch (e) { /* stockage indisponible : on continue sans */ }
// Annuler : chaque changement de câblage (fil, composant, puce, câble) est empilé ; « annuler » revient à l'état précédent.
const History = (() => {
  let stack = [], last = null;
  const snap = () => JSON.stringify([state.placedWires, state.placedComps, state.placedChips, state.placedCables]);
  function track() { const s = snap(); if (last !== null && s !== last) { stack.push(last); if (stack.length > 200) stack.shift(); } last = s; }
  function undo() {
    if (!stack.length) return false;
    const prev = JSON.parse(stack.pop());
    [state.placedWires, state.placedComps, state.placedChips, state.placedCables] = prev;
    last = JSON.stringify(prev); return true;
  }
  function reset() { stack = []; last = snap(); }
  return { track, undo, reset, size: () => stack.length };
})();
state.dmm = { v: null, com: null, mode: "dc", type: "trms", bw: 1e5 };
function saveProgress() { try { localStorage.setItem("labdec.progress", JSON.stringify(state.progress)); } catch (e) { /* ignoré */ } }

// Premier nom libre « R1, R2… » : évite les doublons après suppression
function nextName(prefix, list, key) {
  const used = new Set(list.map(x => x[key]));
  for (let i = 1; ; i++) if (!used.has(prefix + i)) return prefix + i;
}
// Toutes les résistances de la série E12 du labo, 10 Ω → 1 MΩ
const E12_MANT = [10, 12, 15, 18, 22, 27, 33, 39, 47, 56, 68, 82];
const E12_ALL = (() => { const a = []; for (let e = 0; e <= 4; e++) E12_MANT.forEach(m => a.push(Math.round(m * Math.pow(10, e)))); a.push(1000000); return a; })();
function ohmLabel(v) { return v >= 1e6 ? +(v / 1e6).toFixed(2) + " MΩ" : v >= 1e3 ? String(+(v / 1e3).toFixed(2)).replace(".", ",") + " kΩ" : v + " Ω"; }

// ---- formats d'affichage (virgule française, unités SI) -------------------------------
function fmtV(v, d) {
  const a = Math.abs(v);
  d = d == null ? 2 : d;
  if (a >= 1 || a === 0) return v.toFixed(d) + " V";
  if (a >= 1e-3) return (v * 1e3).toFixed(d === 2 ? 1 : d) + " mV";
  return (v * 1e6).toFixed(0) + " µV";
}
function fmtHz(f) {
  if (f >= 1e6) return (f / 1e6).toFixed(3) + " MHz";
  if (f >= 1e3) return (f / 1e3).toFixed(3) + " kHz";
  return f.toFixed(2) + " Hz";
}
function fmtT(t) {
  const a = Math.abs(t);
  if (a >= 1) return t.toFixed(2) + " s";
  if (a >= 1e-3) return (t * 1e3).toFixed(a >= 1e-2 ? 1 : 2).replace(/\.?0+$/, "") + " ms";
  if (a >= 1e-6) return (t * 1e6).toFixed(a >= 1e-5 ? 1 : 2).replace(/\.?0+$/, "") + " µs";
  return (t * 1e9).toFixed(0) + " ns";
}
const SEQ125 = [];
for (let e = -9; e <= 1; e++) [1, 2, 5].forEach(m => SEQ125.push(m * Math.pow(10, e)));
function nextSeq(v, dir) {
  let i = SEQ125.findIndex(x => x >= v * 0.999);
  if (i < 0) i = SEQ125.length - 1;
  return SEQ125[Math.max(0, Math.min(SEQ125.length - 1, i + dir))];
}
const niceUp = v => SEQ125.find(x => x >= v * 0.999) || SEQ125[SEQ125.length - 1];
