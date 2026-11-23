# -*- coding: utf-8 -*-
"""Page complète d'un montage : table, schéma, plaque, ordre de câblage, différences, réglages des appareils."""
import render as R
import bench

E = R.E


def comp_id(name, c):
    if c.get("type") == "chip":
        return "%s %s (broche 1 en %s, encoche %s)" % (name, c["etiquette"], c["1"], c["notch"])
    if c.get("type") == "led":
        return "%s LED (anode %s, cathode %s)" % (name, c["a"], c["k"])
    return "%s %s (%s – %s)" % (name, c["etiquette"], c["a"], c["b"])


def wire_id(w):
    return "%s → %s" % tuple(sorted((w["de"], w["vers"])))


def diff_box(m, prev):
    cw = dict((wire_id(w), w) for w in m["fils"])
    pw = dict((wire_id(w), w) for w in prev["fils"])
    cc = dict((comp_id(n, c), 1) for n, c in m["composants"].items())
    pc = dict((comp_id(n, c), 1) for n, c in prev["composants"].items())
    rem_w = [pw[k] for k in pw if k not in cw]
    add_w = [cw[k] for k in cw if k not in pw]
    rem_c = [k for k in pc if k not in cc]
    add_c = [k for k in cc if k not in pc]
    li = lambda items: "".join("<li>%s</li>" % i for i in items) or "<li><i>rien</i></li>"
    wtxt = lambda w: "fil <b>%s</b> → <b>%s</b> (%s)" % (E(w["de"]), E(w["vers"]), E(w["couleur"]))
    return ("<div class='row'><div><b>À RETIRER</b><ul>%s%s</ul></div><div><b>À AJOUTER</b><ul>%s%s</ul></div></div>"
            "<p class='note'>Compté : %d fil(s) et %d composant(s) à retirer, %d fil(s) et %d composant(s) à ajouter.</p>") % (
        li([wtxt(w) for w in rem_w]), "".join("<li>%s</li>" % E(c) for c in rem_c) if rem_c else "",
        li([wtxt(w) for w in add_w]), "".join("<li>%s</li>" % E(c) for c in add_c) if add_c else "",
        len(rem_w), len(rem_c), len(add_w), len(add_c))


