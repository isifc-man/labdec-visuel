# -*- coding: utf-8 -*-
"""Pages « Prédis d'abord, puis regarde » : TP1 et TP2, écrans calculés par tools/predict.py."""
import math
import pathlib
import render
import predict as P

E = render.E
ROOT = render.ROOT

PANEL = {"mode": "autoscale", "titre": "Rég. auto éch",
         "boutons": ["Annuler\nEchelle auto", "Débog rapide", "Voies\nAffichées", "Mode acq\nNormal"]}

LABELS = {
    "led": {"ve": "E (sortie du GBF)", "vs": "LED"},
    "internal": {"ve": "Uc"},
    "direct": {"ve": "signal du GBF"},
    "divider": {"ve": "Ue", "vs": "Us"},
    "subtractor": {"ve": "V2", "v1": "V1", "vs": "Vs"},
    "association": {"ve": "Ve", "v1": "V1 (sortie étage 1)", "vs": "Vs"},
}
KIND = {"sine": "Sinus", "square": "Carré", "triangle": "Triangle"}


def fv(v):
    a = abs(v)
    if a < 1e-6:
        return "0.00V"
    if a >= 1:
        return "%.2fV" % v
    if a >= 0.1:
        return "%.0fmV" % (v * 1000)
    if a >= 1e-3:
        return "%.1fmV" % (v * 1000)
    return "%.0fµV" % (v * 1e6)


def ff(f):
    if f >= 1e6:
        return "%.3fMHz" % (f / 1e6)
    if f >= 1e3:
        return "%.3fkHz" % (f / 1e3)
    return "%.3fHz" % f


def fscale(v):
    return render.fmt_v(v).replace("/", "/div")


def ftime(t):
    return render.fmt_t(t).replace("/", "/div")


def label_of(circ, node):
    return LABELS.get(circ["type"], {}).get(node, {"ve": "Ve", "vs": "Vs", "v1": "V1"}[node])


# ------------------------------------------------------------------ schémas (SVG simples)
class Sch(object):
    def __init__(self):
        self.l, self.t = [], []

    def wire(self, pts):
        self.l.append('<polyline points="%s"/>' % " ".join("%d,%d" % p for p in pts))

    def dot(self, x, y, big=False):
        self.l.append('<circle cx="%d" cy="%d" r="%d" fill="#111"/>' % (x, y, 5 if big else 4))

    def pin(self, x, y):
        self.l.append('<circle cx="%d" cy="%d" r="5" fill="#fff"/>' % (x, y))

    def res(self, cx, cy, horiz, label, lx=0, ly=-14):
        w, h = (60, 20) if horiz else (20, 50)
        self.l.append('<rect x="%d" y="%d" width="%d" height="%d" fill="#fff"/>' % (cx - w / 2, cy - h / 2, w, h))
        self.text(cx + lx, cy + ly, label, "middle", 12)

    def gnd(self, x, y):
        self.l.append('<path d="M%d,%d H%d M%d,%d H%d M%d,%d H%d"/>' % (x - 14, y, x + 14, x - 9, y + 7, x + 9, x - 4, y + 14, x + 4))

    def text(self, x, y, s, anchor="start", size=13, color="#111", bold=False):
        self.t.append('<text x="%d" y="%d" font-size="%d" fill="%s" text-anchor="%s"%s>%s</text>' % (x, y, size, color, anchor, ' font-weight="700"' if bold else "", E(s)))

    def amp(self, x, y, flip=False):
        self.l.append('<polygon points="%d,%d %d,%d %d,%d" fill="#fff"/>' % (x, y - 60, x, y + 60, x + 120, y))
        self.t.append('<text x="%d" y="%d" font-size="18">%s</text><text x="%d" y="%d" font-size="18">%s</text>' % (x + 8, y - 24, "+" if flip else "−", x + 8, y + 38, "−" if flip else "+"))

    def svg(self, w, h):
        return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" style="max-width:100%%;height:auto;background:#fff;border:1px solid #ddd;border-radius:8px" font-family="Arial">'
                '<g stroke="#111" stroke-width="2" fill="none">%s</g>%s</svg>') % (w, h, w, "".join(self.l), "".join(self.t))


