#!/usr/bin/env python3
"""Découpe les extraits du VRAI sujet de TP (PDF) et écrit app/sujet_data.js.

- Aucun texte n'est réécrit : ce sont des captures des pages du sujet.
- Les PDF du sujet appartiennent à l'établissement : ils ne sont PAS dans le dépôt.
  Cherchés dans $LABDEC_SUJET_DIR, sinon dans le dossier « TP (electronique) » (2 niveaux au-dessus du projet).
  S'ils sont absents (ou PyMuPDF manquant), on écrit `const SUJET = null;` et l'app affiche le texte des fichiers montage.
- Pour corriger un découpage : modifier PIECES (page, y_haut, y_bas en points PDF, A4 = 595 x 842) puis
  `python tools/build_app.py`.
"""
import base64, io, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "app" / "sujet_data.js"
X0, X1, DPI, QUALITY = 30, 566, 115, 72

# clé -> (TP, titre, genre, [(page, y0, y1), ...])   genre : prep | enonce | q | annexe
PIECES = {
    "tp1_prep":   (1, "Préparation : série E12, conditions sur les résistances", "prep", [(1, 508, 746), (2, 76, 192)]),
    "tp1_A":      (1, "A. Utilisation de l'oscilloscope et du GBF", "enonce", [(2, 210, 462)]),
    "tp1_B":      (1, "B. Pont diviseur par 10 : énoncé et figure 1", "enonce", [(2, 480, 778)]),
    "tp1_B_q":    (1, "B. Réalisation et mesures", "q", [(3, 74, 300)]),
    "tp1_B_lim":  (1, "B. Limites du montage", "q", [(3, 306, 476)]),
    "tp1_C":      (1, "C. Impédance interne : énoncé et figure 2", "enonce", [(3, 478, 778)]),
    "tp1_C_q":    (1, "C. Mesure de la résistance interne", "q", [(4, 74, 262)]),
    "tp1_C_hz":   (1, "C. Réglage « High Z »", "q", [(4, 270, 470)]),
    "tp1_D":      (1, "D. LED", "q", [(4, 498, 640)]),
    "tp2_intro":  (2, "TP2 : objectif, préparation, brochage de l'AOP", "prep", [(1, 92, 490)]),
    "tp2_A":      (2, "A. Suiveur : énoncé et figure 2", "enonce", [(1, 487, 776)]),
    "tp2_A_q":    (2, "A. Suiveur : questions", "q", [(2, 74, 255)]),
    "tp2_B":      (2, "B. Inverseur / non inverseur : énoncé et figure 3", "enonce", [(2, 272, 492)]),
    "tp2_B_q":    (2, "B. Questions (gain, coupure, GBP, déphasage)", "q", [(2, 490, 726)]),
    "tp2_C":      (2, "C. Association de deux montages", "q", [(3, 94, 256)]),
    "tp2_D":      (2, "D. Soustracteur (bonus)", "q", [(3, 258, 572)]),
    "tp3_prep":   (3, "TP3 : objectif et préparation", "prep", [(1, 92, 392)]),
    "tp3_A":      (3, "A. Porte NAND : énoncé, figure 1, tensions de sortie", "enonce", [(1, 390, 772)]),
    "tp3_A2":     (3, "A.2 Tensions d'entrée de basculement", "q", [(2, 76, 300)]),
    "tp3_B":      (3, "B. Bascule D : énoncé, figure 2, tensions de sortie", "enonce", [(2, 308, 772)]),
    "tp3_B_ret":  (3, "B.2 Retard de propagation", "q", [(3, 74, 196)]),
    "tp3_C":      (3, "C. Compteurs : énoncé, figure 3, questions", "enonce", [(3, 194, 640)]),
    "an_gbf":     (1, "Annexe 1 : générateur basse fréquence", "annexe", [(5, 78, 776)]),
    "an_scope":   (1, "Annexe 2 : oscilloscope", "annexe", [(6, 78, 776)]),
    "an_board":   (1, "Annexe 3 : platine Labdec", "annexe", [(7, 102, 772)]),
    "an_psu":     (2, "Annexe 1 (TP2) : alimentation stabilisée", "annexe", [(4, 78, 748)]),
}
MONTAGES = {
    "tp1-B1-pont-diviseur":     ["tp1_prep", "tp1_A", "tp1_B", "tp1_B_q", "tp1_B_lim"],
    "tp1-C1-impedance-interne": ["tp1_C", "tp1_C_q", "tp1_C_hz"],
    "tp1-D1-led":               ["tp1_D"],
    "tp2-A-suiveur":            ["tp2_intro", "tp2_A", "tp2_A_q"],
    "tp2-B1-inverseur":         ["tp2_intro", "tp2_B", "tp2_B_q"],
    "tp2-B2-non-inverseur":     ["tp2_intro", "tp2_B", "tp2_B_q"],
    "tp2-C-association":        ["tp2_C"],
    "tp2-D-soustracteur":       ["tp2_D"],
    "tp3-A-nand":               ["tp3_prep", "tp3_A"],
    "tp3-A2-seuils":            ["tp3_A2"],
    "tp3-B-bascule-D":          ["tp3_B", "tp3_B_ret"],
    "tp3-C-compteur":           ["tp3_C"],
}
ANNEXES = {"gbf": ["an_gbf"], "scope": ["an_scope"], "psu": ["an_psu"], "board": ["an_board"]}


