// Tests du moteur (sans navigateur) : node tests/engine_test.js   (après python tools/build_app.py, qui écrit app/data.js)
// Valeurs attendues : calculs à la main (diviseurs, gains, GBW / (1 + gain)), fiches TI (TL081, 74LS00, 74LS74), sujets TP1–TP3.
const fs = require("fs"), path = require("path"), vm = require("vm");
const root = path.join(__dirname, "..");
const ctx = {}; vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(root, "app/data.js"), "utf8") + ";this.HOLES=HOLES;this.MONTAGES=MONTAGES;this.CHIPS_LIB=CHIPS_LIB;", ctx);
const Engine = require(path.join(root, "app/js/engine.js"));
const { HOLES, MONTAGES, CHIPS_LIB } = ctx;
const HOLE_IDS = new Set(HOLES.map(h => h.id));

let fails = 0;
const ok = (c, label, got) => { console.log((c ? "ok   " : "ÉCHEC ") + label.padEnd(62) + (got !== undefined ? " obtenu " + got : "")); if (!c) fails++; };
const near = (v, exp, tol) => v != null && Math.abs(v - exp) <= tol;

function sol(id) {
  const m = MONTAGES[id];
  return { wiring: {
      wires: (m.fils || []).map(w => ({ de: w.de, vers: w.vers })),
      comps: Object.entries(m.composants || {}).filter(([, c]) => c.type === "resistor" || c.type === "led").map(([name, c]) => ({ name, type: c.type, a: c.a, b: c.b, k: c.k, ohm: c.ohm })),
      chips: JSON.parse(JSON.stringify(m.puces || [])) }, cables: JSON.parse(JSON.stringify(m.cables || [])) };
}
const env = cables => ({ holes: HOLES, holeIds: HOLE_IDS, chipsLib: CHIPS_LIB, cables });
const psu = (v1, v2, v3, i) => ({ 1: { v: v1, i: i || 0.1, on: v1 != null }, 2: { v: v2, i: i || 0.1, on: v2 != null }, 3: { v: v3, i: i || 0.1, on: v3 != null } });
const PM15 = psu(null, 15, 15, 0.05), P5 = psu(5, null, null, 0.1);
function run(id, gbf, ps, mod) {
  const s = sol(id); if (mod) mod(s);
  return Engine.analyze(s.wiring, env(s.cables), { gbf: Object.assign({ on: true, f: 1000, vpp: 1, offset: 0, wave: "sine" }, gbf), psu: ps || {} });
}
const meas = (an, ch, ta, tb) => Engine.measure(an.rec, ch, ta == null ? 0 : ta, tb == null ? 2 * an.rec.P + 1e-15 : tb);
function fc(id, vpp) {                         // fréquence où |Vs/Ve| = gain BF / √2 (balayage puis dichotomie)
  const g0 = run(id, { vpp, f: 1000 }, PM15).gain;
  let lo = 1e4, hi = 3e6;
  for (let i = 0; i < 18; i++) { const m = Math.sqrt(lo * hi); if (run(id, { vpp, f: m }, PM15).gain > g0 / Math.SQRT2) lo = m; else hi = m; }
  return Math.sqrt(lo * hi);
}

console.log("— TP1 / TP2 : régime linéaire —");
let a = run("tp1-B1-pont-diviseur", { vpp: 2 });
ok(near(a.gain, 1000 / 10020, 0.001), "pont diviseur : Vs/Ve = 1000 / (8200 + 820 + 1000)", a.gain.toFixed(4));
a = run("tp2-A-suiveur", { vpp: 5 }, PM15); ok(near(a.gain, 1, 0.002), "suiveur : gain 1", a.gain.toFixed(4));
a = run("tp2-B1-inverseur", { vpp: 0.4 }, PM15);
ok(near(a.gain, 20, 0.05) && near(Math.abs(a.phaseDeg), 180, 1), "inverseur : gain 20, phase 180°", a.gain.toFixed(3) + " / " + a.phaseDeg.toFixed(1));
ok(near(meas(a, "ch1").vpp, 0.4 * 1000 / 1050, 0.003), "inverseur : Vpp(1) = 0,4 × 1000/1050 (GBF 50 Ω chargé par R1)", meas(a, "ch1").vpp.toFixed(4));
a = run("tp2-B2-non-inverseur", { vpp: 1 }, PM15); ok(near(a.gain, 1 + 9100 / 1000, 0.03), "non inverseur : gain 1 + R2/R1 = 10,1", a.gain.toFixed(3));
a = run("tp2-C-association", { vpp: 0.04 }, PM15); ok(near(a.gain, 10.1 * 20, 1), "association : gain 202, phase 180°", a.gain.toFixed(2));
a = run("tp2-D-soustracteur", { vpp: 1 }, psu(1, 15, 15, 0.05));
ok(near(meas(a, "ch2").mean, 1, 0.02) && near(meas(a, "ch2").vpp, 1, 0.02), "soustracteur : Vs = V2 − V1 (moyenne 1 V, 1 Vpp)", meas(a, "ch2").mean.toFixed(3));
const f1 = fc("tp2-B1-inverseur", 0.1); ok(near(f1, 4e6 / 21, 0.05 * 4e6 / 21), "inverseur : fc ≈ GBW / (1 + 20) = 190 kHz", (f1 / 1e3).toFixed(1) + " kHz");
const f2 = fc("tp2-B2-non-inverseur", 0.1); ok(near(f2, 4e6 / 10.1, 0.05 * 4e6 / 10.1), "non inverseur : fc ≈ GBW / 10,1 = 396 kHz", (f2 / 1e3).toFixed(1) + " kHz");

