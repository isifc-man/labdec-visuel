#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Assemble l'app v2 en UN fichier HTML autonome (ouvrable hors ligne) :  /usr/bin/python3 tools/build_app.py
Sources : app/index.html (gabarit) + app/css + app/js + app/partials ; données : app/data.js (tools/export_app_data.py)."""
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
APP = ROOT / "app"
JS_ORDER = ["data.js", "sujet_data.js", "js/engine.js", "js/state.js", "js/runtime.js", "js/cables.js", "js/zoom.js", "js/faces.js", "js/board.js", "js/checks.js",
            "js/interactions.js", "js/scope.js", "js/gbf.js", "js/psu.js", "js/dock.js", "js/lesson.js", "js/main.js"]


def main():
    subprocess.run([sys.executable, str(ROOT / "tools" / "export_app_data.py")], check=True)
    subprocess.run([sys.executable, str(ROOT / "tools" / "sujet_crops.py")], check=True)   # extraits du vrai sujet si les PDF sont présents, sinon SUJET = null
    css = (APP / "css/base.css").read_text(encoding="utf-8") + "\n" + (APP / "css/app.css").read_text(encoding="utf-8")
    js = "\n".join("// ==== %s ====\n%s" % (f, (APP / f).read_text(encoding="utf-8")) for f in JS_ORDER)
    js = js.replace("</script>", "<\\/script>")
    html = (APP / "index.html").read_text(encoding="utf-8")
    html = html.replace("/*@@CSS@@*/", css).replace("<!--@@BOARD_SVG@@-->", (APP / "partials/board_svg.html").read_text(encoding="utf-8")).replace("/*@@JS@@*/", js)
    out = ROOT / "out" / "labdec_app.html"
    out.write_text(html, encoding="utf-8")
    print("écrit", out, out.stat().st_size // 1024, "Ko")


if __name__ == "__main__":
    main()