def stage(s, kind, x0, C, names):
    """Un étage d'ampli (amplificateur à x0). C = composants, names = (R_in, R_fb, R_g, R_4)."""
    ax, ay = x0 + 200, 130
    lab = lambda n: C[n]["etiquette"]
    if kind == "follower":
        s.amp(ax, ay)
        s.wire([(x0 + 30, 160), (ax, 160)])
        s.pin(x0 + 30, 160)
        s.text(x0 + 30, 185, "Ve", "middle", 14, "#0b3d91", True)
        s.wire([(x0 + 320, ay), (x0 + 370, ay)])
        s.pin(x0 + 370, ay)
        s.text(x0 + 370, ay - 12, "Vs", "middle", 14, "#0b3d91", True)
        s.wire([(x0 + 345, ay), (x0 + 345, 60), (x0 + 170, 60), (x0 + 170, 100), (ax, 100)])
        s.dot(x0 + 345, ay)
    elif kind in ("inverting", "subtractor"):
        s.amp(ax, ay)
        r1, r2 = names[0], names[1]
        s.pin(x0 + 20, 100)
        s.text(x0 + 20, 85, "V1" if kind == "subtractor" else "Ve", "middle", 14, "#0b3d91", True)
        s.wire([(x0 + 20, 100), (x0 + 60, 100)])
        s.res(x0 + 90, 100, True, lab(r1))
        s.wire([(x0 + 120, 100), (ax, 100)])
        s.dot(x0 + 170, 100)
        s.wire([(x0 + 170, 100), (x0 + 170, 50), (x0 + 200, 50)])
        s.res(x0 + 240, 50, True, lab(r2), 0, -14)
        s.wire([(x0 + 270, 50), (x0 + 345, 50), (x0 + 345, ay)])
        s.wire([(x0 + 320, ay), (x0 + 370, ay)])
        s.dot(x0 + 345, ay)
        s.pin(x0 + 370, ay)
        s.text(x0 + 370, ay - 12, "Vs", "middle", 14, "#0b3d91", True)
        if kind == "inverting":
            s.wire([(ax, 160), (x0 + 170, 160), (x0 + 170, 200)])
            s.gnd(x0 + 170, 200)
        else:
            r3, r4 = names[2], names[3]
            s.pin(x0 + 20, 160)
            s.text(x0 + 20, 185, "V2", "middle", 14, "#0b3d91", True)
            s.wire([(x0 + 20, 160), (x0 + 60, 160)])
            s.res(x0 + 90, 160, True, lab(r3), 0, 26)
            s.wire([(x0 + 120, 160), (ax, 160)])
            s.dot(x0 + 170, 160)
            s.wire([(x0 + 170, 160), (x0 + 170, 185)])
            s.res(x0 + 170, 210, False, lab(r4), 40, 4)
            s.wire([(x0 + 170, 235), (x0 + 170, 255)])
            s.gnd(x0 + 170, 255)
    elif kind == "noninverting":
        s.amp(ax, ay, flip=True)
        r1, r2 = names[0], names[1]
        s.pin(x0 + 30, 100)
        s.text(x0 + 30, 85, "Ve", "middle", 14, "#0b3d91", True)
        s.wire([(x0 + 30, 100), (ax, 100)])
        s.wire([(x0 + 320, ay), (x0 + 370, ay)])
        s.pin(x0 + 370, ay)
        s.text(x0 + 370, ay - 12, "Vs", "middle", 14, "#0b3d91", True)
        s.wire([(x0 + 345, ay), (x0 + 345, 210), (x0 + 290, 210)])
        s.dot(x0 + 345, ay)
        s.res(x0 + 255, 210, True, lab(r2), 0, 30)
        s.wire([(x0 + 225, 210), (x0 + 170, 210), (x0 + 170, 160), (ax, 160)])
        s.dot(x0 + 170, 210)
        s.wire([(x0 + 170, 210), (x0 + 170, 230)])
        s.res(x0 + 170, 255, False, lab(r1), 40, 4)
        s.wire([(x0 + 170, 280), (x0 + 170, 295)])
        s.gnd(x0 + 170, 295)


