# -*- coding: utf-8 -*-
"""Vérification croisée : montage posé sur la plaque -> netlist -> solveur AC (MNA) -> comparé au modèle de prédiction.
Usage : /usr/bin/python3 tools/check_netlist.py"""
import sys
import math
import pathlib
import cmath
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import render as R
import netlist as N
import predict as P

hw = R.load("hardware/board_wish106.yaml")
PRED = {1: R.load("predictions/tp1.yaml"), 2: R.load("predictions/tp2.yaml")}
CASES = [
    ("montages/tp1/B1_pont_diviseur.yaml", 1, "tp1-B-pont-diviseur", [1e3, 1e6, 1e7]),
    ("montages/tp2/A_suiveur.yaml", 2, "tp2-A-suiveur", [1e3, 1e6, 4e6]),
    ("montages/tp2/B1_inverseur.yaml", 2, "tp2-B1-inverseur", [1e3, 1.9e5]),
    ("montages/tp2/B2_non_inverseur.yaml", 2, "tp2-B2-non-inverseur", [1e3, 3.96e5]),
    ("montages/tp2/C_association.yaml", 2, "tp2-C-association", [1e3, 1.6e5]),
]
SET = {"psu": {1: 1.0, 2: 15.0, 3: 15.0}}


def circ_of(tp, cid):
    return [c for c in PRED[tp]["circuits"] if c["id"] == cid][0]


def ratio(net, f):
    v = N.ac_solve(net, f)
    a, b = v[net["probes"]["ch1"]], v[net["probes"]["ch2"]]
    return b / a


def main():
    ok = True
    print("%-24s %9s | %-11s %-11s %7s | %-9s %-9s %6s" % ("montage", "f", "|H| netlist", "|H| modèle", "écart", "φ netlist", "φ modèle", "écart"))
    for path, tp, cid, freqs in CASES:
        m = R.load_montage(path)
        net = N.extract(m, hw, SET)
        circ = circ_of(tp, cid)
        tl = PRED[tp]["tl081"]
        for f in freqs:
            h = ratio(net, f)
            bd = P.bode(circ, f, tl, {})
            mod, ph = abs(h), math.degrees(cmath.phase(h))
            if bd:
                em = (mod / bd[0] - 1) * 100
                ep = (ph - bd[1] + 180) % 360 - 180
                flag = "" if abs(em) < 2 and abs(ep) < 3 else "  <-- ÉCART"
                ok = ok and not flag
                print("%-24s %9g | %-11.5g %-11.5g %6.2f%% | %-9.1f %-9.1f %5.1f%s" % (m["id"][:24], f, mod, bd[0], em, ph, bd[1], ep, flag))
    # impédance interne : Uc / E = Rc / (Rc + 50)
    m = R.load_montage("montages/tp1/C1_impedance_interne.yaml")
    net = N.extract(m, hw, SET)
    v = N.ac_solve(net, 1e3)[net["probes"]["ch1"]]
    exp = 47 / 97.0
    print("%-24s %9g | Uc/E netlist %.5f  modèle Rc/(Rc+Rint) %.5f  écart %.2f%%" % (m["id"][:24], 1e3, abs(v), exp, (abs(v) / exp - 1) * 100))
    ok = ok and abs(abs(v) / exp - 1) < 0.01
    # soustracteur : V2 -> Vs doit valoir 1 (R égales), coupure GBP/2
    m = R.load_montage("montages/tp2/D_soustracteur.yaml")
    net = N.extract(m, hw, SET)
    h = ratio(net, 1e3)
    print("%-24s %9g | |Vs/V2| netlist %.5f  attendu 1.00000 (4 R égales)" % (m["id"][:24], 1e3, abs(h)))
    ok = ok and abs(abs(h) - 1) < 0.01

    print("\n== Le montage réagit au câblage (c'est ce que fera l'app) ==")
    base = R.load_montage("montages/tp2/B1_inverseur.yaml")

    def powered(mm, label):
        net = N.extract(mm, hw, SET)
        dcv = N.ac_solve(net, 0.0, dc=True)
        op = [e for e in net["elements"] if e["k"] == "OPAMP"][0]
        vp, vm = dcv[op["vcc"]].real, dcv[op["vee"]].real
        h = ratio(net, 1e3)
        verdict = "alimentée" if (vp > 10 and vm < -10 and not net["warnings"]) else "NON ALIMENTÉE / ALIM FLOTTANTE"
        print("%-40s V+ = %6.2f V  V− = %6.2f V | %-30s | |Vs/Ve| linéaire = %.2f" % (label, vp, vm, verdict, abs(h)))
        for w in net["warnings"]:
            print("      ⚠ " + w)
        return vp, vm
    powered(base, "montage correct")
    m2 = R.load_montage("montages/tp2/B1_inverseur.yaml")
    m2["fils"] = [w for w in m2["fils"] if not (w["de"] == "T1d47")]          # fil V− oublié
    vs, g = powered(m2, "fil V− (broche 4 → rail −15 V) oublié")
    print("   -> l'app doit afficher « AOP non alimenté » (le solveur linéaire seul ne le sait pas : gain %.1f)" % g)
    m3 = R.load_montage("montages/tp2/B1_inverseur.yaml")
    m3["fils"] = [w for w in m3["fils"] if w["de"] != "MASSE.main"]            # 0 V de l'alim non relié à la plaque
    try:
        powered(m3, "douille ⏚ non reliée à la plaque")
    except Exception as e:
        print("   erreur :", e)
    print("\nRÉSULTAT :", "tous les écarts sont dans la tolérance" if ok else "AU MOINS UN ÉCART HORS TOLÉRANCE")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
