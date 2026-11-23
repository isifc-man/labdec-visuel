#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LABDEC_VISUEL : validateur de câblage + générateur HTML/SVG.

Usage :  /usr/bin/python3 tools/render.py
Lit hardware/*.yaml, montages/**/*.yaml, tests/*.yaml  ->  écrit out/*.html
(Python 3.9 : /usr/bin/python3 a PyYAML.)
"""
import sys
import re
import math
import pathlib
import html
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
E = html.escape


def load(rel):
    with open(ROOT / rel, encoding="utf-8") as f:
        return yaml.safe_load(f)


def subst(obj, table):
    """Remplace les marqueurs __XXX__ dans toute la structure."""
    if isinstance(obj, dict):
        return {k: subst(v, table) for k, v in obj.items()}
    if isinstance(obj, list):
        return [subst(v, table) for v in obj]
    if isinstance(obj, str) and obj in table:
        return table[obj]
    return obj


WIRE = {"rouge": "#d62828", "noir": "#1f2328", "bleu": "#1d4ed8", "vert": "#16a34a",
        "orange": "#f77f00", "jaune": "#eab308", "turquoise": "#0ea5a4", "blanc": "#e5e7eb", "violet": "#7c3aed", "marron": "#92400e"}
SCHEMA_HOOK = None   # fonction(m) -> svg, posée par build.py
CHC = {1: "#f6e90f", 2: "#4cf04c"}

# ---------------------------------------------------------------- géométrie de la plaque
P, ROWS, PAD, GAP = 14, 63, 8, 10
STRIPS = ["N1", "T1L", "T1R", "N2", "T2L", "T2R", "N3", "T3L", "T3R", "N4"]


def ncols(s):
    return 2 if s[0] == "N" else 5


POS = {}
_x = 40
for _s in STRIPS:
    _w = ncols(_s) * P + 2 * PAD
    POS[_s] = (_x, _w)
    _x += _w + GAP
PLATE_W = _x - GAP + 40
Y0 = 230
PLATE_H = Y0 + 2 * PAD + ROWS * P + 30
TOP_Y = Y0 - 75
EYE_Y = 125
CONN_Y = 62

RT = re.compile(r"^T([123])([a-j])(\d{1,2})$")
RN = re.compile(r"^N([1-4])-([12])([ud])-(\d{1,2})$")
RP = re.compile(r"^TOP-([LR])([12])-(\d{1,2})$")


def row_y(r):
    return Y0 + PAD + (ROWS - r) * P + P / 2.0


def is_hole(a):
    return bool(RT.match(a) or RN.match(a) or RP.match(a))


def netkey(a):
    m = RT.match(a)
    if m:
        r = int(m.group(3))
        if not 1 <= r <= ROWS:
            raise ValueError("rangée %d hors 1..%d (%s)" % (r, ROWS, a))
        return ("T", m.group(1), "L" if m.group(2) in "fghij" else "R", r)
    m = RN.match(a)
    if m:
        r = int(m.group(4))
        h = m.group(3)
        if not 1 <= r <= ROWS or (h == "u" and r < 33) or (h == "d" and r > 32):
            raise ValueError("rangée %d incompatible avec la moitié « %s » du rail (coupure au W, entre 32 et 33) : %s" % (r, h, a))
        return ("N", m.group(1), m.group(2), h)
    m = RP.match(a)
    if m:
        p = int(m.group(3))
        if not 1 <= p <= 25:
            raise ValueError("position %d hors 1..25 sur le bus haut (%s)" % (p, a))
        return ("TOP", m.group(1), m.group(2))
    raise ValueError("adresse de trou inconnue : %s" % a)


def xy(a):
    netkey(a)
    m = RT.match(a)
    if m:
        l = m.group(2)
        strip = "T%s%s" % (m.group(1), "L" if l in "fghij" else "R")
        col = "fghij".index(l) if l in "fghij" else "abcde".index(l)
        return POS[strip][0] + PAD + col * P + P / 2.0, row_y(int(m.group(3)))
    m = RN.match(a)
    if m:
        return POS["N" + m.group(1)][0] + PAD + (int(m.group(2)) - 1) * P + P / 2.0, row_y(int(m.group(4)))
    m = RP.match(a)
    p = int(m.group(3))
    x0 = 60 if m.group(1) == "L" else PLATE_W / 2.0 + 30
    return x0 + (p - 1) * P, TOP_Y + (int(m.group(2)) - 1) * P + P / 2.0


def conn_geom(hw):
    def fx(xp):
        return 20 + (xp - 105) / 900.0 * (PLATE_W - 40)
    out = {}
    for c in hw["connecteurs"]:
        pins = {}
        for name, xp in c["oeillets"].items():
            pins[name] = (fx(xp), EYE_Y)
        out[c["id"]] = {"c": c, "cx": fx(c["x_ph"]), "cy": CONN_Y, "pins": pins}
    return out


# ---------------------------------------------------------------- puces (DIP) posées à cheval sur la fente
def expand_chips(m):
    """Transforme m['puces'] en composants de type « chip » : une broche = un trou (colonnes e et f, contre la fente).
    Encoche en haut : broche 1 en haut à gauche, on descend à gauche puis on remonte à droite.
    Encoche en bas : la puce est tournée de 180°."""
    comps = m.get("composants") or {}
    m["composants"] = comps
    if not m.get("puces"):
        return m
    lib = load("hardware/components.yaml")
    for ch in m["puces"]:
        spec = lib[ch["modele"]]
        n = spec["dip"]
        half = n // 2
        blk, r1 = ch["bloc"], ch["rangee_broche1"]
        up = ch.get("encoche", "haut") == "haut"
        d = {"type": "chip", "etiquette": ch["modele"], "dip": n, "notch": "haut" if up else "bas",
             "roles": dict((str(k), v) for k, v in spec["brochage"].items())}
        for p in range(1, n + 1):
            if up:
                letter, row = ("j", r1 - (p - 1)) if p <= half else ("a", r1 - (half - 1) + (p - half - 1))
            else:
                letter, row = ("a", r1 + (p - 1)) if p <= half else ("j", r1 + (half - 1) - (p - half - 1))
            d[str(p)] = "%s%s%d" % (blk, letter, row)
        comps[ch["ref"]] = d
    return m


def load_montage(rel):
    return expand_chips(load(rel))


def legs_of(c):
    if c.get("type") == "chip":
        return [k for k in c if k.isdigit()]
    if c.get("type") == "led":
        return ["a", "k"]
    return ["a", "b"]


# ---------------------------------------------------------------- validateur
class UF(object):
    def __init__(self):
        self.p = {}

    def f(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def u(self, a, b):
        self.p[self.f(a)] = self.f(b)


def resolve(a, comps):
    if "." in a and a.split(".")[0] in comps:
        c, leg = a.split(".")
        return comps[c][leg]
    return a


def key(a, comps):
    r = resolve(a, comps)
    return netkey(r) if is_hole(r) else ("J", r)


def numbers_of(m):
    """Calculs électriques déduits des composants (pas de valeur écrite à la main)."""
    n = {}
    cal = m.get("calcul")
    if cal and cal["type"] == "diviseur":
        comps = m["composants"]
        rh = sum(comps[c]["ohm"] for c in cal["haut"])
        rb = sum(comps[c]["ohm"] for c in cal["bas"])
        ratio = rb / float(rh + rb)
        us = cal["ue_vpp"] * ratio
        n.update({"rh": rh, "rb": rb, "ratio": ratio, "us_vpp": us,
                  "__US_VPP__": round(us, 4), "__US_TXT__": "%.0fmV" % (us * 1000),
                  "__RATIO_TXT__": "%.4f (1/%.2f)" % (ratio, 1.0 / ratio)})
    return n


def validate(m, hw):
    res = []
    comps = m["composants"]
    conns = conn_geom(hw)
    pins = set("%s.%s" % (cid, p) for cid, g in conns.items() for p in g["pins"])
    used = {}
    uf = UF()
    err = [0]

    def ko(msg):
        res.append(("ERREUR", msg))
        err[0] += 1

    def chk(a, label):
        r = resolve(a, comps)
        if is_hole(r):
            try:
                netkey(r)
            except ValueError as e:
                ko("%s : %s" % (label, e))
                return
            if r in used:
                ko("trou %s utilisé deux fois (%s et %s)" % (r, used[r], label))
            used[r] = label
        elif r not in pins:
            ko("%s : adresse inconnue « %s »" % (label, a))

    for name, c in comps.items():
        for leg in legs_of(c):
            chk(c[leg], "%s.%s" % (name, leg))
    for w in m["fils"]:
        chk(w["de"], "fil %s (de)" % w["n"])
        chk(w["vers"], "fil %s (vers)" % w["n"])
    if err[0]:
        return res, uf
    res.append(("ok", "Toutes les adresses existent et aucun trou n'est utilisé deux fois."))

    for w in m["fils"]:
        uf.u(key(w["de"], comps), key(w["vers"], comps))

    # 1) chaque BNC utilisé est câblé deux fois (âme ET blindage)
    wired = set()
    for w in m["fils"]:
        for e in (w["de"], w["vers"]):
            if e in pins:
                wired.add(e)
    for cb in m.get("cables", []):
        for e in (cb["de"], cb["vers"]):
            if e.startswith("BNC"):
                for conductor in ("core", "shield"):
                    pin = "%s.%s" % (e, conductor)
                    if pin in wired:
                        res.append(("ok", "%s câblé (câble %s)." % (pin, cb["id"])))
                    else:
                        ko("%s n'est pas câblé : un BNC se câble DEUX fois (âme ET blindage)." % pin)

    # 1b) chaque douille banane alimentée par un câble doit avoir un fil vers la plaque
    for cb in m.get("cables", []):
        for e in (cb["de"], cb["vers"]):
            if e in conns and conns[e]["c"]["type"] == "banane":
                if ("%s.main" % e) in wired:
                    res.append(("ok", "Douille %s : câble %s + fil vers la plaque." % (e, cb["id"])))
                else:
                    ko("Douille %s alimentée par le câble %s mais aucun fil ne la relie à la plaque." % (e, cb["id"]))

    # 2) aucune résistance / LED en court-circuit
    for name, c in comps.items():
        if c.get("type") in ("resistor", "led"):
            a, b = (c["a"], c["b"]) if c.get("type") == "resistor" else (c["a"], c["k"])
            if uf.f(key(a, comps)) == uf.f(key(b, comps)):
                ko("%s a ses deux pattes dans le même nœud (court-circuit)." % name)
            else:
                res.append(("ok", "%s : pattes dans deux nœuds différents." % name))

    # 3) nœuds exigés
    roots = {}
    for nm, members in m.get("noeuds", {}).items():
        rs = set(uf.f(key(x, comps)) for x in members)
        if len(rs) == 1:
            res.append(("ok", "Nœud %s : %d points bien reliés." % (nm, len(members))))
            roots[nm] = rs.pop()
        else:
            ko("Nœud %s : ses points ne sont pas tous reliés entre eux (%s)." % (nm, ", ".join(members)))
    names = list(roots)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            if roots[names[i]] == roots[names[j]]:
                ko("Court-circuit : les nœuds %s et %s sont reliés." % (names[i], names[j]))
    if len(names) > 1 and not any(r[0] == "ERREUR" and "Court-circuit" in r[1] for r in res):
        res.append(("ok", "Les nœuds %s sont bien distincts." % ", ".join(names)))

    # 4) blindages BNC à la masse
    if "GND" in roots:
        for cid in conns:
            sh = "%s.shield" % cid
            if sh in wired:
                if uf.f(("J", sh)) == roots["GND"]:
                    res.append(("ok", "%s est à la masse commune." % sh))
                else:
                    ko("%s n'est pas relié à la masse." % sh)

    # 5) points à confirmer
    for cb in m.get("cables", []):
        pass
    if m.get("tee"):
        res.append(("à confirmer", "Adaptateur en T sur la sortie du GBF : %s" % m["tee"]["preuve"]))
    res.append(("à confirmer", "Placement sur la plaque (rangées/lettres) : proposition du projet, lettres lues par l'utilisateur sur la plaque : f–j à gauche, a–e à droite."))
    return res, uf


# ---------------------------------------------------------------- SVG : plaque
def wire_path(p1, p2, bulge=0.0, arch=False):
    (x1, y1), (x2, y2) = p1, p2
    if arch:
        c1, c2 = (x1, y1 - 70), (x2, y2 - 70)
    elif bulge:
        c1, c2 = (x1 + bulge, y1), (x2 + bulge, y2)
    else:
        c1, c2 = (x1, y1 + 70), (x2, y2 - 70)
    d = "M%.1f,%.1f C%.1f,%.1f %.1f,%.1f %.1f,%.1f" % (x1, y1, c1[0], c1[1], c2[0], c2[1], x2, y2)
    mid = ((x1 + 3 * c1[0] + 3 * c2[0] + x2) / 8.0, (y1 + 3 * c1[1] + 3 * c2[1] + y2) / 8.0)
    return d, mid


def _draw_special(o, name, c):
    """Dessine une puce (DIP) ou une LED. Renvoie True si le composant a été traité."""
    t = c.get("type")
    if t == "chip":
        pins = dict((int(k), xy(v)) for k, v in c.items() if k.isdigit())
        xs = [p[0] for p in pins.values()]
        ys = [p[1] for p in pins.values()]
        x0, x1, y0, y1 = min(xs) - 10, max(xs) + 10, min(ys) - 10, max(ys) + 10
        cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="3" fill="#2b2f36" stroke="#0b0c0e" stroke-width="2"/>' % (x0, y0, x1 - x0, y1 - y0))
        if c["notch"] == "haut":
            o.append('<path d="M%.1f,%.1f a7,7 0 0 0 14,0z" fill="#17191c"/>' % (cx - 7, y0))
        else:
            o.append('<path d="M%.1f,%.1f a7,7 0 0 1 14,0z" fill="#17191c"/>' % (cx - 7, y1))
        o.append('<text transform="translate(%.1f,%.1f) rotate(-90)" font-size="12" font-weight="700" fill="#e5e7eb" text-anchor="middle" font-family="Arial">%s  %s</text>' % (cx, cy, E(name), E(c["etiquette"])))
        for n, (px, py) in sorted(pins.items()):
            left = px < cx
            o.append('<circle cx="%.1f" cy="%.1f" r="3.4" fill="#e5e7eb"/>' % (px, py))
            o.append('<text x="%.1f" y="%.1f" font-size="8" font-weight="700" fill="#fde68a" text-anchor="%s" font-family="Arial">%d</text>' % (px + (-5 if left else 5), py + 3, "end" if left else "start", n))
        return True
    if t == "led":
        (x1, y1), (x2, y2) = xy(c["a"]), xy(c["k"])
        mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#888" stroke-width="3"/>' % (x1, y1, x2, y2))
        o.append('<circle cx="%.1f" cy="%.1f" r="9" fill="#e11d48" stroke="#7f1d1d" stroke-width="2"/>' % (mx, my))
        o.append('<text x="%.1f" y="%.1f" font-size="11" font-weight="700" fill="#111" font-family="Arial">%s %s</text>' % (max(x1, x2) + 12, my + 4, E(name), E(c.get("etiquette", "LED"))))
        o.append('<text x="%.1f" y="%.1f" font-size="12" font-weight="700" fill="#e11d48" text-anchor="end" font-family="Arial">+</text>' % (x1 - 7, y1 + 4))
        for (px, py) in ((x1, y1), (x2, y2)):
            o.append('<circle cx="%.1f" cy="%.1f" r="4" fill="#333" stroke="#fff" stroke-width="1.5"/>' % (px, py))
        return True
    return False


def board_inner(m, hw):
    comps = m["composants"]
    conns = conn_geom(hw)
    o = []
    o.append('<rect x="0" y="0" width="%d" height="%d" rx="18" fill="#17191c"/>' % (PLATE_W, PLATE_H))
    o.append('<text x="%d" y="%d" font-size="13" fill="#e8742a" font-family="Arial" font-weight="700" text-anchor="end">Wish Board 106</text>' % (PLATE_W - 24, PLATE_H - 8))
    # bus du haut
    o.append('<rect x="50" y="%d" width="%d" height="%d" rx="4" fill="#f1f1ee"/>' % (TOP_Y - 8, PLATE_W - 100, 2 * P + 12))
    o.append('<g fill="#555">')
    for half in "LR":
        for line in (1, 2):
            for p in range(1, 26):
                x, y = xy("TOP-%s%d-%d" % (half, line, p))
                o.append('<circle cx="%.1f" cy="%.1f" r="2.2"/>' % (x, y))
    o.append('</g>')
    o.append('<text x="60" y="%d" font-size="11" fill="#bbb" font-family="Arial">bus haut gauche (TOP-L) — masse 0 V</text>' % (TOP_Y - 14))
    o.append('<text x="%d" y="%d" font-size="11" fill="#bbb" font-family="Arial">bus haut droit (TOP-R) — structure à confirmer</text>' % (PLATE_W / 2.0 + 30, TOP_Y - 14))
    # bandes
    for s in STRIPS:
        x, w = POS[s]
        o.append('<rect x="%d" y="%d" width="%d" height="%d" rx="3" fill="#f1f1ee"/>' % (x, Y0, w, 2 * PAD + ROWS * P))
        o.append('<g fill="#555">')
        for c in range(ncols(s)):
            for r in range(1, ROWS + 1):
                o.append('<circle cx="%.1f" cy="%.1f" r="2.2"/>' % (x + PAD + c * P + P / 2.0, row_y(r)))
        o.append('</g>')
        if s[0] == "N":
            o.append('<text x="%.1f" y="%.1f" font-size="10" font-weight="700" fill="#b91c1c" text-anchor="middle" font-family="Arial">W</text>' % (x + w / 2.0, (row_y(32) + row_y(33)) / 2.0 + 3))
            o.append('<text x="%.1f" y="%d" font-size="11" fill="#bbb" text-anchor="middle" font-family="Arial">rail %s</text>' % (x + w / 2.0, Y0 - 6, s))
        else:
            o.append('<text x="%.1f" y="%d" font-size="11" fill="#bbb" text-anchor="middle" font-family="Arial">%s</text>' % (x + w / 2.0, Y0 - 19, "f–j" if s[2] == "L" else "a–e"))
            for ci, letter in enumerate("fghij" if s[2] == "L" else "abcde"):
                lx = x + PAD + ci * P + P / 2.0
                o.append('<text x="%.1f" y="%d" font-size="11" font-weight="700" fill="#f59e0b" text-anchor="middle" font-family="Arial">%s</text>' % (lx, Y0 - 4, letter))
                o.append('<text x="%.1f" y="%d" font-size="11" font-weight="700" fill="#f59e0b" text-anchor="middle" font-family="Arial">%s</text>' % (lx, Y0 + 2 * PAD + ROWS * P + 12, letter))
            if s[2] == "L":
                for rr in [1] + list(range(5, ROWS + 1, 5)):
                    o.append('<text x="%.1f" y="%.1f" font-size="8" font-weight="700" fill="#6b7280" text-anchor="middle" font-family="Arial">%d</text>' % (x + w + GAP / 2.0, row_y(rr) + 3, rr))
                xr, wr = POS[s[:2] + "R"]
                o.append('<text x="%.1f" y="%d" font-size="13" font-weight="700" fill="#ddd" text-anchor="middle" font-family="Arial">bloc %s</text>' % ((x + xr + wr) / 2.0, Y0 - 34, s[:2]))
    for r in range(5, ROWS + 1, 5):
        o.append('<text x="26" y="%.1f" font-size="9" fill="#aaa" text-anchor="middle" font-family="Arial">%d</text>' % (row_y(r) + 3, r))
        o.append('<text x="%d" y="%.1f" font-size="9" fill="#aaa" text-anchor="middle" font-family="Arial">%d</text>' % (PLATE_W - 26, row_y(r) + 3, r))
    # connecteurs
    for cid, g in conns.items():
        c, cx, cy = g["c"], g["cx"], g["cy"]
        if c["type"] == "bnc":
            o.append('<circle cx="%.1f" cy="%d" r="27" fill="#cfd2d6" stroke="#7b8087" stroke-width="3"/>' % (cx, cy))
            o.append('<circle cx="%.1f" cy="%d" r="16" fill="#9aa0a6"/><circle cx="%.1f" cy="%d" r="6" fill="#222"/>' % (cx, cy, cx, cy))
        else:
            col = {"rouge": "#d62828", "noir": "#2b2b2b", "bleu": "#1d4ed8", "turquoise": "#0ea5a4"}.get(c["couleur"], "#888")
            o.append('<circle cx="%.1f" cy="%d" r="19" fill="%s" stroke="#ddd" stroke-width="2"/><circle cx="%.1f" cy="%d" r="7" fill="#111"/>' % (cx, cy, col, cx, cy))
        o.append('<text x="%.1f" y="20" font-size="12" fill="#ddd" text-anchor="middle" font-family="Arial">%s</text>' % (cx, E({"BANANE_ROUGE": "rouge", "BANANE_NOIRE": "noire"}.get(cid, cid))))
        for pn, (ex, ey) in g["pins"].items():
            o.append('<circle cx="%.1f" cy="%d" r="7" fill="none" stroke="#bbb" stroke-width="3"/>' % (ex, ey))
            if c["type"] == "bnc":
                o.append('<text x="%.1f" y="%d" font-size="10" fill="#ccc" text-anchor="middle" font-family="Arial">%s</text>' % (ex, ey + 22, "âme" if pn == "core" else "blindage"))
                if cid == "BNC2" and pn == "shield":   # « Va » est imprimé à côté de ce trou sur la plaque (borne Va d'origine retirée)
                    o.append('<text x="%.1f" y="%d" font-size="15" font-weight="700" fill="#facc15" font-family="Arial">Va</text>' % (ex + 12, ey + 5))
            else:
                o.append('<text x="%.1f" y="%d" font-size="16" font-weight="700" fill="#facc15" font-family="Arial">%s</text>' % (ex + 11, ey + 6, {"VB": "Vb", "VC": "Vc", "MASSE": "⏚"}.get(cid, "")))
    # composants
    for name, c in comps.items():
        if _draw_special(o, name, c):
            continue
        (x1, y1), (x2, y2) = xy(c["a"]), xy(c["b"])
        mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        ang = math.degrees(math.atan2(y2 - y1, x2 - x1))
        ln = math.hypot(x2 - x1, y2 - y1)
        o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#888" stroke-width="3"/>' % (x1, y1, x2, y2))
        o.append('<g transform="translate(%.1f,%.1f) rotate(%.1f)"><rect x="%.1f" y="-6" width="%.1f" height="12" rx="4" fill="#d9b77e" stroke="#8a6d3b" stroke-width="1.5"/></g>' % (mx, my, ang, -ln * 0.3, ln * 0.6))
        o.append('<text x="%.1f" y="%.1f" font-size="11" font-weight="700" fill="#111" font-family="Arial">%s %s</text>' % (max(x1, x2) + 12, my + 4, E(name), E(c["etiquette"])))
        for (px, py) in ((x1, y1), (x2, y2)):
            o.append('<circle cx="%.1f" cy="%.1f" r="4" fill="#333" stroke="#fff" stroke-width="1.5"/>' % (px, py))
    # fils
    pins_xy = {}
    for cid, g in conns.items():
        for pn, p in g["pins"].items():
            pins_xy["%s.%s" % (cid, pn)] = p

    def pt(a):
        r = resolve(a, comps)
        return pins_xy[r] if r in pins_xy else xy(r)
    for w in m["fils"]:
        p1, p2 = pt(w["de"]), pt(w["vers"])
        both_holes = is_hole(resolve(w["de"], comps)) and is_hole(resolve(w["vers"], comps))
        if both_holes and abs(p1[0] - p2[0]) < 60:
            d, mid = wire_path(p1, p2, bulge=-(24 + 0.05 * abs(p1[1] - p2[1])))
        elif both_holes:
            d, mid = wire_path(p1, p2, arch=True)
        else:
            d, mid = wire_path(p1, p2)
        col = WIRE.get(w["couleur"], "#999")
        o.append('<path d="%s" fill="none" stroke="#fff" stroke-width="8" stroke-linecap="round" opacity=".85"/>' % d)
        o.append('<path d="%s" fill="none" stroke="%s" stroke-width="5" stroke-linecap="round"/>' % (d, col))
        for (px, py) in (p1, p2):
            o.append('<circle cx="%.1f" cy="%.1f" r="5" fill="%s" stroke="#fff" stroke-width="1.5"/>' % (px, py, col))
        o.append('<circle cx="%.1f" cy="%.1f" r="11" fill="#0b3d91" stroke="#fff" stroke-width="2"/><text x="%.1f" y="%.1f" font-size="13" font-weight="700" fill="#fff" text-anchor="middle" font-family="Arial">%s</text>' % (mid[0], mid[1], mid[0], mid[1] + 4.5, w["n"]))
    return "".join(o), conns


def board_svg(m, hw, width=640):
    inner, _ = board_inner(m, hw)
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" style="max-width:100%%;height:auto">%s</svg>' % (PLATE_W, PLATE_H, width, inner)


# ---------------------------------------------------------------- SVG : schéma électrique (diviseur)
def schema_diviseur_svg(m, nb):
    comps = m["composants"]
    r1 = " + ".join(comps[c]["etiquette"] for c in m["calcul"]["haut"])
    r2 = " + ".join(comps[c]["etiquette"] for c in m["calcul"]["bas"])
    s = []
    s.append('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 560 360" width="560" style="max-width:100%;height:auto;background:#fff;border:1px solid #ddd;border-radius:8px" font-family="Arial">')
    s.append('<defs><marker id="ar" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#0b3d91"/></marker></defs>')
    s.append('<g stroke="#111" stroke-width="2" fill="none">')
    s.append('<circle cx="80" cy="190" r="28" fill="#fff"/><path d="M66,190 q7,-14 14,0 t14,0"/>')
    s.append('<path d="M80,162 V60 H300"/><path d="M300,60 V80"/><rect x="288" y="80" width="24" height="80" fill="#fff"/><path d="M300,160 V180"/>')
    s.append('<path d="M300,170 H430"/><path d="M300,180 V200"/><rect x="288" y="200" width="24" height="60" fill="#fff"/><path d="M300,260 V300"/>')
    s.append('<path d="M80,218 V300 H300"/><path d="M300,300 H430"/>')
    s.append('<path d="M284,300 H316 M290,308 H310 M296,316 H304"/>')
    s.append('</g><g fill="#111"><circle cx="300" cy="60" r="4"/><circle cx="300" cy="170" r="4"/><circle cx="430" cy="170" r="4"/><circle cx="430" cy="300" r="4"/></g>')
    s.append('<g font-size="14" fill="#111">')
    s.append('<text x="304" y="52">E</text><text x="436" y="166">S</text><text x="436" y="304">M</text>')
    s.append('<text x="80" y="195" text-anchor="middle" font-size="12">GBF</text>')
    s.append('<text x="322" y="116">R1 = %s</text><text x="322" y="134" font-size="12" fill="#555">(%s)</text>' % (E("%.2f kΩ" % (nb["rh"] / 1000.0)), E(r1)))
    s.append('<text x="322" y="234">R2 = %s</text>' % E(r2))
    s.append('</g><g stroke="#0b3d91" stroke-width="2.5" fill="none" marker-end="url(#ar)"><path d="M40,300 V70"/><path d="M470,300 V180"/></g>')
    s.append('<g font-size="15" fill="#0b3d91" font-weight="700"><text x="12" y="190">Ue</text><text x="480" y="240">Us</text>')
    s.append('<text x="100" y="52" fill="#a16207">voie 1 en E</text><text x="450" y="160" fill="#15803d">voie 2 en S</text></g>')
    s.append('<text x="280" y="344" font-size="13" fill="#444" text-anchor="middle">Us = Ue · R2 / (R1 + R2) = %.4f · Ue  →  Ue = 2 Vpp ⇒ Us ≈ %.3f Vpp</text>' % (nb["ratio"], nb["us_vpp"]))
    s.append('</svg>')
    return "".join(s)


# ---------------------------------------------------------------- SVG : écran d'oscilloscope Keysight
def wave(sp, t):
    kind, f = sp["kind"], sp["f"]
    a, dc = sp.get("vpp", 0) / 2.0, sp.get("dc", 0.0)
    x = (f * t + sp.get("phase", 0) / 360.0) % 1.0
    if kind == "sine":
        v = math.sin(2 * math.pi * x)
    elif kind == "square":
        e, d = sp.get("edge", 0.015), sp.get("duty", 0.5)
        up = min(1.0, max(0.0, x / e))
        dn = min(1.0, max(0.0, (x - d) / e))
        v = 2 * (up - dn) - 1
    else:  # tri
        s = sp.get("sym", 0.5)
        v = -1 + 2 * x / s if x < s else 1 - 2 * (x - s) / (1 - s)
        n = sp.get("notch", 0)
        if n:
            v -= n * math.exp(-((x - s) / 0.02) ** 2)
            v += n * (math.exp(-(x / 0.02) ** 2) + math.exp(-((x - 1) / 0.02) ** 2))
    out = dc + a * v + sp.get("ripple", 0) * math.sin(2 * math.pi * sp.get("ripple_f", 50000) * t)
    if "clip" in sp:
        out = max(-sp["clip"], min(sp["clip"], out))
    return out


def fmt_v(v):
    if v >= 10:
        return "%.1fV/" % v
    if v >= 1:
        return "%.2fV/" % v
    return "%.0fmV/" % (v * 1000)


def fmt_t(t):
    if t >= 1e-3:
        return "%.1fms/" % (t * 1e3)
    if t >= 1e-6:
        return "%.1fµs/" % (t * 1e6)
    return "%.1fns/" % (t * 1e9)


def scope_svg(cfg, uid="s"):
    W, H = 800, 480
    gx, gy, gw, gh = 16, 34, 600, 360
    dx, dy = gw / 10.0, gh / 8.0
    cx, cy = gx + gw / 2.0, gy + gh / 2.0
    td = cfg["tdiv"]
    o = []
    o.append('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="100%%" style="display:block;background:#0b0d10" font-family="Arial">' % (W, H))
    o.append('<defs><clipPath id="cl%s"><rect x="%d" y="%d" width="%d" height="%d"/></clipPath>' % (uid, gx, gy, gw, gh))
    o.append('<linearGradient id="bt%s" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#4f8fe0"/><stop offset="1" stop-color="#2a63b4"/></linearGradient></defs>' % uid)
    o.append('<rect x="4" y="4" width="%d" height="%d" rx="6" fill="#04101c" stroke="#1c2733" stroke-width="2"/>' % (W - 8, H - 8))
    # grille
    o.append('<g stroke="#3b6cb0" stroke-width="1" opacity=".55">')
    for i in range(11):
        o.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d"/>' % (gx + i * dx, gy, gx + i * dx, gy + gh))
    for j in range(9):
        o.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f"/>' % (gx, gy + j * dy, gx + gw, gy + j * dy))
    o.append('</g><g stroke="#5b8fd0" stroke-width="1.6" opacity=".9"><line x1="%.1f" y1="%d" x2="%.1f" y2="%d"/><line x1="%d" y1="%.1f" x2="%d" y2="%.1f"/></g>' % (cx, gy, cx, gy + gh, gx, cy, gx + gw, cy))
    # traces
    for n in (1, 2):
        ch = cfg.get("ch%d" % n)
        if not ch:
            continue
        pts = []
        N = 900
        for i in range(N + 1):
            t = (i / float(N) * 10 - 5) * td
            v = ch["samples"][i] if "samples" in ch else wave(ch["wave"], t)
            yd = (v - ch["offset"]) / ch["scale"]
            pts.append("%.1f,%.1f" % (gx + i / float(N) * gw, cy - yd * dy))
        o.append('<polyline clip-path="url(#cl%s)" points="%s" fill="none" stroke="%s" stroke-width="3.2" stroke-linejoin="round" stroke-linecap="round"/>' % (uid, " ".join(pts), CHC[n]))
        yg = cy - ((0 - ch["offset"]) / ch["scale"]) * dy
        yg = max(gy + 8, min(gy + gh - 8, yg))
        o.append('<rect x="%d" y="%.1f" width="13" height="15" fill="%s"/><text x="%.1f" y="%.1f" font-size="11" font-weight="700" fill="#000" text-anchor="middle">%d</text>' % (gx, yg - 7.5, CHC[n], gx + 6.5, yg + 4, n))
    # curseurs
    cur = cfg.get("cursors")
    if cur:
        o.append('<g stroke="#e8742a" stroke-width="1.5" stroke-dasharray="5,4" clip-path="url(#cl%s)">' % uid)
        for xdiv in cur.get("x", []):
            o.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d"/>' % (cx + xdiv * dx, gy, cx + xdiv * dx, gy + gh))
        for ydiv in cur.get("y", []):
            o.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f"/>' % (gx, cy - ydiv * dy, gx + gw, cy - ydiv * dy))
        o.append('</g>')
    # repère de déclenchement
    o.append('<path d="M%.1f,%d l-6,-9 h12 z" fill="#e8742a"/>' % (cx, gy))
    # barre du haut
    o.append('<g font-size="13" fill="#ddd">')
    x = 10
    for n in (1, 2):
        ch = cfg.get("ch%d" % n)
        if ch:
            o.append('<text x="%d" y="24" fill="%s" font-weight="700">%d</text><text x="%d" y="24" fill="#eee">%s</text>' % (x, CHC[n], n, x + 14, fmt_v(ch["scale"])))
            x += 92
    o.append('<text x="%d" y="24" fill="#eee">0.0s</text><text x="%d" y="24" fill="#eee">%s</text><text x="%d" y="24" fill="#eee">Auto</text>' % (cx - 90, cx - 10, fmt_t(td), cx + 110))
    tr = cfg.get("trig", {"src": 1, "level": "0.00V"})
    o.append('<text x="%d" y="24" fill="#eee">ƒ</text><text x="%d" y="24" fill="%s" font-weight="700">%s</text><text x="%d" y="24" fill="#eee">%s</text>' % (gx + gw - 92, gx + gw - 76, CHC[tr["src"]], tr["src"], gx + gw - 60, E(tr["level"])))
    o.append('</g>')
    # panneau de droite
    px, pw = gx + gw + 10, W - (gx + gw + 10) - 10
    o.append('<rect x="%d" y="%d" width="%d" height="%d" fill="#1a4f94" stroke="#2e78c7" stroke-width="2"/>' % (px, gy, pw, gh))
    o.append('<text x="%d" y="%d" font-size="13" font-weight="700" fill="#fff">KEYSIGHT</text><text x="%d" y="%d" font-size="7" fill="#cfe">TECHNOLOGIES</text>' % (px + 40, gy + 22, px + 40, gy + 31))
    pan = cfg.get("panel", {"mode": "status", "lignes": []})
    if pan["mode"] == "autoscale":
        o.append('<text x="%.1f" y="%d" font-size="12" fill="#fff" text-anchor="middle">%s</text>' % (px + pw / 2.0, gy + 56, E(pan["titre"])))
        for i, b in enumerate(pan["boutons"]):
            by = gy + 70 + i * 62
            o.append('<rect x="%d" y="%d" width="%d" height="50" rx="4" fill="url(#bt%s)" stroke="#9cc3f0"/>' % (px + 8, by, pw - 16, uid))
            for k, line in enumerate(b.split("\n")):
                o.append('<text x="%.1f" y="%d" font-size="12" fill="#fff" text-anchor="middle">%s</text>' % (px + pw / 2.0, by + (21 if "\n" in b else 29) + 16 * k, E(line)))
    else:
        for i, line in enumerate(pan.get("lignes", [])):
            head = line in ("Acquisition", "Voies", "Math", "Réf")
            o.append('<text x="%d" y="%d" font-size="12" fill="%s" %s>%s</text>' % (px + 12, gy + 62 + i * 22, "#bfe0ff" if head else "#fff", 'font-weight="700"' if head else "", E(line)))
    # barre du bas
    items = cfg.get("bottom", [])
    if items:
        cw = (gw + 160) / float(len(items))
        for i, it in enumerate(items):
            bx = gx + i * cw
            col = {"ch1": CHC[1], "ch2": CHC[2]}.get(it.get("c"), "#e6e6e6")
            o.append('<text x="%.1f" y="418" font-size="12" fill="%s">%s</text><text x="%.1f" y="436" font-size="12" fill="#e6e6e6">%s</text>' % (bx + 6, col, E(it["l"]), bx + 6, E(it["v"])))
    o.append('</svg>')
    return "".join(o)


# ---------------------------------------------------------------- photos annotées
def photo_pastilles(inst, photo_key, steps):
    ph = inst["photos"][photo_key]
    z = ph["zones"]
    h = ['<div class="ph"><img src="../assets/photos/%s" alt="%s">' % (ph["file"], E(inst["modele"]))]
    seen = {}
    for st in steps:
        cibles = st["cible"] if isinstance(st["cible"], list) else [st["cible"]]
        for c in cibles:
            x, y = z[c]
            k = seen.get(c, 0)          # plusieurs étapes sur le même bouton : on décale les pastilles
            seen[c] = k + 1
            h.append('<span class="pas" style="left:%.2f%%;top:%.2f%%">%d</span>' % ((x + 34 * k) / float(ph["w"]) * 100, (y - 34 * k) / float(ph["h"]) * 100, st["n"]))
    h.append('</div>')
    return "".join(h)


def steps_list(steps):
    return '<ol class="steps">' + "".join('<li value="%d">%s</li>' % (s["n"], E(s["texte"])) for s in steps) + "</ol>"


# ---------------------------------------------------------------- carte de la table (câbles GBF -> plaque -> oscillo)
def rounded(pts, r=24):
    """Chemin à angles droits arrondis passant par les points donnés."""
    d = "M%.1f,%.1f" % pts[0]
    for i in range(1, len(pts) - 1):
        p0, p1, p2 = pts[i - 1], pts[i], pts[i + 1]

        def toward(a, b, dist):
            ln = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
            t = min(dist, ln / 2.0) / ln
            return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
        a, b = toward(p1, p0, r), toward(p1, p2, r)
        d += " L%.1f,%.1f Q%.1f,%.1f %.1f,%.1f" % (a[0], a[1], p1[0], p1[1], b[0], b[1])
    return d + " L%.1f,%.1f" % pts[-1]


def bench_svg(m, hw, gbf, scope):
    k = 0.66
    bx0, by0 = 640, 60
    conns = conn_geom(hw)
    inner, _ = board_inner(m, hw)

    def bpt(cid, pin=None):
        g = conns[cid]
        return bx0 + g["cx"] * k, by0 + (g["cy"] + 12) * k
    sg = 520 / 2048.0
    g_out = (gbf["photos"]["gbf_ports"]["zones"]["out1"][0] * sg, gbf["photos"]["gbf_ports"]["zones"]["out1"][1] * sg)
    sc = scope["photos"]["scope_ports"]["zones"]
    s_ch1 = (sc["bnc_ch1"][0] * sg, 430 + sc["bnc_ch1"][1] * sg)
    s_ch2 = (sc["bnc_ch2"][0] * sg, 430 + sc["bnc_ch2"][1] * sg)
    b1, b2 = bpt("BNC1"), bpt("BNC2")
    o = []
    o.append('<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 1360 %d" width="1360" style="max-width:100%%;height:auto;background:#fafafa;border:1px solid #ddd;border-radius:8px" font-family="Arial">' % (int(PLATE_H * k) + 80))
    o.append('<image href="../assets/photos/gbf_ports.jpg" x="0" y="0" width="520" height="390"/>')
    o.append('<image href="../assets/photos/scope_ports.jpg" x="0" y="430" width="520" height="390"/>')
    o.append('<text x="8" y="408" font-size="14" font-weight="700" fill="#111">GBF Keysight EDU33211A — ports</text>')
    o.append('<text x="8" y="838" font-size="14" font-weight="700" fill="#111">Oscilloscope Keysight DSOX1202A — entrées</text>')
    o.append('<svg x="%d" y="%d" width="%d" height="%d" viewBox="0 0 %d %d">%s</svg>' % (bx0, by0, PLATE_W * k, PLATE_H * k, PLATE_W, PLATE_H, inner))

    def cable(p1, p2, lab, col, c1d=(240, 0), c2d=(0, -160)):
        d = "M%.1f,%.1f C%.1f,%.1f %.1f,%.1f %.1f,%.1f" % (p1[0], p1[1], p1[0] + c1d[0], p1[1] + c1d[1], p2[0] + c2d[0], p2[1] + c2d[1], p2[0], p2[1])
        mid = ((p1[0] + 3 * (p1[0] + c1d[0]) + 3 * (p2[0] + c2d[0]) + p2[0]) / 8.0, (p1[1] + 3 * (p1[1] + c1d[1]) + 3 * (p2[1] + c2d[1]) + p2[1]) / 8.0)
        s = '<path d="%s" fill="none" stroke="#fff" stroke-width="11" stroke-linecap="round" opacity=".9"/><path d="%s" fill="none" stroke="%s" stroke-width="6" stroke-linecap="round"/>' % (d, d, col)
        s += '<circle cx="%.1f" cy="%.1f" r="13" fill="%s" stroke="#fff" stroke-width="2"/><text x="%.1f" y="%.1f" font-size="15" font-weight="700" fill="#fff" text-anchor="middle">%s</text>' % (mid[0], mid[1], col, mid[0], mid[1] + 5, lab)
        return s
    def routed_cable(pts, lab, col, seg):
        d = rounded(pts)
        a, b = pts[seg], pts[seg + 1]
        mx, my = (a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0
        return ('<path d="%s" fill="none" stroke="#fff" stroke-width="11" stroke-linecap="round" opacity=".9"/>'
                '<path d="%s" fill="none" stroke="%s" stroke-width="6" stroke-linecap="round"/>'
                '<circle cx="%.1f" cy="%.1f" r="13" fill="%s" stroke="#fff" stroke-width="2"/>'
                '<text x="%.1f" y="%.1f" font-size="15" font-weight="700" fill="#fff" text-anchor="middle">%s</text>') % (d, d, col, mx, my, col, mx, my + 5, lab)
    o.append(routed_cable([g_out, (560, g_out[1]), (560, 34), (b1[0], 34), (b1[0], b1[1])], "A", "#c2410c", 1))
    o.append(cable(g_out, s_ch1, "B", "#7c3aed", (-60, 80), (60, -120)))
    o.append(routed_cable([s_ch2, (600, s_ch2[1]), (600, 14), (b2[0], 14), (b2[0], b2[1])], "C", "#047857", 1))
    for p, lab, col in ((g_out, "sortie 1", "#c2410c"), (s_ch1, "voie 1", "#7c3aed"), (s_ch2, "voie 2", "#047857")):
        o.append('<circle cx="%.1f" cy="%.1f" r="20" fill="none" stroke="%s" stroke-width="4"/><text x="%.1f" y="%.1f" font-size="13" font-weight="700" fill="%s" stroke="#fff" stroke-width="3" paint-order="stroke">%s</text>' % (p[0], p[1], col, p[0] - 22, p[1] - 26, col, lab))
    o.append('<text x="%.1f" y="%.1f" font-size="12" font-weight="700" fill="#7c3aed" stroke="#fff" stroke-width="3" paint-order="stroke">T (à confirmer)</text>' % (g_out[0] + 26, g_out[1] + 4))
    o.append('</svg>')
    return "".join(o)


# ---------------------------------------------------------------- pages HTML
CSS = """
:root{--bg:#f6f7f9;--fg:#15181d;--mut:#5b6472;--card:#fff;--line:#dfe3e8;--ac:#0b3d91}
@media (prefers-color-scheme:dark){:root{--bg:#101318;--fg:#e8ebf0;--mut:#98a2b3;--card:#171b22;--line:#2a313c;--ac:#7fb0ff}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 -apple-system,Segoe UI,Arial,sans-serif;padding:0 16px 60px}
main{max-width:1400px;margin:0 auto}h1{font-size:26px;margin:24px 0 4px}h2{font-size:19px;margin:0 0 10px;color:var(--ac)}
.sub{color:var(--mut);margin:0 0 18px}.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;margin:16px 0}
.row{display:flex;gap:18px;flex-wrap:wrap;align-items:flex-start}.row>*{flex:1 1 440px;min-width:0}
.ph{position:relative;line-height:0}.ph img{width:100%;border-radius:8px;display:block}
.pas{position:absolute;transform:translate(-50%,-50%);width:26px;height:26px;border-radius:50%;background:#d6246e;color:#fff;font:700 14px/26px Arial;text-align:center;border:2px solid #fff;box-shadow:0 1px 4px #0006}
.steps{margin:0;padding-left:0;list-style:none}.steps li{margin:6px 0;padding-left:34px;position:relative}
.steps li::before{content:attr(value);position:absolute;left:0;top:0;width:24px;height:24px;border-radius:50%;background:#d6246e;color:#fff;text-align:center;font:700 13px/24px Arial}
table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left;font-size:14px}
.tag{display:inline-block;border-radius:6px;padding:1px 8px;font-size:12px;font-weight:700}.ok{background:#d9f7e4;color:#0a6b34}.ERREUR{background:#fde0e0;color:#a30d0d}.conf{background:#fff0c9;color:#8a5a00}
.sw{display:inline-block;width:14px;height:14px;border-radius:50%;vertical-align:middle;border:1px solid #888;margin-right:6px}
.note{color:var(--mut);font-size:13px}
details{margin:8px 0}summary{cursor:pointer;font-weight:700;color:var(--ac)}h3{font-size:16px;margin:0 0 6px}
"""


def page(title, body):
    return '<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>%s</title><style>%s</style></head><body><main>%s</main></body></html>' % (E(title), CSS, body)


def tag(level):
    cls = {"ok": "ok", "ERREUR": "ERREUR"}.get(level, "conf")
    return '<span class="tag %s">%s</span>' % (cls, E(level))


def montage_page(path, hw, gbf, scope):
    m = load(path)
    nb = numbers_of(m)
    m = subst(m, {k: v for k, v in nb.items() if k.startswith("__")})
    res, _ = validate(m, hw)
    nerr = sum(1 for r in res if r[0] == "ERREUR")
    b = []
    b.append("<h1>%s</h1><p class='sub'>TP%s · %s · %s</p>" % (E(m["titre"]), m["tp"], E(m["id"]), E(m["objectif"])))
    b.append("<div class='card'><b>Vérification automatique du câblage :</b> %s</div>" % (tag("ERREUR") + " %d erreur(s) — voir plus bas" % nerr if nerr else tag("ok") + " aucune erreur de câblage détectée"))
    b.append("<div class='card'><h2>1. Vue d'ensemble de la table : câbles GBF → plaque → oscilloscope</h2>%s" % bench_svg(m, hw, gbf, scope))
    b.append("<table><tr><th>Câble</th><th>De</th><th>Vers</th><th>Rôle</th></tr>")
    for c in m["cables"]:
        b.append("<tr><td><b>%s</b> — %s</td><td>%s</td><td>%s</td><td>%s %s</td></tr>" % (c["id"], E(c["nom"]), E(c["de"]), E(c["vers"]), E(c["role"]), tag("à confirmer")))
    b.append("</table><p class='note'>Les deux BNC de la plaque reçoivent chacun <b>deux fils</b> (âme + blindage). La sortie du GBF sert <b>deux fois</b> : vers la plaque (câble A) et vers la voie 1 (câble B, par le T), pour afficher Ue.</p></div>")
    b.append("<div class='card'><h2>2. Schéma électrique</h2>%s</div>" % schema_diviseur_svg(m, nb))
    b.append("<div class='card'><h2>3. Câblage sur la plaque (vue de dessus, comme sur ta table)</h2><div class='row'><div>%s</div><div>" % board_svg(m, hw, 640))
    b.append("<table><tr><th>N°</th><th>Fil</th><th>De → vers</th><th>Rôle</th></tr>")
    for w in m["fils"]:
        b.append("<tr><td><b>%s</b></td><td><span class='sw' style='background:%s'></span>%s</td><td>%s → %s</td><td>%s</td></tr>" % (w["n"], WIRE.get(w["couleur"], "#999"), E(w["couleur"]), E(w["de"]), E(w["vers"]), E(w["role"])))
    b.append("</table><h3>Composants</h3><table><tr><th>Réf.</th><th>Valeur</th><th>Pattes</th></tr>")
    for n, c in m["composants"].items():
        b.append("<tr><td>%s</td><td>%s</td><td>%s – %s</td></tr>" % (E(n), E(c["etiquette"]), E(c["a"]), E(c["b"])))
    b.append("</table><p class='note'>Adresse d'un trou : T1b62 = bloc 1, lettre b (bande de droite a–e), rangée 62. TOP-L1-3 = bus du haut, côté gauche, ligne 1, position 3. Les 5 trous d'une même rangée et d'un même côté de la fente sont reliés.</p></div></div></div>")
    for key, inst, lab in (("gbf", gbf, "GBF"), ("scope", scope, "oscilloscope")):
        cfg = m["instruments"][key]
        b.append("<div class='card'><h2>%s. Réglages : %s</h2><p><b>%s</b></p><div class='row'><div>%s</div><div>%s</div></div></div>" % (4 if key == "gbf" else 5, lab, E(cfg["reglages"]), photo_pastilles(inst, cfg["photo"], cfg["etapes"]), steps_list(cfg["etapes"])))
    ec = m["ecran_attendu"]
    b.append("<div class='card'><h2>6. Résultat attendu à l'écran de l'oscilloscope</h2><div class='row'><div style='max-width:760px'>%s</div><div>" % scope_svg(ec, "att"))
    b.append("<table><tr><th>Grandeur</th><th>Valeur attendue</th></tr><tr><td>Ue (voie 1, jaune)</td><td>2 Vpp, 1 kHz, 2 carreaux à 1 V/div</td></tr>")
    b.append("<tr><td>Us (voie 2, verte)</td><td>%.3f Vpp, 2 carreaux à 100 mV/div</td></tr><tr><td>Rapport Us/Ue</td><td>%.4f (R2 / (R1+R2))</td></tr><tr><td>Période</td><td>1 ms = 5 carreaux à 200 µs/div</td></tr></table>" % (nb["us_vpp"], nb["ratio"]))
    b.append("<p class='note'>Les deux courbes sont en phase (diviseur résistif). Elles sont rangées en deux bandes (jaune en haut, verte en bas) comme après un Auto Scale.</p></div></div></div>")
    b.append("<div class='card'><h2>7. Pannes fréquentes</h2><ul>%s</ul></div>" % "".join("<li>%s</li>" % E(p) for p in m["pannes"]))
    b.append("<div class='card'><h2>8. Détail des vérifications automatiques</h2><table>%s</table></div>" % "".join("<tr><td>%s</td><td>%s</td></tr>" % (tag(l), E(t)) for l, t in res))
    return m, res, page(m["titre"], "".join(b))


def crop_div(photo, width):
    f, (x, y, w, h) = photo["file"], photo["crop"]
    full = {"scope_tp2_a.jpg": (1600, 1200), "scope_tp2_b.jpg": (1600, 1200), "scope_tp2_c.jpg": (1200, 1600)}[f]
    s = width / float(w)
    return '<div style="width:%dpx;height:%dpx;background:url(../assets/photos/%s) -%.1fpx -%.1fpx / %.1fpx %.1fpx no-repeat;border-radius:6px"></div>' % (width, h * s, f, x * s, y * s, full[0] * s, full[1] * s)


def tests_page():
    b = ["<h1>Test de fidélité du rendu d'écran</h1><p class='sub'>À gauche : ta photo (recadrée sur l'écran). À droite : l'écran regénéré depuis le YAML. Les valeurs sont lues sur la photo.</p>"]
    for n in ("a", "b", "c"):
        cfg = load("tests/scope_tp2_%s.yaml" % n)
        v = cfg.get("vue", {})
        tr = "perspective(1100px) rotateY(%sdeg) rotate(%sdeg)" % (v.get("rotateY", 0), v.get("rotate", 0))
        b.append("<div class='card'><h2>%s</h2><div class='row'><div><p class='note'>Photo d'origine</p>%s</div><div><p class='note'>Rendu face à face</p>%s</div><div style='overflow:hidden'><p class='note'>Rendu « vu depuis ta place » (même inclinaison que la photo)</p><div style='transform:%s;transform-origin:center;background:#0b0d10'>%s</div></div></div></div>" % (E(cfg["titre"]), crop_div(cfg["photo"], 440), scope_svg(cfg, "t%sa" % n), tr, scope_svg(cfg, "t%sb" % n)))
    return page("Tests de rendu écran", "".join(b))


def main():
    hw = load("hardware/board_wish106.yaml")
    gbf = load("hardware/instruments/gbf.yaml")
    scope = load("hardware/instruments/scope.yaml")
    psu = load("hardware/instruments/psu.yaml")
    import montage_page as mp
    devs = {"gbf": gbf, "scope": scope, "psu": psu}
    out = ROOT / "out"
    out.mkdir(exist_ok=True)
    index = ["<h1>LABDEC_VISUEL</h1><p class='sub'>Montages générés depuis les YAML — ne jamais éditer les pages à la main.</p><div class='card' style='background:linear-gradient(135deg,#0369a1,#0284c7);color:#fff;'><h2 style='color:#fff;margin:0 0 6px;'>🎯 Banc Virtuel Interactif (Entraînement au câblage)</h2><p style='margin:0 0 10px;font-size:14px;opacity:0.95;'>Prenez les câbles, pointez trou par trou sur la plaque Wish Board 106, suivez en temps réel le placement des fils à droite et validez automatiquement vos montages (TP1, TP2, TP3).</p><a href='labdec_interactif.html' style='display:inline-block;background:#fff;color:#0369a1;font-weight:700;padding:8px 16px;border-radius:6px;text-decoration:none;'>🚀 Lancer le Simulateur Interactif</a></div><div class='card'><b>Séance rapide</b><ul><li><a href='seance_30min.html'><b>Séance 30 minutes : tous les cas à prédire + montages à câbler</b></a></li></ul></div><div class='card'><b>Montages (câblage réel sur la plaque)</b><ul>"]
    status = 0
    for p in sorted((ROOT / "montages").rglob("*.yaml")):
        rel = str(p.relative_to(ROOT))
        m, res, pg = mp.build(rel, hw, devs, SCHEMA_HOOK)
        (out / (m["id"] + ".html")).write_text(pg, encoding="utf-8")
        nerr = sum(1 for r in res if r[0] == "ERREUR")
        status += nerr
        print("%-28s %s" % (m["id"], "OK" if not nerr else "%d ERREUR(S)" % nerr))
        for l, t in res:
            print("   [%s] %s" % (l, t))
        index.append("<li><a href='%s.html'>%s</a> — TP%s</li>" % (m["id"], E(m["titre"]), m["tp"]))
    index.append("</ul></div><div class='card'><b>Prédictions d'écran</b><ul>")
    index.append("<li><a href='predictions_tp2.html'><b>TP2 — prédictions d'écran avec les artefacts</b> (saturation, bande passante, vitesse de montée)</a></li>")
    index.append("<li><a href='predictions_tp1.html'><b>TP1 — prédictions d'écran</b> (GBF direct, pont diviseur, impédance interne, LED)</a></li>")
    index.append("<li><a href='scope_tests.html'>Test de fidélité du rendu des écrans (3 photos TP2)</a></li></ul></div>")
    (out / "index.html").write_text(page("LABDEC_VISUEL", "".join(index)), encoding="utf-8")
    (out / "scope_tests.html").write_text(tests_page(), encoding="utf-8")
    print("pages écrites dans", out)
    return 1 if status else 0


if __name__ == "__main__":
    sys.exit(main())
