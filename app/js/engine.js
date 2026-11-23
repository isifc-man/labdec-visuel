// =====================================================================================
// MOTEUR — pur (aucun DOM), testable sous Node : voir tests/engine_test.js
// Port JavaScript de tools/netlist.py (extraction de netlist + solveur AC par MNA complexe).
//
//   câblage posé + câbles d'appareils -> nœuds (union-find) -> éléments (R, C, V, AOP)
//   -> solveur -> Vs/Ve, déphasage, point continu, alimentation de l'AOP
//   -> formes d'onde (saturation, vitesse de montée, passe-bas) lues par l'écran de l'oscillo
//
// Convention (identique à netlist.py) :
//   · TERRE = blindages des BNC (le GBF et l'oscillo sont reliés à la terre) ;
//   · alimentation FLOTTANTE : son 0 V n'est relié à la terre que par les fils de la plaque ;
//   · chaque nœud est tiré vers la terre par 1 GΩ (gmin).
// Paramètres (hardware/behavior.yaml) : TL081 GBW 4 MHz et SR 13 V/µs vérifiés ; marge de saturation 2,5 V à vérifier.
// Limites assumées : pas de LED, pas de numérique (74LS00/74LS74) -> supported:false + raison, jamais de valeur inventée.
// =====================================================================================
const Engine = (() => {
  const DEV = ["gbf", "scope", "psu"];
  const isDev = e => e.indexOf(".") > 0 && DEV.includes(e.split(".")[0]);
  const DEFAULTS = { gbfRout: 50, scopeR: 1e6, scopeCpf: 16, cablePf: 100, a0: 2e5, gbw: 4e6, slew: 13e6, vsatMargin: 2.5 };

  class UF {
    constructor() { this.p = new Map(); }
    f(x) {
      if (!this.p.has(x)) this.p.set(x, x);
      let r = x;
      while (this.p.get(r) !== r) r = this.p.get(r);
      let c = x;
      while (this.p.get(c) !== r) { const n = this.p.get(c); this.p.set(c, r); c = n; }
      return r;
    }
    u(a, b) { const ra = this.f(a), rb = this.f(b); if (ra !== rb) this.p.set(ra, rb); }
    c(a, b) { return this.f(a) === this.f(b); }
  }

  // trou de la plaque où tombe la broche p d'une puce DIP (encoche en haut)
  function pinHole(ch, p, lib) {
    const n = lib[ch.modele].dip, half = Math.floor(n / 2);
    const letter = p <= half ? "j" : "a";
    const row = p <= half ? ch.rangee_broche1 - (p - 1) : ch.rangee_broche1 - (half - 1) + (p - half - 1);
    return `${ch.bloc}${letter}${row}`;
  }

  // wiring : {wires:[{de,vers}], comps:[{name,type,a,b,ohm}], chips:[{ref,modele,bloc,rangee_broche1}]}
  // env    : {holes, holeIds:Set, chipsLib, cables, gbf:{offset}, psu:{on,v:{1,2,3}}, params?}
  function buildNet(wiring, env) {
    const P = Object.assign({}, DEFAULTS, env.params || {});
    const uf = new UF(), EARTH = "EARTH";
    uf.f(EARTH);
    const port = e => "P:" + e;

    env.holes.forEach(h => uf.u(h.id, h.net));
    (wiring.chips || []).forEach(ch => {
      const spec = env.chipsLib[ch.modele];
      if (spec) for (let p = 1; p <= spec.dip; p++) uf.u(`${ch.ref}.${p}`, pinHole(ch, p, env.chipsLib));
    });
    (wiring.wires || []).forEach(w => uf.u(w.de, w.vers));

    const portsUsed = new Set();
    (env.cables || []).forEach(cb => {
      const a = cb.de, b = cb.vers;
      [a, b].forEach(e => { if (isDev(e)) portsUsed.add(e); });
      if (isDev(a) && isDev(b)) { uf.u(port(a), port(b)); return; }
      const dev = isDev(a) ? a : b, con = isDev(a) ? b : a;
      if (env.holeIds.has(con + ".core")) { uf.u(port(dev), con + ".core"); uf.u(con + ".shield", EARTH); }
      else if (env.holeIds.has(con + ".main")) uf.u(port(dev), con + ".main");
    });

    const names = new Map([[uf.f(EARTH), "0"]]);
    let count = 0;
    const node = k => { const r = uf.f(k); if (!names.has(r)) names.set(r, "n" + (++count)); return names.get(r); };

    const el = [], notes = [], warnings = [];
    let digital = false, led = false;
    (wiring.comps || []).forEach(c => {
      if (c.type === "resistor") el.push({ k: "R", name: c.name, a: node(c.a), b: node(c.b), v: Number(c.ohm) });
      else if (c.type === "led") led = true;
    });
    const opamps = [];
    (wiring.chips || []).forEach(ch => {
      if (ch.modele === "TL081") {
        const g = p => node(`${ch.ref}.${p}`);
        opamps.push({ k: "OPAMP", name: ch.ref, inp: g(3), inn: g(2), vcc: g(7), vee: g(4), out: g(6) });
      } else digital = true;
    });
    if (led) notes.push("LED : non modélisée (pas de diode dans le solveur).");
    if (digital) notes.push("Puce numérique 74LS : moteur numérique absent (étape M6).");

    const gbfAll = [...portsUsed].filter(p => p.startsWith("gbf."));
    const gbfOut = gbfAll.filter(p => p.startsWith("gbf.out"));
    const logicSrc = gbfAll.length > 0 && gbfOut.length === 0;       // ex. SYNC TTL
    gbfOut.slice(0, 1).forEach(p => {
      el.push({ k: "V", name: "Vgbf", a: "gbf_int", b: "0", dc: (env.gbf && env.gbf.offset) || 0, ac: 1, src: "gbf" });
      el.push({ k: "R", name: "Rout_gbf", a: "gbf_int", b: node(port(p)), v: P.gbfRout });
    });
    [...portsUsed].sort().forEach(p => {
      if (!p.startsWith("scope.")) return;
      const nd = node(port(p));
      el.push({ k: "R", name: "Rin_" + p, a: nd, b: "0", v: P.scopeR });
      el.push({ k: "C", name: "Cin_" + p, a: nd, b: "0", v: P.scopeCpf * 1e-12 });
    });
    const psuOn = !(env.psu && env.psu.on === false);
    [1, 2, 3].forEach(k => {
      const plus = `psu.ch${k}_plus`, moins = `psu.ch${k}_moins`;
      if (portsUsed.has(plus) || portsUsed.has(moins)) {
        const v = psuOn ? Number(((env.psu && env.psu.v) || {})[k] || 0) : 0;
        el.push({ k: "V", name: "Vpsu" + k, a: node(port(plus)), b: node(port(moins)), dc: v, ac: 0, src: "psu" });
      }
    });
    (env.cables || []).forEach(cb => [cb.de, cb.vers].forEach(e => {
      if (env.holeIds.has(e + ".core") && P.cablePf)
        el.push({ k: "C", name: "Ccab_" + cb.id, a: node(e + ".core"), b: "0", v: P.cablePf * 1e-12 });
    }));

    const probes = {};
    [...portsUsed].sort().forEach(p => { if (p.startsWith("scope.ch")) probes[p.split(".")[1]] = node(port(p)); });

    const mins = [...portsUsed].filter(p => p.startsWith("psu.") && p.endsWith("_moins"));
    if (mins.length && !mins.some(p => uf.c(port(p), EARTH)))
      warnings.push("ALIMENTATION FLOTTANTE : le 0 V de l'alim n'est relié ni à la masse de la plaque ni aux blindages BNC.");

    const nodeSet = new Set(["0"]);
    el.forEach(e => ["a", "b"].forEach(y => { if (e[y]) nodeSet.add(e[y]); }));
    opamps.forEach(o => ["inp", "inn", "vcc", "vee", "out"].forEach(y => nodeSet.add(o[y])));
    return { uf, elements: el, opamps, nodes: [...nodeSet].sort(), probes, notes, warnings, digital, led, logicSrc, node, P, portsUsed };
  }

  // ---- algèbre complexe ----------------------------------------------------------------
  const cadd = (a, b) => [a[0] + b[0], a[1] + b[1]];
  const csub = (a, b) => [a[0] - b[0], a[1] - b[1]];
  const cmul = (a, b) => [a[0] * b[0] - a[1] * b[1], a[0] * b[1] + a[1] * b[0]];
  const cdiv = (a, b) => { const d = b[0] * b[0] + b[1] * b[1]; return [(a[0] * b[0] + a[1] * b[1]) / d, (a[1] * b[0] - a[0] * b[1]) / d]; };
  const cabs = a => Math.hypot(a[0], a[1]);

  function gauss(A, b) {
    const n = b.length;
    for (let i = 0; i < n; i++) {
      let piv = i, best = cabs(A[i][i]);
      for (let r = i + 1; r < n; r++) { const m = cabs(A[r][i]); if (m > best) { best = m; piv = r; } }
      if (best < 1e-300) throw new Error("matrice singulière");
      if (piv !== i) { [A[i], A[piv]] = [A[piv], A[i]]; [b[i], b[piv]] = [b[piv], b[i]]; }
      for (let r = i + 1; r < n; r++) {
        const m = cdiv(A[r][i], A[i][i]);
        if (m[0] === 0 && m[1] === 0) continue;
        for (let c = i; c < n; c++) A[r][c] = csub(A[r][c], cmul(m, A[i][c]));
        b[r] = csub(b[r], cmul(m, b[i]));
      }
    }
    const x = new Array(n);
    for (let i = n - 1; i >= 0; i--) {
      let s = b[i];
      for (let c = i + 1; c < n; c++) s = csub(s, cmul(A[i][c], x[c]));
      x[i] = cdiv(s, A[i][i]);
    }
    return x;
  }

  // MNA. dc=true : point continu (condensateurs ouverts, sources à leur valeur DC).
  // opOn[i]=false : l'AOP i n'est pas alimenté, il ne pilote pas sa sortie.
  function acSolve(net, f, dc, opOn) {
    const P = net.P, w = 2 * Math.PI * f;
    const s = dc ? [0, 1e-12] : [0, w];
    const nodes = net.nodes.filter(n => n !== "0");
    const idx = new Map(nodes.map((n, i) => [n, i]));
    const vs = net.elements.filter(e => e.k === "V");
    const ops = net.opamps.filter((o, i) => !opOn || opOn[i]);
    const N = nodes.length + vs.length + ops.length;
    const A = Array.from({ length: N }, () => Array.from({ length: N }, () => [0, 0]));
    const b = Array.from({ length: N }, () => [0, 0]);
    const ix = n => idx.has(n) ? idx.get(n) : null;
    const add = (i, j, v) => { if (i !== null && j !== null) A[i][j] = cadd(A[i][j], v); };
    net.elements.forEach(e => {
      if (e.k !== "R" && e.k !== "C") return;
      const y = e.k === "R" ? [1 / e.v, 0] : cmul(s, [e.v, 0]);
      const a = ix(e.a), c = ix(e.b), ny = [-y[0], -y[1]];
      add(a, a, y); add(c, c, y); add(a, c, ny); add(c, a, ny);
    });
    nodes.forEach(n => add(ix(n), ix(n), [1e-9, 0]));
    vs.forEach((e, k) => {
      const row = nodes.length + k, p = ix(e.a), n = ix(e.b);
      add(p, row, [1, 0]); add(n, row, [-1, 0]); add(row, p, [1, 0]); add(row, n, [-1, 0]);
      b[row] = dc ? [e.dc, 0] : [e.src === "gbf" ? e.ac : 0, 0];
    });
    const wp = 2 * Math.PI * P.gbw / P.a0;
    ops.forEach((o, k) => {
      const row = nodes.length + vs.length + k;
      const Ag = cdiv([P.a0, 0], cadd([1, 0], cdiv(s, [wp, 0])));
      const out = ix(o.out), ip = ix(o.inp), im = ix(o.inn);
      add(out, row, [1, 0]); add(row, out, [1, 0]);
      add(row, ip, [-Ag[0], -Ag[1]]); add(row, im, Ag);
    });
    const x = gauss(A, b);
    const res = new Map([["0", [0, 0]]]);
    nodes.forEach((n, i) => res.set(n, x[i]));
    vs.forEach((e, k) => res.set("I:" + e.name, x[nodes.length + k]));   // courant entrant par la borne + (sortant de la source = −I)
    return res;
  }

  // nœuds reliés (par R ou source) à une borne d'alimentation ou à la terre : les seuls qui ont un potentiel défini
  function drivenNodes(net) {
    const adj = new Map();
    const link = (a, b) => { if (!adj.has(a)) adj.set(a, []); if (!adj.has(b)) adj.set(b, []); adj.get(a).push(b); adj.get(b).push(a); };
    net.elements.forEach(e => { if (e.k === "R" || e.k === "V") link(e.a, e.b); });
    const seen = new Set(), stack = [];
    net.elements.forEach(e => { if (e.k === "V" && e.src === "psu") { stack.push(e.a, e.b); } });
    while (stack.length) { const n = stack.pop(); if (seen.has(n)) continue; seen.add(n); (adj.get(n) || []).forEach(m => stack.push(m)); }
    return seen;
  }

  // ---- analyse complète d'un montage -----------------------------------------------------
  function analyze(wiring, env, gbf) {
    const net = buildNet(wiring, env);
    const an = { net, supported: true, reasons: [], warnings: net.warnings.slice(), notes: net.notes.slice(),
      powered: true, hasOpamp: net.opamps.length > 0, digital: net.digital, probes: net.probes,
      rails: { hi: Infinity, lo: -Infinity }, opOn: net.opamps.map(() => true) };
    if (net.digital) { an.supported = false; an.reasons.push("Montage numérique (74LS) : écran non simulé."); }
    if (net.logicSrc) { an.supported = false; an.reasons.push("Source logique SYNC : non modélisée."); }
    if (net.led) { an.supported = false; an.reasons.push("LED non modélisée."); }
    if (!net.probes.ch1 && !net.probes.ch2) { an.supported = false; an.reasons.push("Aucune voie d'oscillo câblée."); return an; }

    try {
      if (net.opamps.length) {
        const d0 = acSolve(net, 0, true, an.opOn);
        // une broche d'alimentation doit être RELIÉE à une source (un nœud flottant lit 0 V sans être alimenté)
        const driven = drivenNodes(net);
        an.opOn = net.opamps.map(o => {
          const vp = d0.get(o.vcc)[0], vm = d0.get(o.vee)[0];
          return driven.has(o.vcc) && driven.has(o.vee) && (vp - vm) >= 10;
        });
        an.powered = an.opOn.every(Boolean);
        if (!an.powered) an.warnings.push("AOP non alimenté (V+ / V− absents ou inversés) : sa sortie reste à 0 V.");
        net.opamps.forEach((o, i) => {
          if (!an.opOn[i]) return;
          an.rails.hi = Math.min(an.rails.hi, d0.get(o.vcc)[0] - net.P.vsatMargin);
          an.rails.lo = Math.max(an.rails.lo, d0.get(o.vee)[0] + net.P.vsatMargin);
        });
      }
      const f = Math.max(0.001, (gbf && gbf.f) || 1000);
      const acv = acSolve(net, f, false, an.opOn), dcv = acSolve(net, 0, true, an.opOn);
      const lv = acSolve(net, Math.max(0.01, f / 1000), false, an.opOn);
      const g = (m, n) => n ? m.get(n) : null;
      an.V1 = g(acv, net.probes.ch1); an.V2 = g(acv, net.probes.ch2);
      an.K1 = g(lv, net.probes.ch1); an.K2 = g(lv, net.probes.ch2);
      an.psuI = {};
      [1, 2, 3].forEach(k => { const i = dcv.get("I:Vpsu" + k); if (i) an.psuI[k] = -i[0]; });
      an.dc1 = net.probes.ch1 ? dcv.get(net.probes.ch1)[0] : 0;
      an.dc2 = net.probes.ch2 ? dcv.get(net.probes.ch2)[0] : 0;
      if (an.V1 && an.V2) {
        an.H = cdiv(an.V2, an.V1); an.gain = cabs(an.H);
        an.phaseDeg = Math.atan2(an.H[1], an.H[0]) * 180 / Math.PI;
      }
    } catch (e) { an.supported = false; an.reasons.push("Calcul impossible : " + e.message); }
    return an;
  }

  // fréquence de coupure à −3 dB (balayage log 10 Hz → 50 MHz), null si introuvable
  function cutoff(an) {
    if (!an.K1 || !an.K2 || !an.net.probes.ch1 || !an.net.probes.ch2) return null;
    const g0 = cabs(cdiv(an.K2, an.K1));
    if (!(g0 > 1e-9)) return null;
    let prev = null;
    for (let e = 1; e <= 7.7; e += 0.05) {
      const f = Math.pow(10, e);
      let g;
      try { const v = acSolve(an.net, f, false, an.opOn); g = cabs(cdiv(v.get(an.net.probes.ch2), v.get(an.net.probes.ch1))); } catch (x) { return null; }
      if (g <= g0 / Math.SQRT2) {
        if (!prev) return f;
        const t = (Math.log(g0 / Math.SQRT2) - Math.log(prev.g)) / (Math.log(g) - Math.log(prev.g));
        return Math.pow(10, prev.e + t * (e - prev.e));
      }
      prev = { e, g };
    }
    return null;
  }

  const shape = (wave, ph) => wave === "square" ? (ph < 0.5 ? 1 : -1) : wave === "triangle" ? (ph < 0.5 ? -1 + 4 * ph : 3 - 4 * ph) : Math.sin(2 * Math.PI * ph);

  // Fenêtre [-5,+5]×tdiv ; déclenchement : front montant de la voie 1 à t = 0.
  // Décalage temporel qui place un front montant de la voie 1 au niveau `level` à t = 0 (null : pas de déclenchement possible).
  function trigShift(an, gbf, level) {
    if (!an.V1 || gbf.on === false) return null;
    const f = Math.max(0.001, gbf.f || 1000), A = (gbf.vpp || 0) / 2 * cabs(an.V1), x = (level - an.dc1) / (A || 1e-12);
    if (!(A > 0) || x < -1 || x > 1) return null;
    const ph1 = Math.atan2(an.V1[1], an.V1[0]);
    if (gbf.wave === "square") return x <= 1 ? 0 : null;
    if (gbf.wave === "triangle") return ((x + 1) / 4) / f;
    return (Math.asin(x) - ph1) / (2 * Math.PI * f);
  }

  function waveforms(an, gbf, tdiv, N, shift) {
    N = N || 900; shift = shift || 0;
    const f = Math.max(0.001, gbf.f || 1000), T = 1 / f, A = (gbf.vpp || 0) / 2, wave = gbf.wave || "sine";
    const on = gbf.on !== false;
    const hasCh1 = !!an.probes.ch1, hasCh2 = !!an.probes.ch2 && an.supported && !!an.V2;
    const win = 10 * tdiv, t0 = -5 * tdiv;
    const t = new Array(N + 1), v1 = new Array(N + 1), v2 = new Array(N + 1);

    const mag1 = an.V1 ? cabs(an.V1) : 1, ph1 = an.V1 ? Math.atan2(an.V1[1], an.V1[0]) : 0;
    for (let i = 0; i <= N; i++) {
      const tdisp = t0 + i / N * win; t[i] = tdisp; const ti = tdisp + shift;
      if (!hasCh1) { v1[i] = 0; continue; }
      if (!on) { v1[i] = an.dc1 - (gbf.offset || 0); continue; }
      v1[i] = (wave === "sine" ? A * mag1 * Math.sin(2 * Math.PI * f * ti + ph1) : A * mag1 * shape(wave, ((f * ti) % 1 + 1) % 1)) + an.dc1;
    }

    if (!hasCh2) { for (let i = 0; i <= N; i++) v2[i] = 0; }
    else {
      const P = an.net.P;
      const hi = an.hasOpamp ? an.rails.hi : Infinity, lo = an.hasOpamp ? an.rails.lo : -Infinity;
      const mag2 = cabs(an.V2), ph2 = Math.atan2(an.V2[1], an.V2[0]);
      let fc = null, K = 0;
      if (wave !== "sine") { fc = cutoff(an); K = an.K2[0] * (an.K1[0] < 0 ? -1 : 1); }
      const tau = fc ? 1 / (2 * Math.PI * fc) : 0;
      let dts = Math.min(win / N, T / 200);
      if (tau) dts = Math.min(dts, tau / 12);
      const pre = 3 * T + 6 * tau;
      let steps = Math.ceil((win + pre) / dts);
      if (steps > 150000) { dts = (win + pre) / 150000; steps = 150000; }
      let y = 0, yo = an.dc2, k = 0;
      for (let s = 0; s <= steps; s++) {
        const ts = t0 - pre + s * dts, tsig = ts + shift, ph = ((f * tsig) % 1 + 1) % 1;
        let tgt;
        if (!on) tgt = an.dc2;
        else if (wave === "sine") tgt = A * mag2 * Math.sin(2 * Math.PI * f * tsig + ph2) + an.dc2;
        else { const x = A * shape(wave, ph) * K; y = tau ? y + (x - y) * (1 - Math.exp(-dts / tau)) : x; tgt = y + an.dc2; }
        tgt = Math.max(lo, Math.min(hi, tgt));
        if (an.hasOpamp) { const md = P.slew * dts, d = tgt - yo; yo += Math.abs(d) > md ? Math.sign(d) * md : d; } else yo = tgt;
        while (k <= N && t[k] <= ts + dts) { v2[k] = yo; k++; }
      }
      for (; k <= N; k++) v2[k] = yo;
    }
    const st = a => { let mx = -Infinity, mn = Infinity, s = 0; a.forEach(x => { if (x > mx) mx = x; if (x < mn) mn = x; s += x; }); return { max: mx, min: mn, vpp: mx - mn, mean: s / a.length }; };
    return { t, v1, v2, stats: { ch1: st(v1), ch2: st(v2) }, hasCh1, hasCh2 };
  }

  return { buildNet, acSolve, analyze, waveforms, trigShift, cutoff, pinHole, UF, DEFAULTS };
})();

if (typeof module !== "undefined") module.exports = Engine;