def find_pdf(tp):
    bases = [Path(os.environ["LABDEC_SUJET_DIR"])] if os.environ.get("LABDEC_SUJET_DIR") else []
    bases += [ROOT.parents[1], ROOT.parent, ROOT]
    for b in bases:
        for p in sorted(b.glob(f"Sujet TP {tp}*.pdf")):
            return p
    return None


def render(docs, boxes):
    import fitz
    from PIL import Image
    ims = []
    for page, y0, y1 in boxes:
        pg = docs.load_page(page - 1)
        pix = pg.get_pixmap(clip=fitz.Rect(X0, y0, X1, y1), dpi=DPI)
        ims.append(Image.frombytes("RGB", (pix.width, pix.height), pix.samples))
    w = max(i.width for i in ims)
    out = Image.new("RGB", (w, sum(i.height for i in ims) + 6 * (len(ims) - 1)), "white")
    y = 0
    for i in ims:
        out.paste(i, (0, y)); y += i.height + 6
    buf = io.BytesIO()
    out.save(buf, "JPEG", quality=QUALITY, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode(), out.size


def keep_existing(why):
    """Sans PDF (ex. GitHub Actions) : on garde app/sujet_data.js s'il contient déjà des extraits."""
    if OUT.exists() and "= null" not in OUT.read_text(encoding="utf-8")[:40]:
        print(f"sujet : {why} -> extraits existants conservés ({OUT.stat().st_size // 1024} Ko)")
        return True
    return False


def main(preview_dir=None):
    try:
        import fitz  # noqa: F401
        import PIL  # noqa: F401
    except Exception:
        if keep_existing("PyMuPDF/Pillow absents"):
            return
        OUT.write_text("const SUJET = null;\n", encoding="utf-8")
        print("sujet : PyMuPDF/Pillow absents -> pas d'extraits (SUJET = null)")
        return
    docs = {}
    for tp in (1, 2, 3):
        p = find_pdf(tp)
        if p:
            import fitz
            docs[tp] = fitz.open(p)
    if len(docs) < 3:
        if keep_existing("PDF absents"):
            return
        OUT.write_text("const SUJET = null;\n", encoding="utf-8")
        print(f"sujet : PDF trouvés pour TP {sorted(docs)} seulement -> pas d'extraits (SUJET = null)")
        return
    pieces = {}
    for key, (tp, titre, genre, boxes) in PIECES.items():
        img, size = render_tp(docs, key)
        pieces[key] = {"t": titre, "k": genre, "img": img, "w": size[0], "h": size[1]}
        if preview_dir:
            Path(preview_dir).mkdir(parents=True, exist_ok=True)
            (Path(preview_dir) / f"{key}.jpg").write_bytes(base64.b64decode(img.split(",", 1)[1]))
    import json
    data = {"pieces": pieces, "montages": MONTAGES, "annexes": ANNEXES}
    OUT.write_text("const SUJET = " + json.dumps(data, ensure_ascii=False) + ";\n", encoding="utf-8")
    print(f"sujet : {len(pieces)} extraits, {OUT.stat().st_size // 1024} Ko -> {OUT.name}")


def render_tp(docs, key):
    tp, _, _, boxes = PIECES[key]
    return render(docs[tp], boxes)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