def schema_svg(circ, nb=None):
    s = Sch()
    t = circ["type"]
    C = circ.get("comps", {})
    if t == "follower":
        stage(s, "follower", 0, C, None)
        return s.svg(430, 300)
    if t == "inverting":
        stage(s, "inverting", 0, C, ("R1", "R2"))
        return s.svg(430, 300)
    if t == "noninverting":
        stage(s, "noninverting", 0, C, ("R1", "R2"))
        return s.svg(430, 320)
    if t == "subtractor":
        stage(s, "subtractor", 0, C, ("R1", "R2", "R3", "R4"))
        return s.svg(430, 300)
    if t == "association":
        stage(s, "noninverting", 0, C, ("R1", "R2"))
        s.wire([(370, 130), (385, 130), (385, 100), (400, 100)])
        stage(s, "inverting", 380, C, ("R3", "R4"))
        s.text(375, 20, "étage 1 : non inverseur (+10)", "middle", 12, "#555")
        s.text(570, 20, "étage 2 : inverseur (−20)", "middle", 12, "#555")
        # le nœud entre les deux étages s'appelle V1 (pas Vs / Ve)
        s.t = [x.replace(">Vs<", ">V1<") if 'x="370"' in x else x.replace(">Ve<", ">V1<") if 'x="400"' in x else x for x in s.t]
        return s.svg(820, 320)
    if t == "direct":
        s.l.append('<circle cx="80" cy="130" r="28" fill="#fff"/><path d="M66,130 q7,-14 14,0 t14,0"/>')
        s.wire([(80, 102), (80, 70), (330, 70)])
        s.wire([(80, 158), (80, 190), (330, 190)])
        s.l.append('<rect x="330" y="50" width="160" height="160" rx="8" fill="#fff"/>')
        s.text(410, 120, "Oscilloscope", "middle", 15, "#111", True)
        s.text(410, 142, "1 MΩ ∥ 16 pF", "middle", 13)
        s.text(80, 135, "GBF", "middle", 12)
        s.text(205, 62, "câble BNC", "middle", 12, "#555")
        return s.svg(520, 240)
    if t == "internal":
        s.l.append('<rect x="30" y="40" width="130" height="190" rx="4" stroke-dasharray="6,4"/>')
        s.text(95, 34, "GBF", "middle", 13, "#111", True)
        s.res(95, 85, False, "Rint ≈ 50 Ω", 62, 4)
        s.l.append('<circle cx="95" cy="170" r="26" fill="#fff"/>')
        s.text(95, 175, "E", "middle", 14)
        s.wire([(95, 60), (95, 40), (300, 40), (300, 80)])
        s.res(300, 105, False, C["Rc"]["etiquette"], 56, 4)
        s.wire([(300, 130), (300, 250)])
        s.wire([(95, 196), (95, 250), (300, 250)])
        s.gnd(300, 250)
        s.text(330, 180, "Uc", "start", 15, "#0b3d91", True)
        return s.svg(460, 290)
    if t == "led":
        s.l.append('<circle cx="70" cy="140" r="26" fill="#fff"/><path d="M57,140 h8 v-10 h8 v20 h8"/>')
        s.text(70, 188, "GBF (carré 0–5 V)", "middle", 12)
        s.wire([(70, 114), (70, 70), (170, 70)])
        s.res(200, 70, True, C["R"]["etiquette"])
        s.wire([(230, 70), (330, 70), (330, 100)])
        s.l.append('<polygon points="316,100 344,100 330,128" fill="#fff"/><path d="M316,128 H344"/>')
        s.wire([(330, 128), (330, 200), (70, 200), (70, 166)])
        s.gnd(200, 200)
        s.text(352, 118, "LED", "start", 14)
        s.dot(170, 70)
        s.text(160, 52, "E", "middle", 14, "#0b3d91", True)
        s.text(345, 80, "A", "start", 14, "#0b3d91", True)
        return s.svg(440, 240)
    if t == "divider":
        m_like = {"composants": C, "calcul": {"haut": ["R1"], "bas": ["R2"]}}
        return render.schema_diviseur_svg(m_like, nb)
    return ""


