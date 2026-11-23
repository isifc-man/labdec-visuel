// =====================================================================================
// MOTEUR — pur (aucun DOM), testable sous Node : voir tests/engine_test.js
//
//   câblage posé + câbles d'appareils -> nœuds (union-find) -> éléments
//   -> simulation TEMPORELLE en régime périodique (méthode nodale modifiée, intégration implicite
//      Gear-2 avec redémarrage Euler aux discontinuités, Newton pour les diodes, « ensembles actifs »
//      pour les butées de l'AOP et la limite de courant de l'alim)
//   -> enregistrement d'une période (ou plusieurs pour les bascules) lu par l'oscilloscope.
//
// Ce qui est simulé :
//   · GBF : 50 Ω, sinus / carré (fronts de 10 ns) / triangle, offset ; sortie Sync (créneau 0–5 V, 50 Ω).
//   · Oscilloscope : 1 MΩ ∥ 16 pF par voie, câble BNC ≈ 100 pF.
//   · Alimentation : 3 voies flottantes, CV / CC (limite de courant réglée), court-circuit compris.
//   · TL081 : un pôle (GBW 4 MHz), vitesse de montée 13 V/µs, saturation PAR ÉTAGE à 2,5 V des rails,
//     résistance de sortie 50 Ω, courant de repos 1,4 mA ; non alimenté / alimenté à l'envers signalés.
//   · LED rouge (diode exponentielle, paramètres de hardware/behavior.yaml).
//   · 74LS00 et 74LS74 : seuil d'entrée 1,3 V, entrée en l'air = 1, sorties ≈ 3,5 V / 0,1 V avec
//     résistances de sortie, diodes d'entrée, retards de propagation de la fiche TI, fronts de 6 ns,
//     alimentation hors plage (< 4,5 V ou > 7 V) signalée.
// Convention : TERRE = blindages des BNC ; l'alim est FLOTTANTE ; chaque nœud est tiré vers la terre par 1 GΩ.
// =====================================================================================
const Engine = (() => {
  const DEV = ["gbf", "scope", "psu"];
  const isDev = e => e.indexOf(".") > 0 && DEV.includes(e.split(".")[0]);
  const DEFAULTS = {
    gbfRout: 50, gbfEdge: 10e-9, syncHigh: 5, syncRout: 50,
    scopeR: 1e6, scopeCpf: 16, cablePf: 100,
    a0: 2e5, gbw: 4e6, slew: 13e6, vsatMargin: 2.5, opRout: 50, opIq: 1.4e-3, opMinSupply: 10,
    psuR: 0.01, gmin: 1e-9,
    ledNvt: 0.1, ledVf: 1.9, ledIref: 0.008, ledImax: 0.03,
    ttlVth: 1.3, ttlVin: 1.6, ttlRin: 4000, ttlRoh: 60, ttlRol: 30, ttlVol: 0.1, ttlDrop: 1.5, ttlEdge: 6e-9,
    ttlVccOk: 4.5, ttlVccMax: 7, clampIs: 1e-14, clampNvt: 0.02585,
    stepsPerPeriod: 400,
  };
  // Fiches TI : SN74LS00 tPLH 9 ns / tPHL 10 ns typ ; SN74LS74A CLK→Q tPLH 13 ns / tPHL 25 ns typ.
  const CHIPS = {
    "74LS00": { lh: 9e-9, hl: 10e-9, icc: 2.5e-3, inputs: [1, 2, 4, 5, 9, 10, 12, 13], outputs: [3, 6, 8, 11],
      gates: [[1, 2, 3], [4, 5, 6], [9, 10, 8], [12, 13, 11]] },
    "74LS74": { lh: 13e-9, hl: 25e-9, icc: 4e-3, inputs: [1, 2, 3, 4, 10, 11, 12, 13], outputs: [5, 6, 8, 9],
      ffs: [{ clr: 1, d: 2, clk: 3, pre: 4, q: 5, qb: 6 }, { clr: 13, d: 12, clk: 11, pre: 10, q: 9, qb: 8 }] },
  };

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

  // ---------------------------------------------------------------------------------------
  // 1. NETLIST
  // wiring : {wires:[{de,vers}], comps:[{name,type,a,b|k,ohm}], chips:[{ref,modele,bloc,rangee_broche1}]}
  // env    : {holes, holeIds:Set, chipsLib, cables, params?}
  function buildNet(wiring, env) {
    const P = Object.assign({}, DEFAULTS, env.params || {});
    const uf = new UF(), EARTH = "EARTH";
    uf.f(EARTH);
    const port = e => "P:" + e;
    env.holes.forEach(h => uf.u(h.id, h.net));
    const chipsIn = (wiring.chips || []).filter(ch => env.chipsLib[ch.modele]);
    chipsIn.forEach(ch => { for (let p = 1; p <= env.chipsLib[ch.modele].dip; p++) uf.u(`${ch.ref}.${p}`, pinHole(ch, p, env.chipsLib)); });
    (wiring.wires || []).forEach(w => uf.u(w.de, w.vers));
    (wiring.comps || []).forEach(c => { uf.u(c.name + ".a", c.a); if (c.type === "led") uf.u(c.name + ".k", c.k); else uf.u(c.name + ".b", c.b); });

    const portsUsed = new Set(), cableHoles = [];
    (env.cables || []).forEach(cb => {
      const a = cb.de, b = cb.vers;
      [a, b].forEach(e => { if (isDev(e)) portsUsed.add(e); });
      if (isDev(a) && isDev(b)) { uf.u(port(a), port(b)); return; }
      const dev = isDev(a) ? a : b, con = isDev(a) ? b : a;
      if (env.holeIds.has(con + ".core")) { uf.u(port(dev), con + ".core"); uf.u(con + ".shield", EARTH); cableHoles.push([cb.id, con + ".core"]); }
      else if (env.holeIds.has(con + ".main")) uf.u(port(dev), con + ".main");
    });

    const names = new Map([[uf.f(EARTH), "0"]]);
    let count = 0;
    const node = k => { const r = uf.f(k); if (!names.has(r)) names.set(r, "n" + (++count)); return names.get(r); };

    const R = [], C = [], TH = [], psu = [], ops = [], leds = [], chips = [], warnings = [], notes = [], info = [];
    (wiring.comps || []).forEach(c => {
      if (c.type === "resistor") {
        const a = node(c.a), b = node(c.b), v = Number(c.ohm);
        if (a === b) warnings.push(`${c.name} (${fmtOhmE(v)}) est court-circuitée : ses deux pattes sont reliées au même nœud.`);
        if (v > 0) R.push({ a, b, g: 1 / v, name: c.name });
      } else if (c.type === "led") {
        const a = node(c.a), k = node(c.k);
        if (a === k) warnings.push(`${c.name} est court-circuitée : anode et cathode sur le même nœud.`);
        leds.push({ name: c.name, a, k });
      }
    });
    chipsIn.forEach(ch => {
      const g = p => node(`${ch.ref}.${p}`);
      if (ch.modele === "TL081") {
        const o = { name: ch.ref, inp: g(3), inn: g(2), vcc: g(7), vee: g(4), out: g(6), y: "y:" + ch.ref };
        ops.push(o);
        R.push({ a: o.y, b: o.out, g: 1 / P.opRout, name: ch.ref + ".Rout" });
        R.push({ a: o.vcc, b: o.vee, g: P.opIq / 30, name: ch.ref + ".Iq" });
      } else if (CHIPS[ch.modele]) {
        const spec = CHIPS[ch.modele], pins = {};
        for (let p = 1; p <= 14; p++) pins[p] = g(p);
        chips.push({ ref: ch.ref, model: ch.modele, spec, pins, vcc: pins[14], gnd: pins[7] });
        R.push({ a: pins[14], b: pins[7], g: spec.icc / 5, name: ch.ref + ".Icc" });
      } else notes.push(`${ch.modele} : modèle absent du simulateur.`);
    });

    if (portsUsed.has("gbf.out1")) TH.push({ kind: "gbf", a: node(port("gbf.out1")), b: "0", r: P.gbfRout });
    if (portsUsed.has("gbf.sync_out")) TH.push({ kind: "sync", a: node(port("gbf.sync_out")), b: "0", r: P.syncRout });
    const probes = {};
    ["scope.ch1", "scope.ch2"].forEach(p => {
      if (!portsUsed.has(p)) return;
      const nd = node(port(p));
      R.push({ a: nd, b: "0", g: 1 / P.scopeR, name: "Rin_" + p });
      C.push({ a: nd, b: "0", c: P.scopeCpf * 1e-12, name: "Cin_" + p });
      probes[p.split(".")[1]] = nd;
    });
    [1, 2, 3].forEach(k => {
      const plus = `psu.ch${k}_plus`, moins = `psu.ch${k}_moins`;
      if (portsUsed.has(plus) || portsUsed.has(moins)) psu.push({ k, a: node(port(plus)), b: node(port(moins)) });
    });
    cableHoles.forEach(([id, h]) => { if (P.cablePf) C.push({ a: node(h), b: "0", c: P.cablePf * 1e-12, name: "Ccab_" + id }); });

    const mins = [...portsUsed].filter(p => p.startsWith("psu.") && p.endsWith("_moins"));
    if (mins.length && !mins.some(p => uf.c(port(p), EARTH)))
      warnings.push("ALIMENTATION FLOTTANTE : le 0 V de l'alim n'est relié ni à la masse de la plaque ni aux blindages BNC.");

    // nœuds réellement utilisés
    const nodeSet = new Set();
    const add = n => { if (n && n !== "0") nodeSet.add(n); };
    R.forEach(e => { add(e.a); add(e.b); }); C.forEach(e => { add(e.a); add(e.b); }); TH.forEach(e => add(e.a));
    psu.forEach(e => { add(e.a); add(e.b); }); leds.forEach(e => { add(e.a); add(e.k); });
    ops.forEach(o => ["inp", "inn", "vcc", "vee", "out", "y"].forEach(y => add(o[y])));
    chips.forEach(c => Object.values(c.pins).forEach(add));
    return { uf, node, P, R, C, TH, psu, ops, leds, chips, probes, nodes: [...nodeSet].sort(), warnings, notes, info, portsUsed };
  }
  const fmtOhmE = v => v >= 1e6 ? +(v / 1e6).toFixed(2) + " MΩ" : v >= 1e3 ? String(+(v / 1e3).toFixed(2)).replace(".", ",") + " kΩ" : v + " Ω";

  // ---------------------------------------------------------------------------------------
  // 2. ALGÈBRE : élimination de Gauss avec pivot partiel (matrice dense, Float64Array)
  function solveLin(A, b, N) {
    for (let i = 0; i < N; i++) {
      let piv = i, best = Math.abs(A[i * N + i]);
      for (let r = i + 1; r < N; r++) { const m = Math.abs(A[r * N + i]); if (m > best) { best = m; piv = r; } }
      if (best < 1e-300) return null;
      if (piv !== i) {
        for (let c = 0; c < N; c++) { const t = A[i * N + c]; A[i * N + c] = A[piv * N + c]; A[piv * N + c] = t; }
        const t = b[i]; b[i] = b[piv]; b[piv] = t;
      }
      const d = A[i * N + i];
      for (let r = i + 1; r < N; r++) {
        const m = A[r * N + i] / d;
        if (m === 0) continue;
        for (let c = i; c < N; c++) A[r * N + c] -= m * A[i * N + c];
        b[r] -= m * b[i];
      }
    }
    const x = new Float64Array(N);
    for (let i = N - 1; i >= 0; i--) {
      let s = b[i];
      for (let c = i + 1; c < N; c++) s -= A[i * N + c] * x[c];
      x[i] = s / A[i * N + i];
    }
    return x;
  }

  // ---------------------------------------------------------------------------------------
  // 3. SIMULATION
  // src : {gbf:{on,f,vpp,offset,wave}, psu:{1:{v,i,on},2:…,3:…}}  (amplitudes « à vide », déjà corrigées High Z / 50 Ω)
  function simulate(net, src) {
    const P = net.P, nodes = net.nodes, nN = nodes.length;
    const idx = new Map(nodes.map((n, i) => [n, i]));
    const ix = n => (n === "0" || n == null) ? -1 : idx.get(n);
    const nOp = net.ops.length, N = nN + nOp;
    const g = src.gbf || {}, gbfOn = !!g.on && net.TH.length > 0;
    const f = Math.max(1e-3, g.f || 1000), T = 1 / f, A = (g.vpp || 0) / 2, off = g.offset || 0, wave = g.wave || "sine";
    const edge = Math.min(P.gbfEdge, T / 10);
    const psuSet = k => { const c = (src.psu || {})[k] || {}; return { v: c.on ? Number(c.v) || 0 : 0, i: Math.max(1e-4, Number(c.i) || 0.1), on: !!c.on }; };

    // ---- sources ----
    const sq = tt => { const ph = ((tt % T) + T) % T;
      if (ph < edge) return -1 + 2 * ph / edge; if (ph < T / 2) return 1;
      if (ph < T / 2 + edge) return 1 - 2 * (ph - T / 2) / edge; return -1; };
    const tri = tt => { const ph = (((tt % T) + T) % T) / T; return ph < 0.5 ? -1 + 4 * ph : 3 - 4 * ph; };
    const gbfV = tt => wave === "square" ? off + A * sq(tt) : wave === "triangle" ? off + A * tri(tt) : off + A * Math.sin(2 * Math.PI * f * tt);
    const syncV = tt => P.syncHigh * (sq(tt) + 1) / 2;
    const hasSync = net.TH.some(s => s.kind === "sync"), hasGbfOut = net.TH.some(s => s.kind === "gbf");
    const edgy = gbfOn && (hasSync || (hasGbfOut && wave !== "sine"));
    function nextSrcBreak(t) {               // prochaine discontinuité de pente des sources après t
      if (!edgy) return Infinity;
      const k = Math.floor(t / T), marks = (hasSync || wave === "square") ? [0, edge, T / 2, T / 2 + edge] : [0, T / 2];
      for (let kk = k; kk <= k + 1; kk++) for (const m of marks) { const tb = kk * T + m; if (tb > t * (1 + 1e-12) + 1e-18) return tb; }
      return Infinity;
    }

    // ---- état des éléments non linéaires / à mémoire ----
    const diodes = [];
    net.leds.forEach(l => { const is = P.ledIref / Math.exp(P.ledVf / P.ledNvt); diodes.push({ led: l.name, a: l.a, k: l.k, is, nvt: P.ledNvt, vd: 0, vcrit: P.ledNvt * Math.log(P.ledNvt / (Math.SQRT2 * is)) }); });
    const chipSt = net.chips.map(c => ({ c, powered: false, vsup: 0, over: false, rev: false, outs: {}, ffQ: [0, 0], clkPrev: [0, 0], lvl: {} }));
    chipSt.forEach(cs => {
      cs.c.spec.inputs.forEach(p => diodes.push({ a: cs.c.gnd, k: cs.c.pins[p], is: P.clampIs, nvt: P.clampNvt, vd: 0, vcrit: P.clampNvt * Math.log(P.clampNvt / (Math.SQRT2 * P.clampIs)) }));
      cs.c.spec.outputs.forEach(p => { cs.outs[p] = { from: 1, to: 1, t0: -1, target: 1 }; });
    });
    const opSt = net.ops.map(() => ({ mode: "lin", powered: false, hi: Infinity, lo: -Infinity, rev: false, satT: 0, slewT: 0 }));
    const psuSt = net.psu.map(p => Object.assign({ mode: "cv", s: 1 }, psuSet(p.k)));
    const caps = net.C.map(c => ({ a: ix(c.a), b: ix(c.b), c: c.c }));
    const res = net.R.map(r => ({ a: ix(r.a), b: ix(r.b), g: r.g }));

    // ---- assemblage ----
    const Am = new Float64Array(N * N), bv = new Float64Array(N);
    const V = (x, n) => { const i = ix(n); return i < 0 ? 0 : x[i]; };
    const addG = (a, b, gg) => { if (a >= 0) Am[a * N + a] += gg; if (b >= 0) Am[b * N + b] += gg; if (a >= 0 && b >= 0) { Am[a * N + b] -= gg; Am[b * N + a] -= gg; } };
    const addJ = (a, b, j) => { if (a >= 0) bv[a] += j; if (b >= 0) bv[b] -= j; };   // j injecté dans a, retiré de b
    const lev = (o, t) => { if (t <= o.t0) return o.from; const d = (t - o.t0) / P.ttlEdge; return d >= 1 ? o.to : o.from + (o.to - o.from) * d; };

    // integ : {dc:true} ou {h, beta, a1, a2, x1, x2} (Gear-2 ; Euler implicite : beta=1,a1=1,a2=0)
    function assemble(t, integ, x) {
      Am.fill(0); bv.fill(0);
      res.forEach(r => addG(r.a, r.b, r.g));
      for (let i = 0; i < nN; i++) Am[i * N + i] += P.gmin;
      if (!integ.dc) caps.forEach(c => {
        const gc = c.c / (integ.beta * integ.h), vp = (integ.x1 ? (c.a >= 0 ? integ.x1[c.a] : 0) - (c.b >= 0 ? integ.x1[c.b] : 0) : 0),
          vpp = integ.a2 ? ((c.a >= 0 ? integ.x2[c.a] : 0) - (c.b >= 0 ? integ.x2[c.b] : 0)) : 0;
        addG(c.a, c.b, gc); addJ(c.a, c.b, gc * (integ.a1 * vp + integ.a2 * vpp));
      });
      if (gbfOn) net.TH.forEach(s => { const e = s.kind === "gbf" ? gbfV(t) : syncV(t); addG(ix(s.a), -1, 1 / s.r); addJ(ix(s.a), -1, e / s.r); });
      net.psu.forEach((p, i) => {
        const st = psuSt[i]; if (!st.on) return;
        if (st.mode === "cv") { addG(ix(p.a), ix(p.b), 1 / P.psuR); addJ(ix(p.a), ix(p.b), st.v / P.psuR); }
        else addJ(ix(p.a), ix(p.b), st.s * st.i);
      });
      diodes.forEach(d => {
        const vd = d.vd, ex = Math.exp(Math.min(vd / d.nvt, 80)), id = d.is * (ex - 1) + (vd / d.nvt > 80 ? d.is * ex * (vd / d.nvt - 80) : 0);
        const gd = d.is * ex / d.nvt + P.gmin;
        addG(ix(d.a), ix(d.k), gd); addJ(ix(d.a), ix(d.k), -(id - gd * vd));
      });
      chipSt.forEach(cs => {
        if (!cs.powered) return;
        const gi = ix(cs.c.gnd);
        cs.c.spec.inputs.forEach(p => { addG(ix(cs.c.pins[p]), gi, 1 / P.ttlRin); addJ(ix(cs.c.pins[p]), gi, P.ttlVin / P.ttlRin); });
        const vhi = Math.max(0, cs.vsup - P.ttlDrop);
        cs.c.spec.outputs.forEach(p => {
          const l = lev(cs.outs[p], t), e = P.ttlVol + (vhi - P.ttlVol) * l, r = P.ttlRol + (P.ttlRoh - P.ttlRol) * l;
          addG(ix(cs.c.pins[p]), gi, 1 / r); addJ(ix(cs.c.pins[p]), gi, e / r);
        });
      });
      const wp = 2 * Math.PI * P.gbw / P.a0;
      net.ops.forEach((o, k) => {
        const row = nN + k, y = ix(o.y), st = opSt[k];
        Am[y * N + row] -= 1;                                   // courant de la source injecté dans le nœud interne
        if (!st.powered) { Am[row * N + row] = 1; return; }      // non alimenté : la source ne débite rien
        if (st.mode === "lin") {
          const ip = ix(o.inp), im = ix(o.inn);
          if (integ.dc) { Am[row * N + y] += 1; if (ip >= 0) Am[row * N + ip] -= P.a0; if (im >= 0) Am[row * N + im] += P.a0; }
          else {
            const k1 = integ.beta * integ.h * wp;
            Am[row * N + y] += 1 + k1;
            if (ip >= 0) Am[row * N + ip] -= k1 * P.a0; if (im >= 0) Am[row * N + im] += k1 * P.a0;
            bv[row] = integ.a1 * integ.x1[y] + integ.a2 * (integ.x2 ? integ.x2[y] : 0);
          }
        } else { Am[row * N + y] += 1; bv[row] = st.fixed; }
      });
    }

    // Newton (diodes) + ensembles actifs (AOP : linéaire / saturé / vitesse de montée ; alim : CV / CC)
    function solveAt(t, integ, xGuess) {
      let x = xGuess ? Float64Array.from(xGuess) : new Float64Array(N);
      diodes.forEach(d => { d.vd = V(x, d.a) - V(x, d.k); });
      for (let outer = 0; outer < 25; outer++) {
        let ok = false;
        for (let it = 0; it < 80; it++) {
          assemble(t, integ, x);
          const xn = solveLin(Am, bv, N);
          if (!xn) return null;
          let lim = false, dmax = 0;
          for (let i = 0; i < N; i++) dmax = Math.max(dmax, Math.abs(xn[i] - x[i]) / (1 + Math.abs(xn[i])));
          diodes.forEach(d => {
            const vn = V(xn, d.a) - V(xn, d.k), vo = d.vd;
            let v = vn;
            if (vn > d.vcrit && Math.abs(vn - vo) > 2 * d.nvt) {
              if (vo > 0) { const arg = 1 + (vn - vo) / d.nvt; v = arg > 0 ? vo + d.nvt * Math.log(arg) : d.vcrit; } else v = d.nvt * Math.log(Math.max(vn / d.nvt, 1e-30));
              lim = true;
            }
            d.vd = v;
          });
          x = xn;
          if (!lim && dmax < 1e-8) { ok = true; break; }
          if (!diodes.length) { ok = true; break; }
        }
        // ---- contrôle des contraintes ----
        let changed = false;
        net.ops.forEach((o, k) => {
          const st = opSt[k]; if (!st.powered) return;
          const e = V(x, o.inp) - V(x, o.inn), y1 = integ.dc ? null : integ.x1[ix(o.y)];
          let free;
          if (integ.dc) free = P.a0 * e;
          else { const k1 = integ.beta * integ.h * 2 * Math.PI * P.gbw / P.a0; free = (integ.a1 * y1 + integ.a2 * (integ.x2 ? integ.x2[ix(o.y)] : 0) + k1 * P.a0 * e) / (1 + k1); }
          let want = free, mode = "lin", fixed = null;
          if (!integ.dc) {
            const dmx = P.slew * integ.h;
            if (want > y1 + dmx) { want = y1 + dmx; mode = "sr+"; fixed = want; } else if (want < y1 - dmx) { want = y1 - dmx; mode = "sr-"; fixed = want; }
          }
          if (want > st.hi) { mode = "hi"; fixed = st.hi; } else if (want < st.lo) { mode = "lo"; fixed = st.lo; }
          const pm = st.mode, pf = st.fixed;
          st.mode = mode; st.fixed = fixed;
          if (mode !== pm || (mode !== "lin" && Math.abs(fixed - pf) > 1e-9 * (1 + Math.abs(fixed)))) changed = true;
        });
        net.psu.forEach((p, i) => {
          const st = psuSt[i]; if (!st.on) return;
          const vt = V(x, p.a) - V(x, p.b);
          if (st.mode === "cv") { const I = (st.v - vt) / P.psuR; if (Math.abs(I) > st.i) { st.mode = "cc"; st.s = Math.sign(I); changed = true; } }
          else if ((st.s > 0 && vt > st.v + 1e-9) || (st.s < 0 && vt < st.v - 1e-9)) { st.mode = "cv"; changed = true; }
        });
        if (!changed) return x;
      }
      return x;
    }

    // ---- logique TTL ----
    const events = [];                         // {t, cs, pin, to}
    function schedule(cs, pin, val, t) {
      const o = cs.outs[pin]; if (o.target === val) return;
      o.target = val;
      const spec = cs.c.spec;
      events.push({ t: t + (val ? spec.lh : spec.hl), cs, pin, to: val });
      events.sort((a, b) => a.t - b.t);
    }
    function updatePower(x) {
      chipSt.forEach(cs => {
        const vs = V(x, cs.c.vcc) - V(x, cs.c.gnd);
        cs.vsup = vs; cs.rev = vs < -0.5; cs.over = cs.over || vs > P.ttlVccMax;
        cs.powered = vs >= P.ttlVccOk && !cs.over;
      });
      net.ops.forEach((o, k) => {
        const st = opSt[k], vp = V(x, o.vcc), vm = V(x, o.vee);
        st.rev = st.rev || vm - vp > 1;
        st.powered = vp - vm >= P.opMinSupply && !st.rev;
        st.hi = vp - P.vsatMargin; st.lo = vm + P.vsatMargin;
      });
    }
    const lvlOf = (cs, x, p) => (V(x, cs.c.pins[p]) - V(x, cs.c.gnd)) > P.ttlVth ? 1 : 0;
    function evalLogic(x, t, immediate) {
      chipSt.forEach(cs => {
        if (!cs.powered) return;
        const L = p => lvlOf(cs, x, p), spec = cs.c.spec;
        const put = (pin, v) => { if (immediate) { const o = cs.outs[pin]; o.from = o.to = o.target = v; o.t0 = t; } else schedule(cs, pin, v, t); };
        if (spec.gates) spec.gates.forEach(([a, b, y]) => put(y, L(a) && L(b) ? 0 : 1));
        if (spec.ffs) spec.ffs.forEach((ff, i) => {
          const pre = L(ff.pre), clr = L(ff.clr), clk = L(ff.clk);
          let q, qb;
          if (!pre || !clr) { q = !pre ? 1 : 0; qb = !clr ? 1 : 0; cs.ffQ[i] = !pre && clr ? 1 : (!clr && pre ? 0 : cs.ffQ[i]); }
          else { if (clk && !cs.clkPrev[i] && !immediate) cs.ffQ[i] = L(ff.d); q = cs.ffQ[i]; qb = 1 - q; }
          cs.clkPrev[i] = clk;
          put(ff.q, q); put(ff.qb, qb);
        });
      });
    }
    const inputPins = () => { const a = []; chipSt.forEach(cs => { if (cs.powered) cs.c.spec.inputs.forEach(p => a.push([cs, p])); }); return a; };

    // ---- point de repos (t = 0) ----
    let x = null;
    for (let k = 0; k < 10; k++) {
      x = solveAt(0, { dc: true }, x);
      if (!x) return { ok: false, reason: "matrice singulière (circuit mal défini)" };
      const before = JSON.stringify(chipSt.map(c => [c.powered, Object.values(c.outs).map(o => o.target)]) .concat(opSt.map(o => o.powered)));
      updatePower(x); evalLogic(x, 0, true);
      const after = JSON.stringify(chipSt.map(c => [c.powered, Object.values(c.outs).map(o => o.target)]).concat(opSt.map(o => o.powered)));
      if (before === after && k > 0) break;
    }
    x = solveAt(0, { dc: true }, x);
    if (!x) return { ok: false, reason: "matrice singulière (circuit mal défini)" };

    const leds = net.leds.map(l => l.name);
    const ledI = xx => diodes.filter(d => d.led).map(d => { const v = V(xx, d.a) - V(xx, d.k); return d.is * (Math.exp(Math.min(v / d.nvt, 80)) - 1); });
    const psuI = xx => net.psu.map((p, i) => { const st = psuSt[i]; if (!st.on) return 0; return st.mode === "cv" ? (st.v - (V(xx, p.a) - V(xx, p.b))) / P.psuR : st.s * st.i; });
    const psuV = xx => net.psu.map(p => V(xx, p.a) - V(xx, p.b));
    const probeKeys = ["ch1", "ch2"].filter(c => net.probes[c]);

    const rec = { t: [], ch: { ch1: [], ch2: [] }, led: leds.map(() => []), psuI: net.psu.map(() => []), psuV: net.psu.map(() => []), psuCC: net.psu.map(() => false) };
    const push = (tt, xx) => {
      rec.t.push(tt);
      probeKeys.forEach(c => rec.ch[c].push(V(xx, net.probes[c])));
      const li = ledI(xx); li.forEach((v, i) => rec.led[i].push(v));
      const pi = psuI(xx), pv = psuV(xx); pi.forEach((v, i) => { rec.psuI[i].push(v); rec.psuV[i].push(pv[i]); if (psuSt[i].mode === "cc") rec.psuCC[i] = true; });
    };

    let steps = 0, recStart = 0, recLen = 0, dc = !gbfOn;
    if (dc) { push(0, x); }
    else {
      const nrec = chipSt.some(c => c.c.model === "74LS74") ? 4 : 1;
      let nset = Math.max(3, Math.ceil(5e-6 / T)); if (nset > 60) nset = 60;
      recStart = nset * T; recLen = nrec * T;
      const tEnd = recStart + recLen, hNom = T / P.stepsPerPeriod, hMin = Math.min(hNom, P.ttlEdge / 4, edge / 4);
      let t = 0, x1 = x, x2 = null, hPrev = null, restart = true, hCur = hMin, recording = false;
      updatePower(x);
      const bpList = [recStart, tEnd];
      const nextBp = tt => { let nb = nextSrcBreak(tt); for (const b of bpList) if (b > tt + 1e-18 && b < nb) nb = b; for (const e of events) { if (e.t > tt + 1e-18) { nb = Math.min(nb, e.t); break; } } return nb; };
      while (t < tEnd - 1e-15 * tEnd) {
        if (++steps > 60000) break;
        const nb = nextBp(t);
        let h = Math.min(hNom, hCur), tTry = Math.min(t + h, nb), hitBp = tTry === nb;
        const mkInteg = tt => { const hh = tt - t;
          // Euler implicite après une discontinuité et tant que le pas grandit (monotone, sans dépassement) ; Gear-2 au pas nominal
          if (restart || !x2 || hh < hNom * 0.999 || Math.abs(hh / hPrev - 1) > 0.01) return { h: hh, beta: 1, a1: 1, a2: 0, x1, x2: null };
          const w = hh / hPrev; return { h: hh, beta: (1 + w) / (1 + 2 * w), a1: (1 + w) * (1 + w) / (1 + 2 * w), a2: -w * w / (1 + 2 * w), x1, x2 }; };
        let xn = solveAt(tTry, mkInteg(tTry), x1);
        if (!xn) return { ok: false, reason: "calcul impossible à t = " + tTry.toExponential(2) + " s" };
        // localisation des basculements d'entrées TTL
        const ins = inputPins();
        for (let ref = 0; ref < 4 && ins.length; ref++) {
          let tc = Infinity;
          ins.forEach(([cs, p]) => {
            const v0 = V(x1, cs.c.pins[p]) - V(x1, cs.c.gnd), v1 = V(xn, cs.c.pins[p]) - V(xn, cs.c.gnd);
            if ((v0 > P.ttlVth) !== (v1 > P.ttlVth)) { const fr = (P.ttlVth - v0) / (v1 - v0); tc = Math.min(tc, t + fr * (tTry - t)); }
          });
          if (!isFinite(tc) || tTry - tc < 2e-12 + 1e-6 * (tTry - t)) break;
          const tNew = Math.min(tTry, tc + Math.max(1e-12, 1e-4 * (tTry - t)));
          const xt = solveAt(tNew, mkInteg(tNew), x1);
          if (!xt) break;
          tTry = tNew; xn = xt; hitBp = false;
        }
        const hh = tTry - t;
        x2 = x1; x1 = xn; hPrev = hh; t = tTry;
        // activation des transitions programmées à t
        while (events.length && events[0].t <= t * (1 + 1e-12) + 1e-18) {
          const e = events.shift(), o = e.cs.outs[e.pin];
          o.from = lev(o, e.t); o.to = e.to; o.t0 = e.t;
          bpList.push(e.t + P.ttlEdge); hitBp = true;
        }
        updatePower(xn);
        evalLogic(xn, t, false);
        net.ops.forEach((o, k) => { const st = opSt[k]; if (t > recStart) { if (st.mode === "hi" || st.mode === "lo") st.satT += hh; if (st.mode === "sr+" || st.mode === "sr-") st.slewT += hh; } });
        if (hitBp) { restart = true; hCur = hMin; } else { restart = false; hCur = Math.min(hNom, hCur * 2); }
        if (!recording && t >= recStart - 1e-15 * tEnd) { recording = true; }
        if (recording) push(t - recStart, xn);
        for (let i = bpList.length - 1; i >= 0; i--) if (bpList[i] <= t && bpList[i] !== recStart && bpList[i] !== tEnd) bpList.splice(i, 1);
      }
    }

    if (!dc && (rec.t.length < 2 || rec.t[rec.t.length - 1] < recLen * 0.999)) return { ok: false, reason: "simulation trop longue (fréquence trop élevée pour ce montage)" };
    // ---- résultats ----
    const tt = Float64Array.from(rec.t);
    const out = { ok: true, dc, T: dc ? null : T, f: dc ? null : f, P: dc ? 0 : recLen, t: tt, ch: {}, steps, leds: {}, psu: {}, ops: [], chips: [] };
    probeKeys.forEach(c => { out.ch[c] = Float64Array.from(rec.ch[c]); });
    const avg = arr => { if (dc || arr.length < 2) return arr[0] || 0; let s = 0; for (let i = 1; i < arr.length; i++) s += (arr[i] + arr[i - 1]) / 2 * (tt[i] - tt[i - 1]); return s / (tt[tt.length - 1] - tt[0]); };
    leds.forEach((n, i) => { const a = Float64Array.from(rec.led[i]); out.leds[n] = { i: a, avg: avg(a), max: a.reduce((m, v) => v > m ? v : m, -Infinity), min: a.reduce((m, v) => v < m ? v : m, Infinity) }; });
    net.psu.forEach((p, i) => { out.psu[p.k] = { i: avg(rec.psuI[i]), v: avg(rec.psuV[i]), imax: rec.psuI[i].reduce((m, v) => Math.max(m, Math.abs(v)), 0), cc: rec.psuCC[i] }; });
    net.ops.forEach((o, k) => { const st = opSt[k]; out.ops.push({ name: o.name, powered: st.powered, rev: st.rev, sat: dc ? (st.mode === "hi" || st.mode === "lo") : st.satT / recLen > 0.002, slew: !dc && st.slewT / recLen > 0.002 }); });
    chipSt.forEach(cs => out.chips.push({ ref: cs.c.ref, model: cs.c.model, vsup: cs.vsup, powered: cs.powered, over: cs.over, rev: cs.rev }));
    // statistiques par période (pour l'oscilloscope)
    out.stats = {};
    Object.keys(out.ch).forEach(c => { const a = out.ch[c]; let mn = Infinity, mx = -Infinity; a.forEach(v => { if (v < mn) mn = v; if (v > mx) mx = v; }); out.stats[c] = { min: mn, max: mx, mean: avg(a), integ: avg(a) * recLen }; });
    return out;
  }

  // ---------------------------------------------------------------------------------------
  // 4. LECTURE DE L'ENREGISTREMENT (périodique)
  const mod = (a, p) => ((a % p) + p) % p;
  function interp(rec, arr, tm) {              // tm ∈ [0, P]
    const t = rec.t; let lo = 0, hi = t.length - 1;
    if (tm <= t[0]) return arr[0]; if (tm >= t[hi]) return arr[hi];
    while (hi - lo > 1) { const m = (lo + hi) >> 1; if (t[m] <= tm) lo = m; else hi = m; }
    const d = t[hi] - t[lo]; return d > 0 ? arr[lo] + (arr[hi] - arr[lo]) * (tm - t[lo]) / d : arr[hi];
  }
  function at(rec, key, tAbs) { const arr = rec.ch[key]; if (!arr) return 0; if (rec.dc) return arr[0]; return interp(rec, arr, mod(tAbs, rec.P)); }
  // parcours d'un intervalle [u,v] ⊂ [0,P] : appelle cb(t, v) aux bornes et à chaque point intérieur
  function walk(rec, arr, u, v, cb) {
    const t = rec.t; let lo = 0, hi = t.length - 1;
    while (hi - lo > 1) { const m = (lo + hi) >> 1; if (t[m] <= u) lo = m; else hi = m; }
    cb(u, interp(rec, arr, u));
    for (let i = lo + 1; i < t.length && t[i] < v; i++) if (t[i] > u) cb(t[i], arr[i]);
    cb(v, interp(rec, arr, v));
  }
  function walkAbs(rec, arr, ta, tb, cb) {      // intervalle absolu [ta, tb] de longueur < P
    const P = rec.P, u = mod(ta, P), L = tb - ta;
    if (u + L <= P) walk(rec, arr, u, u + L, (t, v) => cb(t - u + ta, v));
    else { walk(rec, arr, u, P, (t, v) => cb(t - u + ta, v)); walk(rec, arr, 0, u + L - P, (t, v) => cb(t + (P - u) + ta, v)); }
  }
  function segStats(rec, key, ta, tb) {
    const arr = rec.ch[key]; if (!arr) return null;
    if (rec.dc) return { min: arr[0], max: arr[0], mean: arr[0], first: arr[0] };
    const P = rec.P, s = rec.stats[key], L = tb - ta, full = Math.floor(L / P);
    let mn = Infinity, mx = -Infinity, integ = 0;
    if (full >= 1) { mn = s.min; mx = s.max; integ = full * s.integ; }
    const a = ta + full * P;
    if (tb - a > 0) { let pt = null, pv = 0; walkAbs(rec, arr, a, tb, (t, v) => { if (v < mn) mn = v; if (v > mx) mx = v; if (pt !== null) integ += (v + pv) / 2 * (t - pt); pt = t; pv = v; }); }
    return { min: mn, max: mx, mean: L > 0 ? integ / L : at(rec, key, ta), first: at(rec, key, ta) };
  }
  // colonnes d'affichage (min / max par colonne : enveloppe quand le signal est trop rapide pour la base de temps)
  function view(rec, key, t0, t1, ncol) {
    const mn = new Float64Array(ncol), mx = new Float64Array(ncol), st = new Float64Array(ncol), dt = (t1 - t0) / ncol;
    for (let j = 0; j < ncol; j++) { const s = segStats(rec, key, t0 + j * dt, t0 + (j + 1) * dt); mn[j] = s.min; mx[j] = s.max; st[j] = s.first; }
    return { min: mn, max: mx, start: st };
  }
  // fronts : temps où le signal franchit `level` (front montant si slope>0) dans [ta, tb]
  function crossings(rec, key, level, slope, ta, tb, maxN) {
    const arr = rec.ch[key], out = []; if (!arr || rec.dc) return out;
    let pt = null, pv = 0;
    const scan = (a, b) => walkAbs(rec, arr, a, b, (t, v) => {
      if (pt !== null && out.length < (maxN || 1e5)) {
        if (slope > 0 ? (pv < level && v >= level) : (pv > level && v <= level)) out.push(pt + (level - pv) / (v - pv) * (t - pt));
      }
      pt = t; pv = v;
    });
    for (let a = ta; a < tb && out.length < (maxN || 1e5); a += rec.P) scan(a, Math.min(tb, a + rec.P * (1 - 1e-12)));
    return out;
  }
  // mesures « oscilloscope » sur la fenêtre affichée [ta, tb]
  function measure(rec, key, ta, tb) {
    const s = segStats(rec, key, ta, tb); if (!s) return null;
    const vpp = s.max - s.min, mid = (s.max + s.min) / 2;
    let freq = null;
    if (!rec.dc && vpp > 1e-3) {
      if (tb - ta >= 2 * rec.P) { const k = crossings(rec, key, mid, 1, 0, rec.P).length; freq = k ? k / rec.P : null; }
      else { const c = crossings(rec, key, mid, 1, ta, tb, 2e4); freq = c.length >= 2 ? (c.length - 1) / (c[c.length - 1] - c[0]) : null; }
    }
    return { max: s.max, min: s.min, vpp, mean: s.mean, freq, mid };
  }
  // déphasage de la voie 2 par rapport à la voie 1 (front montant à mi-hauteur), en degrés ; négatif = retard
  function phase(rec) {
    if (rec.dc || !rec.ch.ch1 || !rec.ch.ch2) return null;
    const s1 = rec.stats.ch1, s2 = rec.stats.ch2;
    if (s1.max - s1.min < 1e-3 || s2.max - s2.min < 1e-3) return null;
    const m1 = (s1.max + s1.min) / 2, m2 = (s2.max + s2.min) / 2;
    const c1 = crossings(rec, "ch1", m1, 1, 0, rec.P);
    if (!c1.length) return null;
    const T1 = rec.P / c1.length, t1 = c1[0];
    const c2 = crossings(rec, "ch2", m2, 1, t1 - T1 / 2, t1 + T1 / 2 + 1e-15);
    if (!c2.length) return null;
    let best = c2[0]; c2.forEach(c => { if (Math.abs(c - t1) < Math.abs(best - t1)) best = c; });
    let ph = -360 * (best - t1) / T1;
    if (ph <= -180) ph += 360; if (ph > 180) ph -= 360;
    return ph;
  }
  // composante fondamentale (phaseur complexe [re, im]) sur l'enregistrement
  function fundamental(rec, key) {
    const arr = rec.ch[key]; if (!arr || rec.dc) return null;
    const t = rec.t, w = 2 * Math.PI / rec.T; let re = 0, im = 0;
    for (let i = 1; i < t.length; i++) {
      const dt = t[i] - t[i - 1], tm = (t[i] + t[i - 1]) / 2, v = (arr[i] + arr[i - 1]) / 2;
      re += v * Math.cos(w * tm) * dt; im += v * Math.sin(w * tm) * dt;
    }
    const k = 2 / rec.P;
    return [im * k, re * k];                  // v ≈ re·sin + im·cos -> phaseur en sinus
  }

  // ---------------------------------------------------------------------------------------
  // 5. ANALYSE COMPLÈTE (utilisée par l'interface)
  function analyze(wiring, env, srcIn) {
    const src = srcIn || {};
    const net = buildNet(wiring, env);
    const an = { net, supported: true, reasons: [], warnings: net.warnings.slice(), notes: net.notes.slice(), probes: net.probes,
      powered: true, hasOpamp: net.ops.length > 0, digital: net.chips.length > 0 };
    const rec = simulate(net, src);
    if (!rec.ok) { an.supported = false; an.reasons.push("Calcul impossible : " + rec.reason); return an; }
    an.rec = rec;
    rec.ops.forEach(o => {
      if (o.rev) an.warnings.push(`${o.name} (TL081) alimenté À L'ENVERS : sur le vrai banc la puce chauffe et est détruite. Débranche tout et vérifie V+ (broche 7) et V− (broche 4).`);
      else if (!o.powered) an.warnings.push(`${o.name} (TL081) non alimenté (V+ broche 7 et V− broche 4 : ±15 V attendus) : sa sortie n'est pas pilotée.`);
      if (o.sat) an.notes.push(`${o.name} : sortie en saturation (butée à ≈ 2,5 V des rails).`);
      if (o.slew) an.notes.push(`${o.name} : sortie limitée par la vitesse de montée (13 V/µs).`);
    });
    an.powered = rec.ops.every(o => o.powered);
    rec.chips.forEach(c => {
      if (c.rev) an.warnings.push(`${c.ref} (${c.model}) alimentée À L'ENVERS (GND broche 7 plus haut que VCC broche 14) : puce détruite sur le vrai banc.`);
      else if (c.over) an.warnings.push(`${c.ref} (${c.model}) : VCC = ${c.vsup.toFixed(1)} V > 7 V (maximum absolu) — sur le vrai banc la puce est DÉTRUITE. Un 74LS s'alimente en 5 V.`);
      else if (!c.powered) an.warnings.push(`${c.ref} (${c.model}) non alimentée : +5 V sur la broche 14 (VCC), 0 V sur la broche 7 (GND).`);
      else if (c.vsup < 4.75 || c.vsup > 5.25) an.notes.push(`${c.ref} : VCC = ${c.vsup.toFixed(2)} V, hors de la plage recommandée 4,75–5,25 V.`);
    });
    Object.entries(rec.psu).forEach(([k, p]) => { if (p.cc) an.warnings.push(`Alim voie ${k} en limitation de courant (CC) : ${(p.imax * 1e3).toFixed(0)} mA demandés. Court-circuit ou charge trop faible ?`); });
    Object.entries(rec.leds).forEach(([n, l]) => {
      if (l.max > net.P.ledImax) an.warnings.push(`${n} : ${(l.max * 1e3).toFixed(0)} mA dans la LED (> 30 mA) : elle grille sur le vrai banc. Il manque une résistance de protection ?`);
    });
    if (!net.probes.ch1 && !net.probes.ch2) an.notes.push("Aucune voie d'oscillo câblée.");
    if (src.gbf && src.gbf.on && net.TH.length === 0 && (net.probes.ch1 || net.probes.ch2)) an.notes.push("Le GBF est allumé mais aucun câble ne part de sa sortie.");
    // grandeurs de synthèse
    const s = rec.stats;
    an.dc1 = s.ch1 ? s.ch1.mean : 0; an.dc2 = s.ch2 ? s.ch2.mean : 0;
    if (!rec.dc) {
      an.V1 = fundamental(rec, "ch1"); an.V2 = fundamental(rec, "ch2");
      if (an.V1 && an.V2 && Math.hypot(an.V1[0], an.V1[1]) > 1e-9) {
        const d = an.V1[0] * an.V1[0] + an.V1[1] * an.V1[1];
        const h = [(an.V2[0] * an.V1[0] + an.V2[1] * an.V1[1]) / d, (an.V2[1] * an.V1[0] - an.V2[0] * an.V1[1]) / d];
        an.gain = Math.hypot(h[0], h[1]); an.phaseDeg = Math.atan2(h[1], h[0]) * 180 / Math.PI;
      }
    }
    return an;
  }

  return { buildNet, simulate, analyze, pinHole, UF, DEFAULTS, CHIPS, at, segStats, view, crossings, measure, phase, fundamental, isDev };
})();

if (typeof module !== "undefined") module.exports = Engine;
