# -*- coding: utf-8 -*-
"""Page UNIQUE de relecture / validation : TP1, TP2, TP3 (toutes les parties du sujet).
Pour chaque partie : énoncé du sujet, figure du sujet, schéma du montage avec les broches, brochage de la puce,
vue d'ensemble de la table, plaque, écrans / valeurs attendus, tableau de cohérence (modèle / fiche / mesure de la copie),
et un bloc de validation par résultat. Fichier autonome (images intégrées).

Lancer :  /usr/bin/python3 tools/validation_complete.py        ->  out/validation_TP1_TP2_TP3.html
Ne modifie aucune page existante.
"""
import base64
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import render  # noqa: E402
import pages_pred  # noqa: E402
import ttl_ports  # noqa: E402
import predict as P  # noqa: E402

E = render.E
OUT = ROOT / "out" / "validation_TP1_TP2_TP3.html"

TPDIR = ROOT.parent
IMG_DIRS = [
    TPDIR / "Project Entrainement probabiliste pr arriver à rendre TP temps (nxt time) " / "04_CR_v3" / "images",
    TPDIR / "TP perso retouché à envoyer à la prof (pour feedback réaliste)" / "images",
]
MISSING = []

# ---------------------------------------------------------------- hypothèses numériques TP3 (toutes affichées)
VOH_Q, VOL_Q = 3.4, 0.25         # niveaux « typiques » 74LS (hypothèse : la fiche garantit ≥ 2,7 V et ≤ 0,4 V)
TPLH, TPHL = 13e-9, 25e-9        # hardware/behavior.yaml : 74LS74, « guide banc TP3 » (typ)
T_RISE = 8e-9                    # durée d'un front de sortie : hypothèse
VT_PLUS, VT_MINUS = 1.45, 1.25   # milieu des plages MESURÉES de la copie (1,4–1,5 V et 1,2–1,3 V)
Y_HI, Y_LO = 4.15, 0.1           # VOH à vide (4,1–4,2 V) et VOL (≈ 0,1 V) MESURÉS dans la copie


def b64(path):
    return base64.b64encode(Path(path).read_bytes()).decode()


def fig(name, caption, kind="sujet"):
    for d in IMG_DIRS:
        p = d / name
        if p.exists():
            label = {"sujet": "<span class='pill p-sujet'>figure du sujet (image d'origine)</span>",
                     "copie": "<span class='pill p-dedu'>schéma de la copie du TP (non fourni par le sujet)</span>"}[kind]
            return ("<figure style='margin:8px 0'><img src='data:image/png;base64,%s' alt='%s' style='max-width:min(100%%,560px);background:#fff;border:1px solid #ccc;border-radius:8px;padding:6px'>"
                    "<figcaption class='src'>%s %s</figcaption></figure>") % (b64(p), E(caption), label, E(caption))
    MISSING.append(name)
    return "<p class='src'>[image absente : %s]</p>" % E(name)


def neutral(t):
    return (t.replace("tu vois la tension complète", "on voit la tension complète")
             .replace("Ton ancienne photo C (≈ ±12 V) est ce cas.", "Une capture d'écran prise en séance (≈ ±12 V) correspond à ce cas.")
             .replace("Si tu gardes", "Si l'on garde"))


def pill(kind, txt):
    return "<span class='pill p-%s'>%s</span>" % (kind, txt)


PILL = {
    "sujet": lambda t: pill("sujet", t), "gen": lambda t: pill("gen", t), "ds": lambda t: pill("ds", t),
    "dedu": lambda t: pill("dedu", t), "hyp": lambda t: pill("hyp", t), "mes": lambda t: pill("mes", t),
}


def vitem(iid, title, tp):
    n = "r-" + iid
    return ("<div class='valid vi' data-id='%s' data-tp='%s' data-title='%s'><b>Validation — %s</b><br>"
            "<label><input type='radio' name='%s' value='ok'> ✅ Cohérent</label>"
            "<label><input type='radio' name='%s' value='ko'> ❌ Pas cohérent</label>"
            "<label><input type='radio' name='%s' value='q'> ❓ À discuter</label>"
            "<textarea placeholder='Remarque ou correction demandée (schéma, valeur, réglage…)'></textarea></div>") % (
        E(iid), tp, E(title), E(title), n, n, n)


def section(bid, n, title, pills, body, closed=False):
    return "<div class='sec%s' id='%s-s%d'><h3><span class='num'>%d</span>%s %s</h3><div class='body'>%s</div></div>" % (
        " closed" if closed else "", bid, n, n, title, pills, body)


# ---------------------------------------------------------------- vue d'ensemble / plaque
_PH_USED = False


def photo_defs():
    g, s = b64(ROOT / "assets/photos/gbf_ports.jpg"), b64(ROOT / "assets/photos/scope_ports.jpg")
    return ("<svg width='0' height='0' style='position:absolute' aria-hidden='true'><defs>"
            "<image id='ph_gbf' href='data:image/jpeg;base64,%s' width='520' height='390'/>"
            "<image id='ph_scope' href='data:image/jpeg;base64,%s' width='520' height='390'/></defs></svg>") % (g, s)


HW = render.load("hardware/board_wish106.yaml")
GBF_I = render.load("hardware/instruments/gbf.yaml")
SCOPE_I = render.load("hardware/instruments/scope.yaml")