# ------------------------------------------------------------------ scénarios
def build_cfg(circ, sc, shown, tdiv):
    names = sc["voies"]
    two = len(names) == 2
    cfg = {"tdiv": tdiv, "panel": PANEL, "bottom": []}
    meas = {}
    for n, name in enumerate(names, 1):
        a = shown[name]
        span = max(P.vpp(a), 1e-6)
        if two:
            scale = P.nice_ceil(span / 3.2)
            off = P.mid(a) - (2 if n == 1 else -2) * scale
        else:
            scale = P.nice_ceil(span / 6.4)
            off = P.mid(a)
        cfg["ch%d" % n] = {"scale": scale, "offset": off, "samples": a}
        meas[n] = a
    a1 = meas[1]
    cfg["trig"] = {"src": 1, "level": fv(P.mid(a1))}
    f = sc["gbf"]["f"]
    # Barre du bas = TA configuration de mesures : Moy - PE(1), Fréq(1), Max(1), Max(2)
    periodic = P.vpp(a1) > 1e-6
    mp1 = mean_pe(a1, tdiv, f) if periodic else None
    cfg["bottom"] = [
        {"l": "Moy - PE(1):", "v": fmean(mp1), "c": "ch1"},
        {"l": "Fréq(1):", "v": ff(f) if periodic else "Aucun signal", "c": "ch1"},
        {"l": "Max(1):", "v": fv(max(a1)), "c": "ch1"},
        {"l": "Max(2):", "v": fv(max(meas[2])) if 2 in meas else "—", "c": "ch2"},
    ]
    extra = []
    for m in sc.get("mesures", []):
        if m == "vpp1":
            extra.append(("Cr-cr(1)", fv(P.vpp(meas[1]))))
        elif m == "vpp2" and 2 in meas:
            extra.append(("Cr-cr(2)", fv(P.vpp(meas[2]))))
        elif m == "phase21" and 2 in meas:
            ph = P.phase_deg(meas[1], meas[2], f, tdiv)
            if ph is not None and abs(ph) < 0.5:
                ph = 0.0
            extra.append(("Phase(2→1)", ("%.1f°" % ph) if ph is not None else "—"))
    if 2 in meas and periodic:
        extra.append(("Moy - PE(2)", fmean(mean_pe(meas[2], tdiv, f))))
    cfg["extra"] = extra
    return cfg


def extra_vals(circ, sc, vals, tl):
    g = sc["gbf"]
    so = 1.0 if g.get("charge", "HighZ") == "HighZ" else 2.0
    v = dict(vals)
    for k in list(v):
        if v[k] is None:
            v[k] = float("nan")
    if v["phase"] == v["phase"] and abs(v["phase"]) < 0.5:
        v["phase"] = 0.0
    v["tr_us"] = min(v["vpp_demand"], 2 * tl["vsat"]) / tl["slew_vus"] if v["vpp_demand"] == v["vpp_demand"] else float("nan")
    v["perte_pct"] = (1 - v["vpp_in"] / (so * g["vpp"])) * 100 if g.get("vpp") else float("nan")
    v["res_pct"] = v["vpp_out"] / v["vpp_in"] * 100 if v["vpp_in"] > 0 else float("nan")
    v["c_pf"] = circ.get("c_charge_pf", float("nan"))
    v["fc_k"] = (v["fc"] / 1e6) if v["fc"] == v["fc"] and v["fc"] else float("nan")
    if circ["type"] == "led":
        vin_max = so * (g.get("offset", 0) + g["vpp"] / 2.0)
        v["i_ma"] = (vin_max - v["max_out"]) / (circ["comps"]["R"]["ohm"] + 50.0) * 1000
    return v


