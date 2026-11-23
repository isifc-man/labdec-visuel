#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Générateur du Banc d'Électronique Virtuel Complet LABDEC_VISUEL (Wish Board 106 + Instruments Keysight)."""
import sys
import pathlib
import json
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import render as R

def collect_data():
    """Calcule les données du banc (trous, montages, puces). Réutilisé par tools/build_app.py."""
    hw = R.load("hardware/board_wish106.yaml")
    chips_lib = R.load("hardware/components.yaml")
    gbf_data = R.load("hardware/instruments/gbf.yaml")
    scope_data = R.load("hardware/instruments/scope.yaml")
    psu_data = R.load("hardware/instruments/psu.yaml")
    
    # 1. Calcul de tous les trous de la plaque Wish Board 106
    holes = []
    # Bus haut
    for half in "LR":
        for line in (1, 2):
            for p in range(1, 26):
                addr = f"TOP-{half}{line}-{p}"
                x, y = R.xy(addr)
                holes.append({
                    "id": addr,
                    "x": round(x, 1),
                    "y": round(y, 1),
                    "t": "top",
                    "net": f"TOP_{half}_{line}",
                    "desc": f"Bus haut {half}{line}, pos {p} (0 V / masse)"
                })

    # Bandes et rails
    for s in R.STRIPS:
        for c in range(R.ncols(s)):
            for r in range(1, R.ROWS + 1):
                if s[0] == "N":
                    h = "u" if r >= 33 else "d"
                    col = c + 1
                    addr = f"{s}-{col}{h}-{r}"
                    net = f"{s}_{col}_{h}"
                    t = "rail"
                    desc = f"Rail {s}, colonne {col}, moitié {'haute' if h=='u' else 'basse'}, rangée {r}"
                else:
                    blk = s[:2]
                    side = "L" if s[2] == "L" else "R"
                    letters = "fghij" if side == "L" else "abcde"
                    let = letters[c]
                    addr = f"{blk}{let}{r}"
                    net = f"{blk}_{side}_{r}"
                    t = "strip"
                    desc = f"Bloc {blk}, colonne {let} ({'gauche' if side=='L' else 'droite'}), rangée {r}"
                x, y = R.xy(addr)
                holes.append({
                    "id": addr,
                    "x": round(x, 1),
                    "y": round(y, 1),
                    "t": t,
                    "net": net,
                    "desc": desc
                })

    # Connecteurs du haut de la plaque
    conns = R.conn_geom(hw)
    for cid, g in conns.items():
        for pn, (px, py) in g["pins"].items():
            addr = f"{cid}.{pn}"
            label_desc = {
                "BNC1.core": "BNC 1 — Âme (Signal Ve / Entrée)",
                "BNC1.shield": "BNC 1 — Blindage (Masse signal)",
                "BNC2.core": "BNC 2 — Âme (Signal Vs / Sortie)",
                "BNC2.shield": "BNC 2 — Blindage (Masse signal)",
                "VB.main": "Borne Bleue VB (−15 V alimentation)",
                "VC.main": "Borne Rouge VC (+15 V alimentation)",
                "MASSE.main": "Borne Turquoise MASSE (0 V référence alim)",
                "BANANE_ROUGE.main": "Borne Banane Rouge auxiliaire",
                "BANANE_NOIRE.main": "Borne Banane Noire auxiliaire",
            }.get(addr, addr)
            holes.append({
                "id": addr,
                "x": round(px, 1),
                "y": round(py, 1),
                "t": "conn",
                "net": addr.replace(".", "_"),
                "desc": label_desc
            })

    # 2. Chargement de tous les montages et calcul des prédictions
    import bench
    devs = {"gbf": gbf_data, "scope": scope_data, "psu": psu_data}
    montages = {}
    for p in sorted((ROOT / "montages").rglob("*.yaml")):
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
        mid = data["id"]
        m_exp = R.expand_chips(dict(data))
        try:
            overview_svg = bench.bench_svg(data, hw, devs)
        except Exception as e:  # ne jamais casser la page si un montage n'a pas de câbles
            print(f"[vue d'ensemble] {mid} : {e}")
            overview_svg = ""
        montages[mid] = {
            "id": mid,
            "tp": data.get("tp", 1),
            "titre": data.get("titre", mid),
            "objectif": data.get("objectif", ""),
            "description": data.get("description", ""),
            "puces": data.get("puces", []),
            "composants": m_exp.get("composants", {}),
            "fils": data.get("fils", []),
            "cables": data.get("cables", []),
            "overview_svg": overview_svg,
            "noeuds": data.get("noeuds", {}),
            "gbf_def": data.get("reglages_gbf", {"forme": "sine", "f": 1000, "vpp": 0.4}),
            "pred_url": f"predictions_tp{data.get('tp', 1)}.html#{mid}"
        }

    return holes, montages, hw, chips_lib


def generate():
    holes, montages, hw, chips_lib = collect_data()
    # 3. Assemblage du HTML
    html = build_full_workbench_html(holes, montages, hw, chips_lib)
    out_file = ROOT / "out" / "labdec_interactif.html"
    out_file.write_text(html, encoding="utf-8")
    print(f"Banc complet interactif généré : {out_file}")
    return out_file

def build_full_workbench_html(holes, montages, hw, chips_lib):
    holes_json = json.dumps(holes, ensure_ascii=False)
    montages_json = json.dumps(montages, ensure_ascii=False)
    chips_json = json.dumps(chips_lib, ensure_ascii=False)

    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LABDEC_VISUEL — Banc Complet d'Électronique (Keysight + Wish Board 106)</title>
<style>
:root {{
  --bg: #0b0e14;
  --bg-card: #151a23;
  --bg-panel: #1a202c;
  --line: #2b3545;
  --text: #e6edf3;
  --text-muted: #8b949e;
  --accent: #38bdf8;
  --accent-hover: #0ea5e9;
  --ok: #22c55e;
  --ok-bg: #14532d55;
  --warn: #eab308;
  --warn-bg: #713f1255;
  --err: #ef4444;
  --err-bg: #7f1d1d55;
  --ch1-color: #facc15;
  --ch2-color: #22c55e;
  --cursor-color: #f97316;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  background: var(--bg);
  color: var(--text);
  overflow: hidden;
  height: 100vh;
  display: flex;
  flex-direction: column;
}}

/* HEADER */
header {{
  background: var(--bg-card);
  border-bottom: 1px solid var(--line);
  padding: 8px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-shrink: 0;
}}
.brand {{
  display: flex;
  align-items: center;
  gap: 10px;
}}
.brand h1 {{
  font-size: 16px;
  font-weight: 700;
  color: #fff;
}}
.brand span {{
  background: #0284c7;
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 4px;
}}
.nav-tabs {{
  display: flex;
  background: var(--bg-panel);
  padding: 3px;
  border-radius: 6px;
  border: 1px solid var(--line);
}}
.nav-tab {{
  background: transparent;
  border: none;
  color: var(--text-muted);
  padding: 5px 12px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}}
.nav-tab.active {{
  background: #0284c7;
  color: #fff;
}}
.montage-select {{
  background: var(--bg-panel);
  color: var(--text);
  border: 1px solid var(--line);
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  outline: none;
}}
.top-actions {{
  display: flex;
  align-items: center;
  gap: 6px;
}}
.btn {{
  background: var(--bg-panel);
  border: 1px solid var(--line);
  color: var(--text);
  padding: 5px 10px;
  border-radius: 5px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 5px;
}}
.btn:hover {{ background: var(--line); color: #fff; }}
.btn-primary {{ background: #0284c7; border-color: #0284c7; color: #fff; }}
.btn-primary:hover {{ background: #0369a1; }}
.btn-success {{ background: #15803d; border-color: #15803d; color: #fff; }}

/* SUB-HEADER / TOOLBAR */
.sub-toolbar {{
  background: #11151f;
  border-bottom: 1px solid var(--line);
  padding: 6px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-shrink: 0;
}}
.tools-left {{
  display: flex;
  align-items: center;
  gap: 12px;
}}
.tool-group {{
  display: flex;
  gap: 3px;
  background: var(--bg-panel);
  padding: 2px;
  border-radius: 5px;
  border: 1px solid var(--line);
}}
.t-btn {{
  background: transparent;
  border: none;
  color: var(--text-muted);
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
}}
.t-btn.active {{
  background: #0284c7;
  color: #fff;
}}
.color-picker {{
  display: flex;
  align-items: center;
  gap: 4px;
}}
.color-dot {{
  width: 16px;
  height: 16px;
  border-radius: 50%;
  cursor: pointer;
  border: 2px solid transparent;
}}
.color-dot.active {{
  border-color: #fff;
  box-shadow: 0 0 0 2px #0284c7;
}}

/* WORKSPACE SPLIT */
.main-workspace {{
  flex: 1;
  display: flex;
  overflow: hidden;
}}

/* VIEW CONTAINERS */
.view-panel {{
  flex: 1;
  display: flex;
  overflow: hidden;
  position: relative;
}}
.view-panel.hidden {{
  display: none !important;
}}

/* SPLIT MODE */
#view-split {{
  display: flex;
  flex: 1;
  overflow: hidden;
}}
.split-left {{
  flex: 1;
  background: #090c10;
  border-right: 1px solid var(--line);
  overflow: auto;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 10px;
}}
.split-right {{
  width: 600px;
  background: var(--bg-card);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}}

/* BENCH VIEW (Table Instruments + Board) */
#view-bench {{
  background: #0d1117;
  overflow: auto;
  align-items: center;
  justify-content: center;
  padding: 20px;
}}

/* BOARD VIEW (Zoomed Breadboard) */
#view-board {{
  background: #090c10;
  overflow: auto;
  align-items: center;
  justify-content: center;
  padding: 20px;
}}

/* SCOPE VIEW (Full Screen Oscilloscope) */
#view-scope {{
  background: #090c10;
  padding: 20px;
  align-items: center;
  justify-content: center;
  overflow: auto;
}}

