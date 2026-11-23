// Test du moteur : node tests/engine_test.js   (génère d'abord app/data.js : /usr/bin/python3 tools/export_app_data.py)
const fs = require("fs"), path = require("path");
const root = path.resolve(__dirname, "..");
const Engine = require(path.join(root, "app/js/engine.js"));
const D = new Function(fs.readFileSync(path.join(root, "app/data.js"), "utf8") + "; return {HOLES, MONTAGES, CHIPS_LIB};")();
const holeIds = new Set(D.HOLES.map(h => h.id));

function solution(id) {
  const m = D.MONTAGES[id];
  return {
    m,
    wiring: {
      wires: m.fils.map(w => ({ de: w.de, vers: w.vers })),
      comps: Object.entries(m.composants).filter(([, c]) => c.type === "resistor" || c.type === "led").map(([name, c]) => ({ name, type: c.type, a: c.a, b: c.b, ohm: c.ohm })),
      chips: m.puces,
    },
  };
}
const env = (m, extra) => Object.assign({ holes: D.HOLES, holeIds, chipsLib: D.CHIPS_LIB, cables: m.cables, gbf: { offset: 0 }, psu: { on: true, v: { 1: 1, 2: 15, 3: 15 } } }, extra || {});

let fail = 0;
const check = (label, got, exp, tolPct) => {
  const ok = Math.abs(got - exp) <= Math.abs(exp) * tolPct / 100 + 1e-9;
  if (!ok) fail++;
  console.log((ok ? "ok   " : "FAIL ") + label.padEnd(58) + "obtenu " + got.toFixed(4) + "  attendu " + exp);
};

// 1) gains du câblage CORRIGÉ de chaque montage analogique (1 kHz), sinus
[["tp1-B1-pont-diviseur", 1000, 0.0998, 1, 0], ["tp2-A-suiveur", 1000, 1, 1, 0], ["tp2-B1-inverseur", 1000, 20, 1, 180],
 ["tp2-B2-non-inverseur", 1000, 10.1, 1, 0], ["tp2-C-association", 1000, 202, 2, 180]].forEach(([id, f, g, tol, ph]) => {
  const { m, wiring } = solution(id);
  const an = Engine.analyze(wiring, env(m), { f });
  check(id + " |Vs/Ve|", an.gain, g, tol);
  const dph = Math.abs(((an.phaseDeg - ph + 540) % 360) - 180);   // écart angulaire à la phase attendue
  const okp = dph < 1;
  console.log((okp ? "ok   " : "FAIL ") + (id + " phase (°)").padEnd(58) + "obtenu " + an.phaseDeg.toFixed(2) + "  attendu " + ph);
  if (!okp) fail++;
});

// 2) coupures : inverseur ~ GBW/21, non inverseur ~ GBW/10,1
[["tp2-B1-inverseur", 4e6 / 21], ["tp2-B2-non-inverseur", 4e6 / 10.1]].forEach(([id, fc]) => {
  const { m, wiring } = solution(id);
  const an = Engine.analyze(wiring, env(m), { f: 1000 });
  check(id + " fc (Hz)", Engine.cutoff(an), fc, 4);
});

// 3) le câblage décide : fil V− oublié, 0 V alim non relié, plaque vide
{
  const { m, wiring } = solution("tp2-B1-inverseur");
  const noVminus = { ...wiring, wires: wiring.wires.filter(w => !(w.de === "T1i47" || w.vers === "T1i47")) };
  const a1 = Engine.analyze(noVminus, env(m), { f: 1000 });
  console.log((a1.powered ? "FAIL " : "ok   ") + "fil V− oublié -> AOP non alimenté : powered=" + a1.powered);
  if (a1.powered) fail++;
  const noGnd = { ...wiring, wires: wiring.wires.filter(w => w.de !== "MASSE.main") };
  const a2 = Engine.analyze(noGnd, env(m), { f: 1000 });
  console.log((a2.warnings.length ? "ok   " : "FAIL ") + "0 V alim non relié -> avertissement : " + JSON.stringify(a2.warnings));
  if (!a2.warnings.length) fail++;
  const empty = Engine.analyze({ wires: [], comps: [], chips: [] }, env(m), { f: 1000 });
  const w = Engine.waveforms(empty, { f: 1000, vpp: 0.4, wave: "sine", on: true }, 2e-4);
  console.log((w.stats.ch2.vpp < 0.01 ? "ok   " : "FAIL ") + "plaque vide -> voie 2 plate : Vpp(2) = " + w.stats.ch2.vpp.toFixed(4));
  if (w.stats.ch2.vpp >= 0.01) fail++;
}

// 4) formes d'onde : valeurs que l'écran affichera
{
  const { m, wiring } = solution("tp2-B1-inverseur");
  const an = Engine.analyze(wiring, env(m), { f: 1000 });
  const w = Engine.waveforms(an, { f: 1000, vpp: 0.4, wave: "sine", on: true }, 2e-4);
  check("B1 : Vpp(1) = 0,4 × 1000/(1000+50) (GBF 50 Ω chargé par R1)", w.stats.ch1.vpp, 0.4 * 1000 / 1050, 1);
  check("B1 : Vpp(2) = 20 × Vpp(1), non saturé", w.stats.ch2.vpp, 20 * 0.4 * 1000 / 1050, 1);
  const an5 = Engine.analyze(wiring, env(m), { f: 1000 });
  const s = Engine.waveforms(an5, { f: 1000, vpp: 5, wave: "sine", on: true }, 2e-4);
  check("B1 5 Vpp : saturation, Vpp(2) = 2 × 12,5 V", s.stats.ch2.vpp, 25, 2);
  const sq = Engine.waveforms(an, { f: 1000, vpp: 0.4, wave: "square", on: true }, 2e-4);
  check("B1 carré 0,4 Vpp : Vpp(2) ≈ 20 × Vpp(1)", sq.stats.ch2.vpp, 20 * 0.4 * 1000 / 1050, 3);
  const a4 = solution("tp2-A-suiveur"), anA = Engine.analyze(a4.wiring, env(a4.m), { f: 2e6 });
  const sl = Engine.waveforms(anA, { f: 2e6, vpp: 5, wave: "sine", on: true }, 1e-7);
  console.log("info suiveur 5 Vpp à 2 MHz (slew) : Vpp(2) = " + sl.stats.ch2.vpp.toFixed(2) + " V (< 5 V attendu, forme triangulaire)");
  if (!(sl.stats.ch2.vpp < 4.9)) { fail++; console.log("FAIL slew non appliqué"); }
}

// 5) TP3 / LED : déclarés non simulés
["tp3-C-compteur", "tp1-D1-led"].forEach(id => {
  const { m, wiring } = solution(id);
  const an = Engine.analyze(wiring, env(m), { f: 1000 });
  console.log((an.supported ? "FAIL " : "ok   ") + id + " -> supported=" + an.supported + " : " + an.reasons.join(" | "));
  if (an.supported) fail++;
});
console.log(fail ? "\n" + fail + " ÉCHEC(S)" : "\nTOUS LES TESTS PASSENT");
process.exit(fail ? 1 : 0);