def build(rel, hw, devs, hook):
    m = R.load_montage(rel)
    nb = R.numbers_of(m)
    m = R.subst(m, dict((k, v) for k, v in nb.items() if k.startswith("__")))
    res, _ = R.validate(m, hw)
    nerr = sum(1 for r in res if r[0] == "ERREUR")
    sec = [0]

    def h2(t):
        sec[0] += 1
        return "<h2>%d. %s</h2>" % (sec[0], E(t))
    b = ["<h1>%s</h1><p class='sub'>TP%s · %s · %s</p>" % (E(m["titre"]), m["tp"], E(m["id"]), E(m["objectif"]))]
    b.append("<div class='card'><b>Vérification automatique du câblage :</b> %s</div>" % (
        R.tag("ERREUR") + " %d erreur(s) — voir plus bas" % nerr if nerr else R.tag("ok") + " aucune erreur de câblage détectée"))

    # 1. table
    b.append("<div class='card'>%s%s" % (h2("Vue d'ensemble de la table : câbles entre les appareils et la plaque"), bench.bench_svg(m, hw, devs)))
    b.append("<table><tr><th>Câble</th><th>De</th><th>Vers</th><th>Rôle</th></tr>")
    for c in m.get("cables", []):
        b.append("<tr><td><b>%s</b> — %s</td><td>%s</td><td>%s</td><td>%s %s</td></tr>" % (c["id"], E(c["nom"]), E(c["de"]), E(c["vers"]), E(c["role"]), R.tag("à confirmer")))
    b.append("</table><p class='note'>Chaque BNC de la plaque reçoit <b>deux fils</b> (âme + blindage). La sortie du GBF sert <b>deux fois</b> quand le T est utilisé : vers la plaque et vers la voie 1 de l'oscilloscope.</p></div>")

    # 2. schéma
    svg = ""
    has_pred = False
    if hook:
        probe = dict(m)
        probe.setdefault("circuit", m["id"])   # par défaut : le circuit prédit qui porte le même identifiant
        svg = hook(probe)
        if svg:
            m["circuit"] = probe["circuit"]
            has_pred = True
    if not svg and m.get("calcul") and m["calcul"]["type"] == "diviseur":
        svg = R.schema_diviseur_svg(m, nb)
    if svg:
        b.append("<div class='card'>%s%s</div>" % (h2("Schéma électrique"), svg))

    # 3. plaque
    b.append("<div class='card'>%s<div class='row'><div>%s</div><div>" % (h2("Câblage sur la plaque (vue de dessus, comme sur ta table)"), R.board_svg(m, hw, 640)))
    b.append("<table><tr><th>N°</th><th>Fil</th><th>De → vers</th><th>Rôle</th></tr>")
    for w in m["fils"]:
        b.append("<tr><td><b>%s</b></td><td><span class='sw' style='background:%s'></span>%s</td><td>%s → %s</td><td>%s</td></tr>" % (
            w["n"], R.WIRE.get(w["couleur"], "#999"), E(w["couleur"]), E(w["de"]), E(w["vers"]), E(w["role"])))
    b.append("</table><h3>Composants</h3><table><tr><th>Réf.</th><th>Valeur / type</th><th>Pattes</th></tr>")
    for n, c in m["composants"].items():
        if c.get("type") == "chip":
            b.append("<tr><td>%s</td><td>%s (DIP%d)</td><td>encoche en %s ; broche 1 = %s</td></tr>" % (E(n), E(c["etiquette"]), c["dip"], E(c["notch"]), E(c["1"])))
        elif c.get("type") == "led":
            b.append("<tr><td>%s</td><td>LED</td><td>anode (patte longue) %s · cathode %s</td></tr>" % (E(n), E(c["a"]), E(c["k"])))
        else:
            b.append("<tr><td>%s</td><td>%s</td><td>%s – %s</td></tr>" % (E(n), E(c["etiquette"]), E(c["a"]), E(c["b"])))
    b.append("</table>")
    for n, c in m["composants"].items():
        if c.get("type") == "chip":
            b.append("<h3>Broches de %s</h3><table><tr><th>Broche</th><th>Trou</th><th>Rôle</th></tr>%s</table>" % (
                E(n), "".join("<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (p, E(c[str(p)]), E(c["roles"][str(p)])) for p in range(1, c["dip"] + 1))))
    b.append("<p class='note'>Adresse d'un trou : T1b62 = bloc 1, lettre b (bande de droite a–e), rangée 62. N1-1u-40 = rail 1, colonne 1, moitié haute (rangées 33 à 63), position 40. TOP-L1-3 = bus du haut, côté gauche, ligne 1, position 3. Les 5 trous d'une même rangée d'un même côté de la fente sont reliés.</p></div></div></div>")

    # 4. ordre de câblage rapide
    if m.get("etapes_montage"):
        b.append("<div class='card'>%s<ol>%s</ol></div>" % (h2("Ordre de câblage rapide"), "".join("<li>%s</li>" % E(s) for s in m["etapes_montage"])))

    # 5. différences avec le montage précédent
    if m.get("precedent"):
        prev = R.load_montage(m["precedent"])
        b.append("<div class='card'>%s<p class='note'>Depuis : <b>%s</b>. Ne démonte que ce qui est listé.</p>%s</div>" % (
            h2("Ce qu'il faut changer depuis le montage précédent"), E(prev["titre"]), diff_box(m, prev)))

    # 6. réglages des appareils
    names = {"psu": "alimentation", "gbf": "GBF", "scope": "oscilloscope"}
    for key in ("psu", "gbf", "scope"):
        cfg = m.get("instruments", {}).get(key)
        if not cfg:
            continue
        b.append("<div class='card'>%s<p><b>%s</b></p><div class='row'><div>%s</div><div>%s</div></div></div>" % (
            h2("Réglages : %s" % names[key]), E(cfg["reglages"]), R.photo_pastilles(devs[key], cfg["photo"], cfg["etapes"]), R.steps_list(cfg["etapes"])))

    # 7. écran attendu
    if m.get("ecran_attendu"):
        ec = m["ecran_attendu"]
        b.append("<div class='card'>%s<div class='row'><div style='max-width:760px'>%s</div><div>" % (h2("Résultat attendu à l'écran de l'oscilloscope"), R.scope_svg(ec, "att")))
        b.append("<table><tr><th>Grandeur</th><th>Valeur attendue</th></tr><tr><td>Ue (voie 1, jaune)</td><td>2 Vpp, 1 kHz, 2 carreaux à 1 V/div</td></tr>")
        b.append("<tr><td>Us (voie 2, verte)</td><td>%.3f Vpp, 2 carreaux à 100 mV/div</td></tr><tr><td>Rapport Us/Ue</td><td>%.4f (R2 / (R1+R2))</td></tr><tr><td>Période</td><td>1 ms = 5 carreaux à 200 µs/div</td></tr></table>" % (nb["us_vpp"], nb["ratio"]))
        b.append("<p class='note'>Les deux courbes sont en phase (diviseur résistif). Elles sont rangées en deux bandes (jaune en haut, verte en bas) comme après un Auto Scale.</p></div></div></div>")
    if has_pred:
        b.append("<div class='card'><b>Tous les écrans prédits pour ce montage</b> (normal, saturation, bande passante…) : <a href='predictions_tp%s.html#%s'>ouvrir la page de prédiction</a></div>" % (m["tp"], E(m["circuit"])))
    if m.get("table_rc"):
        t = m["table_rc"]
        rows = "".join("<tr><td>%s Ω</td><td>%.3f Vpp</td><td></td></tr>" % (("%g" % r), t["e_vpp"] * r / (r + t["rint"])) for r in t["valeurs"])
        b.append("<div class='card'>%s<p class='note'>Uc = E · Rc / (Rc + Rint), avec E = %g Vpp (High Z) et Rint = %g Ω nominal. Rint se lit là où Uc = E/2 = %g Vpp : alors Rc = Rint.</p><table><tr><th>Rc</th><th>Uc attendu</th><th>Ta mesure</th></tr>%s</table></div>" % (
            h2("Tableau à remplir : Uc en fonction de Rc"), t["e_vpp"], t["rint"], t["e_vpp"] / 2.0, rows))
    if m.get("pannes"):
        b.append("<div class='card'>%s<ul>%s</ul></div>" % (h2("Pannes fréquentes"), "".join("<li>%s</li>" % E(p) for p in m["pannes"])))
    b.append("<div class='card'>%s<table>%s</table></div>" % (h2("Détail des vérifications automatiques"), "".join("<tr><td>%s</td><td>%s</td></tr>" % (R.tag(l), E(t)) for l, t in res)))
    return m, res, R.page(m["titre"], "".join(b))
