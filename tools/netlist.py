# -*- coding: utf-8 -*-
"""Extraction d'un netlist électrique à partir d'un montage posé sur la plaque (ce que fera l'app en temps réel).

  montage YAML  ->  nœuds (trous reliés, rails, bus, fils, câbles BNC/banane)  ->  éléments (R, C, sources, AOP, LED)
                ->  (1) texte SPICE pour ngspice          (2) solveur AC linéaire (MNA, numpy) pour vérifier sans ngspice

Convention physique modélisée :
  - la TERRE (référence 0) est portée par les blindages des câbles BNC (GBF et oscillo sont reliés à la terre) ;
  - l'alimentation est FLOTTANTE : son 0 V n'est relié à la terre que par les fils de la plaque ;
  - un nœud flottant est tiré vers la terre par 1 GΩ (gmin) pour que le calcul reste possible, comme en réalité.
"""
import math
import render as R

DEV = ("gbf", "scope", "psu")


def is_dev(e):
    return "." in e and e.split(".")[0] in DEV


def extract(m, hw, settings=None):
    """Renvoie un dict : nodes (noms), elements, probes, notes. Lève ValueError si le montage a des erreurs de câblage."""
    st = {"cable_pf": 100.0, "scope_r": 1e6, "scope_c_pf": 16.0, "gbf_rout": 50.0}
    st.update(settings or {})
    comps = m["composants"]
    res, uf = R.validate(m, hw)
    # En mode libre (l'app), un câblage « faux » doit quand même se simuler : seules les erreurs d'adresse bloquent.
    tolerable = lambda t: t.startswith(("Nœud", "Court-circuit", "BNC", "Douille")) or "court-circuit" in t
    errs = [t for l, t in res if l == "ERREUR" and not tolerable(t)]
    if errs:
        raise ValueError("montage invalide : " + " | ".join(errs[:3]))
    conns = R.conn_geom(hw)
    EARTH = ("EARTH",)
    uf.f(EARTH)
    P = lambda e: ("PORT", e)

    # câbles entre appareils et plaque
    for cb in m.get("cables", []):
        a, b = cb["de"], cb["vers"]
        if is_dev(a) and is_dev(b):
            uf.u(P(a), P(b))
        else:
            dev, con = (a, b) if is_dev(a) else (b, a)
            if con in conns and conns[con]["c"]["type"] == "bnc":
                uf.u(P(dev), ("J", con + ".core"))
                uf.u(("J", con + ".shield"), EARTH)
            elif con in conns:
                uf.u(P(dev), ("J", con + ".main"))
    root = lambda k: uf.f(k)

    names, count = {root(EARTH): "0"}, [0]
    noeuds = m.get("noeuds", {})
    for nm, members in noeuds.items():
        r = root(R.key(members[0], comps))
        names.setdefault(r, nm.lower())

    def node(k):
        r = root(k)
        if r not in names:
            count[0] += 1
            names[r] = "n%d" % count[0]
        return names[r]

    el, notes = [], []
    # composants
    for n, c in comps.items():
        t = c.get("type")
        if t == "resistor":
            el.append({"k": "R", "name": n, "a": node(R.key(c["a"], comps)), "b": node(R.key(c["b"], comps)), "v": float(c["ohm"])})
        elif t == "led":
            el.append({"k": "D", "name": n, "a": node(R.key(c["a"], comps)), "b": node(R.key(c["k"], comps))})
        elif t == "chip" and c["etiquette"] == "TL081":
            g = lambda p: node(R.key("%s.%d" % (n, p), comps))
            el.append({"k": "OPAMP", "name": n, "inp": g(3), "inn": g(2), "vcc": g(7), "vee": g(4), "out": g(6)})
        elif t == "chip":
            notes.append("%s (%s) : modèle numérique non couvert par le solveur analogique" % (n, c["etiquette"]))
    # appareils
    ports_used = set()
    for cb in m.get("cables", []):
        for e in (cb["de"], cb["vers"]):
            if is_dev(e):
                ports_used.add(e)
    gbf_ports = [p for p in ports_used if p.startswith("gbf.")]
    for p in gbf_ports:
        el.append({"k": "V", "name": "Vgbf", "a": "gbf_int", "b": "0", "dc": 0.0, "ac": 1.0, "src": "gbf"})
        el.append({"k": "R", "name": "Rout_gbf", "a": "gbf_int", "b": node(P(p)), "v": st["gbf_rout"]})
    for p in sorted(ports_used):
        if p.startswith("scope."):
            nd = node(P(p))
            el.append({"k": "R", "name": "Rin_" + p.replace(".", "_"), "a": nd, "b": "0", "v": st["scope_r"]})
            el.append({"k": "C", "name": "Cin_" + p.replace(".", "_"), "a": nd, "b": "0", "v": st["scope_c_pf"] * 1e-12})
    psu = st.get("psu", {1: 0.0, 2: 15.0, 3: 15.0})
    for k in (1, 2, 3):
        plus, minus = "psu.ch%d_plus" % k, "psu.ch%d_moins" % k
        if plus in ports_used or minus in ports_used:
            el.append({"k": "V", "name": "Vpsu%d" % k, "a": node(P(plus)), "b": node(P(minus)), "dc": float(psu.get(k, 0.0)), "ac": 0.0, "src": "psu"})
    for cb in m.get("cables", []):       # capacité de câble sur chaque âme de BNC
        for e in (cb["de"], cb["vers"]):
            if e in conns and conns[e]["c"]["type"] == "bnc" and st["cable_pf"]:
                nd = node(("J", e + ".core"))
                el.append({"k": "C", "name": "Ccab_" + cb["id"], "a": nd, "b": "0", "v": st["cable_pf"] * 1e-12})
    # sondes = ce que l'oscillo voit
    probes = {}
    for p in sorted(ports_used):
        if p.startswith("scope.ch"):
            probes[p.split(".")[1]] = node(P(p))
    warnings = []
    if any(p.startswith("psu.") for p in ports_used):
        mins = [p for p in sorted(ports_used) if p.startswith("psu.") and p.endswith("_moins")]
        if mins and not any(root(P(p)) == root(EARTH) for p in mins):
            warnings.append("ALIMENTATION FLOTTANTE : le 0 V de l'alim n'est relié ni à la masse de la plaque ni aux blindages BNC. Les tensions de la puce n'ont pas de référence commune avec le signal.")
    allnodes = sorted(set(names.values()) | {x for e in el for x in (e.get(y) for y in ("a", "b", "inp", "inn", "vcc", "vee", "out")) if x})
    return {"nodes": allnodes, "elements": el, "probes": probes, "notes": notes, "warnings": warnings, "settings": st}


