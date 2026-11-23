# -*- coding: utf-8 -*-
"""Audit automatique : tes YAML suffisent-ils pour une app « comme sur le vrai banc » ? Écrit docs/AUDIT_DONNEES_APP.md.
Usage : /usr/bin/python3 tools/audit_data.py"""
import sys
import glob
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import render as R
import netlist as N

ROOT = R.ROOT
OK, PART, KO = "✅", "🟡", "❌"
rows = []


def add(area, item, status, detail):
    rows.append((area, item, status, detail))


def count_status(node):
    c = {"verifie": 0, "a_verifier": 0, "a_remplir": 0}

    def walk(x):
        if isinstance(x, dict):
            s = x.get("statut")
            if s in c:
                c[s] += 1
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(node)
    return c


hw = R.load("hardware/board_wish106.yaml")
beh = R.load("hardware/behavior.yaml")
montages = sorted(glob.glob(str(ROOT / "montages" / "*" / "*.yaml")))

# 1. plaque
txt = (ROOT / "hardware/board_wish106.yaml").read_text(encoding="utf-8")
na = txt.count("a_confirmer")
add("Plaque", "géométrie des trous, blocs, rails coupés au W, 7 connecteurs, adresses", OK, "adressage T/N/TOP unique, validé par 12 montages")
add("Plaque", "points encore « a_confirmer » dans board_wish106.yaml", PART if na else OK, "%d occurrence(s) : rangée 1 en bas, structure du bus haut, côté âme des BNC…" % na)

# 2. composants / comportement
c = count_status(beh)
add("Comportement", "hardware/behavior.yaml : paramètres (TL081, LED, résistances, TTL, GBF, oscillo, alim)", PART,
    "%d vérifiés, %d à vérifier, %d à remplir (valeurs null)" % (c["verifie"], c["a_verifier"], c["a_remplir"]))
add("Comportement", "modèle SPICE complet du TL081 (offset, polarisation, sortie dépendant de la charge)", KO, "seul le modèle comportemental à un pôle existe (tools/netlist.py)")
add("Comportement", "modèles numériques 74LS00 / 74LS74 (seuils, retards, sorties)", PART, "seuils et retards du 74LS74 lus dans le guide ; retards du 74LS00 manquants ; pas de moteur numérique")
add("Comportement", "multimètre (bande passante, impédance d'entrée)", KO, "non photographié ni décrit")

# 3. instruments
need = {
    "scope": ["btn_autoscale", "btn_default_setup", "btn_run_stop", "btn_single", "btn_meas", "btn_cursors", "btn_ch1", "btn_ch2", "knob_vert", "knob_horiz", "btn_trig_menu", "knob_trig_level", "bnc_ch1", "bnc_ch2"],
    "gbf": ["btn_waveform", "btn_parameter", "btn_ch1_onoff", "btn_ch1_setup", "out1", "sync_out", "keypad_0", "keypad_9", "softkey_1", "softkey_6"],
    "psu": ["ch1_plus", "ch2_plus", "ch3_plus", "ch1_moins", "ch2_moins", "ch3_moins", "btn_on_1", "voltage_knob", "current_knob", "enter"],
}
for dev in ("scope", "gbf", "psu"):
    y = R.load("hardware/instruments/%s.yaml" % dev)
    zones = {}
    for ph in y["photos"].values():
        zones.update(ph["zones"])
    miss = [z for z in need[dev] if z not in zones]
    add("Instruments", "%s : zones cliquables nécessaires" % dev, OK if not miss else PART, "%d zones ; manquantes : %s" % (len(zones), ", ".join(miss) or "aucune"))
add("Instruments", "oscillo : boutons de position verticale (voies 1 et 2), menus de voie (couplage, sonde), menu Trigger, touches de menu à droite de l'écran", KO, "non cartographiés : il faut une photo de face nette et la liste des menus utilisés")
add("Instruments", "GBF : arbre des menus (Parameter, Setup → charge High Z, unités)", PART, "chemin High Z noté « à vérifier » dans tous les montages")
add("Instruments", "alimentation : écran, sélection de voie, saisie de tension et de limite", PART, "photo des ports et du clavier ; chemin des menus non décrit")

# 4. montages
nosettings, ext_ok, ext_ko, pred_ok = [], [], [], []
for p in montages:
    rel = str(pathlib.Path(p).relative_to(ROOT))
    m = R.load_montage(rel)
    s = m.get("instruments", {})
    structured = all(isinstance(s.get(k, {}).get("reglages"), dict) for k in s) if s else False
    if not structured:
        nosettings.append(m["id"])
    try:
        net = N.extract(m, hw, {"psu": {1: 1.0, 2: 15.0, 3: 15.0}})
        ext_ok.append((m["id"], net["notes"]))
    except Exception as e:
        ext_ko.append((m["id"], str(e)[:80]))
add("Montages", "12 montages : câblage valide (validateur)", OK, "%d montages YAML" % len(montages))
add("Montages", "netlist extractible depuis le câblage", OK if not ext_ko else PART, "%d/%d ; avec puce numérique non simulée : %s" % (len(ext_ok), len(montages), ", ".join(i for i, n in ext_ok if n) or "aucune"))
add("Montages", "réglages d'appareils LISIBLES PAR LA MACHINE (amplitude, fréquence, V/div, tensions d'alim)", KO,
    "aujourd'hui du texte libre dans « reglages » pour les %d montages : il faut un bloc « settings: » structuré (voir docs/ARCHITECTURE_APP.md §5)" % len(nosettings))
add("Montages", "résultat attendu lisible par la machine (pour comparer à ce que fait l'élève)", PART, "TP1 et TP2 : predictions/*.yaml (27 cas) ; TP3 : aucun")
add("Montages", "valeurs de résistances dans la série E12", PART, "9,1 kΩ (non inverseur, association) et 20 kΩ ne sont pas E12 : vérifier les montages")

# 5. vérité terrain
gt = [pathlib.Path(p).name for p in glob.glob(str(ROOT / "assets/photos/scope_tp2_*.jpg"))]
add("Vérité terrain", "photos d'écran d'oscilloscope (TP2) pour caler le modèle", PART, "%d photos ; sans valeurs mesurées associées (circuit, réglages inconnus)" % len(gt))
add("Vérité terrain", "tes mesures de TP (Cr-cr, phases, Rint…) dans un fichier structuré", KO, "elles existent seulement dans des .md (COMPTE_RENDU_PERSO_TP*.md) : créer mesures_reelles.yaml")
add("Vérité terrain", "tests de non-régression : moteur de l'app contre predict.py et check_netlist.py", PART, "check_netlist.py compare déjà 14 points (< 0,1 %) ; manque l'export JSON de référence")

out = ["# Audit des données pour l'app « comme sur le vrai banc »", "",
       "Généré par `tools/audit_data.py` — ne pas éditer à la main. ✅ prêt · 🟡 partiel · ❌ manquant.", "",
       "| Domaine | Élément | État | Détail |", "|---|---|---|---|"]
for a, i, s, d in rows:
    out.append("| %s | %s | %s | %s |" % (a, i, s, d.replace("|", "/")))
n = {OK: 0, PART: 0, KO: 0}
for r in rows:
    n[r[2]] += 1
out += ["", "**Bilan : %d prêts, %d partiels, %d manquants.**" % (n[OK], n[PART], n[KO]), ""]
outp = ROOT / "docs"
outp.mkdir(exist_ok=True)
(outp / "AUDIT_DONNEES_APP.md").write_text("\n".join(out), encoding="utf-8")
print("\n".join(out))
