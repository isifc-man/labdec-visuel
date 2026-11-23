#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Exporte les données du banc vers app/data.js (lu par le moteur et l'interface).
Usage :  /usr/bin/python3 tools/export_app_data.py
Source de vérité = YAML ; ce fichier est généré, ne pas l'éditer à la main."""
import json
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import build_interactive as BI  # noqa: E402


def main():
    holes, montages, hw, chips_lib = BI.collect_data()
    # extras de leçon lus directement dans les YAML (sujet, pannes, étapes, questions « à prédire »)
    preds = {}
    for pf in sorted((ROOT / "predictions").glob("*.yaml")):
        d = yaml.safe_load(pf.read_text(encoding="utf-8"))
        for c in d.get("circuits", []):
            preds[c["id"]] = [{"titre": sc.get("titre", ""), "q": sc.get("a_predire", ""), "gbf": sc.get("gbf", {})}
                              for sc in c.get("scenarios", []) if sc.get("a_predire")]
    light = {}
    for p in sorted((ROOT / "montages").rglob("*.yaml")):
        y = yaml.safe_load(p.read_text(encoding="utf-8"))
        mid = y["id"]
        m = dict(montages[mid])
        m.pop("overview_svg", None)          # lourd, inutile pour le moteur
        ins = y.get("instruments", {})
        m["pannes"] = y.get("pannes", [])
        m["etapes_montage"] = y.get("etapes_montage", [])
        m["precedent"] = (y.get("precedent") or "").split("/")[-1].replace(".yaml", "") or None
        m["reglages"] = {k: (ins.get(k) or {}).get("reglages") for k in ("gbf", "psu", "scope")}
        m["questions"] = preds.get(y.get("circuit", mid), [])
        light[mid] = m
    out = ROOT / "app" / "data.js"
    out.write_text(
        "// GÉNÉRÉ par tools/export_app_data.py — ne pas éditer\n"
        "const HOLES = %s;\nconst MONTAGES = %s;\nconst CHIPS_LIB = %s;\n"
        % (json.dumps(holes, ensure_ascii=False), json.dumps(light, ensure_ascii=False), json.dumps(chips_lib, ensure_ascii=False)),
        encoding="utf-8")
    print("écrit", out, out.stat().st_size // 1024, "Ko ;", len(holes), "trous,", len(light), "montages")


if __name__ == "__main__":
    main()