# ---------------------------------------------------------------- texte SPICE
TL081_SUBCKT = """* TL081 : modèle comportemental à un pôle (GBW, vitesse de montée, saturation).
* NON EXÉCUTÉ dans ngspice (absent de cette machine) : à valider au banc d'essai M1 (docs/ARCHITECTURE_APP.md). A COMPLÉTER avec le modèle TI si besoin.
.param A0=2e5 GBW=4e6 SR=13e6 VSAT_MARGIN=2.5
.subckt TL081 inp inn vcc vee out
.param gm=1m
* courant maximal = SR * C1  (c'est ce qui limite la vitesse de montée de n1)
B1 0 n1 I = max(min(gm*(V(inp)-V(inn)), {SR}*(1/(6.2832*({GBW}/{A0})*({A0}/gm)))), -{SR}*(1/(6.2832*({GBW}/{A0})*({A0}/gm))))
R1 n1 0 {A0/gm}
C1 n1 0 {1/(6.2832*({GBW}/{A0})*({A0}/gm))}
B2 out 0 V = max(min(V(n1), V(vcc)-{VSAT_MARGIN}), V(vee)+{VSAT_MARGIN})
.ends TL081
"""


def to_spice(net, analysis=".tran 1u 4m", gbf="SIN(0 1 1k)"):
    L = ["* généré par tools/netlist.py : ne pas éditer à la main", TL081_SUBCKT]
    for e in net["elements"]:
        k = e["k"]
        if k == "R":
            L.append("R%s %s %s %g" % (e["name"], e["a"], e["b"], e["v"]))
        elif k == "C":
            L.append("C%s %s %s %g" % (e["name"], e["a"], e["b"], e["v"]))
        elif k == "V":
            L.append("V%s %s %s %s" % (e["name"], e["a"], e["b"], gbf if e["src"] == "gbf" else "DC %g" % e["dc"]))
        elif k == "OPAMP":
            L.append("X%s %s %s %s %s %s TL081" % (e["name"], e["inp"], e["inn"], e["vcc"], e["vee"], e["out"]))
        elif k == "D":
            L.append("D%s %s %s DLED" % (e["name"], e["a"], e["b"]))
    for nd in net["nodes"]:
        if nd != "0" and not nd.startswith("gbf_int"):
            L.append("Rgmin_%s %s 0 1G" % (nd, nd))
    L.append(".model DLED D(IS=4.4e-11 N=3.9 RS=3)")
    L.append(analysis)
    L.append(".end")
    return "\n".join(L)


# ---------------------------------------------------------------- solveur AC linéaire (MNA)
def ac_solve(net, f, a0=2e5, gbw=4e6, dc=False):
    """f en Hz. dc=True : point de fonctionnement continu (condensateurs ouverts, sources à leur valeur DC)."""
    import numpy as np
    w = 2 * math.pi * f
    s = 1e-12j if dc else 1j * w
    nodes = [n for n in net["nodes"] if n != "0"]
    idx = dict((n, i) for i, n in enumerate(nodes))
    branches = [e for e in net["elements"] if e["k"] in ("V", "OPAMP")]
    N = len(nodes) + len(branches)
    A = np.zeros((N, N), dtype=complex)
    b = np.zeros(N, dtype=complex)

    def add(i, j, v):
        if i is not None and j is not None:
            A[i, j] += v
    ix = lambda n: idx.get(n)
    for e in net["elements"]:
        if e["k"] in ("R", "C"):
            y = (1.0 / e["v"]) if e["k"] == "R" else s * e["v"]
            a, bb = ix(e["a"]), ix(e["b"])
            add(a, a, y)
            add(bb, bb, y)
            add(a, bb, -y)
            add(bb, a, -y)
    for nd in nodes:                      # gmin
        add(ix(nd), ix(nd), 1e-9)
    wp = 2 * math.pi * gbw / a0
    for k, e in enumerate(branches):
        row = len(nodes) + k
        if e["k"] == "V":
            p, n = ix(e["a"]), ix(e["b"])
            add(p, row, 1)
            add(n, row, -1)
            add(row, p, 1)
            add(row, n, -1)
            if dc:
                b[row] = e["dc"]
            else:
                b[row] = e["ac"] if e["src"] == "gbf" else 0.0
        else:
            Ag = a0 / (1 + s / wp)
            o, ip, im = ix(e["out"]), ix(e["inp"]), ix(e["inn"])
            add(o, row, 1)
            add(row, o, 1)
            add(row, ip, -Ag)
            add(row, im, Ag)
    x = np.linalg.solve(A, b)
    return dict((n, x[i]) for n, i in idx.items())