def fmt_text(txt, vals):
    try:
        return txt.format(**vals)
    except (KeyError, ValueError, IndexError) as e:
        return txt + "  [champ non calculé : %s]" % e


def settings_text(circ, sc, cfg):
    g = sc["gbf"]
    gb = "GBF : %s · %s · %s · offset %s V · charge %s" % (
        KIND[g["kind"]], ("%g Vpp" % g["vpp"]), ("%g Hz" % g["f"] if g["f"] < 1000 else ("%g kHz" % (g["f"] / 1e3) if g["f"] < 1e6 else "%g MHz" % (g["f"] / 1e6))),
        "%g" % g.get("offset", 0), "High Z" if g.get("charge", "HighZ") == "HighZ" else "50 Ω (⚠ ne correspond pas à l'oscillo 1 MΩ)")
    if sc.get("v1"):
        gb += " · V1 = %g V continu (alimentation)" % sc["v1"]["v"]
    if sc.get("ohm"):
        gb += " · résistances réelles : " + ", ".join("%s = %g Ω" % (k, v) for k, v in sc["ohm"].items())
    parts = []
    for n, name in enumerate(sc["voies"], 1):
        ch = cfg["ch%d" % n]
        parts.append("voie %d (%s) = %s, %s" % (n, "jaune" if n == 1 else "verte", label_of(circ, name), fscale(ch["scale"])))
    sc_t = "Oscillo : %s ; %s ; déclenchement voie 1, front montant ; Auto Scale puis ajustements" % ("  /  ".join(parts), ftime(cfg["tdiv"]))
    return gb, sc_t


def bode_table(circ, tl):
    if not circ.get("bode_f"):
        return ""
    rows = []
    for f in circ["bode_f"]:
        b = P.bode(circ, f, tl, {})
        if b:
            fl = ("%g kHz" % (f / 1e3)) if f < 1e6 else ("%g MHz" % (f / 1e6))
            rows.append("<tr><td>%s</td><td>%.4g</td><td>%.1f</td><td>%.1f°</td></tr>" % (fl, b[0], 20 * math.log10(b[0]), b[1]))
    fc = P.fc_of(circ, tl)
    cap = "Gain et phase PRÉVUS sans calcul sur l'écran (petit signal, modèle à un pôle). f_c ≈ %.0f kHz." % (fc / 1e3) if fc else ""
    return "<details><summary>Tableau de Bode prévu</summary><table><tr><th>Fréquence</th><th>|gain|</th><th>dB</th><th>phase</th></tr>%s</table><p class='note'>%s</p></details>" % ("".join(rows), cap)


def mean_pe(a, tdiv, f):
    """Moyenne sur un nombre ENTIER de périodes (mesure « Moy - PE » de l'oscillo) ; None s'il n'y a pas une période entière."""
    nper = int(math.floor(10 * tdiv * f + 1e-9))
    if nper < 1:
        return None
    n = int(round(nper / (f * 10 * tdiv) * 900))
    seg = a[:n + 1]
    return sum((seg[i] + seg[i + 1]) / 2.0 for i in range(len(seg) - 1)) / (len(seg) - 1)


def fmean(v):
    if v is None:
        return "Aucun signal"
    if abs(v) < 5e-4:
        return "0.0mV"
    return fv(v)


def divider_nb(circ):
    C = circ["comps"]
    rh, rb = C["R1"]["ohm"], C["R2"]["ohm"]
    return {"rh": rh, "ratio": rb / float(rh + rb), "us_vpp": 2.0 * rb / float(rh + rb)}


def schema_for_montage(m):
    if not (ROOT / ("predictions/tp%s.yaml" % m["tp"])).exists():
        return ""
    data = render.load("predictions/tp%s.yaml" % m["tp"])
    for circ in data["circuits"]:
        if circ["id"] == m["circuit"]:
            return schema_svg(circ, divider_nb(circ) if circ["type"] == "divider" else None)
    return ""