/* OSCILLOSCOPE GUI */
.scope-chassis {{
  background: #1e2530;
  border-radius: 12px;
  border: 3px solid #334155;
  box-shadow: 0 15px 35px rgba(0,0,0,0.8);
  padding: 14px;
  width: 100%;
  max-width: 900px;
}}
.scope-header {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}}
.scope-title {{
  font-weight: 700;
  font-size: 13px;
  color: #94a3b8;
  letter-spacing: 0.5px;
}}
.scope-screen {{
  position: relative;
  background: #04101c;
  border-radius: 8px;
  border: 2px solid #1c2733;
  overflow: hidden;
  box-shadow: inset 0 0 20px rgba(0,0,0,0.9);
}}
#scope-canvas {{
  display: block;
  width: 100%;
  height: auto;
  cursor: crosshair;
}}

/* SCOPE CONTROLS PANEL */
.scope-controls {{
  margin-top: 10px;
  background: #141922;
  border-radius: 8px;
  border: 1px solid var(--line);
  padding: 10px;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}}
.ctrl-block {{
  background: var(--bg-panel);
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 8px;
}}
.ctrl-block h4 {{
  font-size: 11px;
  text-transform: uppercase;
  color: var(--text-muted);
  margin-bottom: 6px;
}}
.ctrl-row {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
  font-size: 12px;
}}
.ctrl-row select, .ctrl-row input {{
  background: #11151f;
  color: #fff;
  border: 1px solid var(--line);
  border-radius: 4px;
  padding: 2px 6px;
  font-size: 11px;
}}

/* GBF & PSU COMPACT PANELS */
.instrument-strip {{
  background: #11151f;
  border-top: 1px solid var(--line);
  padding: 10px 16px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}}
.inst-box {{
  background: var(--bg-card);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 8px 12px;
}}
.inst-header {{
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  color: #38bdf8;
  display: flex;
  justify-content: space-between;
  margin-bottom: 6px;
}}

