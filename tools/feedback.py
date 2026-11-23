#!/usr/bin/env python3
"""Rassemble les retours des utilisateurs (Issues GitHub étiquetées « retour-montage ») en un tableau.

  python tools/feedback.py            # affiche les retours ouverts, classés par montage
  python tools/feedback.py --all      # inclut les retours fermés
  python tools/feedback.py --md RETOURS.md   # écrit aussi un fichier Markdown

Nécessite la CLI GitHub (`gh auth login`). Pour chaque retour : ouvrir le fichier indiqué dans docs/MODIFIER_APRES_VERIF.md,
corriger, `python tools/build_app.py && node tests/engine_test.js`, noter la ligne dans CORRECTIONS.md, puis `git push`
(la page se met à jour et l'Issue se ferme avec « Fixes #N » dans le message de commit).
"""
import json, re, subprocess, sys

def sections(body):
    out, cur = {}, None
    for line in (body or "").splitlines():
        m = re.match(r"###\s+(.*)", line)
        if m: cur = m.group(1).strip(); out[cur] = []
        elif cur: out[cur].append(line)
    return {k: "\n".join(v).strip() for k, v in out.items()}

def main():
    state = "all" if "--all" in sys.argv else "open"
    r = subprocess.run(["gh", "issue", "list", "--label", "retour-montage", "--state", state, "--limit", "200",
                        "--json", "number,title,body,state,createdAt,url,author"], capture_output=True, text=True)
    if r.returncode:
        sys.exit("gh a échoué : " + r.stderr.strip())
    rows = []
    for i in json.loads(r.stdout):
        s = sections(i["body"])
        rows.append({"n": i["number"], "montage": s.get("Montage concerné", "?") or "?", "type": s.get("Type de retour", "?"),
                     "texte": s.get("Ce qui ne va pas, et ce que tu attendais", "").replace("\n", " ")[:200],
                     "url": i["url"], "date": i["createdAt"][:10], "etat": i["state"]})
    rows.sort(key=lambda x: (x["montage"], x["n"]))
    if not rows:
        print("Aucun retour pour le moment."); return
    md = ["| # | Date | Montage | Type | Retour | Lien |", "|---|---|---|---|---|---|"]
    for x in rows:
        line = f'| {x["n"]} | {x["date"]} | {x["montage"]} | {x["type"]} | {x["texte"]} | {x["url"]} |'
        md.append(line)
        print(f'#{x["n"]:<4} {x["date"]} {x["montage"]:<26} {x["type"][:34]:<34} {x["texte"][:90]}')
    if "--md" in sys.argv:
        path = sys.argv[sys.argv.index("--md") + 1]
        open(path, "w", encoding="utf-8").write("# Retours des utilisateurs\n\n" + "\n".join(md) + "\n")
        print("écrit", path)

if __name__ == "__main__":
    main()