def montage_block(circ):
    if not circ.get("montage"):
        return "<p class='note'><b>Montage :</b> aucune plaque. Un câble BNC relie la sortie du GBF (50 Ω) à la voie 1 de l'oscilloscope.</p>"
    hw = render.load("hardware/board_wish106.yaml")
    m = render.load_montage(circ["montage"])
    res, _ = render.validate(m, hw)
    nerr = sum(1 for r in res if r[0] == "ERREUR")
    rows = "".join("<tr><td><b>%s</b></td><td><span class='sw' style='background:%s'></span>%s</td><td>%s → %s</td></tr>" % (
        w["n"], render.WIRE.get(w["couleur"], "#999"), E(w["couleur"]), E(w["de"]), E(w["vers"])) for w in m["fils"])
    return ("<details open><summary>Montage sur la plaque : %d fils, %d composants — %s</summary><div class='row'><div>%s</div><div>"
            "<table><tr><th>N°</th><th>Fil</th><th>De → vers</th></tr>%s</table>"
            "<p><a href='%s.html'>Page complète du montage</a> (câbles de la table, alimentation, réglages des appareils, ordre de câblage).</p></div></div></details>") % (
        len(m["fils"]), len(m["composants"]), "câblage vérifié ✓" if not nerr else "%d ERREUR(S)" % nerr, render.board_svg(m, hw, 520), rows, m["id"])


def circuit_card(circ, tl, glob):
    b = ["<div class='card' id='%s'><h2>%s</h2>" % (E(circ["id"]), E(circ["titre"]))]
    nb = divider_nb(circ) if circ["type"] == "divider" else None
    b.append("<div class='row'><div>%s</div><div>%s</div></div>" % (schema_svg(circ, nb), bode_table(circ, tl)))
    b.append(montage_block(circ))
    for sc in circ["scenarios"]:
        shown, tdiv, vals = P.run(circ, sc, tl, glob)
        cfg = build_cfg(circ, sc, shown, tdiv)
        vals = extra_vals(circ, sc, vals, tl)
        gb, ot = settings_text(circ, sc, cfg)
        b.append("<div class='card' id='%s-%s' style='background:transparent'><h3>%s</h3><p class='note'>%s<br>%s</p>" % (E(circ["id"]), E(sc["id"]), E(sc["titre"]), E(gb), E(ot)))
        b.append("<p><b>À prédire avant de regarder :</b> %s</p>" % E(sc["a_predire"]))
        b.append("<details><summary>Voir ce que l'oscilloscope affiche</summary><div class='row'><div style='max-width:760px'>%s</div><div>" % render.scope_svg(cfg, "%s%s" % (circ["id"][-4:], sc["id"])))
        rows = [("Ve (entrée)", "%.3f Vpp" % vals["vpp_in"]), ("Sortie observée", "%.3f Vpp" % vals["vpp_out"]), ("Rapport", "%.4g" % vals["gain"])]
        if vals["phase"] == vals["phase"]:
            rows.append(("Déphasage sortie / entrée", "%.1f°" % vals["phase"]))
        rows += cfg["extra"]
        b.append("<table>%s</table>" % "".join("<tr><td>%s</td><td><b>%s</b></td></tr>" % (E(a), E(c)) for a, c in rows))
        b.append("<p><b>Attendu :</b> %s</p>" % E(fmt_text(sc["attendu"], vals)))
        if sc.get("artefact"):
            b.append("<p style='border-left:4px solid #d6246e;padding-left:10px'><b>Artefact / piège :</b> %s</p>" % E(fmt_text(sc["artefact"], vals)))
        b.append("</div></div></details></div>")
    b.append("</div>")
    return "".join(b)