console.log("— limites de l'AOP et de l'alim —");
a = run("tp2-B1-inverseur", { vpp: 5 }, PM15); ok(near(meas(a, "ch2").vpp, 25, 0.1), "inverseur 5 Vpp : saturation à ±12,5 V", meas(a, "ch2").vpp.toFixed(3));
a = run("tp2-C-association", { vpp: 3 }, PM15); ok(a.notes.some(n => /U1.*saturation/.test(n)) && a.notes.some(n => /U2.*saturation/.test(n)), "association 3 Vpp : les DEUX étages saturent (par étage)");
a = run("tp2-A-suiveur", { vpp: 5, f: 2e6 }, PM15);
ok(meas(a, "ch2").vpp < 4 && a.notes.some(n => /vitesse de montée/.test(n)), "suiveur 5 Vpp 2 MHz : limité par la vitesse de montée", meas(a, "ch2").vpp.toFixed(2) + " Vpp");
const phT = Engine.phase(a.rec); ok(phT < -45, "suiveur 2 MHz : la phase mesurée suit la courbe déformée", phT.toFixed(1) + "°");
a = run("tp2-B1-inverseur", { vpp: 0.4 }, PM15, s => { s.wiring.wires = s.wiring.wires.filter(w => w.de !== "T1i47"); });
ok(a.warnings.some(w => /non alimenté/.test(w)), "fil V− oublié -> AOP non alimenté");
a = run("tp2-B1-inverseur", { vpp: 0.4 }, PM15, s => s.wiring.wires.forEach(w => { if (w.de === "T1b49") w.vers = "N1-1u-49"; else if (w.de === "T1i47") w.vers = "N2-1u-47"; }));
ok(a.warnings.some(w => /À L'ENVERS/.test(w)), "AOP alimenté à l'envers -> signalé (puce détruite)");
a = run("tp2-B1-inverseur", { vpp: 0.4 }, PM15, s => { s.wiring.wires = s.wiring.wires.filter(w => w.de !== "MASSE.main"); });
ok(a.warnings.some(w => /FLOTTANTE/.test(w)), "0 V de l'alim non relié -> alimentation flottante");
a = run("tp2-B1-inverseur", { vpp: 0.4 }, PM15, s => s.wiring.wires.push({ de: "N2-1u-40", vers: "TOP-L1-12" }));
ok(a.supported && a.rec.psu[2].cc && Math.abs(a.rec.psu[2].v) < 0.01, "court-circuit franc du +15 V : voie en CC, 0 V, pas d'erreur de calcul", a.rec.psu[2].v.toFixed(3) + " V");
a = run("tp2-B1-inverseur", { vpp: 0.4 }, PM15, s => s.wiring.comps.push({ name: "Rx", type: "resistor", a: "N2-1u-40", b: "TOP-L1-12", ohm: 10 }));
ok(a.rec.psu[2].cc && near(a.rec.psu[2].v, 0.05 * 10, 0.02), "10 Ω sur le +15 V limité à 50 mA : la tension chute à 0,5 V", a.rec.psu[2].v.toFixed(3) + " V");

console.log("— oscilloscope —");
a = run("tp2-B1-inverseur", { vpp: 0.4 }, PM15);
let m = Engine.measure(a.rec, "ch1", -1e-3, 1e-3);
ok(near(m.freq, 1000, 1), "200 µs/div (2 périodes à l'écran) : Fréq(1) = 1 kHz", m.freq);
a = run("tp2-B1-inverseur", { vpp: 0.4, f: 1e6 }, PM15);
m = Engine.measure(a.rec, "ch1", -5e-3, 5e-3);
ok(near(m.freq, 1e6, 10), "GBF 1 MHz vu à 1 ms/div : Fréq(1) = 1 MHz (pas de repliement)", m.freq);
const v = Engine.view(a.rec, "ch1", -5e-3, 5e-3, 50);
ok(v.max[10] - v.min[10] > 0.35, "1 MHz à 1 ms/div : bande pleine (min/max) au lieu d'un faux signal", (v.max[10] - v.min[10]).toFixed(3));
ok(Engine.crossings(a.rec, "ch1", 2, 1, 0, a.rec.P).length === 0, "niveau de déclenchement hors du signal : aucun front (image instable)");

console.log("— TP1 D, TP3 : LED et logique TTL —");
a = run("tp1-D1-led", { wave: "square", vpp: 5, offset: 2.5, f: 1 });
const iLed = a.rec.leds.LED;
ok(near(iLed.max, (5 - 1.9) / 380, 0.0015) && near(iLed.avg, iLed.max / 2, 0.0006), "LED 330 Ω, carré 0–5 V : ≈ 8 mA allumée, moyenne ≈ moitié", (iLed.max * 1e3).toFixed(2) + " mA");
a = run("tp3-A-nand", { on: false }, P5);
ok(meas(a, "ch2").mean < 0.4 && a.rec.leds.LED.avg < 1e-4, "NAND A = B = 1 : Y bas (< 0,4 V), LED éteinte", meas(a, "ch2").mean.toFixed(3));
a = run("tp3-A-nand", { on: false }, P5, s => s.wiring.wires.forEach(w => { if (w.de === "T1f50") w.vers = "TOP-L1-9"; }));
ok(meas(a, "ch2").mean > 2.7 && a.rec.leds.LED.avg > 2e-3, "NAND A = 0 : Y haut (> 2,7 V), LED allumée", meas(a, "ch2").mean.toFixed(3) + " V");
a = run("tp3-A-nand", { on: false }, P5, s => s.wiring.wires = s.wiring.wires.filter(w => w.de !== "T1f50"));
ok(meas(a, "ch2").mean < 0.4, "entrée TTL en l'air = 1 logique (Y bas)");
a = run("tp3-A-nand", { on: false }, psu(15, null, null, 0.1));
ok(a.warnings.some(w => /DÉTRUITE/.test(w)), "74LS00 alimenté en 15 V : puce détruite signalée");
a = run("tp3-A2-seuils", { wave: "triangle", vpp: 5, offset: 2.5 }, P5);
const yf = Engine.crossings(a.rec, "ch2", 1.75, -1, 0, a.rec.P)[0], vin = Engine.at(a.rec, "ch1", yf - 10e-9);
ok(near(vin, 1.3, 0.08), "NAND en inverseur : bascule quand l'entrée passe ≈ 1,3 V", vin.toFixed(3) + " V");
a = run("tp3-B-bascule-D", { wave: "square", vpp: 5, offset: 2.5 }, P5);
ok(near(meas(a, "ch2", 0, 2 * a.rec.P).freq, 500, 1), "bascule D (D = Q̄) : Q = CLK / 2", meas(a, "ch2", 0, 2 * a.rec.P).freq);
const ck = Engine.crossings(a.rec, "ch1", 1.5, 1, 0, a.rec.P), qr = Engine.crossings(a.rec, "ch2", 1.5, 1, 0, a.rec.P), qf = Engine.crossings(a.rec, "ch2", 1.5, -1, 0, a.rec.P);
const tplh = qr[0] - ck.filter(x => x < qr[0]).pop(), tphl = qf[0] - ck.filter(x => x < qf[0]).pop();
ok(tplh > 13e-9 && tplh < 25e-9, "retard CLK → Q montant à 1,5 V entre 13 et 25 ns (fiche : 13 typ, 25 max)", (tplh * 1e9).toFixed(1) + " ns");
ok(tphl > 25e-9 && tphl < 40e-9, "retard CLK → Q descendant à 1,5 V entre 25 et 40 ns (fiche : 25 typ, 40 max)", (tphl * 1e9).toFixed(1) + " ns");
a = run("tp3-C-compteur", { wave: "square", vpp: 5, offset: 2.5 }, P5, s => s.wiring.wires.forEach(w => { if (w.de === "BNC2.core") w.vers = "T1c45"; }));
ok(near(meas(a, "ch2", 0, 2 * a.rec.P).freq, 250, 1), "compteur : Q1 = CLK / 4", meas(a, "ch2", 0, 2 * a.rec.P).freq);
ok(Object.values(a.rec.leds).every(l => l.avg > 1e-3), "compteur : les deux LED clignotent");

console.log("— multimètre et sortie Sync —");
a = run("tp1-B1-pont-diviseur", { vpp: 2 }, null, s => { s.wiring.dmm = { v: s.wiring.wires.find(w => w.de === "BNC2.core").vers, com: "TOP-L1-20" }; });
ok(near(a.rec.dmm.acRms, 2 * 10020 / 10070 * 1000 / 10020 / (2 * Math.SQRT2), 0.0005), "multimètre TRMS sur le pont : Vpp / (2√2)", (a.rec.dmm.acRms * 1e3).toFixed(2) + " mV");
a = run("tp3-B-bascule-D", { on: false, wave: "square", vpp: 5, offset: 2.5 }, P5);
ok(!a.rec.dc && near(meas(a, "ch2", 0, 2 * a.rec.P).freq, 500, 1), "sortie 1 du GBF éteinte : la Sync reste active (manuel EDU33210)");
a = run("tp3-B-bascule-D", { on: true, sync: false, wave: "square", vpp: 5, offset: 2.5 }, P5);
ok(a.rec.dc, "Sync désactivée (menu Trigger) : plus d'horloge");

console.log(fails ? `\n${fails} ÉCHEC(S)` : "\nTOUS LES TESTS PASSENT");
process.exit(fails ? 1 : 0);