/* SIDEBAR INSPECTOR */
.sidebar {{
  width: 360px;
  background: var(--bg-card);
  border-left: 1px solid var(--line);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  flex-shrink: 0;
}}
.sidebar-section {{
  border-bottom: 1px solid var(--line);
  padding: 10px 14px;
}}
.sec-title {{
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted);
  font-weight: 700;
  margin-bottom: 6px;
  display: flex;
  justify-content: space-between;
}}
.checklist-container {{
  max-height: 180px;
  overflow-y: auto;
}}
.checklist-item {{
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 5px 8px;
  border-radius: 5px;
  font-size: 12px;
  margin-bottom: 3px;
  background: var(--bg-panel);
}}
.checklist-item.done {{
  background: var(--ok-bg);
  color: #86efac;
}}
.checklist-item.missing {{
  color: var(--text-muted);
}}
.placed-list {{
  flex: 1;
  overflow-y: auto;
  padding: 6px 14px;
}}
.placed-table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 11px;
}}
.placed-table th {{
  text-align: left;
  padding: 4px;
  color: var(--text-muted);
  border-bottom: 1px solid var(--line);
}}
.placed-table td {{
  padding: 4px;
  border-bottom: 1px solid #1f2633;
}}
.wire-del {{
  color: var(--err);
  background: transparent;
  border: none;
  cursor: pointer;
  font-weight: 700;
}}
.alerts-box {{
  padding: 8px 14px;
  background: #0f131a;
  border-top: 1px solid var(--line);
}}
.alert-row {{
  font-size: 11px;
  padding: 4px 8px;
  border-radius: 4px;
  margin-bottom: 3px;
}}
.alert-warn {{ background: var(--warn-bg); color: #fde047; }}
.alert-err {{ background: var(--err-bg); color: #fca5a5; }}
.alert-ok {{ background: var(--ok-bg); color: #86efac; }}

/* HOLE INTERACTION */
circle.h-target {{
  cursor: pointer;
  fill: transparent;
}}
circle.h-target:hover {{
  fill: rgba(56, 189, 248, 0.45);
  stroke: #38bdf8;
  stroke-width: 1.5px;
}}
circle.h-sel {{
  fill: #f59e0b !important;
  stroke: #fff !important;
  stroke-width: 2.5px !important;
}}
</style>
</head>
<body>

<!-- HEADER -->
<header>
  <div class="brand">
    <h1>Banc d'Électronique Virtuel — ISIFC</h1>
    <span>TP EXAMEN</span>
  </div>

  <div class="nav-tabs">
    <button class="nav-tab active" data-view="split">🖥️ Vue Mixte (Plaque + Oscillo)</button>
    <button class="nav-tab" data-view="board">📌 Plaque Zoomée (Wish Board 106)</button>
    <button class="nav-tab" data-view="scope">📈 Pupitre & Écran Oscilloscope</button>
    <button class="nav-tab" data-view="overview">🔌 Vue d'ensemble de la table</button>
  </div>

  <div>
    <select id="select-montage" class="montage-select">
      <option value="tp1-B1-pont-diviseur">TP1 · Pont diviseur de tension par 10</option>
      <option value="tp1-C1-impedance-interne">TP1 · Impédance interne du GBF</option>
      <option value="tp1-D1-led">TP1 · LED avec résistance</option>
      <option value="tp2-A-suiveur">TP2 · A. Suiveur (TL081, Av = 1)</option>
      <option value="tp2-B1-inverseur" selected>TP2 · B1. Amplificateur inverseur (Av = −20)</option>
      <option value="tp2-B2-non-inverseur">TP2 · B2. Amplificateur non inverseur (Av ≈ +10)</option>
      <option value="tp2-C-association">TP2 · C. Association cascade (Av ≈ −200)</option>
      <option value="tp2-D-soustracteur">TP2 · D. Soustracteur (Vs = V2 − V1)</option>
      <option value="tp3-A-nand">TP3 · A. Porte NAND 74LS00 + LED</option>
      <option value="tp3-A2-seuils">TP3 · A2. Seuils de basculement</option>
      <option value="tp3-B-bascule-D">TP3 · B. Bascule D (diviseur par 2)</option>
      <option value="tp3-C-compteur">TP3 · C. Compteur binaire 2 bits</option>
      <option value="libre">Mode Libre</option>
    </select>
  </div>

  <div class="top-actions">
    <button class="btn btn-primary" id="btn-solution">💡 Corrigé</button>
    <button class="btn" id="btn-undo">⎌ Annuler</button>
    <button class="btn" id="btn-clear">🗑️ Vider</button>
  </div>
</header>

<!-- SUB-TOOLBAR -->
<div class="sub-toolbar">
  <div class="tools-left">
    <div class="tool-group">
      <button class="t-btn active" data-tool="wire">Fil</button>
      <button class="t-btn" data-tool="resistor">Résistance</button>
      <button class="t-btn" data-tool="chip">Puce DIP</button>
      <button class="t-btn" data-tool="delete">Gomme</button>
    </div>

    <div class="color-picker">
      <span style="font-size:11px;color:var(--text-muted)">Couleur :</span>
      <div class="color-dot active" data-color="rouge" style="background:#ef4444" title="Rouge (+15V / Entrée)"></div>
      <div class="color-dot" data-color="noir" style="background:#1f2937;border:1px solid #444" title="Noir (Masse / 0V)"></div>
      <div class="color-dot" data-color="bleu" style="background:#3b82f6" title="Bleu (−15V)"></div>
      <div class="color-dot" data-color="jaune" style="background:#eab308" title="Jaune"></div>
      <div class="color-dot" data-color="orange" style="background:#f97316" title="Orange (Sortie)"></div>
      <div class="color-dot" data-color="vert" style="background:#22c55e" title="Vert"></div>
    </div>

    <div id="resistor-select-box" style="display:none;align-items:center;gap:4px;">
      <span style="font-size:11px;color:var(--text-muted)">Valeur R :</span>
      <select id="resistor-val-input" style="background:var(--bg-panel);color:#fff;border:1px solid var(--line);padding:2px 6px;border-radius:4px;font-size:11px">
        <option value="1000">1 kΩ (Marron-Noir-Rouge)</option>
        <option value="9100">9.1 kΩ (Blanc-Marron-Rouge)</option>
        <option value="10000">10 kΩ (Marron-Noir-Orange)</option>
        <option value="20000">20 kΩ (Rouge-Noir-Orange)</option>
        <option value="100">100 Ω (Marron-Noir-Marron)</option>
      </select>
    </div>

    <div id="chip-select-box" style="display:none;align-items:center;gap:4px;">
      <span style="font-size:11px;color:var(--text-muted)">Puce :</span>
      <select id="chip-val-input" style="background:var(--bg-panel);color:#fff;border:1px solid var(--line);padding:2px 6px;border-radius:4px;font-size:11px">
        <option value="TL081">TL081 (AOP 8 broches)</option>
        <option value="74LS00">74LS00 (NAND TTL 14 broches)</option>
        <option value="74LS74">74LS74 (Bascule D 14 broches)</option>
      </select>
    </div>
  </div>

  <div style="font-size:12px;color:var(--accent);" id="active-pointer-info">
    Survolez un trou de la plaque pour commencer.
  </div>
</div>

<!-- WORKSPACE -->
<div class="main-workspace">

  <!-- VUE 1 : SPLIT (Plaque à gauche + Oscillo en direct à droite) -->
  <div id="view-split" class="view-panel">
    <!-- Côté Gauche : Plaque Wish Board 106 -->
    <div class="split-left" id="split-board-container">
      <div id="board-host-split" style="max-height:100%;max-width:100%;"></div>
    </div>

    <!-- Côté Droit : Écran Oscilloscope & Contrôles -->
    <div class="split-right">
      <!-- Oscilloscope Chassis -->
      <div style="padding:12px;">
        <div class="scope-chassis">
          <div class="scope-header">
            <span class="scope-title">KEYSIGHT DSOX1202A — 2 Voies 70 MHz</span>
            <div style="display:flex;gap:6px;">
              <button class="btn btn-primary" id="btn-autoscale" style="padding:2px 8px;font-size:11px;">Auto-Scale</button>
              <button class="btn" id="btn-run-stop" style="padding:2px 8px;font-size:11px;background:#15803d;color:#fff;">RUN</button>
            </div>
          </div>

          <div class="scope-screen">
            <canvas id="scope-canvas" width="800" height="480"></canvas>
          </div>

          <!-- Contrôles rapides sous l'écran -->
          <div class="scope-controls">
            <!-- Voie 1 -->
            <div class="ctrl-block" style="border-left:3px solid var(--ch1-color);">
              <h4 style="color:var(--ch1-color);">Voie 1 (Ve)</h4>
              <div class="ctrl-row">
                <span>V/div :</span>
                <select id="scope-ch1-vdiv">
                  <option value="0.05">50 mV</option>
                  <option value="0.1">100 mV</option>
                  <option value="0.2" selected>200 mV</option>
                  <option value="0.5">500 mV</option>
                  <option value="1.0">1.0 V</option>
                  <option value="2.0">2.0 V</option>
                </select>
              </div>
              <div class="ctrl-row">
                <span>Offset :</span>
                <input type="range" id="scope-ch1-offset" min="-4" max="4" step="0.1" value="0" style="width:70px;">
              </div>
            </div>

            <!-- Voie 2 -->
            <div class="ctrl-block" style="border-left:3px solid var(--ch2-color);">
              <h4 style="color:var(--ch2-color);">Voie 2 (Vs)</h4>
              <div class="ctrl-row">
                <span>V/div :</span>
                <select id="scope-ch2-vdiv">
                  <option value="0.5">500 mV</option>
                  <option value="1.0">1.0 V</option>
                  <option value="2.0" selected>2.0 V</option>
                  <option value="5.0">5.0 V</option>
                  <option value="10.0">10.0 V</option>
                </select>
              </div>
              <div class="ctrl-row">
                <span>Offset :</span>
                <input type="range" id="scope-ch2-offset" min="-4" max="4" step="0.1" value="0" style="width:70px;">
              </div>
            </div>

            <!-- Base de temps -->
            <div class="ctrl-block">
              <h4>Base de temps</h4>
              <div class="ctrl-row">
                <span>s/div :</span>
                <select id="scope-tdiv">
                  <option value="0.00002">20 µs</option>
                  <option value="0.00005">50 µs</option>
                  <option value="0.0001">100 µs</option>
                  <option value="0.0002" selected>200 µs</option>
                  <option value="0.0005">500 µs</option>
                  <option value="0.001">1.0 ms</option>
                  <option value="0.002">2.0 ms</option>
                </select>
              </div>
              <div class="ctrl-row">
                <span>Trigger :</span>
                <span style="color:#facc15;font-weight:700;">CH1 0.0V</span>
              </div>
            </div>

            <!-- Curseurs Interactifs -->
            <div class="ctrl-block" style="border-left:3px solid var(--cursor-color);">
              <h4 style="color:var(--cursor-color);">Curseurs X & Y</h4>
              <div class="ctrl-row">
                <span>Curseurs :</span>
                <select id="scope-cursors-mode">
                  <option value="none">Désactivés</option>
                  <option value="x">X (Temps / Fréq)</option>
                  <option value="y">Y (Tension Vpp)</option>
                  <option value="both" selected>X & Y (Tous)</option>
                </select>
              </div>
              <div class="ctrl-row">
                <span style="font-size:10px;color:var(--cursor-color);" id="cursor-readout">Glissez sur l'écran</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Pupitre GBF et Alimentation -->
      <div class="instrument-strip">
        <!-- GBF -->
        <div class="inst-box">
          <div class="inst-header">
            <span>GBF Keysight EDU33211A</span>
            <button class="btn" id="gbf-onoff-btn" style="padding:1px 6px;font-size:10px;background:#15803d;color:#fff;">OUT: ON</button>
          </div>
          <div style="display:flex;gap:8px;font-size:12px;margin-bottom:4px;">
            <span>Forme :</span>
            <select id="gbf-wave-select" style="background:#11151f;color:#fff;border:1px solid var(--line);border-radius:4px;padding:2px 4px;">
              <option value="sine" selected>Sinus</option>
              <option value="square">Carré</option>
              <option value="triangle">Triangle</option>
            </select>
          </div>
          <div style="display:flex;gap:8px;font-size:12px;margin-bottom:4px;">
            <span>Fréq :</span>
            <input type="number" id="gbf-freq-val" value="1000" step="100" style="width:70px;background:#11151f;color:#fff;border:1px solid var(--line);border-radius:4px;padding:2px;">
            <span>Hz</span>
            <span style="margin-left:auto;color:var(--text-muted);font-size:11px;">(1 kHz)</span>
          </div>
          <div style="display:flex;gap:8px;font-size:12px;">
            <span>Vpp :</span>
            <input type="number" id="gbf-vpp-val" value="0.4" step="0.1" style="width:70px;background:#11151f;color:#fff;border:1px solid var(--line);border-radius:4px;padding:2px;">
            <span>Vpp</span>
            <span style="margin-left:auto;color:var(--text-muted);font-size:11px;">Charge: High Z</span>
          </div>
        </div>

        <!-- Alimentation Triple -->
        <div class="inst-box">
          <div class="inst-header">
            <span>Alim Keysight EDU36311A</span>
            <button class="btn" id="psu-onoff-btn" style="padding:1px 6px;font-size:10px;background:#15803d;color:#fff;">ALL ON</button>
          </div>
          <div style="font-size:11px;color:var(--text-muted);margin-bottom:4px;">
            Voie 2 (+15V) : <b style="color:#ef4444;">+15.00 V</b> / Lim 1.0 A
          </div>
          <div style="font-size:11px;color:var(--text-muted);margin-bottom:4px;">
            Voie 3 (−15V) : <b style="color:#3b82f6;">−15.00 V</b> / Lim 1.0 A
          </div>
          <div style="font-size:10px;color:#facc15;">
            Strap 0V : CH2(−) relié à CH3(+) vers borne MASSE (⏚).
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- VUE 2 : PLAQUE SEULE EN GRAND -->
  <div id="view-board" class="view-panel hidden">
    <div id="board-host-full" style="max-height:100%;max-width:100%;"></div>
  </div>

  <!-- VUE 3 : OSCILLOSCOPE SEUL EN GRAND -->
  <div id="view-scope" class="view-panel hidden">
    <div id="scope-host-full" style="width:900px;"></div>
  </div>

  <!-- VUE 4 : VUE D'ENSEMBLE DE LA TABLE (câbles appareils -> plaque, comme sur le vrai banc) -->
  <div id="view-overview" class="view-panel hidden" style="overflow:auto;background:#fff;">
    <div id="overview-host" style="padding:12px;min-width:880px;"></div>
  </div>

  <!-- SIDEBAR D'INSPECTION & OBJECTIFS -->
  <div class="sidebar">
    <!-- INSPECTEUR -->
    <div class="sidebar-section">
      <div class="sec-title">
        <span>Trou Pointé</span>
        <span id="insp-badge" style="color:var(--accent);">--</span>
      </div>
      <div style="background:var(--bg-panel);border:1px solid var(--line);border-radius:6px;padding:6px 10px;">
        <div style="font-family:monospace;font-weight:700;color:var(--accent);font-size:14px;" id="insp-addr">--</div>
        <div style="font-size:11px;color:var(--text-muted);margin-top:2px;" id="insp-desc">Survolez un trou de la plaque.</div>
      </div>
    </div>

    <!-- OBJECTIFS & VALIDATION -->
    <div class="sidebar-section">
      <div class="sec-title">
        <span>Objectifs TP</span>
        <span id="score-tag" style="background:#0284c7;color:#fff;padding:1px 6px;border-radius:4px;font-size:10px;">0 / 0</span>
      </div>
      <div style="font-size:11px;color:var(--text-muted);margin-bottom:6px;" id="montage-title-desc">Sélectionnez un montage.</div>
      <div class="checklist-container" id="checklist-box">
        <!-- Rempli en JS -->
      </div>
    </div>

    <!-- TABLEAU DES LIAISONS -->
    <div class="sec-title" style="padding:8px 14px 2px;">
      <span>Liaisons sur la plaque (<span id="placed-num">0</span>)</span>
    </div>
    <div class="placed-list">
      <table class="placed-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Type</th>
            <th>De</th>
            <th>Vers</th>
            <th></th>
          </tr>
        </thead>
        <tbody id="placed-tbody">
          <!-- Rempli en JS -->
        </tbody>
      </table>
    </div>

    <!-- ALERTES PANNES & ERREURS -->
    <div class="alerts-box" id="alerts-box">
      <div class="alert-row alert-ok">✓ Prêt. Câblez la plaque pour voir le signal en direct !</div>
    </div>
  </div>

</div>

<!-- SVG TEMPLATE MASTER DE LA WISH BOARD 106 -->
<div style="display:none;">
  <svg id="master-board-svg" viewBox="0 0 862 1158" xmlns="http://www.w3.org/2000/svg">
    <!-- Plaque -->
    <rect x="0" y="0" width="862" height="1158" rx="18" fill="#17191c"/>
    <text x="838" y="1150" font-size="13" fill="#e8742a" font-family="Arial" font-weight="700" text-anchor="end">Wish Board 106 — ISIFC</text>
    
    <!-- Bus haut -->
    <rect x="50" y="147" width="762" height="40" rx="4" fill="#f1f1ee"/>
    <text x="60" y="141" font-size="11" fill="#888" font-family="Arial">bus haut gauche (TOP-L) — masse 0 V</text>
    <text x="461" y="141" font-size="11" fill="#888" font-family="Arial">bus haut droit (TOP-R)</text>

    <!-- Bandes & Rails -->
    <g id="svg-strips"></g>

    <!-- Connecteurs -->
    <g id="svg-connectors"></g>

    <!-- Grille des trous -->
    <g id="svg-holes-dots" fill="#555"></g>

    <!-- Composants & Fils -->
    <g id="svg-chips"></g>
    <g id="svg-resistors"></g>
    <g id="svg-wires"></g>

    <!-- Fil élastique en cours -->
    <line id="svg-rubberband" x1="0" y1="0" x2="0" y2="0" stroke="#38bdf8" stroke-width="4" stroke-dasharray="6,4" style="display:none"/>

    <!-- Trous interactifs -->
    <g id="svg-targets"></g>

    <!-- Marqueur premier clic -->
    <circle id="svg-sel" cx="0" cy="0" r="7" class="h-sel" style="display:none"/>
  </svg>
</div>

<script>
// DONNÉES DU BANC
const HOLES = {holes_json};
const MONTAGES = {montages_json};
const CHIPS_LIB = {chips_json};

const HOLE_MAP = new Map();
HOLES.forEach(h => HOLE_MAP.set(h.id, h));

const WIRE_COLORS = {{
  rouge: "#ef4444",
  noir: "#1f2937",
  bleu: "#3b82f6",
  jaune: "#eab308",
  orange: "#f97316",
  vert: "#22c55e",
  blanc: "#f8fafc"
}};

// ÉTAT GLOBAL DU SYSTÈME
const state = {{
  currentMontage: "tp2-B1-inverseur",
  activeView: "split",
  tool: "wire",
  wireColor: "rouge",
  resistorVal: 1000,
  chipVal: "TL081",
  firstHole: null,
  placedWires: [],
  placedComps: [],
  placedChips: [],
  // Réglages Instruments
  gbf: {{ on: true, wave: "sine", f: 1000, vpp: 0.4, offset: 0.0 }},
  psu: {{ on: true, v2: 15.0, v3: -15.0, strap_ok: true }},
  scope: {{
    ch1_vdiv: 0.2,
    ch1_offset: 0.0,
    ch2_vdiv: 2.0,
    ch2_offset: 0.0,
    tdiv: 0.0002,
    running: true,
    cursorMode: "both",
    curX1: -1.5,
    curX2: 1.5,
    curY1: 2.0,
    curY2: -2.0,
    draggingCursor: null
  }}
}};

// 1. GÉOMÉTRIE DE LA PLAQUE WISH BOARD 106
function buildBoardGeometry() {{
  const POS = {{
    N1: [46, 32], T1L: [88, 74], T1R: [172, 74],
    N2: [256, 32], T2L: [298, 74], T2R: [382, 74],
    N3: [466, 32], T3L: [508, 74], T3R: [592, 74],
    N4: [676, 32]
  }};
  const Y0 = 240, PAD = 8, P = 14.0, ROWS = 63, GAP = 10;

  let stripSvg = "";
  let dotsSvg = "";

  // Trous bus haut
  for (let half of ["L", "R"]) {{
    for (let line = 1; line <= 2; line++) {{
      for (let p = 1; p <= 25; p++) {{
        const h = HOLE_MAP.get(`TOP-${{half}}${{line}}-${{p}}`);
        if (h) dotsSvg += `<circle cx="${{h.x}}" cy="${{h.y}}" r="2.2"/>`;
      }}
    }}
  }}

  // Bandes et rails
  for (let [s, [x, w]] of Object.entries(POS)) {{
    stripSvg += `<rect x="${{x}}" y="${{Y0}}" width="${{w}}" height="${{2*PAD + ROWS*P}}" rx="3" fill="#f1f1ee"/>`;
    if (s.startsWith("N")) {{
      const my = Y0 + PAD + (ROWS - 32.5) * P;
      stripSvg += `<text x="${{x + w/2}}" y="${{my}}" font-size="10" font-weight="700" fill="#b91c1c" text-anchor="middle" font-family="Arial">W</text>`;
      stripSvg += `<text x="${{x + w/2}}" y="${{Y0 - 6}}" font-size="11" fill="#bbb" text-anchor="middle" font-family="Arial">rail ${{s}}</text>`;
    }} else {{
      const isLeft = s.endsWith("L");
      const sideLetters = isLeft ? "fghij" : "abcde";
      stripSvg += `<text x="${{x + w/2}}" y="${{Y0 - 19}}" font-size="11" fill="#bbb" text-anchor="middle" font-family="Arial">${{isLeft ? "f–j" : "a–e"}}</text>`;
      for (let ci = 0; ci < 5; ci++) {{
        const lx = x + PAD + ci * P + P / 2.0;
        stripSvg += `<text x="${{lx}}" y="${{Y0 - 4}}" font-size="11" font-weight="700" fill="#f59e0b" text-anchor="middle" font-family="Arial">${{sideLetters[ci]}}</text>`;
      }}
      if (isLeft) {{
        for (let rr of [1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60]) {{
          const ry = Y0 + PAD + (ROWS - rr) * P + P / 2.0;
          stripSvg += `<text x="${{x + w + GAP/2}}" y="${{ry + 3}}" font-size="8" font-weight="700" fill="#6b7280" text-anchor="middle" font-family="Arial">${{rr}}</text>`;
        }}
        const xr = POS[s.slice(0, 2) + "R"][0], wr = POS[s.slice(0, 2) + "R"][1];
        stripSvg += `<text x="${{(x + xr + wr)/2}}" y="${{Y0 - 34}}" font-size="13" font-weight="700" fill="#ddd" text-anchor="middle" font-family="Arial">bloc ${{s.slice(0, 2)}}</text>`;
      }}
    }}
  }}

  HOLES.forEach(h => {{
    if (h.t === "strip" || h.t === "rail") dotsSvg += `<circle cx="${{h.x}}" cy="${{h.y}}" r="2.2"/>`;
  }});

  // Bornes de connexion en haut
  let connSvg = "";
  const connsData = [
    {{ id: "BANANE_ROUGE", label: "rouge", x: 120, col: "#d62828", type: "banane" }},
    {{ id: "BANANE_NOIRE", label: "noire", x: 180, col: "#2b2b2b", type: "banane" }},
    {{ id: "BNC1", label: "BNC 1 (GBF)", x: 285, col: "#cfd2d6", type: "bnc" }},
    {{ id: "BNC2", label: "BNC 2 (Oscillo)", x: 375, col: "#cfd2d6", type: "bnc" }},
    {{ id: "VB", label: "VB (−15V)", x: 475, col: "#1d4ed8", type: "banane" }},
    {{ id: "VC", label: "VC (+15V)", x: 575, col: "#d62828", type: "banane" }},
    {{ id: "MASSE", label: "MASSE (0V)", x: 675, col: "#0ea5a4", type: "banane" }}
  ];

  connsData.forEach(c => {{
    if (c.type === "bnc") {{
      connSvg += `<circle cx="${{c.x}}" cy="60" r="27" fill="#cfd2d6" stroke="#7b8087" stroke-width="3"/>`;
      connSvg += `<circle cx="${{c.x}}" cy="60" r="16" fill="#9aa0a6"/><circle cx="${{c.x}}" cy="60" r="6" fill="#222"/>`;
      connSvg += `<text x="${{c.x}}" y="20" font-size="11" font-weight="700" fill="#ddd" text-anchor="middle" font-family="Arial">${{c.label}}</text>`;
    }} else {{
      connSvg += `<circle cx="${{c.x}}" cy="60" r="19" fill="${{c.col}}" stroke="#ddd" stroke-width="2"/><circle cx="${{c.x}}" cy="60" r="7" fill="#111"/>`;
      connSvg += `<text x="${{c.x}}" y="20" font-size="11" font-weight="700" fill="#ddd" text-anchor="middle" font-family="Arial">${{c.label}}</text>`;
    }}
  }});

  HOLES.filter(h => h.t === "conn").forEach(h => {{
    connSvg += `<circle cx="${{h.x}}" cy="${{h.y}}" r="7" fill="none" stroke="#bbb" stroke-width="3"/>`;
    if (h.id.includes("core")) connSvg += `<text x="${{h.x}}" y="${{h.y + 20}}" font-size="10" fill="#ccc" text-anchor="middle" font-family="Arial">âme</text>`;
    if (h.id.includes("shield")) connSvg += `<text x="${{h.x}}" y="${{h.y + 20}}" font-size="10" fill="#ccc" text-anchor="middle" font-family="Arial">blindage</text>`;
    if (h.id === "VB.main") connSvg += `<text x="${{h.x + 12}}" y="${{h.y + 5}}" font-size="14" font-weight="700" fill="#facc15" font-family="Arial">Vb</text>`;
    if (h.id === "VC.main") connSvg += `<text x="${{h.x + 12}}" y="${{h.y + 5}}" font-size="14" font-weight="700" fill="#facc15" font-family="Arial">Vc</text>`;
    if (h.id === "MASSE.main") connSvg += `<text x="${{h.x + 12}}" y="${{h.y + 5}}" font-size="14" font-weight="700" fill="#facc15" font-family="Arial">⏚</text>`;
  }});

  document.getElementById("svg-strips").innerHTML = stripSvg;
  document.getElementById("svg-holes-dots").innerHTML = dotsSvg;
  document.getElementById("svg-connectors").innerHTML = connSvg;

  // Trous interactifs
  let targets = "";
  HOLES.forEach(h => {{
    targets += `<circle cx="${{h.x}}" cy="${{h.y}}" r="6" class="h-target" data-id="${{h.id}}"/>`;
  }});
  document.getElementById("svg-targets").innerHTML = targets;

  // Injection du SVG dans le conteneur Split
  const host = document.getElementById("board-host-split");
  const masterSvg = document.getElementById("master-board-svg");
  host.appendChild(masterSvg);
}}

// 2. RENDU DES ÉLÉMENTS DE CÂBLAGE SUR LA PLAQUE
function wirePath(p1, p2) {{
  const dx = p2.x - p1.x;
  const dy = p2.y - p1.y;
  let c1, c2;
  if (Math.abs(dx) < 60) {{
    const bulge = -(24 + 0.05 * Math.abs(dy));
    c1 = {{ x: p1.x + bulge, y: p1.y }};
    c2 = {{ x: p2.x + bulge, y: p2.y }};
  }} else {{
    c1 = {{ x: p1.x, y: p1.y - 70 }};
    c2 = {{ x: p2.x, y: p2.y - 70 }};
  }}
  const d = `M ${{p1.x.toFixed(1)}},${{p1.y.toFixed(1)}} C ${{c1.x.toFixed(1)}},${{c1.y.toFixed(1)}} ${{c2.x.toFixed(1)}},${{c2.y.toFixed(1)}} ${{p2.x.toFixed(1)}},${{p2.y.toFixed(1)}}`;
  const mid = {{
    x: (p1.x + 3 * c1.x + 3 * c2.x + p2.x) / 8.0,
    y: (p1.y + 3 * c1.y + 3 * c2.y + p2.y) / 8.0
  }};
  return {{ d, mid }};
}}

function renderPlacedElements() {{
  // Fils
  let wSvg = "";
  state.placedWires.forEach((w, idx) => {{
    const h1 = HOLE_MAP.get(w.de), h2 = HOLE_MAP.get(w.vers);
    if (!h1 || !h2) return;
    const {{ d, mid }} = wirePath(h1, h2);
    const col = WIRE_COLORS[w.couleur] || "#999";
    wSvg += `<path d="${{d}}" fill="none" stroke="#fff" stroke-width="8" stroke-linecap="round" opacity=".85"/>`;
    wSvg += `<path d="${{d}}" fill="none" stroke="${{col}}" stroke-width="5" stroke-linecap="round"/>`;
    wSvg += `<circle cx="${{h1.x}}" cy="${{h1.y}}" r="5" fill="${{col}}" stroke="#fff" stroke-width="1.5"/>`;
    wSvg += `<circle cx="${{h2.x}}" cy="${{h2.y}}" r="5" fill="${{col}}" stroke="#fff" stroke-width="1.5"/>`;
    wSvg += `<circle cx="${{mid.x}}" cy="${{mid.y}}" r="10" fill="#0b3d91" stroke="#fff" stroke-width="2"/>`;
    wSvg += `<text x="${{mid.x}}" y="${{mid.y + 4}}" font-size="11" font-weight="700" fill="#fff" text-anchor="middle" font-family="Arial">${{idx + 1}}</text>`;
  }});
  document.getElementById("svg-wires").innerHTML = wSvg;

  // Résistances
  let rSvg = "";
  state.placedComps.forEach(r => {{
    const h1 = HOLE_MAP.get(r.a), h2 = HOLE_MAP.get(r.b);
    if (!h1 || !h2) return;
    const mx = (h1.x + h2.x) / 2.0, my = (h1.y + h2.y) / 2.0;
    const ang = Math.atan2(h2.y - h1.y, h2.x - h1.x) * 180 / Math.PI;
    const ln = Math.hypot(h2.x - h1.x, h2.y - h1.y);

    rSvg += `<line x1="${{h1.x}}" y1="${{h1.y}}" x2="${{h2.x}}" y2="${{h2.y}}" stroke="#888" stroke-width="3"/>`;
    rSvg += `<g transform="translate(${{mx}},${{my}}) rotate(${{ang}})"><rect x="${{-ln * 0.3}}" y="-6" width="${{ln * 0.6}}" height="12" rx="4" fill="#d9b77e" stroke="#8a6d3b" stroke-width="1.5"/></g>`;
    rSvg += `<text x="${{Math.max(h1.x, h2.x) + 12}}" y="${{my + 4}}" font-size="11" font-weight="700" fill="#facc15" font-family="Arial">${{r.name}} (${{r.etiquette}})</text>`;
    rSvg += `<circle cx="${{h1.x}}" cy="${{h1.y}}" r="4" fill="#333" stroke="#fff" stroke-width="1.5"/>`;
    rSvg += `<circle cx="${{h2.x}}" cy="${{h2.y}}" r="4" fill="#333" stroke="#fff" stroke-width="1.5"/>`;
  }});
  document.getElementById("svg-resistors").innerHTML = rSvg;

  // Puces
  let cSvg = "";
  state.placedChips.forEach(ch => {{
    const spec = CHIPS_LIB[ch.modele];
    if (!spec) return;
    const n = spec.dip, half = Math.floor(n / 2);
    const blk = ch.bloc, r1 = ch.rangee_broche1;
    const pins = {{}};
    for (let p = 1; p <= n; p++) {{
      let letCode = p <= half ? "j" : "a";
      let rowCode = p <= half ? r1 - (p - 1) : r1 - (half - 1) + (p - half - 1);
      const h = HOLE_MAP.get(`${{blk}}${{letCode}}${{rowCode}}`);
      if (h) pins[p] = h;
    }}
    const xs = Object.values(pins).map(h => h.x), ys = Object.values(pins).map(h => h.y);
    if (!xs.length) return;
    const x0 = Math.min(...xs) - 10, x1 = Math.max(...xs) + 10;
    const y0 = Math.min(...ys) - 10, y1 = Math.max(...ys) + 10;
    const cx = (x0 + x1) / 2.0, cy = (y0 + y1) / 2.0;

    cSvg += `<rect x="${{x0}}" y="${{y0}}" width="${{x1 - x0}}" height="${{y1 - y0}}" rx="3" fill="#2b2f36" stroke="#0b0c0e" stroke-width="2"/>`;
    cSvg += `<path d="M ${{cx - 7}},${{y0}} a 7,7 0 0 0 14,0 z" fill="#17191c"/>`;
    cSvg += `<text transform="translate(${{cx}},${{cy}}) rotate(-90)" font-size="12" font-weight="700" fill="#e5e7eb" text-anchor="middle" font-family="Arial">${{ch.ref}} ${{ch.modele}}</text>`;
    for (let [p, h] of Object.entries(pins)) {{
      const left = h.x < cx;
      cSvg += `<circle cx="${{h.x}}" cy="${{h.y}}" r="3.4" fill="#e5e7eb"/>`;
      cSvg += `<text x="${{h.x + (left ? -5 : 5)}}" y="${{h.y + 3}}" font-size="8" font-weight="700" fill="#fde68a" text-anchor="${{left ? 'end' : 'start'}}" font-family="Arial">${{p}}</text>`;
    }}
  }});
  document.getElementById("svg-chips").innerHTML = cSvg;

  updatePlacedTable();
  updateElectricalChecklist();
  triggerScopeRedraw();
}}

// 3. VALIDATION ÉLECTRIQUE (UNION-FIND)
class UF {{
  constructor() {{ this.p = new Map(); }}
  f(x) {{
    if (!this.p.has(x)) this.p.set(x, x);
    if (this.p.get(x) !== x) this.p.set(x, this.f(this.p.get(x)));
    return this.p.get(x);
  }}
  u(a, b) {{
    const ra = this.f(a), rb = this.f(b);
    if (ra !== rb) this.p.set(ra, rb);
  }}
  c(a, b) {{ return this.f(a) === this.f(b); }}
}}

function evaluateCircuit() {{
  const uf = new UF();
  HOLES.forEach(h => uf.u(h.id, h.net));

  state.placedChips.forEach(ch => {{
    const spec = CHIPS_LIB[ch.modele];
    if (!spec) return;
    const n = spec.dip, half = Math.floor(n / 2);
    for (let p = 1; p <= n; p++) {{
      let letCode = p <= half ? "j" : "a";
      let rowCode = p <= half ? ch.rangee_broche1 - (p - 1) : ch.rangee_broche1 - (half - 1) + (p - half - 1);
      uf.u(`${{ch.ref}}.${{p}}`, `${{ch.bloc}}${{letCode}}${{rowCode}}`);
    }}
  }});

  state.placedComps.forEach(c => {{
    uf.u(`${{c.name}}.a`, c.a);
    uf.u(`${{c.name}}.b`, c.b);
  }});

  state.placedWires.forEach(w => uf.u(w.de, w.vers));

  const m = MONTAGES[state.currentMontage];
  let isPowered = false;
  let isGndConnected = uf.c("MASSE.main", "TOP_L_1");
  let vsGain = 0.0;
  let phaseShift = 0.0;
  let isSaturated = false;

  if (m && m.noeuds) {{
    // Vérifier l'alimentation AOP (si TP2)
    if (state.placedChips.some(c => c.modele === "TL081")) {{
      const vplus = uf.c("U1.7", "VC.main") || uf.c("U1.7", "N2_1_u");
      const vminus = uf.c("U1.4", "VB.main") || uf.c("U1.4", "N1_1_u");
      isPowered = vplus && vminus && state.psu.on && isGndConnected;
    }} else {{
      isPowered = true;
    }}

    // Déterminer le comportement selon le montage
    if (state.currentMontage === "tp1-B1-pont-diviseur") {{
      vsGain = 0.1;
      phaseShift = 0.0;
    }} else if (state.currentMontage === "tp2-A-suiveur") {{
      vsGain = isPowered ? 1.0 : 0.0;
      phaseShift = 0.0;
    }} else if (state.currentMontage === "tp2-B1-inverseur") {{
      vsGain = isPowered ? -20.0 : 0.0;
      phaseShift = 180.0;
    }} else if (state.currentMontage === "tp2-B2-non-inverseur") {{
      vsGain = isPowered ? 10.1 : 0.0;
      phaseShift = 0.0;
    }} else if (state.currentMontage === "tp2-C-association") {{
      vsGain = isPowered ? -202.0 : 0.0;
      phaseShift = 180.0;
    }} else if (state.currentMontage === "tp2-D-soustracteur") {{
      vsGain = isPowered ? 1.0 : 0.0;
    }} else {{
      vsGain = 1.0;
    }}
  }}

  return {{ uf, isPowered, isGndConnected, vsGain, phaseShift }};
}}

function updateElectricalChecklist() {{
  const m = MONTAGES[state.currentMontage];
  const checklistBox = document.getElementById("checklist-box");
  const scoreTag = document.getElementById("score-tag");
  const alertsBox = document.getElementById("alerts-box");

  if (!m || !m.noeuds) {{
    checklistBox.innerHTML = "<div style='font-size:11px;color:var(--text-muted);'>Mode libre actif.</div>";
    scoreTag.textContent = "Libre";
    return;
  }}

  const {{ uf, isPowered, isGndConnected }} = evaluateCircuit();
  let done = 0, total = 0, html = "";
  const alerts = [];

  for (let [name, expected] of Object.entries(m.noeuds)) {{
    total++;
    let ok = true;
    for (let i = 1; i < expected.length; i++) {{
      if (!uf.c(expected[0], expected[i])) {{ ok = false; break; }}
    }}
    if (ok) {{
      done++;
      html += `<div class="checklist-item done"><span>✓</span><div><b>Nœud ${{name}}</b> <span style="font-size:10px;opacity:0.8">${{expected.slice(0, 2).join(", ")}}...</span></div></div>`;
    }} else {{
      html += `<div class="checklist-item missing"><span>○</span><div><b>Nœud ${{name}}</b> <span style="font-size:10px;color:var(--text-muted)">Relier : ${{expected.join(" — ")}}</span></div></div>`;
    }}
  }}

  checklistBox.innerHTML = html;
  scoreTag.textContent = `${{done}} / ${{total}}`;
  scoreTag.style.background = done === total ? "var(--ok)" : "#0284c7";

  // Alertes en direct
  if (!isGndConnected) {{
    alerts.push("<div class='alert-row alert-warn'>⚠️ Alimentation flottante : Borne MASSE (0V) non reliée à la plaque (TOP-L1) !</div>");
  }}
  if (!state.psu.on) {{
    alerts.push("<div class='alert-row alert-warn'>⚠️ Alimentation Keysight éteinte (bouton ALL OFF). L'AOP n'est pas alimenté.</div>");
  }}
  if (!uf.c("BNC1.shield", "TOP_L_1")) {{
    alerts.push("<div class='alert-row alert-warn'>⚠️ Blindage BNC 1 non relié à la masse (pas de retour référence signal).</div>");
  }}
  if (state.placedChips.some(c => c.modele === "TL081") && !uf.c("U1.4", "VB.main") && !uf.c("U1.4", "N1_1_u")) {{
    alerts.push("<div class='alert-row alert-err'>❌ Broche 4 TL081 (V−) non alimentée ! Sortie Vs = 0 V.</div>");
  }}
  if (done === total && total > 0 && alerts.length === 0) {{
    alerts.push("<div class='alert-row alert-ok'>🎉 PARFAIT ! Montage validé et signal stabilisé à l'oscilloscope !</div>");
  }} else if (alerts.length === 0) {{
    alerts.push("<div class='alert-row alert-ok'>✓ Aucun court-circuit. Câblage conforme en cours...</div>");
  }}

  alertsBox.innerHTML = alerts.join("");
}}

function updatePlacedTable() {{
  let rows = "", idx = 1;
  state.placedChips.forEach(ch => {{
    rows += `<tr><td>${{idx++}}</td><td>Puce</td><td>${{ch.modele}}</td><td>R.${{ch.rangee_broche1}}</td><td><button class="wire-del" onclick="delChip()">×</button></td></tr>`;
  }});
  state.placedComps.forEach((c, i) => {{
    rows += `<tr><td>${{idx++}}</td><td>R</td><td>${{c.a}}</td><td>${{c.b}}</td><td><button class="wire-del" onclick="delComp(${{i}})">×</button></td></tr>`;
  }});
  state.placedWires.forEach((w, i) => {{
    rows += `<tr><td>${{idx++}}</td><td>Fil</td><td>${{w.de}}</td><td>${{w.vers}}</td><td><button class="wire-del" onclick="delWire(${{i}})">×</button></td></tr>`;
  }});
  document.getElementById("placed-tbody").innerHTML = rows;
  document.getElementById("placed-num").textContent = (idx - 1);
}}

window.delWire = i => {{ state.placedWires.splice(i, 1); renderPlacedElements(); }};
window.delComp = i => {{ state.placedComps.splice(i, 1); renderPlacedElements(); }};
window.delChip = () => {{ state.placedChips = []; renderPlacedElements(); }};

// 4. MOTEUR PHYSIQUE DE L'OSCILLOSCOPE & RENDU CANVAS
const canvas = document.getElementById("scope-canvas");
const ctx = canvas.getContext("2d");

function triggerScopeRedraw() {{
  const W = 800, H = 480;
  const gx = 20, gy = 30, gw = 600, gh = 360;
  const dx = gw / 10.0, dy = gh / 8.0;
  const cx = gx + gw / 2.0, cy = gy + gh / 2.0;

  ctx.fillStyle = "#04101c";
  ctx.fillRect(0, 0, W, H);

  // Grille
  ctx.strokeStyle = "rgba(59, 108, 176, 0.4)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  for (let i = 0; i <= 10; i++) {{
    ctx.moveTo(gx + i * dx, gy);
    ctx.lineTo(gx + i * dx, gy + gh);
  }}
  for (let j = 0; j <= 8; j++) {{
    ctx.moveTo(gx, gy + j * dy);
    ctx.lineTo(gx + gw, gy + j * dy);
  }}
  ctx.stroke();

  // Réticule central
  ctx.strokeStyle = "rgba(91, 143, 208, 0.75)";
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(cx, gy); ctx.lineTo(cx, gy + gh);
  ctx.moveTo(gx, cy); ctx.lineTo(gx + gw, cy);
  ctx.stroke();

  // Évaluation du circuit et signaux
  const {{ isPowered, vsGain, phaseShift }} = evaluateCircuit();
  const gbf = state.gbf;
  const scope = state.scope;
  const f = gbf.f;
  const tdiv = scope.tdiv;

  // Calcul des formes d'ondes (900 points)
  const N = 900;
  const pts1 = [], pts2 = [];
  const dt = (10 * tdiv) / N;

  // Modèle AOP TL081
  const gbw = 4e6;
  const srmax = 13e6;
  const vsat = 12.5;
  const ng = Math.abs(vsGain) + 1.0;
  const fc = gbw / ng;

  let maxV1 = 0, maxV2 = 0;
  let lastVs = 0;

  for (let i = 0; i <= N; i++) {{
    const t = (i / N * 10 - 5) * tdiv;
    // Signal GBF (Ve)
    let v1 = 0;
    if (gbf.on) {{
      const ph = (f * t) % 1.0;
      if (gbf.wave === "sine") v1 = Math.sin(2 * Math.PI * ph);
      else if (gbf.wave === "square") v1 = ph < 0.5 ? 1 : -1;
      else if (gbf.wave === "triangle") v1 = ph < 0.5 ? -1 + 4 * ph : 3 - 4 * ph;
      v1 = (gbf.vpp / 2.0) * v1 + gbf.offset;
    }}
    maxV1 = Math.max(maxV1, Math.abs(v1));

    // Signal Sortie (Vs)
    let v2 = 0;
    if (gbf.on && isPowered) {{
      const atten = 1.0 / Math.sqrt(1.0 + Math.pow(f / fc, 2));
      const rad = (phaseShift * Math.PI / 180.0);
      const ph2 = (f * t) % 1.0;
      
      let rawVs = Math.sin(2 * Math.PI * ph2 + rad) * (gbf.vpp / 2.0) * Math.abs(vsGain) * atten;
      if (vsGain < 0) rawVs = -rawVs;

      const maxDelta = srmax * dt;
      let d = rawVs - lastVs;
      if (d > maxDelta) d = maxDelta;
      if (d < -maxDelta) d = -maxDelta;
      lastVs += d;

      v2 = Math.max(-vsat, Math.min(vsat, lastVs));
    }} else {{
      v2 = 0;
    }}
    maxV2 = Math.max(maxV2, Math.abs(v2));

    const y1 = cy - ((v1 - scope.ch1_offset * scope.ch1_vdiv) / scope.ch1_vdiv) * dy;
    const y2 = cy - ((v2 - scope.ch2_offset * scope.ch2_vdiv) / scope.ch2_vdiv) * dy;
    pts1.push({{ x: gx + i / N * gw, y: y1 }});
    pts2.push({{ x: gx + i / N * gw, y: y2 }});
  }}

  // Clip de la zone grille
  ctx.save();
  ctx.beginPath();
  ctx.rect(gx, gy, gw, gh);
  ctx.clip();

  // Dessin Voie 1 (Jaune)
  ctx.strokeStyle = "#facc15";
  ctx.lineWidth = 2.5;
  ctx.beginPath();
  pts1.forEach((p, idx) => {{
    if (idx === 0) ctx.moveTo(p.x, p.y);
    else ctx.lineTo(p.x, p.y);
  }});
  ctx.stroke();

  // Dessin Voie 2 (Verte)
  ctx.strokeStyle = "#22c55e";
  ctx.lineWidth = 2.5;
  ctx.beginPath();
  pts2.forEach((p, idx) => {{
    if (idx === 0) ctx.moveTo(p.x, p.y);
    else ctx.lineTo(p.x, p.y);
  }});
  ctx.stroke();

  // Curseurs Interactifs X & Y
  if (scope.cursorMode === "x" || scope.cursorMode === "both") {{
    ctx.strokeStyle = "#f97316";
    ctx.lineWidth = 1.5;
    ctx.setLineDash([5, 4]);
    const x1Pos = cx + scope.curX1 * dx;
    ctx.beginPath(); ctx.moveTo(x1Pos, gy); ctx.lineTo(x1Pos, gy + gh); ctx.stroke();
    const x2Pos = cx + scope.curX2 * dx;
    ctx.beginPath(); ctx.moveTo(x2Pos, gy); ctx.lineTo(x2Pos, gy + gh); ctx.stroke();
    ctx.setLineDash([]);
  }}
  if (scope.cursorMode === "y" || scope.cursorMode === "both") {{
    ctx.strokeStyle = "#f97316";
    ctx.lineWidth = 1.5;
    ctx.setLineDash([5, 4]);
    const y1Pos = cy - scope.curY1 * dy;
    ctx.beginPath(); ctx.moveTo(gx, y1Pos); ctx.lineTo(gx + gw, y1Pos); ctx.stroke();
    const y2Pos = cy - scope.curY2 * dy;
    ctx.beginPath(); ctx.moveTo(gx, y2Pos); ctx.lineTo(gx + gw, y2Pos); ctx.stroke();
    ctx.setLineDash([]);
  }}

  ctx.restore();

  // Fanions des voies
  ctx.fillStyle = "#facc15";
  ctx.fillRect(gx, cy - 8, 12, 16);
  ctx.fillStyle = "#000";
  ctx.font = "bold 10px Arial";
  ctx.fillText("1", gx + 3, cy + 4);

  ctx.fillStyle = "#22c55e";
  ctx.fillRect(gx, cy - 8, 12, 16);
  ctx.fillStyle = "#000";
  ctx.fillText("2", gx + 3, cy + 4);

  // Bandeau supérieur de l'écran
  ctx.fillStyle = "#ddd";
  ctx.font = "12px Arial";
  ctx.fillText(`1  ${{scope.ch1_vdiv * 1000}}mV/`, gx + 10, 20);
  ctx.fillText(`2  ${{scope.ch2_vdiv}}V/`, gx + 110, 20);
  ctx.fillText(`0.0s`, cx - 60, 20);
  ctx.fillText(`${{tdiv * 1e6}}µs/`, cx - 10, 20);
  ctx.fillText("Auto", cx + 70, 20);
  ctx.fillText("ƒ 1 0.00V", gx + gw - 70, 20);

  // Panneau de droite Keysight
  const px = gx + gw + 10, pw = W - px - 10;
  ctx.fillStyle = "#1a4f94";
  ctx.fillRect(px, gy, pw, gh);
  ctx.fillStyle = "#fff";
  ctx.font = "bold 13px Arial";
  ctx.fillText("KEYSIGHT", px + 40, gy + 24);
  ctx.font = "7px Arial";
  ctx.fillText("TECHNOLOGIES", px + 40, gy + 34);

  ctx.font = "11px Arial";
  ctx.fillStyle = "#bfe0ff";
  ctx.fillText("Mesures directes :", px + 10, gy + 65);
  ctx.fillStyle = "#fff";
  const realVpp1 = (maxV1 * 2).toFixed(2);
  const realVpp2 = (maxV2 * 2).toFixed(2);
  ctx.fillText(`Cr-cr(1) : ${{realVpp1}} V`, px + 10, gy + 90);
  ctx.fillText(`Cr-cr(2) : ${{realVpp2}} V`, px + 10, gy + 112);
  ctx.fillText(`Fréq(1) : ${{f}} Hz`, px + 10, gy + 134);
  ctx.fillText(`Av = ${{maxV1 > 0 ? (maxV2 / maxV1).toFixed(1) : 0}}`, px + 10, gy + 156);
  if (maxV2 >= vsat - 0.1) {{
    ctx.fillStyle = "#f87171";
    ctx.fillText("⚠ SATURATION ±12.5V", px + 10, gy + 185);
  }}

  // Bandeau inférieur : Mesures ISIFC
  ctx.fillStyle = "#101622";
  ctx.fillRect(0, H - 55, W, 55);
  ctx.fillStyle = "#facc15";
  ctx.font = "11px Arial";
  ctx.fillText("Moy - PE(1) : 0.00 V", 20, H - 34);
  ctx.fillText(`Fréq(1) : ${{f}} Hz`, 20, H - 16);
  ctx.fillStyle = "#22c55e";
  ctx.fillText(`Cr-cr(1) : ${{realVpp1}} V`, 200, H - 34);
  ctx.fillText(`Cr-cr(2) : ${{realVpp2}} V`, 200, H - 16);
  ctx.fillStyle = "#e2e8f0";
  ctx.fillText(`Max(1) : ${{maxV1.toFixed(2)}} V`, 400, H - 34);
  ctx.fillText(`Max(2) : ${{maxV2.toFixed(2)}} V`, 400, H - 16);

  // Lecture curseurs
  const dtCur = Math.abs(scope.curX2 - scope.curX1) * tdiv;
  const dvCur = Math.abs(scope.curY2 - scope.curY1) * scope.ch2_vdiv;
  const fCur = dtCur > 0 ? (1.0 / dtCur).toFixed(0) : "∞";
  document.getElementById("cursor-readout").textContent = 
    `ΔX = ${{ (dtCur * 1e6).toFixed(1) }} µs (${{fCur}} Hz) | ΔY = ${{dvCur.toFixed(2)}} V`;
}}

// 5. DRAG & DROP DES CURSEURS SUR LE CANVAS DE L'OSCILLOSCOPE
canvas.addEventListener("pointerdown", e => {{
  const rect = canvas.getBoundingClientRect();
  const scaleX = canvas.width / rect.width;
  const scaleY = canvas.height / rect.height;
  const mx = (e.clientX - rect.left) * scaleX;
  const my = (e.clientY - rect.top) * scaleY;

  const gx = 20, gy = 30, gw = 600, gh = 360;
  const dx = gw / 10.0, dy = gh / 8.0;
  const cx = gx + gw / 2.0, cy = gy + gh / 2.0;

  const curX1px = cx + state.scope.curX1 * dx;
  const curX2px = cx + state.scope.curX2 * dx;
  const curY1px = cy - state.scope.curY1 * dy;
  const curY2px = cy - state.scope.curY2 * dy;

  if (Math.abs(mx - curX1px) < 15) state.scope.draggingCursor = "x1";
  else if (Math.abs(mx - curX2px) < 15) state.scope.draggingCursor = "x2";
  else if (Math.abs(my - curY1px) < 15) state.scope.draggingCursor = "y1";
  else if (Math.abs(my - curY2px) < 15) state.scope.draggingCursor = "y2";
}});

window.addEventListener("pointermove", e => {{
  if (!state.scope.draggingCursor) return;
  const rect = canvas.getBoundingClientRect();
  const scaleX = canvas.width / rect.width;
  const scaleY = canvas.height / rect.height;
  const mx = (e.clientX - rect.left) * scaleX;
  const my = (e.clientY - rect.top) * scaleY;

  const gx = 20, gy = 30, gw = 600, gh = 360;
  const dx = gw / 10.0, dy = gh / 8.0;
  const cx = gx + gw / 2.0, cy = gy + gh / 2.0;

  if (state.scope.draggingCursor === "x1") {{
    state.scope.curX1 = Math.max(-5, Math.min(5, (mx - cx) / dx));
  }} else if (state.scope.draggingCursor === "x2") {{
    state.scope.curX2 = Math.max(-5, Math.min(5, (mx - cx) / dx));
  }} else if (state.scope.draggingCursor === "y1") {{
    state.scope.curY1 = Math.max(-4, Math.min(4, (cy - my) / dy));
  }} else if (state.scope.draggingCursor === "y2") {{
    state.scope.curY2 = Math.max(-4, Math.min(4, (cy - my) / dy));
  }}
  triggerScopeRedraw();
}});

window.addEventListener("pointerup", () => {{
  state.scope.draggingCursor = null;
}});

// 6. INTERACTIONS PLAQUE & CÂBLAGE
function setupBoardInteractions() {{
  const targets = document.getElementById("svg-targets");
  const rubberband = document.getElementById("svg-rubberband");
  const selMarker = document.getElementById("svg-sel");
  const inspAddr = document.getElementById("insp-addr");
  const inspDesc = document.getElementById("insp-desc");
  const inspBadge = document.getElementById("insp-badge");
  const pointerInfo = document.getElementById("active-pointer-info");

  targets.addEventListener("pointerover", e => {{
    const hid = e.target.dataset.id;
    if (!hid) return;
    const h = HOLE_MAP.get(hid);
    if (!h) return;
    inspAddr.textContent = h.id;
    inspDesc.textContent = h.desc;
    inspBadge.textContent = `${{h.x}}, ${{h.y}}`;
    pointerInfo.textContent = `Trou : ${{h.id}} — ${{h.desc}}`;
  }});

  targets.addEventListener("click", e => {{
    const hid = e.target.dataset.id;
    if (!hid) return;
    handleHoleClick(hid);
  }});

  const masterSvg = document.getElementById("master-board-svg");
  masterSvg.addEventListener("pointermove", e => {{
    if (!state.firstHole) return;
    const pt = masterSvg.createSVGPoint();
    pt.x = e.clientX; pt.y = e.clientY;
    const p = pt.matrixTransform(masterSvg.getScreenCTM().inverse());
    rubberband.setAttribute("x2", p.x);
    rubberband.setAttribute("y2", p.y);
  }});

  function handleHoleClick(hid) {{
    if (state.tool === "delete") {{
      const wIdx = state.placedWires.findIndex(w => w.de === hid || w.vers === hid);
      if (wIdx >= 0) {{ state.placedWires.splice(wIdx, 1); renderPlacedElements(); return; }}
      const rIdx = state.placedComps.findIndex(r => r.a === hid || r.b === hid);
      if (rIdx >= 0) {{ state.placedComps.splice(rIdx, 1); renderPlacedElements(); return; }}
      return;
    }}

    if (state.tool === "chip") {{
      const h = HOLE_MAP.get(hid);
      if (!h || h.t !== "strip") return;
      const blk = hid.slice(0, 2);
      const rowMatch = hid.match(/\\d+$/);
      if (!rowMatch) return;
      state.placedChips = [{{
        ref: "U1",
        modele: state.chipVal,
        bloc: blk,
        rangee_broche1: parseInt(rowMatch[0], 10),
        encoche: "haut"
      }}];
      renderPlacedElements();
      resetSel();
      return;
    }}

    if (!state.firstHole) {{
      state.firstHole = hid;
      const h = HOLE_MAP.get(hid);
      selMarker.setAttribute("cx", h.x);
      selMarker.setAttribute("cy", h.y);
      selMarker.style.display = "block";
      rubberband.setAttribute("x1", h.x);
      rubberband.setAttribute("y1", h.y);
      rubberband.setAttribute("x2", h.x);
      rubberband.setAttribute("y2", h.y);
      rubberband.style.display = "block";
    }} else {{
      const h1 = state.firstHole, h2 = hid;
      if (h1 !== h2) {{
        if (state.tool === "wire") {{
          state.placedWires.push({{ n: state.placedWires.length + 1, de: h1, vers: h2, couleur: state.wireColor }});
        }} else if (state.tool === "resistor") {{
          const val = state.resistorVal;
          state.placedComps.push({{
            name: "R" + (state.placedComps.length + 1),
            type: "resistor",
            a: h1, b: h2, ohm: val,
            etiquette: val >= 1000 ? (val / 1000) + " kΩ" : val + " Ω"
          }});
        }}
        renderPlacedElements();
      }}
      resetSel();
    }}
  }}

  function resetSel() {{
    state.firstHole = null;
    selMarker.style.display = "none";
    rubberband.style.display = "none";
  }}
}}

// 7. GESTION DES ONGLETS & CONTRÔLES INSTRUMENTS
function setupUIControls() {{
  document.querySelectorAll(".nav-tab").forEach(tab => {{
    tab.addEventListener("click", () => {{
      document.querySelectorAll(".nav-tab").forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      const v = tab.dataset.view;
      state.activeView = v;

      document.querySelectorAll(".view-panel").forEach(p => p.classList.add("hidden"));
      const target = document.getElementById("view-" + v);
      if (target) target.classList.remove("hidden");

      const masterSvg = document.getElementById("master-board-svg");
      if (v === "split") {{
        document.getElementById("board-host-split").appendChild(masterSvg);
      }} else if (v === "board") {{
        document.getElementById("board-host-full").appendChild(masterSvg);
      }}
      triggerScopeRedraw();
    }});
  }});

  document.querySelectorAll(".t-btn").forEach(btn => {{
    btn.addEventListener("click", () => {{
      document.querySelectorAll(".t-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      state.tool = btn.dataset.tool;
      document.getElementById("resistor-select-box").style.display = state.tool === "resistor" ? "flex" : "none";
      document.getElementById("chip-select-box").style.display = state.tool === "chip" ? "flex" : "none";
    }});
  }});

  document.querySelectorAll(".color-dot").forEach(d => {{
    d.addEventListener("click", () => {{
      document.querySelectorAll(".color-dot").forEach(x => x.classList.remove("active"));
      d.classList.add("active");
      state.wireColor = d.dataset.color;
    }});
  }});

  // Contrôles Oscilloscope
  document.getElementById("btn-autoscale").addEventListener("click", () => {{
    const {{ vsGain }} = evaluateCircuit();
    const gbf = state.gbf;
    if (gbf.f > 0) {{
      const T = 1.0 / gbf.f;
      state.scope.tdiv = T / 4.0;
      document.getElementById("scope-tdiv").value = state.scope.tdiv;
    }}
    if (Math.abs(vsGain) >= 10) {{
      state.scope.ch2_vdiv = 5.0;
    }} else {{
      state.scope.ch2_vdiv = 1.0;
    }}
    document.getElementById("scope-ch2-vdiv").value = state.scope.ch2_vdiv;
    triggerScopeRedraw();
  }});

  document.getElementById("btn-run-stop").addEventListener("click", e => {{
    state.scope.running = !state.scope.running;
    e.target.textContent = state.scope.running ? "RUN" : "STOP";
    e.target.style.background = state.scope.running ? "#15803d" : "#ef4444";
  }});

  document.getElementById("scope-ch1-vdiv").addEventListener("change", e => {{
    state.scope.ch1_vdiv = parseFloat(e.target.value);
    triggerScopeRedraw();
  }});
  document.getElementById("scope-ch2-vdiv").addEventListener("change", e => {{
    state.scope.ch2_vdiv = parseFloat(e.target.value);
    triggerScopeRedraw();
  }});
  document.getElementById("scope-tdiv").addEventListener("change", e => {{
    state.scope.tdiv = parseFloat(e.target.value);
    triggerScopeRedraw();
  }});
  document.getElementById("scope-cursors-mode").addEventListener("change", e => {{
    state.scope.cursorMode = e.target.value;
    triggerScopeRedraw();
  }});
  document.getElementById("scope-ch1-offset").addEventListener("input", e => {{
    state.scope.ch1_offset = parseFloat(e.target.value);
    triggerScopeRedraw();
  }});
  document.getElementById("scope-ch2-offset").addEventListener("input", e => {{
    state.scope.ch2_offset = parseFloat(e.target.value);
    triggerScopeRedraw();
  }});

  // Contrôles GBF
  document.getElementById("gbf-onoff-btn").addEventListener("click", e => {{
    state.gbf.on = !state.gbf.on;
    e.target.textContent = state.gbf.on ? "OUT: ON" : "OUT: OFF";
    e.target.style.background = state.gbf.on ? "#15803d" : "#64748b";
    triggerScopeRedraw();
  }});
  document.getElementById("gbf-wave-select").addEventListener("change", e => {{
    state.gbf.wave = e.target.value;
    triggerScopeRedraw();
  }});
  document.getElementById("gbf-freq-val").addEventListener("input", e => {{
    state.gbf.f = Math.max(10, parseFloat(e.target.value) || 1000);
    triggerScopeRedraw();
  }});
  document.getElementById("gbf-vpp-val").addEventListener("input", e => {{
    state.gbf.vpp = Math.max(0.01, parseFloat(e.target.value) || 0.4);
    triggerScopeRedraw();
  }});

  // Contrôles Alimentation
  document.getElementById("psu-onoff-btn").addEventListener("click", e => {{
    state.psu.on = !state.psu.on;
    e.target.textContent = state.psu.on ? "ALL ON" : "ALL OFF";
    e.target.style.background = state.psu.on ? "#15803d" : "#64748b";
    updateElectricalChecklist();
    triggerScopeRedraw();
  }});

  // Sélecteur de montage & boutons généraux
  document.getElementById("select-montage").addEventListener("change", e => {{
    loadMontage(e.target.value);
  }});
  document.getElementById("btn-solution").addEventListener("click", loadSolution);
  document.getElementById("btn-clear").addEventListener("click", () => {{
    if (!confirm("Voulez-vous tout effacer ?")) return;
    state.placedWires = []; state.placedComps = []; state.placedChips = [];
    renderPlacedElements();
  }});
  document.getElementById("btn-undo").addEventListener("click", () => {{
    if (state.placedWires.length > 0) state.placedWires.pop();
    else if (state.placedComps.length > 0) state.placedComps.pop();
    renderPlacedElements();
  }});
}}

function loadMontage(mkey) {{
  state.currentMontage = mkey;
  const m = MONTAGES[mkey];
  if (m) {{
    document.getElementById("montage-title-desc").textContent = `${{m.titre}} — ${{m.objectif || ''}}`;
    if (m.gbf_def) {{
      state.gbf.wave = m.gbf_def.forme || "sine";
      state.gbf.f = m.gbf_def.f || 1000;
      state.gbf.vpp = m.gbf_def.vpp || 0.4;
      document.getElementById("gbf-wave-select").value = state.gbf.wave;
      document.getElementById("gbf-freq-val").value = state.gbf.f;
      document.getElementById("gbf-vpp-val").value = state.gbf.vpp;
    }}
  }}
  const ov = document.getElementById("overview-host");
  if (ov) {{
    let rows = "";
    if (m) for (const c of (m.cables || [])) {{
      rows += `<tr><td><b>${{c.id}}</b> — ${{c.nom}}</td><td>${{c.de}}</td><td>${{c.vers}}</td><td>${{c.role}}</td></tr>`;
    }}
    ov.innerHTML = (m && m.overview_svg
      ? `<h3 style="font:600 16px Arial;margin:0 0 8px">Vue d'ensemble de la table : câbles entre les appareils et la plaque</h3>${{m.overview_svg}}
         <table style="border-collapse:collapse;font:13px Arial;margin-top:10px;width:100%">
         <tr style="text-align:left;border-bottom:1px solid #ccc"><th>Câble</th><th>De</th><th>Vers</th><th>Rôle</th></tr>${{rows}}</table>`
      : "<p>Pas de câblage appareils défini pour ce montage.</p>");
  }}
  state.placedWires = []; state.placedComps = []; state.placedChips = [];
  renderPlacedElements();
}}

function loadSolution() {{
  const m = MONTAGES[state.currentMontage];
  if (!m) return;
  state.placedWires = JSON.parse(JSON.stringify(m.fils || []));
  state.placedComps = [];
  for (let [name, c] of Object.entries(m.composants || {{}})) {{
    if (c.type === "resistor") {{
      state.placedComps.push({{
        name, type: "resistor", a: c.a, b: c.b, ohm: c.ohm, etiquette: c.etiquette
      }});
    }}
  }}
  state.placedChips = JSON.parse(JSON.stringify(m.puces || []));
  renderPlacedElements();
}}

// INITIALISATION DU BANC
window.addEventListener("DOMContentLoaded", () => {{
  buildBoardGeometry();
  setupBoardInteractions();
  setupUIControls();
  loadMontage("tp2-B1-inverseur");
  triggerScopeRedraw();
}});
</script>
</body>
</html>
"""

if __name__ == "__main__":
    generate()