def build(tp, out):
    data = render.load("predictions/tp%d.yaml" % tp)
    tl, glob = data["tl081"], data["globaux"]
    body = ["<h1>%s</h1><p class='sub'>Entraînement : lis les réglages, prédis ce que tu vas voir, puis ouvre « Voir ce que l'oscilloscope affiche ». Écrans calculés (voir « Hypothèses ») — non mesurés.</p>" % E(data["titre"])]
    body.append("<div class='card'><b>Hypothèses du modèle (tu peux les changer dans <code>predictions/tp%d.yaml</code>)</b><ul>" % tp)
    body.append("<li>GBF : résistance de sortie %g Ω ; « High Z » : l'affichage est la tension à vide ; « 50 Ω » : tension à vide = 2 × l'affichage.</li>" % glob["rout_gbf"])
    body.append("<li>Oscilloscope : 1 MΩ, sonde 1:1, déclenché sur le front montant de l'entrée. Auto Scale range la voie 1 en haut et la voie 2 en bas.</li>")
    if tp == 2:
        body.append("<li>TL081 (fiche TI, valeurs typiques) : GBP %g MHz, vitesse de montée %g V/µs, sortie limitée à ±%g V (fiche : ±12 V min, ±13,5 V typ).</li>" % (tl["gbw_hz"] / 1e6, tl["slew_vus"], tl["vsat"]))
        body.append("<li>Modèle d'AOP à un pôle (fréquence de coupure = GBP / (1 + R2/R1)), avec vitesse de montée et saturation. Il ne reproduit PAS les petits « pics » que montre ta photo B : leur cause n'est pas identifiée.</li>")
    else:
        body.append("<li>Capacité vue par le pont diviseur : ≈ 116 pF (16 pF oscillo + ≈ 100 pF câble BNC de 1 m) : hypothèse, elle fixe la coupure à haute fréquence.</li>")
        body.append("<li>LED rouge supposée (≈ 1,9 V à 8 mA). Ue est supposé idéal à haute fréquence.</li>")
    body.append("<li>Barre du bas de l'écran = ta configuration de mesures : <b>Moy - PE(1)</b> (moyenne de la voie 1 sur un nombre entier de périodes), <b>Fréq(1)</b>, <b>Max(1)</b>, <b>Max(2)</b>. Cr-cr et phase sont dans le tableau à droite (ajoute-les avec Meas).</li>")
    body.append("<li>Le signe du déphasage affiché par l'oscillo (« Phase(2→1) ») n'est pas vérifié : ici négatif = la voie 2 est en retard sur la voie 1.</li></ul></div>")
    for circ in data["circuits"]:
        body.append(circuit_card(circ, tl, glob))
    path = out / ("predictions_tp%d.html" % tp)
    path.write_text(render.page(data["titre"], "".join(body)), encoding="utf-8")
    return path


ORDER = ["tp1-C-impedance-interne", "tp1-D-led", "tp1-A1-gbf-direct", "tp1-B-pont-diviseur",
         "tp2-A-suiveur", "tp2-B1-inverseur", "tp2-B2-non-inverseur", "tp2-C-association", "tp2-D-soustracteur"]