def bench_html(mpath):
    m = render.load_montage(mpath)
    try:
        mm = render.subst(m, {k: v for k, v in render.numbers_of(m).items() if k.startswith("__")})
    except Exception:
        mm = m
    svg = render.bench_svg(mm, HW, GBF_I, SCOPE_I)
    svg = (svg.replace('<image href="../assets/photos/gbf_ports.jpg" x="0" y="0" width="520" height="390"/>', '<use href="#ph_gbf" x="0" y="0"/>')
              .replace('<image href="../assets/photos/scope_ports.jpg" x="0" y="430" width="520" height="390"/>', '<use href="#ph_scope" x="0" y="430"/>'))
    rows = "".join("<tr><td><b>%s</b> — %s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (c["id"], E(c["nom"]), E(c["de"]), E(c["vers"]), E(c["role"])) for c in mm["cables"])
    return (svg + "<table><tr><th>Câble</th><th>De</th><th>Vers</th><th>Rôle</th></tr>%s</table>"
            "<p class='src'>Chaque BNC de la plaque reçoit deux fils (âme et blindage). Les câbles A à E sont ceux du fichier du montage ; "
            "position du T sur la sortie du GBF : à confirmer sur le banc.</p>" % rows)


def plate_html(mpath):
    m = render.load_montage(mpath)
    res, _ = render.validate(m, HW)
    nerr = sum(1 for r in res if r[0] == "ERREUR")
    rows = "".join("<tr><td><b>%s</b></td><td><span class='sw' style='background:%s'></span>%s</td><td>%s → %s</td></tr>" % (
        w["n"], render.WIRE.get(w["couleur"], "#999"), E(w["couleur"]), E(w["de"]), E(w["vers"])) for w in m["fils"])
    st = "<b style='color:#0a6b34'>aucune erreur de câblage détectée</b>" if not nerr else "<b style='color:#a30d0d'>%d ERREUR(S)</b>" % nerr
    return ("<p class='src'>Validateur automatique du câblage : %s</p><div class='row'><div class='plate-dup'>%s</div><div><table><tr><th>N°</th><th>Fil</th><th>De → vers</th></tr>%s</table>"
            "<p class='src'>Placement des trous : proposition « à confirmer sur la plaque ».</p></div></div>") % (st, render.board_svg(m, HW, 520), rows)


# ---------------------------------------------------------------- tableau de cohérence
def coh(rows, note=""):
    cls = {"ok": "v-ok", "ec": "v-ec", "in": "v-in"}
    h = ["<table><tr><th>Grandeur</th><th>Affiché ici (modèle)</th><th>Fiche technique</th><th>Copie du TP (mesuré en séance)</th><th>Verdict</th></tr>"]
    for g, mo, fi, co, ve, c in rows:
        h.append("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td class='%s'>%s</td></tr>" % (g, mo, fi, co, cls[c], ve))
    h.append("</table>")
    if note:
        h.append("<p class='src'>%s</p>" % note)
    return "".join(h)


def block(bid, tp, num, titre, ref, quote, figs, schema, pins, mpath, results, cohe, no_mont_note="", plate_note=""):
    b = ["<article class='blk' id='%s' data-tp='%d'><h2>%s</h2>" % (bid, tp, E(titre))]
    b.append(section(bid, 1, "Ce que demande le sujet", PILL["sujet"](E(ref)),
                     "<div class='quote'>%s</div><p class='src'>Citation du sujet (extraits).</p>" % quote))
    b.append(section(bid, 2, "Le schéma du sujet qui s'applique", "", figs or "<p class='src'>Le sujet ne fournit pas de schéma pour cette partie.</p>"))
    b.append(section(bid, 3, "Schéma du montage", PILL["gen"]("SVG généré"), schema))
    b.append(section(bid, 4, "Branchement des broches de la puce", PILL["ds"]("brochage : fiche technique"), pins or "<p class='src'>Sans objet : pas de circuit intégré dans ce montage.</p>"))
    if mpath:
        b.append(section(bid, 5, "Vue d'ensemble de la table : appareils et câbles", PILL["gen"]("SVG + photos des appareils"), bench_html(mpath)))
        b.append(section(bid, 6, "Câblage sur la plaque Wish Board 106", PILL["gen"]("SVG généré"), plate_html(mpath) + ("<p class='plate-note'><b>Ce que montre la plaque :</b> %s</p>" % plate_note if plate_note else "") + vitem(bid + "-montage", "%s : schéma et câblage" % titre, tp)))
    else:
        b.append(section(bid, 5, "Vue d'ensemble de la table", "", "<p>%s</p>" % (no_mont_note or "Aucune plaque dans cette partie.")))
        b.append(section(bid, 6, "Câblage sur la plaque Wish Board 106", "", "<p class='src'>Sans objet.</p>"))
    b.append(section(bid, 7, "Résultats attendus à l'écran / valeurs", PILL["gen"]("calculé, non mesuré"), "".join(results)))
    b.append(section(bid, 8, "Cohérence des valeurs : d'où vient chaque chiffre ?", "", cohe + vitem(bid + "-coh", "%s : cohérence des valeurs" % titre, tp)))
    b.append("</article>")
    return "".join(b)


# ---------------------------------------------------------------- TP1 / TP2 : écrans calculés (existants)
PRED = {1: render.load("predictions/tp1.yaml"), 2: render.load("predictions/tp2.yaml")}
CIRC = {c["id"]: (tp, c) for tp in (1, 2) for c in PRED[tp]["circuits"]}


def run_vals(cid, sid):
    tp, c = CIRC[cid]
    sc = [s for s in c["scenarios"] if s["id"] == sid][0]
    tl, glob = PRED[tp]["tl081"], PRED[tp]["globaux"]
    shown, tdiv, vals = P.run(c, sc, tl, glob)
    return pages_pred.extra_vals(c, sc, vals, tl)


def scen_card(bid, cid, sc):
    tp, circ = CIRC[cid]
    tl, glob = PRED[tp]["tl081"], PRED[tp]["globaux"]
    shown, tdiv, vals = P.run(circ, sc, tl, glob)
    cfg = pages_pred.build_cfg(circ, sc, shown, tdiv)
    vals = pages_pred.extra_vals(circ, sc, vals, tl)
    gb, ot = pages_pred.settings_text(circ, sc, cfg)
    rows = [("Ve (entrée)", "%.3f Vpp" % vals["vpp_in"]), ("Sortie observée", "%.3f Vpp" % vals["vpp_out"]), ("Rapport", "%.4g" % vals["gain"])]
    if vals["phase"] == vals["phase"]:
        rows.append(("Déphasage sortie / entrée", "%.1f°" % vals["phase"]))
    rows += cfg["extra"]
    h = ["<div class='card' style='background:transparent'><h4 style='margin:0 0 4px'>%s</h4><p class='src'>%s<br>%s</p>" % (E(sc["titre"]), E(gb), E(ot))]
    h.append("<div class='row'><div style='max-width:760px'>%s</div><div><table>%s</table>" % (
        render.scope_svg(cfg, "%s%s" % (bid.replace("-", ""), sc["id"])), "".join("<tr><td>%s</td><td><b>%s</b></td></tr>" % (E(a), E(c)) for a, c in rows)))
    h.append("<p><b>Attendu :</b> %s</p>" % E(neutral(pages_pred.fmt_text(sc["attendu"], vals))))
    if sc.get("artefact"):
        h.append("<p style='border-left:4px solid #d6246e;padding-left:10px'><b>Artefact / piège :</b> %s</p>" % E(neutral(pages_pred.fmt_text(sc["artefact"], vals))))
    h.append("</div></div>")
    h.append(vitem("%s-%s" % (bid, sc["id"]), sc["titre"], tp))
    h.append("</div>")
    return "".join(h)


def results_of(bid, cid):
    tp, circ = CIRC[cid]
    out = [pages_pred.bode_table(circ, PRED[tp]["tl081"])]
    for sc in circ["scenarios"]:
        out.append(scen_sub_v1gbf(bid) if (cid == "tp2-D-soustracteur" and sc["id"] == "v1_continu") else scen_card(bid, cid, sc))
    return out


def schema_of(cid):
    tp, circ = CIRC[cid]
    nb = pages_pred.divider_nb(circ) if circ["type"] == "divider" else None
    return pages_pred.schema_svg(circ, nb)




def scen_sub_v1gbf(bid):
    """Soustracteur : la plaque met le GBF sur V1 (entrée −, voie 1) et le continu de l'alimentation sur V2 (entrée +)."""
    f, tdiv = 1000.0, 200e-6
    v1 = sampl(lambda t: 0.5 * math.sin(2 * math.pi * f * t), tdiv)
    vs = [1.0 - x for x in v1]
    cfg = {"tdiv": tdiv, "panel": pages_pred.PANEL, "trig": {"src": 1, "level": "0.00V"},
           "ch1": {"samples": v1, "scale": 0.5, "offset": -1.0}, "ch2": {"samples": vs, "scale": 0.5, "offset": 2.0},
           "bottom": [{"l": "Moy - PE(1):", "v": "0.0mV", "c": "ch1"}, {"l": "Fréq(1):", "v": "1.000kHz", "c": "ch1"}, {"l": "Max(1):", "v": "500mV", "c": "ch1"}, {"l": "Max(2):", "v": "1.50V", "c": "ch2"}]}
    inner = ("<h4 style='margin:0 0 4px'>V1 = sinus 1 Vpp (GBF), V2 = +1 V continu (alimentation, voie 1)</h4>"
             "<p class='src'>GBF : sinus · 1 Vpp · 1 kHz · offset 0 V · High Z (sur R1, V1) · alimentation voie 1 réglée à 1,000 V (sur R3, V2) · oscilloscope : voie 1 = V1 (500 mV/div), voie 2 = Vs (500 mV/div), 200 µs/div.</p>"
             "<div class='row'><div style='max-width:760px'>%s</div><div>%s"
             "<p><b>Attendu :</b> Vs = V2 − V1 = 1 V − V1(t) : un sinus de 1 Vpp <b>inversé</b> (déphasage 180° avec la voie 1), de valeur moyenne <b>+1 V</b>.</p>"
             "<p style='border-left:4px solid #d6246e;padding-left:10px'><b>Écart relevé dans le projet :</b> la page de prédiction « predictions_tp2.html » suppose l'inverse (V1 continu, V2 sinus). "
             "Cette page suit le câblage de la plaque (fichier du montage : V1 = GBF, V2 = alimentation), qui correspond à la figure 4 du sujet.</p></div></div>") % (
        render.scope_svg(cfg, "subv1"), table_html(["Grandeur", "Valeur attendue"], [["V1 (voie 1)", "1,000 Vpp, moyenne 0 V"], ["Vs (voie 2)", "1,000 Vpp, moyenne +1,000 V"], ["Déphasage Vs / V1", "180°"]]))
    return "<div class='card' style='background:transparent'>%s%s</div>" % (inner, vitem("%s-v1_continu" % bid, "V1 = sinus 1 Vpp (GBF), V2 = +1 V continu (alimentation)", 2))


def Q(*parts):
    return " ".join(parts)


# ---------------------------------------------------------------- TP3 : formes d'onde numériques
def ramp(t, t0, tr, v0, v1):
    if t <= t0:
        return v0
    if t >= t0 + tr:
        return v1
    return v0 + (v1 - v0) * (t - t0) / tr


def edge(t, tm, tr, v0, v1):
    return ramp(t, tm - tr / 2.0, tr, v0, v1)


def sampl(fn, tdiv):
    N = 900
    return [fn((i / float(N) * 10 - 5) * tdiv) for i in range(N + 1)]


def dscope(tdiv, ch1, ch2, level, cx=None, cy=None, bottom=None):
    cfg = {"tdiv": tdiv, "panel": pages_pred.PANEL, "trig": {"src": 1, "level": level}, "bottom": bottom or []}
    for n, ch in ((1, ch1), (2, ch2)):
        if ch:
            cfg["ch%d" % n] = {"samples": ch[0], "scale": ch[1], "offset": ch[2]}
    cur = {}
    if cx:
        cur["x"] = cx
    if cy:
        cur["y"] = cy
    if cur:
        cfg["cursors"] = cur
    return cfg


def lvl(v, mid_top):
    """Voie en haut : (offset) tel que la trace de milieu 'mid' soit à +2 div ; mid_top False -> à -2 div."""
    return v


def led(on, colour="#d62424"):
    return "<span style='color:%s;font-size:18px'>%s</span> %s" % (colour if on else "#999", "●" if on else "○", "allumée" if on else "éteinte")


def table_html(head, rows):
    return "<table><tr>%s</tr>%s</table>" % ("".join("<th>%s</th>" % h for h in head), "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % c for c in r) for r in rows))


def tp3_item(iid, title, inner):
    return "<div class='card' style='background:transparent'><h4 style='margin:0 0 4px'>%s</h4>%s%s</div>" % (E(title), inner, vitem(iid, title, 3))



# ---------------------------------------------------------------- AUDIT DU CÂBLAGE : connexions attendues (d'après les figures du sujet)
import subprocess
import netlist as NL

SPEC = {
    "montages/tp1/B1_pont_diviseur.yaml": ("TP1 · B pont diviseur", "tp1-B", {
        "same": [("E : sortie du GBF = voie 1 = haut de R1", ["R1a.a", "gbf.out1", "scope.ch1"]), ("R1 = 8,2 kΩ + 820 Ω en série", ["R1a.b", "R1b.a"]),
                 ("S : milieu du pont = voie 2", ["R1b.b", "R2.a", "scope.ch2"]), ("bas de R2 à la masse", ["R2.b", "TERRE"])],
        "diff": [("E et S sont deux nœuds distincts", ("R1a.a", "R2.a"))]}),
    "montages/tp1/C1_impedance_interne.yaml": ("TP1 · C impédance interne", "tp1-C", {
        "same": [("Rc entre la sortie du GBF (et voie 1) et la masse", ["Rc.a", "gbf.out1", "scope.ch1"]), ("autre borne de Rc à la masse", ["Rc.b", "TERRE"])], "diff": []}),
    "montages/tp1/D1_led.yaml": ("TP1 · D LED", "tp1-D", {
        "same": [("GBF → R de 330 Ω (voie 1 sur le GBF)", ["R.a", "gbf.out1", "scope.ch1"]), ("R → anode de la LED (voie 2)", ["R.b", "LED.anode", "scope.ch2"]), ("cathode de la LED à la masse", ["LED.cathode", "TERRE"])], "diff": []}),
    "montages/tp2/A_suiveur.yaml": ("TP2 · A suiveur", "tp2-A", {
        "same": [("sortie (6) reliée à l'entrée − (2) et à la voie 2", ["U1.2", "U1.6", "scope.ch2"]), ("Ve sur l'entrée + (3) et la voie 1", ["U1.3", "gbf.out1", "scope.ch1"]),
                 ("+15 V sur la broche 7", ["U1.7", "psu.ch2_plus"]), ("−15 V sur la broche 4", ["U1.4", "psu.ch3_moins"]), ("0 V commun (point milieu des deux voies)", ["TERRE", "psu.ch2_moins", "psu.ch3_plus"])],
        "diff": [("+15 V et −15 V sont deux nœuds distincts", ("U1.7", "U1.4")), ("entrée + et sortie distinctes", ("U1.3", "U1.6"))]}),
    "montages/tp2/B1_inverseur.yaml": ("TP2 · B inverseur", "tp2-B1", {
        "same": [("Ve (voie 1) → R1", ["R1.a", "gbf.out1", "scope.ch1"]), ("R1 → entrée − (2) et R2", ["R1.b", "R2.a", "U1.2"]), ("R2 → sortie (6) et voie 2", ["R2.b", "U1.6", "scope.ch2"]),
                 ("entrée + (3) à la masse", ["U1.3", "TERRE"]), ("+15 V sur la broche 7", ["U1.7", "psu.ch2_plus"]), ("−15 V sur la broche 4", ["U1.4", "psu.ch3_moins"]), ("0 V commun", ["TERRE", "psu.ch2_moins", "psu.ch3_plus"])],
        "diff": [("entrée − et sortie distinctes (R2 les sépare)", ("U1.2", "U1.6"))]}),
    "montages/tp2/B2_non_inverseur.yaml": ("TP2 · B non inverseur", "tp2-B2", {
        "same": [("Ve sur l'entrée + (3) et la voie 1", ["U1.3", "gbf.out1", "scope.ch1"]), ("R1 et R2 sur l'entrée − (2)", ["R1.a", "R2.a", "U1.2"]), ("R1 à la masse", ["R1.b", "TERRE"]),
                 ("R2 → sortie (6) et voie 2", ["R2.b", "U1.6", "scope.ch2"]), ("+15 V sur la broche 7", ["U1.7", "psu.ch2_plus"]), ("−15 V sur la broche 4", ["U1.4", "psu.ch3_moins"]), ("0 V commun", ["TERRE", "psu.ch2_moins", "psu.ch3_plus"])],
        "diff": [("entrée − et sortie distinctes", ("U1.2", "U1.6"))]}),
    "montages/tp2/C_association.yaml": ("TP2 · C association", "tp2-C", {
        "same": [("étage 1 (non inverseur) : Ve sur + (3), voie 1", ["U1.3", "gbf.out1", "scope.ch1"]), ("étage 1 : R1 et R2 sur − (2)", ["R1.a", "R2.a", "U1.2"]), ("étage 1 : R1 à la masse", ["R1.b", "TERRE"]),
                 ("sortie de l'étage 1 (broche 6) → R2 et R3", ["R2.b", "R3.a", "U1.6"]), ("étage 2 (inverseur) : R3 → entrée − (2) et R4", ["R3.b", "R4.a", "U2.2"]),
                 ("étage 2 : R4 → sortie (6) et voie 2", ["R4.b", "U2.6", "scope.ch2"]), ("étage 2 : entrée + (3) à la masse", ["U2.3", "TERRE"]),
                 ("les deux puces alimentées en +15 V (7)", ["U1.7", "U2.7", "psu.ch2_plus"]), ("les deux puces alimentées en −15 V (4)", ["U1.4", "U2.4", "psu.ch3_moins"])],
        "diff": [("sortie étage 1 et sortie étage 2 distinctes", ("U1.6", "U2.6"))]}),
    "montages/tp2/D_soustracteur.yaml": ("TP2 · D soustracteur", "tp2-D", {
        "same": [("V1 = GBF (voie 1) → R1", ["R1.a", "gbf.out1", "scope.ch1"]), ("R1 → entrée − (2) et R2", ["R1.b", "R2.a", "U1.2"]), ("R2 → sortie (6) et voie 2", ["R2.b", "U1.6", "scope.ch2"]),
                 ("V2 = continu de l'alimentation (voie 1) → R3", ["R3.a", "psu.ch1_plus"]), ("R3 → entrée + (3) et R4", ["R3.b", "R4.a", "U1.3"]), ("R4 à la masse", ["R4.b", "TERRE"]),
                 ("+15 V sur la broche 7", ["U1.7", "psu.ch2_plus"]), ("−15 V sur la broche 4", ["U1.4", "psu.ch3_moins"])],
        "diff": [("V1 et V2 sont deux nœuds distincts", ("R1.a", "R3.a"))]}),
    "montages/tp3/A_nand.yaml": ("TP3 · A NAND + LED", "tp3-A", {
        "same": [("alimentation +5 V sur la broche 14", ["U1.14", "psu.ch1_plus"]), ("masse sur la broche 7", ["U1.7", "TERRE", "psu.ch1_moins"]), ("entrées 1 et 2 à +5 V (ligne 1,1 : LED éteinte)", ["U1.1", "U1.2", "psu.ch1_plus"]),
                 ("sortie (3) → R de 330 Ω, voie 2", ["U1.3", "R.a", "scope.ch2"]), ("R → anode de la LED", ["R.b", "LED.anode"]), ("cathode de la LED à la masse", ["LED.cathode", "TERRE"])], "diff": []}),
    "montages/tp3/A2_seuils.yaml": ("TP3 · A.2 seuils", "tp3-A2", {
        "same": [("GBF triangle sur l'entrée A (1) et la voie 1", ["U1.1", "gbf.out1", "scope.ch1"]), ("entrée B (2) à +5 V", ["U1.2", "psu.ch1_plus", "U1.14"]), ("sortie Y (3) sur la voie 2", ["U1.3", "scope.ch2"]), ("broche 7 à la masse", ["U1.7", "TERRE", "psu.ch1_moins"])],
        "diff": [("entrée A et sortie Y distinctes", ("U1.1", "U1.3"))]}),
    "montages/tp3/B_bascule_D.yaml": ("TP3 · B bascule D", "tp3-B", {
        "same": [("CLR (1), PRE (4) et VCC (14) à +5 V", ["U1.1", "U1.4", "U1.14", "psu.ch1_plus"]), ("D (2) reliée à Q̄ (6)", ["U1.2", "U1.6"]), ("horloge : SYNC du GBF sur CLK (3) et la voie 1", ["U1.3", "gbf.sync_out", "scope.ch1"]),
                 ("Q (5) → R de 330 Ω et voie 2", ["U1.5", "R.a", "scope.ch2"]), ("R → anode de la LED", ["R.b", "LED.anode"]), ("cathode de la LED, broche 7 : masse", ["LED.cathode", "U1.7", "TERRE"])],
        "diff": [("Q (5) et Q̄ (6) distinctes", ("U1.5", "U1.6"))]}),
    "montages/tp3/C_compteur.yaml": ("TP3 · C compteur", "tp3-C", {
        "same": [("CLR (1, 13), PRE (4, 10) et VCC (14) à +5 V", ["U1.1", "U1.4", "U1.10", "U1.13", "U1.14", "psu.ch1_plus"]), ("Q̄0 (6) → D0 (2) et CLK1 (11)", ["U1.2", "U1.6", "U1.11"]), ("Q̄1 (8) → D1 (12)", ["U1.8", "U1.12"]),
                 ("horloge : SYNC du GBF sur CLK0 (3) et la voie 1", ["U1.3", "gbf.sync_out", "scope.ch1"]), ("Q0 (5) → R0 de 330 Ω et voie 2", ["U1.5", "R0.a", "scope.ch2"]), ("R0 → LED0", ["R0.b", "LED0.anode"]),
                 ("Q1 (9) → R1 de 330 Ω", ["U1.9", "R1.a"]), ("R1 → LED1", ["R1.b", "LED1.anode"]), ("cathodes des LED, broche 7 : masse", ["LED0.cathode", "LED1.cathode", "U1.7", "TERRE"])],
        "diff": [("Q0 et Q1 distinctes", ("U1.5", "U1.9"))]}),
}


def net_roots(path):
    m = render.load_montage(path)
    res, uf = render.validate(m, HW)
    conns = render.conn_geom(HW)
    comps = m["composants"]
    EARTH = ("EARTH",)
    uf.f(EARTH)
    Pk = lambda e: ("PORT", e)
    for cb in m.get("cables", []):
        a, b = cb["de"], cb["vers"]
        if NL.is_dev(a) and NL.is_dev(b):
            uf.u(Pk(a), Pk(b))
        else:
            dev, con = (a, b) if NL.is_dev(a) else (b, a)
            if con in conns and conns[con]["c"]["type"] == "bnc":
                uf.u(Pk(dev), ("J", con + ".core"))
                uf.u(("J", con + ".shield"), EARTH)
            elif con in conns:
                uf.u(Pk(dev), ("J", con + ".main"))

    def root(tok):
        if tok == "TERRE":
            return uf.f(EARTH)
        if tok.split(".")[0] in NL.DEV:
            return uf.f(Pk(tok))
        name, leg = tok.split(".")
        c = comps[name]
        if c.get("type") == "chip":
            return uf.f(render.key(tok, comps))
        return uf.f(render.key(c[{"a": "a", "b": "b", "anode": "a", "cathode": "k"}[leg]], comps))
    return m, res, root


def audit():
    out = []
    for path, (label, bid, spec) in SPEC.items():
        m, res, root = net_roots(path)
        nerr = sum(1 for r in res if r[0] == "ERREUR")
        checks = []
        for desc, toks in spec["same"]:
            try:
                ok = len(set(root(t) for t in toks)) == 1
            except Exception as e:
                ok = False
            checks.append((desc, ok))
        for desc, (a, b) in spec["diff"]:
            try:
                ok = root(a) != root(b)
            except Exception:
                ok = False
            checks.append((desc, ok))
        out.append({"label": label, "bid": bid, "path": path, "fils": len(m["fils"]), "comps": len(m["composants"]), "nerr": nerr, "checks": checks})
    return out


def run_check_netlist():
    try:
        r = subprocess.run(["/usr/bin/python3", str(ROOT / "tools" / "check_netlist.py")], capture_output=True, text=True, timeout=120, cwd=str(ROOT))
        last = [l for l in r.stdout.strip().splitlines() if l.strip()][-1] if r.stdout.strip() else "(aucune sortie)"
        return r.returncode, last
    except Exception as e:
        return -1, "contrôle non exécuté : %s" % e


def audit_card(aud):
    rc, last = run_check_netlist()
    rows = []
    tot_ok = tot = 0
    for a in aud:
        ok = sum(1 for _, o in a["checks"] if o)
        tot_ok += ok
        tot += len(a["checks"])
        bad = [d for d, o in a["checks"] if not o]
        det = "".join("<li>%s %s</li>" % ("✅" if o else "❌", E(d)) for d, o in a["checks"])
        rows.append("<tr><td><a href='#%s'>%s</a></td><td>%d</td><td>%d</td><td>%s</td><td class='%s'>%d / %d</td><td><details><summary>voir</summary><ul>%s</ul></details></td></tr>" % (
            a["bid"], E(a["label"]), a["fils"], a["comps"], "aucune erreur" if not a["nerr"] else "<b>%d ERREUR(S)</b>" % a["nerr"], "v-ok" if not bad and not a["nerr"] else "v-ec", ok, len(a["checks"]), det))
    head = ("<div class='card'><b>Index des montages et contrôle automatique du câblage</b>"
            "<p class='src'>Les 12 montages de la plaque Wish Board 106 (TP1 : 3, TP2 : 5, TP3 : 4) sont listés ci-dessous, avec un contrôle automatique : pour chaque montage, les connexions électriques attendues d'après les figures du sujet "
            "(par exemple « sortie reliée à l'entrée − » pour le suiveur) sont recherchées dans le câblage réel. Le TP1 partie A n'a pas de plaque (câble BNC direct).</p>"
            "<table><tr><th>Montage</th><th>Fils</th><th>Composants</th><th>Validateur d'adresses</th><th>Connexions attendues</th><th>Détail</th></tr>%s</table>"
            "<p><b>Total : %d / %d connexions attendues trouvées.</b></p>"
            "<p class='src'>Contrôle électrique des montages analogiques (<code>tools/check_netlist.py</code> : le câblage est converti en circuit puis comparé aux formules, 14 points) : <b>%s</b>. "
            "Les montages TP3 (logique) ne sont pas simulés par ce contrôle. Positions exactes des trous : « à confirmer sur la plaque ».</p></div>") % ("".join(rows), tot_ok, tot, E(last))
    return head, tot_ok, tot


# ================================================================ CONSTRUCTION DES BLOCS
def build_tp1():
    blocks = []
    # ---- A
    v50 = run_vals("tp1-A1-gbf-direct", "cinquante")
    blocks.append(block(
        "tp1-A", 1, "A", "TP1 · A. Utilisation de l'oscilloscope et du GBF", "Sujet TP1, p. 2, § A",
        "Générez un signal sinusoïdal de 2 Vpp avec une fréquence de 1 kHz. Brancher directement la sortie du GBF à l'oscilloscope. ➤ Est-ce que la touche « autoset » fonctionne ? "
        "Réglez « à la main » l'oscilloscope. ➤ Utilisez les fonctions mesures de l'oscilloscope pour mesurer la fréquence et l'amplitude du signal. Est-ce que les valeurs concordent avec ce qui est affiché sur le GBF ? "
        "➤ Réglez le GBF pour lui indiquer l'impédance du circuit, c'est-à-dire celle de l'oscilloscope (grande impédance = « high Z »). Est-ce que les mesures et ce qu'annonce le GBF concordent ?",
        fig("tp1_sch_gbf_oscillo.png", "Branchement direct de la sortie du GBF sur la voie 1 de l'oscilloscope.", "copie"),
        schema_of("tp1-A1-gbf-direct") if False else "<p>Un câble coaxial BNC–BNC relie la sortie principale du GBF (impédance de sortie 50 Ω) à la voie 1 de l'oscilloscope (1 MΩ ∥ 16 pF). Aucun composant.</p>",
        None, None, results_of("tp1-A", "tp1-A1-gbf-direct"),
        coh([
            ("Amplitude lue, GBF en « High Z »", "2,00 Vpp", "—", "≈ 2 Vpp à 500 mV/div (incertitude de lecture ± 0,05 V, soit 2,5 %)", "Cohérent : l'oscillo (1 MΩ) ne charge pas la sortie 50 Ω.", "ok"),
            ("Amplitude lue, GBF resté en « 50 Ω »", "%.2f Vpp (le double)" % v50["vpp_in"], "—", "4 Vpp « attendu » : écrit en préparation, non mesuré en séance", "Prédiction seulement : à confirmer par une mesure.", "in"),
            ("Touche Autoset", "—", "—", "non testée (l'annexe la déconseille)", "Sans objet pour la validation.", "in"),
        ], "La copie note : fréquence 1 kHz et amplitude ≈ 2 Vpp lues à l'oscilloscope, en accord avec l'afficheur du GBF à la précision de lecture près."),
        no_mont_note="Aucune plaque : un câble BNC relie directement la sortie du GBF à la voie 1 de l'oscilloscope. Pas de tableau de câbles pour cette partie."))
    # ---- B
    vb = run_vals("tp1-B-pont-diviseur", "nominal")
    blocks.append(block(
        "tp1-B", 1, "B", "TP1 · B. Pont diviseur de tension par 10", "Sujet TP1, p. 2–3, § B",
        "Réalisez le montage de la figure 1. Pour la source de tension d'entrée UE, utilisez le GBF avec un signal sinusoïdal de 2 Vpp, sans offset et une fréquence de 1 kHz. "
        "➤ Observez la tension de sortie Us à l'oscilloscope. Obtenez-vous bien 0.2 V ? ➤ Notez l'écart relatif entre la valeur théorique Vth et la valeur mesurée Vm. "
        "En gardant le même montage, vous allez maintenant étudier les limites de l'oscilloscope et du multimètre : mesurez la tension de sortie, pour les deux appareils, en faisant varier la forme du signal et la fréquence, en augmentant jusqu'à 10 MHz.",
        fig("tp1_fig1_pont_diviseur.png", "Figure 1 du sujet : montage « à vide » du pont diviseur de tension."),
        schema_of("tp1-B-pont-diviseur"), None, "montages/tp1/B1_pont_diviseur.yaml", results_of("tp1-B", "tp1-B-pont-diviseur"),
        coh([
            ("Us à 1 kHz, à vide", "%.3f Vpp (rapport %.4f)" % (vb["vpp_out"], vb["gain"]), "—", "≈ 0,20 Vpp (calibre non noté)", "Cohérent : dans la plage [0,167 ; 0,239] V calculée avec les tolérances E12 (± 10 %).", "ok"),
            ("Résistances", "8,2 kΩ + 820 Ω = 9,02 kΩ et 1 kΩ", "série E12", "2,2 kΩ + 6,8 kΩ = 9,0 kΩ et 1,0 kΩ (non mesurées au pont RLC)", "Rapport quasi identique (0,0998 contre 0,1000) : sans effet sur l'écran.", "ok"),
            ("Charge de 1 kΩ sur la sortie", "non modélisé dans cet écran", "—", "calcul : Us ≈ 0,105 Vpp (presque divisé par 2)", "À discuter : cas théorique de la copie, sans écran associé.", "ec"),
            ("Limites HF (jusqu'à 10 MHz), multimètre", "écrans à 1 MHz et 10 MHz (capacité de charge ≈ 116 pF : hypothèse)", "—", "discussion qualitative, pas de relevé chiffré", "Hypothèse de capacité non vérifiée : l'écart avec le banc n'est pas chiffré.", "ec"),
        ]),
    ))
    # ---- C
    Rc = [463, 530, 606, 217, 390, 1000, 1470, 1800]
    Um = [2.05, 2.17, 4.10, 3.38, 3.66, 3.94, 4.14, 4.02]
    rows = []
    for r, u in zip(Rc, Um):
        th = 4.0 * r / (50.0 + r)
        e = (u - th) / th * 100
        rows.append(("Rc = %d Ω" % r, "%.2f Vpp" % th, "—", "%.2f V" % u, "écart %+.0f %%" % e + (" : incohérent (la copie le signale)" if abs(e) > 20 else (" : Uc > E, lecture impossible" if u > 4.0 else "")), "ec" if abs(e) > 5 else "ok"))
    blocks.append(block(
        "tp1-C", 1, "C", "TP1 · C. Impédance interne du GBF", "Sujet TP1, p. 3–4, § C",
        "Réglez le GBF en « high Z » pour qu'il ne compense pas sa résistance interne. La tension qu'il affiche est alors la tension E. Prenez E = 4 Vpp (sinusoïdal, 1 kHz). "
        "➤ Exprimez UC en fonction de E, Rint et RC. ➤ Tracez UC en fonction de RC. ➤ D'après la relation théorique, que vaut RC lorsque UC = E/2 ? Trouvez ce point sur la courbe obtenue et déduisez-en la résistance interne du GBF.",
        fig("tp1_fig2_gbf_rint.png", "Figure 2 du sujet : schéma électrique équivalent d'un GBF branché à une résistance."),
        schema_of("tp1-C-impedance-interne"), None, "montages/tp1/C1_impedance_interne.yaml", results_of("tp1-C", "tp1-C-impedance-interne"),
        plate_note="Rc = 47 Ω (une seule résistance). Les autres valeurs de Rc (10 Ω, 1 kΩ…) s'obtiennent en remplaçant cette seule résistance ; le reste du câblage ne change pas.",
        cohe=
        coh(rows, "Modèle : Uc = E · Rc / (Rint + Rc) avec E = 4 Vpp et Rint = 50 Ω. La copie conclut elle-même que ses relevés « ne permettent pas de conclure proprement » : les deux premiers points valent environ la moitié du modèle (réglage d'amplitude probablement différent), trois valeurs dépassent E = 4 V. "
                "Rint déduit dans la copie : ≈ 21,66 Ω (écart de 57 % avec les 50 Ω du GBF). Aucune des résistances prises n'est proche de 50 Ω, donc le point Uc = E/2 n'est pas visible : ces mesures ne valident pas le modèle, elles ne le contredisent pas non plus."),
    ))
    # ---- D
    blocks.append(block(
        "tp1-D", 1, "D", "TP1 · D. LED", "Sujet TP1, p. 4, § D",
        "Qu'est-ce qu'une LED ? Quel est le symbole d'une diode et d'une LED ? ➤ Proposez un schéma simple utilisant une LED et le câbler. Mettre sous tension en choisissant comme signal d'entrée un signal carré de 1 Hz. "
        "➤ Augmentez progressivement la fréquence en observant la LED. Quelle observation faites-vous au-delà d'une certaine fréquence ? Trouvez une explication.",
        "",
        fig("tp1_sch_led.png", "Circuit de commande d'une LED rouge avec sa résistance de protection, alimenté par le GBF en signal carré.", "copie"),
        None, "montages/tp1/D1_led.yaml", results_of("tp1-D", "tp1-D-led"),
        coh([
            ("Résistance de protection", "330 Ω (E12)", "VD ≈ 1,8 V, ID ≈ 10 mA (LED rouge)", "R = (5,0 − 1,8)/0,010 = 320 Ω → 330 Ω ; I ≈ 9,7 mA", "Cohérent.", "ok"),
            ("Fréquence de 1 Hz", "LED clignote", "—", "clignotement net", "Cohérent.", "ok"),
            ("Fréquence où le clignotement disparaît", "« paraît allumée en continu » à 1 kHz", "—", "25 à 30 Hz presque continue ; ≥ 50 Hz lumière continue", "Cohérent : persistance rétinienne ≈ 40 ms.", "ok"),
        ], "Observation à l'œil : l'écran de l'oscilloscope ne montre pas la luminosité, seulement la tension aux bornes de la LED."),
    ))
    return blocks


def pins_tl081(use_by, notes=""):
    out = []
    for lab, use in use_by:
        out.append("<div class='row'><div>%s</div><div><p><b>%s</b></p>%s</div></div>" % (ttl_ports.dip_svg("TL081", use), lab, ttl_ports.pin_table("TL081", use, only_used=True)))
    return "".join(out) + "<p class='src'>Brochage du TL081 : même numérotation que la Figure 1 du sujet (broches 1 et 5 : réglage d'offset ; broche 8 : non connectée). %s</p>" % notes


def build_tp2():
    blocks = []
    tl = PRED[2]["tl081"]
    fig1 = fig("tp2_fig1_brochage_aop.png", "Figure 1 du sujet : schéma du brochage d'un amplificateur opérationnel.")
    # ---- A
    use_a = {2: ("entree", "fil vers la broche 6 (contre-réaction)"), 3: ("entree", "Ve (GBF) et voie 1 de l'oscillo"), 4: ("alim", "−15 V"),
             6: ("sortie", "Vs : voie 2 et broche 2"), 7: ("alim", "+15 V")}
    va = run_vals("tp2-A-suiveur", "nominal")
    blocks.append(block(
        "tp2-A", 2, "A", "TP2 · A. Montage « Suiveur »", "Sujet TP2, p. 1–2, § A",
        "Câblez le montage suiveur avec un AOP TL081 (alimentation stabilisée en +15 V / −15 V). Reliez l'entrée Ve à un signal provenant d'un G.B.F. (sinus, réglage 5 Vpp, 0 VDC, fréquence = 1 kHz). "
        "Validez le montage en mesurant Vs/Ve et en comparant avec le résultat attendu (écart relatif). Effectuez une campagne de mesure pour déterminer quelles sont les limites du montage : en balayant les valeurs de fréquence sur Ve ; en utilisant un signal créneau à haute fréquence pour Ve.",
        fig("tp2_fig2_suiveur.png", "Figure 2 du sujet : schéma électrique du montage suiveur.") + fig1,
        schema_of("tp2-A-suiveur"), pins_tl081([("Suiveur", use_a)]), "montages/tp2/A_suiveur.yaml", results_of("tp2-A", "tp2-A-suiveur"),
        coh([
            ("Gain Vs/Ve à 1 kHz", "%.2f" % va["gain"], "gain unitaire", "Ve = Vs = 5,23 V → G = 1,00 (écart 0 %)", "Cohérent.", "ok"),
            ("Saturation de la sortie", "± %.1f V" % tl["vsat"], "± 12 V min, ± 13,5 V typ (alim ± 15 V, RL = 10 kΩ)", "≈ 13,5 V (valeur de la préparation, pas de capture)", "À discuter : le modèle retient 12,5 V, entre le minimum et le typique de la fiche.", "ec"),
            ("Vitesse de montée (slew rate)", "%g V/µs (valeur typique de la fiche)" % tl["slew_vus"], "13 V/µs typique", "≈ 5,5 V/µs, noté « 5,5 / 1 » sans ΔV ni Δt", "Écart d'un facteur 2,4 : à discuter. La copie ne conserve pas les valeurs qui permettent de recalculer.", "ec"),
        ], "Les trois captures d'écran de la copie (figures 3 à 5) ne correspondent pas toutes au suiveur à gain 1 (calibres différents sur les deux voies) : elles ne sont donc pas utilisées comme référence ici."),
    ))
    # ---- B1 inverseur
    use_i = {2: ("entree", "R1 (depuis Ve) et R2 (depuis la sortie)"), 3: ("entree", "masse (0 V)"), 4: ("alim", "−15 V"),
             6: ("sortie", "Vs : R2 et voie 2"), 7: ("alim", "+15 V")}
    fci = P.fc_of(CIRC["tp2-B1-inverseur"][1], tl)
    blocks.append(block(
        "tp2-B1", 2, "B1", "TP2 · B. Amplificateur « Inverseur » (gain −20)", "Sujet TP2, p. 2, § B",
        "Choisissez des résistances vous permettant d'avoir un gain statique égal à −20 pour l'amplificateur inverseur. Réalisez le montage (figure 3). Validez le montage en comparant Ve et Vs. "
        "Indiquez votre choix pour l'amplitude et la fréquence de Ve (et pourquoi). Augmentez la fréquence : à quelle fréquence le rapport Vs/Ve est-il divisé par √2 ? Cherchez le GBP dans les données « constructeur ». Mesurez le déphasage entre Vs et Ve à la fréquence de coupure.",
        fig("tp2_fig3_inverseur_non_inverseur.png", "Figure 3 du sujet : amplificateur inverseur (gauche) et non inverseur (droite)."),
        schema_of("tp2-B1-inverseur"), pins_tl081([("Inverseur", use_i)]), "montages/tp2/B1_inverseur.yaml", results_of("tp2-B1", "tp2-B1-inverseur"),
        coh([
            ("Gain statique", "−20", "—", "inverseur non réalisé en séance (manque de temps)", "Aucune mesure de comparaison.", "in"),
            ("Résistances", "R1 = 1 kΩ, R2 = 20 kΩ", "—", "préparation : R1 = 10 kΩ, R2 = 200 kΩ (non E12 : 2 × 100 kΩ)", "Même rapport (−20) : mêmes écrans attendus ; seule la charge sur la source change.", "ok"),
            ("Fréquence de coupure", "≈ %.0f kHz (GBP %g MHz)" % (fci / 1e3, tl["gbw_hz"] / 1e6), "GBP ≈ 3 MHz → ≈ 143 kHz pour G = 21", "non mesurée", "Non vérifiable par la copie.", "in"),
        ]),
    ))
    # ---- B2 non inverseur
    use_n = {2: ("entree", "R1 (vers la masse) et R2 (depuis la sortie)"), 3: ("entree", "Ve (GBF) et voie 1 de l'oscillo"), 4: ("alim", "−15 V"),
             6: ("sortie", "Vs : R2 et voie 2"), 7: ("alim", "+15 V")}
    fcn = P.fc_of(CIRC["tp2-B2-non-inverseur"][1], tl)
    blocks.append(block(
        "tp2-B2", 2, "B2", "TP2 · B. Amplificateur « Non inverseur » (gain +10)", "Sujet TP2, p. 2, § B",
        "Choisissez des résistances vous permettant d'avoir un gain statique égal à +10 pour l'amplificateur non inverseur. Réalisez le montage (figure 3). Validez le montage en comparant Ve et Vs. "
        "Augmentez la fréquence (en visualisant Ve et Vs) : à quelle fréquence le rapport Vs/Ve est-il divisé par √2 ? Cherchez le GBP dans les données « constructeur ». Est-ce cohérent avec vos mesures ? Mesurez le déphasage entre Vs et Ve à la fréquence de coupure.",
        fig("tp2_fig3_inverseur_non_inverseur.png", "Figure 3 du sujet : amplificateur inverseur (gauche) et non inverseur (droite)."),
        schema_of("tp2-B2-non-inverseur"), pins_tl081([("Non inverseur", use_n)]), "montages/tp2/B2_non_inverseur.yaml", results_of("tp2-B2", "tp2-B2-non-inverseur"),
        coh([
            ("Gain statique", "+10 (R1 = 1 kΩ, R2 = 9,1 kΩ → 10,1)", "—", "R1 = 1 kΩ, R2 = 9 kΩ (2,2 + 6,8 kΩ) ; Ve = 2,5 V, sortie dans la zone linéaire", "Cohérent (écart sur R2 : 1 %).", "ok"),
            ("Fréquence de coupure fc", "≈ %.0f kHz (GBP %g MHz)" % (fcn / 1e3, tl["gbw_hz"] / 1e6), "GBP ≈ 3 MHz (valeur lue par la copie) → fc ≈ 300 kHz", "fc = 230 kHz", "Écart de 42 % avec le modèle, de 23 % avec la fiche lue par la copie : à discuter.", "ec"),
            ("Produit gain-bande", "%g MHz" % (tl["gbw_hz"] / 1e6), "≈ 3 MHz", "2,3 MHz (= 10 × 230 kHz)", "Écart de 23 % avec la fiche (calculé dans la copie) ; le modèle garde la valeur la plus haute : à discuter.", "ec"),
            ("Déphasage à fc", "− 45° (premier ordre)", "—", "− 55°", "Écart de 22 % (calculé dans la copie) ; incertitude de lecture non chiffrée.", "ec"),
        ], "La copie n'a noté ni le calibre de l'oscilloscope ni la fréquence de départ pour ces lectures : aucune incertitude n'est chiffrée."),
    ))
    # ---- C association
    use_c1 = {2: ("entree", "R1 (vers la masse) et R2 (depuis la sortie de la puce A)"), 3: ("entree", "Ve (GBF) et voie 1"), 4: ("alim", "−15 V"), 6: ("sortie", "V1 : entrée de la puce B"), 7: ("alim", "+15 V")}
    use_c2 = {2: ("entree", "R3 (depuis V1) et R4 (depuis la sortie)"), 3: ("entree", "masse (0 V)"), 4: ("alim", "−15 V"), 6: ("sortie", "Vs : R4 et voie 2"), 7: ("alim", "+15 V")}
    fcc = P.fc_of(CIRC["tp2-C-association"][1], tl)
    blocks.append(block(
        "tp2-C", 2, "C", "TP2 · C. Association de deux montages à base d'AOP", "Sujet TP2, p. 3, § C",
        "Associez un montage amplificateur non inverseur et un montage amplificateur inverseur, de sorte que la sortie d'un montage serve d'entrée à l'autre montage. "
        "➤ Déterminez les valeurs théoriques du gain et de la fréquence de coupure du montage ainsi câblé. Vérifiez le gain et la fréquence de coupure par des mesures expérimentales.",
        fig("tp2_fig3_inverseur_non_inverseur.png", "Figure 3 du sujet (les deux étages à associer)."),
        schema_of("tp2-C-association"), pins_tl081([("Puce A : non inverseur (étage 1)", use_c1), ("Puce B : inverseur (étage 2)", use_c2)]),
        "montages/tp2/C_association.yaml", results_of("tp2-C", "tp2-C-association"),
        plate_note="La plaque pose la voie 2 sur Vs (broche 6 de la puce B). Pour afficher V1, la sortie de l'étage 1, déplacer la sonde sur la broche 6 de la puce A. Étage 1 = R1, R2 (non inverseur) ; étage 2 = R3, R4 (inverseur).",
        cohe=coh([
            ("Gain total", "≈ −202 (10,1 × −20)", "produit des gains", "théorie de la copie : (+10) × (−20) = −200", "Cohérent (écart de 1 % dû à R2 = 9,1 kΩ).", "ok"),
            ("Fréquence de coupure", "≈ %.0f kHz" % (fcc / 1e3), "inférieure à celle de chaque étage", "non réalisé", "Aucune mesure de comparaison.", "in"),
        ], "La copie indique : « par manque de temps, cette partie n'a pas été réalisée ». Les écrans de cette partie sont donc des prévisions seules."),
    ))
    # ---- D soustracteur
    use_d = {2: ("entree", "R1 (depuis V1 = GBF) et R2 (depuis la sortie)"), 3: ("entree", "R3 (depuis V2 = continu de l'alim) et R4 (vers la masse)"), 4: ("alim", "−15 V"), 6: ("sortie", "Vs : voie 2"), 7: ("alim", "+15 V")}
    blocks.append(block(
        "tp2-D", 2, "D", "TP2 · D. Montage « soustracteur » (bonus)", "Sujet TP2, p. 3, § D",
        "Déterminez l'expression de Vs en fonction de V1 et V2 et choisissez la valeur des résistances (une seule valeur). ➤ Câblez le montage et comparez la valeur théorique calculée avec la valeur expérimentale mesurée. "
        "➤ Appliquez une tension identique en V1 et V2. Qu'observez-vous en VS ? Cela correspond-il à la valeur théorique ?",
        fig("tp2_fig4_soustracteur.png", "Figure 4 du sujet : schéma électrique du montage soustracteur à base d'AOP."),
        schema_of("tp2-D-soustracteur"), pins_tl081([("Soustracteur", use_d)]), "montages/tp2/D_soustracteur.yaml", results_of("tp2-D", "tp2-D-soustracteur"),
        plate_note="V1 = sortie du GBF (BNC 1, voie 1) sur R1, du côté de l'entrée − ; V2 = tension continue de la voie 1 de l'alimentation (réglée vers 1 V) sur R3, du côté de l'entrée +. Pour le test V1 = V2, relier les deux entrées au même signal du GBF.",
        cohe=coh([
            ("Expression de Vs", "Vs = V2 − V1 (4 résistances égales)", "—", "même expression (préparation)", "Cohérent.", "ok"),
            ("V1 = V2", "résidu non nul avec tolérances ± 5 % (pire cas)", "—", "attendu 0 V ; non réalisé en séance", "Aucune mesure de comparaison.", "in"),
        ], "La copie indique : « par manque de temps, cette partie n'a pas été réalisée »."),
    ))
    return blocks


def build_tp3():
    blocks = []
    nand_fig = fig("tp3_fig1_porte_nand.png", "Figure 1 du sujet : schéma logique d'une porte Non-Et (NAND).")
    # ---- A : table de vérité + tensions
    tv = table_html(["1A", "1B", "LED", "Y mesurée (copie)", "Y = NON(A·B) attendue"],
                    [["0", "0", led(True), "1", "1"], ["0", "1", led(True), "1", "1"], ["1", "0", led(True), "1", "1"], ["1", "1", led(False), "0", "0"]])
    it_tv = tp3_item("tp3-A-table", "A · table de vérité de la porte NAND", tv + "<p class='src'>LED allumée quand Y = 1, éteinte quand Y = 0. Valeurs mesurées : copie du TP.</p>")
    tens = table_html(["Grandeur", "À vide", "Avec LED + 330 Ω", "Limite fiche 74LS"],
                      [["V<sub>OH</sub>", "4,1 à 4,2 V " + PILL["mes"]("mesuré"), "2,9 à 3,0 V " + PILL["mes"]("mesuré"), "≥ 2,7 V"],
                       ["V<sub>OL</sub>", "≈ 0,1 V " + PILL["mes"]("mesuré"), "≈ 0,2 V " + PILL["mes"]("mesuré"), "≤ 0,4 V"]])
    it_t = tp3_item("tp3-A-tensions", "A.1 · tensions de sortie (niveau haut et niveau bas)",
                    tens + "<p>V<sub>OH</sub> baisse en charge parce que la LED tire du courant : I = (2,9 − 1,8)/330 ≈ 3,3 mA (calcul de la copie, V<sub>D</sub> ≈ 1,8 V pour la LED rouge). "
                    "Dans les deux cas V<sub>OH</sub> reste au-dessus de 2,7 V et V<sub>OL</sub> sous 0,4 V : la porte respecte les niveaux TTL.</p>")
    blocks.append(block(
        "tp3-A", 3, "A", "TP3 · A. Porte logique Non-Et : table de vérité et tensions de sortie", "Sujet TP3, p. 1, § A et A.1",
        "Câblez sur votre Labdec une des portes Non-Et d'une puce 74LS00. Les entrées seront reliées à la ligne 0 V pour un 0 logique et à la ligne 5 V pour 1 logique. Le composant est un composant actif : il faut donc l'alimenter : 0 V à broche « GND » et 5 V à la broche « Vcc ». "
        "Pour observer la tension en sortie, on l'utilisera comme source de tension pour allumer une LED (quelle précaution prendre ?). ➤ Testez que son fonctionnement logique correspond bien à la table de vérité d'une porte Non-Et, en testant chacune des combinaisons. "
        "1. Tensions de sortie ➤ Mesurez la tension de sortie du niveau haut et du niveau bas, avec la LED puis à vide (sans rien branché en sortie). Qu'en déduisez-vous ?",
        nand_fig + fig("tp3_sch_nand_led.png", "Porte NAND 1 du 74LS00 avec LED rouge et résistance de 330 Ω (chaque fil porte son numéro de broche).", "copie"),
        ttl_ports.nand_schema("led"),
        "<div class='row'><div>%s</div><div>%s</div></div>" % (ttl_ports.dip_svg("74LS00", ttl_ports.USE_74LS00_A), ttl_ports.pin_table("74LS00", ttl_ports.USE_74LS00_A, only_used=True)),
        "montages/tp3/A_nand.yaml", [it_tv, it_t],
        plate_note="L'état A = B = +5 V (broches 1 et 2 au +5 V : LED éteinte). Pour les trois autres lignes de la table de vérité, déplacer les fils des broches 1 et 2 entre +5 V et 0 V. Pour la mesure à vide, retirer la résistance et la LED de la broche 3.",
        cohe=coh([
            ("Table de vérité", "NAND : Y = 0 seulement si A = B = 1", "74LS00", "4 lignes conformes", "Cohérent.", "ok"),
            ("V<sub>OH</sub> à vide", "4,15 V (milieu de la plage mesurée)", "≥ 2,7 V", "4,1 à 4,2 V", "Cohérent.", "ok"),
            ("V<sub>OH</sub> avec LED", "2,95 V (milieu de la plage mesurée)", "≥ 2,7 V", "2,9 à 3,0 V", "Cohérent avec la fiche. L'inventaire des manipulations donnait 2,4 à 2,8 V : écart avec la mesure.", "ec"),
            ("V<sub>OL</sub>", "0,1 V / 0,2 V", "≤ 0,4 V", "≈ 0,1 V / ≈ 0,2 V", "Cohérent.", "ok"),
        ], "Les valeurs de cette partie sont celles de la copie (mesurées), pas des valeurs de fiche : la page n'invente aucun chiffre ici."),
    ))
    # ---- A2 : seuils
    tdiv = 200e-6

    def tri(t):
        x = 1000.0 * t + 0.25
        x -= math.floor(x)
        return 5.0 * (1 - abs(2 * x - 1))
    vin = sampl(tri, tdiv)
    y, vy = True, []
    for v in vin:
        if v > VT_PLUS:
            y = False
        elif v < VT_MINUS:
            y = True
        vy.append(Y_HI if y else Y_LO)
    sc1, sc2 = 2.0, 2.0
    off1, off2 = 2.5 - 2 * sc1, 2.075 + 2 * sc2
    cfg = dscope(tdiv, (vin, sc1, off1), (vy, sc2, off2), "2.50V", cy=[(VT_PLUS - off1) / sc1, (VT_MINUS - off1) / sc1],
                 bottom=[{"l": "Fréq(1):", "v": "1.00kHz", "c": "ch1"}, {"l": "Max(1):", "v": "5.00V", "c": "ch1"}, {"l": "Max(2):", "v": "%.2fV" % Y_HI, "c": "ch2"}, {"l": "VT+ / VT− (curseurs):", "v": "1.45V / 1.25V", "c": "x"}])
    it_s = tp3_item("tp3-A2-seuils", "A.2 · tension de basculement (triangle 0–5 V sur A, B à +5 V)",
                    "<p class='src'>GBF : triangle, 5 Vpp, offset +2,5 V, 1 kHz, High Z · oscilloscope : voie 1 = entrée A, voie 2 = sortie Y, 200 µs/div, 2 V/div.</p>"
                    "<div class='row'><div style='max-width:760px'>%s</div><div>%s"
                    "<p><b>Comment lire :</b> la sortie Y (verte) est l'inverse de l'entrée (jaune) ; elle bascule quand le triangle franchit les deux lignes pointillées orange (VT+ en montée, VT− en descente).</p>"
                    "<p class='src'>Seuils : milieu des plages mesurées dans la copie. La copie n'a pas noté le calibre : pas d'incertitude chiffrée, et pas d'affirmation d'une vraie hystérésis.</p></div></div>" % (
                        render.scope_svg(cfg, "a2seuils"),
                        table_html(["Grandeur", "Valeur", "Origine"], [
                            ["Tension sur l'autre entrée (B)", "+5 V", "réponse du sujet : la NAND devient un inverseur"],
                            ["VT+ (bas → haut en entrée)", "1,4 à 1,5 V", PILL["mes"]("mesuré (copie)")],
                            ["VT− (haut → bas en entrée)", "1,2 à 1,3 V", PILL["mes"]("mesuré (copie)")]])))
    blocks.append(block(
        "tp3-A2", 3, "A2", "TP3 · A.2 Tensions d'entrée de basculement", "Sujet TP3, p. 2, § A.2",
        "Lorsqu'on passe de manière continue d'une tension 0 V à 5 V, la tension de basculement de niveau bas vers haut est la tension au-delà de laquelle l'entrée est interprétée comme un 1 logique. "
        "Pour faire varier la tension de manière continue, on peut brancher sur une des deux entrées de la porte NAND un signal triangulaire variant entre 0 V et 5 V, avec une symétrie de 50 %. "
        "➤ Quelle tension continue faut-il mettre sur l'autre entrée pour que la sortie alterne entre 0 V et 5 V ? Tracez le chronogramme des 2 entrées et de la sortie. ➤ Réalisez le montage et affichez à l'oscilloscope le signal du GBF et la sortie. "
        "➤ Mesurez la tension de basculement de niveau bas vers haut et celle de basculement de niveau haut vers bas.",
        nand_fig, ttl_ports.nand_schema("seuils"),
        "<div class='row'><div>%s</div><div>%s</div></div>" % (ttl_ports.dip_svg("74LS00", ttl_ports.USE_74LS00_A2), ttl_ports.pin_table("74LS00", ttl_ports.USE_74LS00_A2, only_used=True)),
        "montages/tp3/A2_seuils.yaml", [it_s],
        coh([
            ("VT+ (bas → haut)", "1,45 V (milieu de la plage mesurée)", "≈ 1,7 V (selon le fichier du montage, « datasheet »)", "1,4 à 1,5 V", "Écart avec la fiche (≈ 0,25 V) : à discuter.", "ec"),
            ("VT− (haut → bas)", "1,25 V (milieu de la plage mesurée)", "≈ 0,9 V (idem)", "1,2 à 1,3 V", "Écart avec la fiche (≈ 0,35 V) : à discuter.", "ec"),
            ("Zone d'indétermination", "—", "[0,8 V ; 2,0 V] (VIL max, VIH min)", "seuils dans cette zone", "Cohérent.", "ok"),
            ("Inventaire des manipulations", "—", "—", "1,3 à 1,5 V", "Proche de la mesure de la copie.", "ok"),
        ], "Le modèle de cette partie utilise les valeurs mesurées de la copie, pas celles de la fiche. Les valeurs de la fiche (≈ 1,7 V / 0,9 V) sont celles écrites dans le fichier du montage, non revérifiées sur la datasheet."),
    ))
    # ---- B : bascule D
    tvb = table_html(["PRE", "CLR", "D", "Événement sur CLK", "Q", "Q̄", "Conclusion"], [
        ["0", "1", "X", "quelconque", "1", "0", "forçage à 1, sans attendre l'horloge"],
        ["1", "0", "X", "quelconque", "0", "1", "forçage à 0, sans attendre l'horloge"],
        ["1", "1", "0", "front montant", "0", "1", "mémorise 0"],
        ["1", "1", "1", "front montant", "1", "0", "mémorise 1"],
        ["1", "1", "X", "niveau constant ou front descendant", "Qp", "Q̄p", "aucun changement"]])
    it_bt = tp3_item("tp3-B-table", "B · table de vérité de la bascule D (LED verte sur Q, LED rouge sur Q̄)",
                     tvb + "<p class='src'>Horloge : SYNC du GBF à basse fréquence (quelques Hz) pour voir les LED changer d'état. Valeurs : copie du TP.</p>")
    it_bv = tp3_item("tp3-B-tensions", "B.1 · tensions de sortie de la bascule (niveau haut et niveau bas)",
                     table_html(["Grandeur", "Valeur attendue", "Origine"], [
                         ["V<sub>OH</sub>", "≥ 2,7 V (typique 3,4 V)", PILL["ds"]("fiche 74LS") + " " + PILL["hyp"]("typique non mesuré")],
                         ["V<sub>OL</sub>", "≤ 0,4 V (typique 0,25 V)", PILL["ds"]("fiche 74LS") + " " + PILL["hyp"]("typique non mesuré")]])
                     + "<p class='src'>La copie indique : « les niveaux de sortie de la bascule et le temps de propagation n'ont pas été relevés, par manque de temps ». Ces valeurs sont donc des valeurs de fiche, sans mesure.</p>")

    def scope_tpd(rising):
        tdv = 5e-9 if rising else 10e-9
        tp_ = TPLH if rising else TPHL
        clk = sampl(lambda t: edge(t, 0.0, 5e-9, 0.0, 5.0), tdv)
        q = sampl(lambda t: edge(t, tp_, T_RISE, VOL_Q, VOH_Q) if rising else edge(t, tp_, T_RISE, VOH_Q, VOL_Q), tdv)
        sc = 2.0
        c = dscope(tdv, (clk, sc, 2.5 - 2 * sc), (q, sc, (VOL_Q + VOH_Q) / 2 + 2 * sc), "2.50V", cx=[0.0, tp_ / tdv],
                   bottom=[{"l": "Fréq(1):", "v": "100kHz", "c": "ch1"}, {"l": "Max(1):", "v": "5.00V", "c": "ch1"}, {"l": "Max(2):", "v": "%.2fV" % VOH_Q, "c": "ch2"},
                           {"l": "ΔX (curseurs):", "v": "%.0fns" % (tp_ * 1e9), "c": "x"}])
        name = "tPLH" if rising else "tPHL"
        return tp3_item("tp3-B-tpd-%s" % ("up" if rising else "down"), "B.2 · retard de propagation, front %s de Q (%s)" % ("montant" if rising else "descendant", name),
                        "<p class='src'>D reliée à Q̄ · GBF : SYNC TTL 100 kHz · voie 1 = CLK, voie 2 = Q · %s · déclenchement voie 1 (front montant).</p>"
                        "<div class='row'><div style='max-width:760px'>%s</div><div>%s"
                        "<p><b>Comment lire :</b> les deux lignes pointillées orange sont les curseurs : le premier sur le front de CLK, le second sur le front de Q ; leur écart est le retard de propagation.</p>"
                        "<p class='src'>Valeurs : fiche 74LS74 (typiques, « guide banc TP3 »). Durées des fronts (5 ns pour CLK, 8 ns pour Q) et niveaux de Q : hypothèses du modèle. La copie n'a pas mesuré ce retard.</p></div></div>" % (
                            "5 ns/div" if rising else "10 ns/div", render.scope_svg(c, "tpd%s" % ("u" if rising else "d")),
                            table_html(["Grandeur", "Valeur"], [["Retard CLK ↑ → Q %s" % ("↑" if rising else "↓"), "<b>%.0f ns</b> (%s typique)" % (tp_ * 1e9, name)], ["Maximum fiche", "%s ns" % ("25" if rising else "40")]])))
    blocks.append(block(
        "tp3-B", 3, "B", "TP3 · B. Bascule D : table de vérité, tensions de sortie, retard de propagation", "Sujet TP3, p. 2–3, § B, B.1 et B.2",
        "Câblez sur votre Labdec une des bascules D d'une puce 74LS74. Pour l'horloge, on prendra la sortie SYNC du GBF. Mis à part les broches d'alimentation, les broches sont à un niveau haut par défaut (si elles ne sont pas connectées). "
        "➤ Vérifiez que son fonctionnement logique correspond bien à sa table de vérité, en testant chacune des lignes. Utilisez des LED pour observer les sorties. Quelle condition a-t-on alors sur la fréquence utilisée ? "
        "1. Tensions de sortie ➤ Mesurez la tension de sortie du niveau haut et du niveau bas. 2. Retard de propagation : la sortie de la bascule D est « mise à jour » à chaque front montant de l'horloge. Mais cela ne se produit pas de manière instantanée : il y a un retard de propagation. ➤ Mesurez le retard de propagation.",
        fig("tp3_fig2_bascule_d.png", "Figure 2 du sujet : schéma logique d'une bascule D (gauche) et sa table de vérité (droite)."),
        ttl_ports.bascule_d_schema() + "<p class='src'>Schéma du retard de propagation (B.2) : D est reliée à Q̄ pour que Q change à chaque front montant ; ce câblage n'est pas imposé par le sujet (déduit). Pour la table de vérité (B), D est reliée à 0 V ou +5 V et Q, Q̄ vont chacune à une LED avec 330 Ω.</p>",
        "<div class='row'><div>%s</div><div><p><b>Tests de la table de vérité (B)</b></p>%s<p><b>Retard de propagation (B.2)</b></p>%s</div></div>" % (
            ttl_ports.dip_svg("74LS74", ttl_ports.USE_74LS74_B0), ttl_ports.pin_table("74LS74", ttl_ports.USE_74LS74_B0, only_used=True), ttl_ports.pin_table("74LS74", ttl_ports.USE_74LS74_B2, only_used=True)),
        "montages/tp3/B_bascule_D.yaml", [it_bt, it_bv, scope_tpd(True), scope_tpd(False)],
        plate_note="Le montage du retard de propagation (B.2) : D (2) reliée à Q̄ (6), une seule LED sur Q (5), voie 1 sur l'horloge et voie 2 sur Q. Pour la table de vérité (B) : retirer le fil entre les broches 2 et 6, relier D à 0 V ou +5 V, ajouter une LED avec 330 Ω sur Q̄ (6) ; pour tester le forçage, mettre PRE (4) puis CLR (1) à 0 V.",
        cohe=coh([
            ("Table de vérité (5 lignes)", "voir le tableau", "74LS74", "5 lignes testées et conformes ; au début la sortie restait figée tant que PRE et CLR n'étaient pas reliées au +5 V", "Cohérent.", "ok"),
            ("V<sub>OH</sub>, V<sub>OL</sub> de la bascule", "≥ 2,7 V / ≤ 0,4 V", "74LS", "non relevés", "Aucune mesure de comparaison.", "in"),
            ("tPLH (Q monte)", "13 ns", "typ 13 ns, max 25 ns", "non relevé", "Valeur de fiche seulement. L'inventaire des manipulations indiquait 15 à 25 ns : plage plus large, cohérente avec le max de la fiche.", "ec"),
            ("tPHL (Q descend)", "25 ns", "typ 25 ns, max 40 ns", "non relevé", "Le retard n'est pas le même sur les deux fronts ; valeur de fiche seulement.", "ec"),
        ], "Les valeurs 13 / 25 / 40 ns viennent du fichier de paramètres du projet (« vérifié », source : guide du banc TP3), pas d'une mesure."),
    ))
    # ---- C : compteur
    tdc = 100e-6
    cnt = lambda t: (math.floor(t / 100e-6) + 1) % 4
    q0 = sampl(lambda t: VOH_Q if cnt(t) & 1 else VOL_Q, tdc)
    q1 = sampl(lambda t: VOH_Q if cnt(t) >> 1 else VOL_Q, tdc)
    sc = 2.0
    mid = (VOL_Q + VOH_Q) / 2
    cfg_c = dscope(tdc, (q0, sc, mid - 2 * sc), (q1, sc, mid + 2 * sc), "1.80V",
                   bottom=[{"l": "Fréq(1):", "v": "5.00kHz", "c": "ch1"}, {"l": "Fréq(2):", "v": "2.50kHz", "c": "ch2"}, {"l": "Max(1):", "v": "%.2fV" % VOH_Q, "c": "ch1"}, {"l": "Max(2):", "v": "%.2fV" % VOH_Q, "c": "ch2"}])
    tdz = 20e-9
    q0z = sampl(lambda t: edge(t, 0.0, T_RISE, VOH_Q, VOL_Q), tdz)
    q1z = sampl(lambda t: edge(t, TPLH, T_RISE, VOH_Q, VOL_Q) if False else edge(t, 13e-9, T_RISE, VOH_Q, VOL_Q), tdz)
    cfg_z = dscope(tdz, (q0z, sc, mid - 2 * sc), (q1z, sc, mid + 2 * sc), "1.80V", cx=[0.0, 13e-9 / tdz],
                   bottom=[{"l": "Voie 1:", "v": "Q0", "c": "ch1"}, {"l": "Voie 2:", "v": "Q1", "c": "ch2"}, {"l": "Max(1):", "v": "%.2fV" % VOH_Q, "c": "ch1"}, {"l": "ΔX (curseurs):", "v": "13ns", "c": "x"}])
    seq = table_html(["Coup d'horloge", "Q1", "Q0", "Mot Q1Q0", "Valeur décimale"], [
        ["0 (initial)", "0", "0", "00", "0"], ["1", "0", "1", "01", "1"], ["2", "1", "0", "10", "2"], ["3", "1", "1", "11", "3"], ["4", "0", "0", "00", "0"]])
    it_c1 = tp3_item("tp3-C-sequence", "C · séquence de comptage (LED sur Q0 et Q1, quelques Hz)", seq + "<p class='src'>Q1 est le bit de poids fort, Q0 le bit de poids faible. Séquence relevée dans la copie : 0 → 1 → 2 → 3 → 0 (compteur binaire modulo 4).</p>")
    it_c2 = tp3_item("tp3-C-chrono", "C · chronogrammes de Q0 et Q1 (horloge 10 kHz)",
                     "<p class='src'>Horloge TTL 10 kHz · sondes déplacées par rapport à la plaque : voie 1 = Q0 (broche 5), voie 2 = Q1 (broche 9) · 100 µs/div, 2 V/div, déclenchement voie 1.</p><div class='row'><div style='max-width:760px'>%s</div><div>%s"
                     "<p><b>Comment lire :</b> Q0 change à chaque front montant de l'horloge (f/2) ; Q1 change quand Q0 retombe (f/4).</p>"
                     "<p class='src'>Calculé à partir du comptage 0→3 ; niveaux de sortie : hypothèse typique 74LS. La copie n'a pas conservé de capture des chronogrammes.</p></div></div>" % (
                         render.scope_svg(cfg_c, "cchr"), table_html(["Grandeur", "Valeur"], [["f(horloge)", "10 kHz"], ["f(Q0) = f/2", "5 kHz"], ["f(Q1) = f/4", "2,5 kHz"]])))
    it_c3 = tp3_item("tp3-C-async", "C · zoom sur les fronts descendants au passage 3 → 0 (20 ns/div) : synchrone ou asynchrone ?",
                     "<p class='src'>Voie 1 = Q0, voie 2 = Q1 · 20 ns/div · l'origine est placée sur le front descendant de Q0.</p><div class='row'><div style='max-width:760px'>%s</div><div>%s"
                     "<p><b>Comment lire :</b> Q1 retombe après Q0 (écart ≈ 13 ns entre les deux curseurs) : la bascule 2 est commandée par la sortie Q̄0 de la bascule 1, pas par l'horloge. Le montage est donc <b>asynchrone</b>, "
                     "et le compteur passe un très court instant par l'état parasite 10 (soit 2), comme l'écrit la copie.</p>"
                     "<p class='src'>Calculé : Q0 retombe tPHL (25 ns) après l'horloge ; Q̄0 monte tPLH (13 ns) après l'horloge, puis Q1 retombe tPHL (25 ns) après ce front, soit 13 ns après Q0. Valeurs typiques de la fiche ; non mesuré dans la copie.</p></div></div>" % (
                         render.scope_svg(cfg_z, "casy"), table_html(["Grandeur", "Valeur"], [["Q0 ↓ après l'horloge", "25 ns (tPHL)"], ["Q1 ↓ après Q0", "≈ 13 ns"]])))
    it_c4 = tp3_item("tp3-C-bonus", "C · bonus : montage de droite (compteur synchrone)",
                     "<p>Non réalisé en séance (la copie : « on n'a pas réalisé ce montage ») et pas de câblage dans le projet. La figure ci-dessus (Figure 3 du sujet, montage de droite) en donne le schéma. "
                     "Principe : les deux bascules reçoivent la même horloge ; la porte logique calcule D1 à partir de Q0 et Q1, donc les deux bits changent au même instant (pas de retard cumulé).</p>")
    blocks.append(block(
        "tp3-C", 3, "C", "TP3 · C. Compteurs : compteur binaire 2 bits (montage de gauche)", "Sujet TP3, p. 3, § C",
        "En utilisant des bascules D, on peut réaliser un compteur binaire (figure 3). ➤ Réalisez le montage de gauche de la figure 3. ➤ Relevez ensuite les chronogrammes des sorties Q0 et Q1 en utilisant l'oscilloscope. "
        "➤ Comment interpréter les sorties Q0 et Q1 pour obtenir un compteur binaire à 2 bits ? ➤ Vérifier le bon fonctionnement de celui-ci via un montage avec des LEDs en sortie. "
        "➤ Zoomez sur les 2 fronts descendants des sorties, le montage est-il synchrone ou asynchrone ? ➤ Bonus : faites les mêmes questions pour le montage de droite de la figure 3.",
        fig("tp3_fig3_compteurs.png", "Figure 3 du sujet : schéma logique de deux compteurs réalisés avec des bascules D (gauche : réalisé ; droite : bonus)."),
        ttl_ports.compteur_schema(),
        "<div class='row'><div>%s</div><div>%s</div></div>" % (ttl_ports.dip_svg("74LS74", ttl_ports.USE_74LS74_C), ttl_ports.pin_table("74LS74", ttl_ports.USE_74LS74_C, only_used=True)),
        "montages/tp3/C_compteur.yaml", [it_c1, it_c2, it_c3, it_c4],
        plate_note="Le montage de gauche de la figure 3, avec une LED sur Q0 et une sur Q1 (suivi du comptage à quelques Hz). Les sondes y sont : voie 1 sur l'horloge (broche 3), voie 2 sur Q0 (broche 5). Pour relever les chronogrammes de Q0 et Q1 demandés par le sujet, déplacer la voie 1 sur Q0 (broche 5) et la voie 2 sur Q1 (broche 9).",
        cohe=coh([
            ("Séquence de comptage", "0 → 1 → 2 → 3 → 0", "—", "0 → 1 → 2 → 3 → 0 (LED)", "Cohérent.", "ok"),
            ("Fréquences", "f(Q0) = f/2, f(Q1) = f/4", "—", "« chaque bascule divise la fréquence par 2 » (écrit, sans capture)", "Cohérent, mais sans mesure chiffrée.", "ok"),
            ("Décalage Q0 / Q1 au passage 3 → 0", "≈ 13 ns (calculé)", "tPHL typ 25 ns, tPLH typ 13 ns", "« Q0 tombe d'abord, puis Q1 un peu après » ; non mesuré en ns", "Cohérent qualitativement ; valeur chiffrée issue de la fiche seulement.", "ec"),
            ("État parasite 10 au passage 3 → 0", "visible pendant ≈ 13 ns", "—", "mentionné dans la copie", "Cohérent.", "ok"),
        ], "La copie : « on n'a pas mesuré ce décalage en nanosecondes, et on n'a pas gardé de capture des chronogrammes »."),
    ))
    return blocks


# ================================================================ PAGE
CSS_EXTRA = """
<style>
:root{--ok:#e6f7ec;--ec:#fff0c9;--in:#e8eefc}
.crumb{font-size:13px;color:var(--mut)}
.nav{position:sticky;top:0;z-index:5;background:var(--card);border-bottom:1px solid var(--line);padding:8px 0;display:flex;gap:6px;flex-wrap:wrap;align-items:center;font-size:14px}
.nav a,.nav span.b{padding:4px 10px;border-radius:6px;border:1px solid var(--line);text-decoration:none;color:var(--ac)}
.tools{margin-left:auto;display:flex;gap:6px;flex-wrap:wrap}.tools button{border:1px solid var(--line);background:var(--card);color:var(--ac);border-radius:6px;padding:4px 10px;font:inherit;cursor:pointer}
.blk{border:1px solid var(--line);border-radius:12px;padding:6px 16px 16px;margin:22px 0;background:var(--card)}
.blk>h2{cursor:pointer;user-select:none;margin:10px 0}.blk>h2::after{content:' ▾';color:var(--mut);font-weight:400}.blk.closed>h2::after{content:' ▸'}.blk.closed>.sec{display:none}
.sec{border-left:5px solid var(--ac);padding-left:12px;margin:16px 0}.sec>h3{margin:0 0 6px;font-size:15px;cursor:pointer;user-select:none}
.sec>h3::after{content:' ▾';color:var(--mut);font-weight:400}.sec.closed>h3::after{content:' ▸'}.sec.closed>.body{display:none}
.num{display:inline-block;width:22px;height:22px;border-radius:50%;background:var(--ac);color:#fff;text-align:center;font:700 13px/22px Arial;margin-right:6px}
.quote{background:#fff8e1;color:#222;border:1px solid #f0d98a;border-radius:8px;padding:10px 14px;font-style:italic}
.src{font-size:12.5px;color:var(--mut)}.pill{display:inline-block;border-radius:10px;padding:1px 9px;font-size:12px;font-weight:700;margin-right:4px}
.p-sujet{background:#dbe8ff;color:#0b3d91}.p-gen{background:#e6e0ff;color:#4a2a9e}.p-ds{background:#d9f7e4;color:#0a6b34}.p-dedu{background:#fff0c9;color:#8a5a00}.p-hyp{background:#fde0e0;color:#a30d0d}.p-mes{background:#d4f0f7;color:#0b5566}
.v-ok{background:var(--ok);color:#222}.v-ec{background:var(--ec);color:#222}.v-in{background:var(--in);color:#222}
.valid{border:2px solid var(--ac);border-radius:12px;padding:10px 14px;margin-top:12px}
.valid label{margin-right:18px;font-weight:700;cursor:pointer}.valid textarea{width:100%;min-height:54px;margin-top:8px;border:1px solid var(--line);border-radius:6px;padding:6px;font:inherit;background:var(--card);color:var(--fg)}
.valid.st-ok{border-color:#1f9d3a}.valid.st-ko{border-color:#d62424}.valid.st-q{border-color:#e0a000}
.bar{height:10px;border-radius:5px;background:var(--line);overflow:hidden;display:flex}.bar i{display:block;height:100%}
.legend span{margin-right:10px}
h4{font-size:15px}
.printonly{display:none;background:#fff8e1;color:#222;border:1px solid #f0d98a;border-radius:8px;padding:8px 12px;margin:8px 0}
@media print{.plate-dup{display:none}h2[id^=tp]{break-before:page}.blk{break-before:page}h2[id^=tp]+.blk{break-before:auto}.valid,figure,tr,.quote{break-inside:avoid}.printonly{display:block!important}h2,h3,h4{break-after:avoid}.nav,.tools{display:none}.sec.closed>.body,.blk.closed>.sec{display:block!important}.valid textarea{border:1px solid #999}}
</style>"""

JS = """<script>(function(){
var K='labdec-validation-v1';
function ld(){try{return JSON.parse(localStorage.getItem(K)||'{}')}catch(e){return {}}}
function sv(o){try{localStorage.setItem(K,JSON.stringify(o))}catch(e){}}
var S=ld();
document.querySelectorAll('.sec>h3').forEach(function(h){h.onclick=function(){h.parentNode.classList.toggle('closed')}});
document.querySelectorAll('.blk>h2').forEach(function(h){h.onclick=function(){h.parentNode.classList.toggle('closed')}});
window.tg=function(c){document.querySelectorAll('.sec,.blk').forEach(function(s){s.classList.toggle('closed',c)})};
var items=[].slice.call(document.querySelectorAll('.vi'));
function part(e){return e.closest('.blk').querySelector('h2').textContent.trim()}
function paint(el){var id=el.dataset.id,st=(S[id]||{}).v||'';el.classList.remove('st-ok','st-ko','st-q');if(st)el.classList.add('st-'+st);}
items.forEach(function(el){var id=el.dataset.id,d=S[id]||{};
 el.querySelectorAll('input[type=radio]').forEach(function(r){if(d.v===r.value)r.checked=true;r.onchange=function(){S[id]=S[id]||{};S[id].v=r.value;sv(S);paint(el);up()}});
 var ta=el.querySelector('textarea');ta.value=d.n||'';ta.oninput=function(){S[id]=S[id]||{};S[id].n=ta.value;sv(S)};paint(el)});
function cnt(tp){var a=items.filter(function(e){return !tp||e.dataset.tp==tp}),c={ok:0,ko:0,q:0,n:0,t:a.length};a.forEach(function(e){var v=(S[e.dataset.id]||{}).v;if(v)c[v]++;else c.n++});return c}
function up(){[0,1,2,3].forEach(function(tp){var c=cnt(tp),el=document.getElementById('p'+tp);if(!el)return;
 el.querySelector('.t').textContent=(tp?'TP'+tp:'Total')+' : '+(c.ok+c.ko+c.q)+' / '+c.t+' vus — ✅ '+c.ok+' · ❌ '+c.ko+' · ❓ '+c.q;
 el.querySelector('.bar').innerHTML='<i style="width:'+c.ok/c.t*100+'%;background:#1f9d3a"></i><i style="width:'+c.q/c.t*100+'%;background:#e0a000"></i><i style="width:'+c.ko/c.t*100+'%;background:#d62424"></i>'});
 var c=cnt(0);var n=document.getElementById('navcnt');if(n)n.textContent=(c.ok+c.ko+c.q)+' / '+c.t;
 var l=document.getElementById('tofix');if(l){l.innerHTML=items.filter(function(e){var v=(S[e.dataset.id]||{}).v;return v==='ko'||v==='q'}).map(function(e){var v=S[e.dataset.id].v;return '<li>'+(v==='ko'?'❌':'❓')+' <a href="#'+e.closest('.blk').id+'">'+part(e)+' — '+e.dataset.title+'</a></li>'}).join('')||'<li class="src">Aucun pour l\\'instant.</li>'}}
function report(){var c=cnt(0),L=['VALIDATION — TP1, TP2, TP3 (ISIFC 1A, Électronique 1)','Export du '+new Date().toLocaleString('fr-FR'),'Résumé : '+c.ok+' cohérents · '+c.ko+' pas cohérents · '+c.q+' à discuter · '+c.n+' non vus (total '+c.t+')',''];
 items.forEach(function(e){var d=S[e.dataset.id]||{},st={ok:'COHÉRENT',ko:'PAS COHÉRENT',q:'À DISCUTER'}[d.v]||'NON VU';L.push('['+part(e)+'] '+e.dataset.title+' : '+st);if(d.n&&d.n.trim())L.push('    Remarque : '+d.n.trim().replace(/\\n/g,'\\n               '))});return L.join('\\n')}
window.exportTxt=function(){var b=new Blob([report()],{type:'text/plain;charset=utf-8'}),a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='validation_TP1_TP2_TP3.txt';document.body.appendChild(a);a.click();a.remove()};
window.copyTxt=function(){var t=report();if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(t).then(function(){alert('Résumé copié : à coller dans un e-mail.')},function(){prompt('Copiez ce texte :',t)})}else{prompt('Copiez ce texte :',t)}};
window.resetAll=function(){if(confirm('Effacer tous les états et remarques de ce navigateur ?')){try{localStorage.removeItem(K)}catch(e){}location.reload()}};
up();})();</script>"""


def page():
    b1, b2, b3 = build_tp1(), build_tp2(), build_tp3()
    allb = b1 + b2 + b3
    toc = []
    for tp, bl in ((1, b1), (2, b2), (3, b3)):
        links = "".join("<a href='#%s' class='b' style='margin-right:8px'>%s</a>" % (x.split("id='")[1].split("'")[0], x.split("<h2>")[1].split("</h2>")[0]) for x in bl)
        toc.append("<p><b>TP%d</b> : %s</p>" % (tp, links))
    prog = "".join("<div id='p%d' style='margin:6px 0'><span class='t'></span><div class='bar'></div></div>" % i for i in (0, 1, 2, 3))
    head = ("<h1>Validation des schémas et des résultats attendus — TP1, TP2, TP3</h1>"
            "<p class='sub'>ISIFC 1A · Électronique 1. Pour chaque partie du sujet : l'énoncé, le schéma du sujet, le schéma du montage avec les broches, la vue d'ensemble de la table, "
            "l'écran attendu et les valeurs, puis un bloc de validation. Cliquer sur un titre replie ou déplie la section.</p>"
            "<p class='printonly'><b>Version PDF :</b> lecture et impression. Pour cocher et exporter les remarques, utiliser le fichier HTML joint ; sinon, noter les remarques sur le papier ou dans le courriel de réponse en citant le titre de la partie.</p>")
    howto = ("<div class='card'><b>Comment relire</b><ol>"
             "<li>Pour chaque partie, lire l'énoncé (①), regarder le schéma du sujet (②) puis le montage et les broches (③ à ⑥).</li>"
             "<li>Comparer l'écran ou les valeurs attendus (⑦) avec le tableau de cohérence (⑧) : chaque chiffre est étiqueté (sujet, fiche, mesure de la copie, calculé, hypothèse).</li>"
             "<li>Cocher ✅ cohérent, ❌ pas cohérent ou ❓ à discuter dans chaque cadre « Validation », avec une remarque si besoin.</li>"
             "<li>Cliquer sur « Exporter les remarques » : un fichier texte est téléchargé (ou « Copier » pour le coller dans un e-mail).</li></ol>"
             "<p class='legend'>Étiquettes : %s %s %s %s %s %s</p>"
             "<p class='src'><b>Limite importante :</b> les écrans d'oscilloscope sont <b>calculés</b> par un modèle (GBF 50 Ω de sortie, oscilloscope 1 MΩ ∥ 16 pF, TL081 à un pôle, TTL typique). Ce ne sont pas des captures. "
             "Les valeurs « mesurées » proviennent de la copie du TP ; lorsque la copie n'a pas relevé une grandeur, la page l'écrit.</p></div>") % (
        PILL["sujet"]("sujet"), PILL["gen"]("généré"), PILL["ds"]("fiche technique"), PILL["mes"]("mesuré (copie)"), PILL["dedu"]("déduit"), PILL["hyp"]("hypothèse du modèle"))
    summary = "<div class='card'><b>Avancement de la relecture</b>%s<p><b>À corriger ou discuter :</b></p><ul id='tofix'></ul></div>" % prog
    nav = ("<div class='nav'><b>Aller à :</b> <a href='#tp1'>TP1</a><a href='#tp2'>TP2</a><a href='#tp3'>TP3</a>"
           "<span class='tools'><button onclick='tg(true)'>Tout replier</button><button onclick='tg(false)'>Tout déplier</button>"
           "<button onclick='exportTxt()'>Exporter les remarques</button><button onclick='copyTxt()'>Copier</button><button onclick='resetAll()'>Réinitialiser</button></span>"
           "<span class='src'>Vus : <b id='navcnt'>0</b></span></div>")
    aud_card, aok, atot = audit_card(audit())
    print("audit câblage : %d / %d connexions attendues trouvées" % (aok, atot))
    body = [photo_defs(), CSS_EXTRA, nav, head, howto, summary, "<div class='card'><b>Sommaire</b>%s</div>" % "".join(toc), aud_card]
    for tp, bl in ((1, b1), (2, b2), (3, b3)):
        body.append("<h2 id='tp%d' style='margin-top:30px;font-size:22px'>TP%d — %s</h2>" % (tp, tp, {1: "Découverte de l'appareillage de mesure", 2: "Amplificateur opérationnel (TL081)", 3: "Électronique numérique (74LS00 et 74LS74)"}[tp]))
        body.extend(bl)
    body.append("<div class='card'><b>Fin du document.</b> Pensez à « Exporter les remarques » avant de fermer la page.</div>")
    body.append(JS)
    html = "".join(body)
    for a, b in [
        ("L'inventaire des manipulations donnait", "Un document de préparation donnait"),
        ("L'inventaire des manipulations indiquait", "Un document de préparation indiquait"),
        ("Inventaire des manipulations", "Document de préparation"),
        ("selon le fichier du montage, « datasheet »", "valeur de préparation attribuée à la fiche"),
        ("sont celles écrites dans le fichier du montage, non revérifiées sur la datasheet", "sont des valeurs de préparation, non revérifiées sur la datasheet"),
        ("fichier de paramètres du projet", "paramètres de simulation"),
        ("Cette page suit le câblage de la plaque (fichier du montage : V1 = GBF, V2 = alimentation)", "Cette page suit le câblage de la plaque (V1 = GBF, V2 = alimentation)"),
        ("la page de prédiction « predictions_tp2.html » suppose l'inverse", "un premier jeu de prédictions suppose l'inverse"),
        ("Écart relevé dans le projet :", "Écart relevé lors de la vérification :"),
        ("sont ceux du fichier du montage", "sont ceux du montage"),
    ]:
        html = html.replace(a, b)
    return render.page("Validation TP1 TP2 TP3", html)


if __name__ == "__main__":
    html = page()
    OUT.write_text(html, encoding="utf-8")
    print("écrit", OUT, "—", len(html) // 1024, "Ko")
    if MISSING:
        print("IMAGES ABSENTES :", sorted(set(MISSING)))