def seance(out):
    import montage_page as mp
    circs = {}
    for tp in (1, 2):
        d = render.load("predictions/tp%d.yaml" % tp)
        for c in d["circuits"]:
            circs[c["id"]] = (tp, c)
    cases = [(circs[cid][0], circs[cid][1], sc) for cid in ORDER for sc in circs[cid][1]["scenarios"]]
    n = len(cases)
    b = ["<h1>Séance 30 minutes</h1><p class='sub'>%d cas à prédire × 1 min = %d min, plus 3 min de marge. Prédis sur papier ou à voix haute AVANT d'ouvrir le lien, puis compare avec l'écran calculé. Ordre : impédance interne d'abord (le plus rapide à câbler).</p>" % (n, n)]
    b.append("<div class='card'><b>Chrono :</b> <span id='t'>00:00</span> <button onclick='go()'>Démarrer / pause</button> · cas faits : <span id='nb'>0</span> / %d</div>" % n)
    b.append("<div class='card'><h2>1. Cas à prédire</h2><table><tr><th></th><th>TP</th><th>Circuit</th><th>Cas</th><th>À prédire</th><th></th></tr>")
    for tp, c, sc in cases:
        b.append("<tr><td><input type='checkbox' class='ck'></td><td>TP%d</td><td>%s</td><td><b>%s</b></td><td>%s</td><td><a href='predictions_tp%d.html#%s-%s'>ouvrir</a></td></tr>" % (
            tp, E(c["titre"]), E(sc["titre"]), E(sc["a_predire"]), tp, E(c["id"]), E(sc["id"])))
    b.append("</table></div>")
    b.append("<div class='card'><h2>2. Montages à câbler (pièces réelles), dans l'ordre le plus rapide</h2><table><tr><th>Montage</th><th>Fils</th><th>Composants</th><th>Depuis le précédent</th></tr>")
    for cid in ORDER:
        tp, c = circs[cid]
        if not c.get("montage"):
            b.append("<tr><td>%s</td><td colspan='3'>aucune plaque : un câble BNC GBF → voie 1</td></tr>" % E(c["titre"]))
            continue
        m = render.load_montage(c["montage"])
        txt = "—"
        if m.get("precedent"):
            pm = render.load_montage(m["precedent"])
            cw, pw = set(mp.wire_id(w) for w in m["fils"]), set(mp.wire_id(w) for w in pm["fils"])
            cc, pc = set(mp.comp_id(k, v) for k, v in m["composants"].items()), set(mp.comp_id(k, v) for k, v in pm["composants"].items())
            txt = "retirer %d fil(s) + %d composant(s) · ajouter %d fil(s) + %d composant(s)" % (len(pw - cw), len(pc - cc), len(cw - pw), len(cc - pc))
        b.append("<tr><td><a href='%s.html'>%s</a></td><td>%d</td><td>%d</td><td>%s</td></tr>" % (E(m["id"]), E(c["titre"]), len(m["fils"]), len(m["composants"]), E(txt)))
    for p in sorted((ROOT / "montages" / "tp3").glob("*.yaml")):
        m = render.load_montage(str(p.relative_to(ROOT)))
        txt = "—"
        if m.get("precedent"):
            pm = render.load_montage(m["precedent"])
            cw, pw = set(mp.wire_id(w) for w in m["fils"]), set(mp.wire_id(w) for w in pm["fils"])
            cc, pc = set(mp.comp_id(k, v) for k, v in m["composants"].items()), set(mp.comp_id(k, v) for k, v in pm["composants"].items())
            txt = "retirer %d fil(s) + %d composant(s) · ajouter %d fil(s) + %d composant(s)" % (len(pw - cw), len(pc - cc), len(cw - pw), len(cc - pc))
        b.append("<tr><td><a href='%s.html'>%s</a> <i>(TP3, pas encore de prédiction d'écran)</i></td><td>%d</td><td>%d</td><td>%s</td></tr>" % (E(m["id"]), E(m["titre"]), len(m["fils"]), len(m["composants"]), E(txt)))
    b.append("</table><p class='note'>Les alimentations, la puce et les fils d'alimentation restent en place d'un montage à l'autre : ne démonte que ce qui est listé.</p></div>")
    b.append("<script>var s=0,h=null;function go(){if(h){clearInterval(h);h=null;return;}h=setInterval(function(){s++;var m=Math.floor(s/60),x=s%60;document.getElementById('t').textContent=(m<10?'0':'')+m+':'+(x<10?'0':'')+x;},1000);}"
             "document.addEventListener('change',function(){document.getElementById('nb').textContent=document.querySelectorAll('.ck:checked').length;});</script>")
    path = out / "seance_30min.html"
    path.write_text(render.page("Séance 30 minutes", "".join(b)), encoding="utf-8")
    return path


def main():
    out = ROOT / "out"
    out.mkdir(exist_ok=True)
    for tp in (2, 1):
        print("écrit", build(tp, out))
    print("écrit", seance(out))
