"""EXEMPLE d'un bloc de validation (TP3 - partie B.2 « Retard de propagation »).
Fichier NOUVEAU : ne modifie aucune page existante. Sortie : out/exemple_bloc_tp3_B2.html
Lancer : /usr/bin/python3 tools/exemple_bloc.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import render  # noqa: E402
import pages_pred  # noqa: E402  (seulement pour réutiliser PANEL)
import ttl_ports  # noqa: E402

E = render.E

# ---- hypothèses du modèle (toutes affichées dans la page) -------------------------------------------------
TD = 5e-9            # base de temps : 5 ns/div -> fenêtre de 50 ns
T_RISE_CLK = 5e-9    # front du SYNC du GBF : HYPOTHÈSE (behavior.yaml : "10 ns supposé", à remplir)
T_RISE_Q = 8e-9      # front de Q : HYPOTHÈSE
TPLH_TYP, TPLH_MAX = 13e-9, 25e-9   # behavior.yaml : 74LS74, source « guide banc TP3 »
V_HI_CLK, V_LO = 5.0, 0.0
VOH_Q, VOL_Q = 3.4, 0.25            # HYPOTHÈSE « typique » (la fiche garantit seulement ≥ 2,7 V et ≤ 0,4 V)


def ramp(t, t0, tr, v0, v1):
    """Front linéaire commençant en t0 (début), durée tr."""
    if t <= t0:
        return v0
    if t >= t0 + tr:
        return v1
    return v0 + (v1 - v0) * (t - t0) / tr


def samples():
    N = 900
    clk, q = [], []
    # t = 0 = franchissement de 50 % du front de CLK -> début du front à -tr/2
    for i in range(N + 1):
        t = (i / float(N) * 10 - 5) * TD
        clk.append(ramp(t, -T_RISE_CLK / 2, T_RISE_CLK, V_LO, V_HI_CLK))
        # Q franchit 50 % à t = tPLH -> début de son front à tPLH - tr/2
        q.append(ramp(t, TPLH_TYP - T_RISE_Q / 2, T_RISE_Q, VOL_Q, VOH_Q))
    return clk, q


def scope_cfg(clk, q):
    sc = 2.0
    return {
        "tdiv": TD, "panel": pages_pred.PANEL,
        "ch1": {"scale": sc, "offset": 2.5 - 2 * sc, "samples": clk},
        "ch2": {"scale": sc, "offset": (VOL_Q + VOH_Q) / 2 + 2 * sc, "samples": q},
        "trig": {"src": 1, "level": "2.50V"},
        "cursors": {"x": [0.0, TPLH_TYP / TD]},
        "bottom": [
            {"l": "Fréq(1):", "v": "100kHz", "c": "ch1"},
            {"l": "Max(1):", "v": "5.00V", "c": "ch1"},
            {"l": "Max(2):", "v": "%.2fV" % VOH_Q, "c": "ch2"},
            {"l": "ΔX (curseurs):", "v": "%.1fns" % (TPLH_TYP * 1e9), "c": "x"},
        ],
    }


# ---- SVG : figure 2 du polycopié (redessinée) -------------------------------------------------------------
def fig2_svg():
    o = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="-50 0 570 190" width="100%" style="max-width:560px;background:#fff;border:1px solid #ccc;border-radius:8px" font-family="Arial" fill="#111">']
    o.append('<rect x="70" y="30" width="110" height="110" fill="none" stroke="#111" stroke-width="2"/>')
    o.append('<line x1="40" y1="55" x2="70" y2="55" stroke="#111" stroke-width="2"/><text x="26" y="60" font-size="16" text-anchor="end">D</text>')
    o.append('<line x1="40" y1="115" x2="70" y2="115" stroke="#111" stroke-width="2"/><path d="M70,105 L82,115 L70,125" fill="none" stroke="#111" stroke-width="2"/>'
             '<text x="26" y="112" font-size="16" text-anchor="end">CLK</text><text x="26" y="130" font-size="12" text-anchor="end">(horloge)</text>')
    o.append('<line x1="180" y1="55" x2="210" y2="55" stroke="#111" stroke-width="2"/><text x="218" y="60" font-size="16" font-style="italic">Q</text>')
    o.append('<line x1="180" y1="115" x2="210" y2="115" stroke="#111" stroke-width="2"/><text x="218" y="120" font-size="16" font-style="italic">Q</text>'
             '<line x1="217" y1="104" x2="227" y2="104" stroke="#111" stroke-width="1.5"/>')
    # table de vérité
    x0, y0 = 290, 30
    o.append('<rect x="%d" y="%d" width="210" height="130" fill="none" stroke="#111" stroke-width="1.5"/>' % (x0, y0))
    o.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#111"/><line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#111"/><line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#111"/>' % (
        x0, y0 + 30, x0 + 210, y0 + 30, x0 + 105, y0, x0 + 105, y0 + 130, x0 + 160, y0, x0 + 160, y0 + 130))
    rows = [("D", "CLK", "Q", "Q̄"), ("0", "↑", "0", "1"), ("1", "↑", "1", "0"), ("X", "autre", "Qp", "Q̄p")]
    for r, row in enumerate(rows):
        y = y0 + 21 + r * 33 if r else y0 + 20
        for c, txt in enumerate(row):
            x = [x0 + 22, x0 + 74, x0 + 132, x0 + 185][c]
            o.append('<text x="%d" y="%d" font-size="15" text-anchor="middle">%s</text>' % (x, y if r == 0 else y0 + 30 + 22 + (r - 1) * 33 - 6 + 6, txt))
    o.append('</svg>')
    return "".join(o)


EXTRA_CSS = """
<style>
.crumb{font-size:13px;color:var(--mut);margin:14px 0 4px}
.nav{position:sticky;top:0;z-index:5;background:var(--card);border-bottom:1px solid var(--line);padding:8px 0;display:flex;gap:6px;flex-wrap:wrap;align-items:center;font-size:14px}
.nav a,.nav span{padding:4px 10px;border-radius:6px;border:1px solid var(--line);text-decoration:none;color:var(--ac)}
.nav span.off{color:var(--mut);border-style:dashed}
.sec{border-left:5px solid var(--ac);padding-left:12px;margin:18px 0}
.sec>h3{margin:0 0 6px;font-size:15px}.num{display:inline-block;width:22px;height:22px;border-radius:50%;background:var(--ac);color:#fff;text-align:center;font:700 13px/22px Arial;margin-right:6px}
.quote{background:#fff8e1;color:#222;border:1px solid #f0d98a;border-radius:8px;padding:10px 14px;font-style:italic}
.src{font-size:12px;color:var(--mut)}.pill{display:inline-block;border-radius:10px;padding:1px 9px;font-size:12px;font-weight:700;margin-right:4px}
.p-sujet{background:#dbe8ff;color:#0b3d91}.p-gen{background:#e6e0ff;color:#4a2a9e}.p-ds{background:#d9f7e4;color:#0a6b34}.p-dedu{background:#fff0c9;color:#8a5a00}.p-hyp{background:#fde0e0;color:#a30d0d}
.valid{border:2px solid var(--ac);border-radius:12px;padding:12px 16px;margin-top:18px}
.valid label{margin-right:18px;font-weight:700;cursor:pointer}.valid textarea{width:100%;min-height:60px;margin-top:8px;border:1px solid var(--line);border-radius:6px;padding:6px;font:inherit}
.ecart{background:#fff0c9;color:#222}
.sec>h3{cursor:pointer;user-select:none}.sec>h3::after{content:' ▾';color:var(--mut);font-weight:400}.sec.closed>h3::after{content:' ▸'}
.sec.closed>.body{display:none}
.tools{margin-left:auto;display:flex;gap:6px}.tools button{border:1px solid var(--line);background:var(--card);color:var(--ac);border-radius:6px;padding:4px 10px;font:inherit;cursor:pointer}
.keyfacts td:first-child{width:210px;font-weight:700;color:var(--mut)}
.toc a{margin-right:12px}
</style>"""


def build():
    hw = render.load("hardware/board_wish106.yaml")
    m = render.load_montage("montages/tp3/B_bascule_D.yaml")
    res, _ = render.validate(m, hw)
    nerr = sum(1 for r in res if r[0] == "ERREUR")
    clk, q = samples()
    scope = render.scope_svg(scope_cfg(clk, q), "ex")
    rows = "".join("<tr><td><b>%s</b></td><td><span class='sw' style='background:%s'></span>%s</td><td>%s → %s</td></tr>" % (
        w["n"], render.WIRE.get(w["couleur"], "#999"), E(w["couleur"]), E(w["de"]), E(w["vers"])) for w in m["fils"])

    b = [EXTRA_CSS]
    b.append("<div class='nav'><b>Navigation :</b> <span class='off'>TP1 (à venir)</span> <span class='off'>TP2 (à venir)</span> "
             "<a href='#tp3'>TP3</a> › <a href='#A' onclick='return false' style='opacity:.5'>A. NAND</a> "
             "<b style='padding:4px 10px'>B. Bascule D</b> <a href='#C' onclick='return false' style='opacity:.5'>C. Compteurs</a>"
             "<span class='tools' style='border:0'><button onclick=\"tg(true)\">Tout replier</button><button onclick=\"tg(false)\">Tout déplier</button></span>"
             "<span style='border:0'>Validés : <b id='cnt'>0</b> / 1 (exemple)</span></div>")
    b.append("<p class='crumb'>Sujet TP3 › Partie B — Bascule D › <b>2. Retard de propagation</b> &nbsp;·&nbsp; "
             "<b>EXEMPLE d'un seul bloc</b> : les autres blocs auront exactement cette forme.</p>")
    b.append("<h1 id='tp3'>B.2 — Retard de propagation de la bascule D (74LS74)</h1>")
    b.append("<p class='toc'><b>Dans ce bloc :</b> <a href='#s1'>① énoncé</a><a href='#s2'>② schéma du cours</a><a href='#s3'>③ schéma + broches</a>"
             "<a href='#s4'>④ brochage</a><a href='#s5'>⑤ vue d'ensemble</a><a href='#s6'>⑥ plaque</a><a href='#s7'>⑦ réglages</a><a href='#s8'>⑧ écran</a><a href='#s9'>⑨ cohérence</a></p>")

    # ① énoncé
    b.append("<div class='sec' id='s1'><h3><span class='num'>1</span>Ce que demande le polycopié <span class='pill p-sujet'>Sujet TP3, p. 3, § B.2</span></h3>"
             "<div class='quote'>« La sortie de la bascule D est « mise à jour » à chaque front montant de l'horloge. Mais cela ne se produit pas de manière instantanée : "
             "il y a un retard de propagation. ➤ Mesurez le retard de propagation. »</div>"
             "<p class='src'>Citation du sujet. Le sujet ne donne <b>ni schéma de câblage, ni valeur attendue</b> pour cette question : tout ce qui suit est déduit (voir les étiquettes).</p></div>")

    # ② schéma du polycopié
    b.append("<div class='sec' id='s2'><h3><span class='num'>2</span>Le schéma du cours qui s'applique <span class='pill p-sujet'>Sujet TP3, Figure 2, p. 2</span><span class='pill p-gen'>SVG redessiné</span></h3>"
             "%s<p class='src'>Redessinée d'après la Figure 2 (bascule D + table de vérité). Lecture : Q recopie D à <b>chaque front montant</b> de CLK ; le reste du temps Q garde sa valeur (Qp). "
             "C'est ce « à chaque front montant » dont on mesure le retard.</p></div>" % fig2_svg())

    # ③ schéma avec tous les ports
    b.append("<div class='sec' id='s3'><h3><span class='num'>3</span>Schéma du montage, avec le numéro de chaque broche <span class='pill p-dedu'>déduit : non imposé par le sujet</span><span class='pill p-gen'>SVG généré</span></h3>"
             "%s<p>On relie <b>D à Q̄</b> : à chaque front montant, Q change d'état, ce qui rend le retard visible à chaque période. "
             "PRE et CLR (actives à 0) sont reliées au +5 V pour être désactivées ; sans cela, la sortie reste figée.</p>"
             "<p class='src'>Même présentation que la Figure 2 de ta copie perso (chaque fil porte son numéro de broche).</p></div>" % ttl_ports.bascule_d_schema())

    # ④ brochage du 74LS74
    b.append("<div class='sec' id='s4'><h3><span class='num'>4</span>Branchement des broches du 74LS74 <span class='pill p-ds'>brochage : datasheet et ta copie perso</span><span class='pill p-gen'>SVG généré</span></h3>"
             "<div class='row'><div>%s</div><div>%s<p class='src'>Seule la bascule 1 (broches 1 à 6) est utilisée. Les broches 8 à 13 appartiennent à la bascule 2 et restent libres dans ce montage. "
             "Le sujet précise que les broches non connectées sont à un niveau haut par défaut.</p></div></div></div>" % (
                 ttl_ports.dip_svg("74LS74", ttl_ports.USE_74LS74_B2), ttl_ports.pin_table("74LS74", ttl_ports.USE_74LS74_B2, only_used=True)))

    # ⑤ VUE D'ENSEMBLE (avant le câblage sur la plaque, repliable)
    try:
        mm = render.subst(m, {k: v for k, v in render.numbers_of(m).items() if k.startswith("__")})
    except Exception:
        mm = m
    gbf_i, scope_i = render.load("hardware/instruments/gbf.yaml"), render.load("hardware/instruments/scope.yaml")
    crow = "".join("<tr><td><b>%s</b> — %s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
        c["id"], E(c["nom"]), E(c["de"]), E(c["vers"]), E(c["role"])) for c in mm["cables"])
    b.append("<div class='sec' id='s5'><h3><span class='num'>5</span>Vue d'ensemble : la table, les appareils et les câbles <span class='pill p-gen'>SVG généré + photos des appareils</span></h3><div class='body'>"
             "<table class='keyfacts'>"
             "<tr><td>Question du sujet</td><td>TP3 › B › 2. Retard de propagation : « Mesurez le retard de propagation »</td></tr>"
             "<tr><td>Composant</td><td>74LS74 (bascule D, front montant), bascule 1 seule</td></tr>"
             "<tr><td>Montage</td><td>D reliée à Q̄ ; PRE et CLR au +5 V ; horloge = SYNC du GBF</td></tr>"
             "<tr><td>Appareils</td><td>alimentation +5 V · GBF (sortie SYNC TTL) · oscilloscope 2 voies (CLK et Q)</td></tr>"
             "<tr><td>Résultat attendu</td><td>CLK ↑ au centre, Q ↑ environ 13 ns plus tard (tPLH typique)</td></tr>"
             "<tr><td>Origine des chiffres</td><td>datasheet 74LS74 (guide du banc) ; <b>rien de mesuré</b> pour cette question dans ta copie</td></tr></table>"
             "%s<table><tr><th>Câble</th><th>De</th><th>Vers</th><th>Rôle</th></tr>%s</table>"
             "<p class='src'>Chaque BNC de la plaque reçoit deux fils (âme et blindage) ; la sortie SYNC du GBF sert deux fois (vers la plaque, et vers la voie 1 par le T). "
             "Les câbles marqués A à E sont ceux du fichier du montage ; position du T « à confirmer sur le banc ».</p></div></div>" % (
                 render.bench_svg(mm, hw, gbf_i, scope_i), crow))


    # ⑤ plaque
    b.append("<div class='sec' id='s6'><h3><span class='num'>6</span>Câblage sur la plaque Wish Board 106 <span class='pill p-gen'>SVG généré</span></h3>"
             "<p class='src'>Validateur automatique : %s</p>"
             "<div class='row'><div>%s</div><div><table><tr><th>N°</th><th>Fil</th><th>De → vers</th></tr>%s</table>"
             "<p class='src'>Page complète du montage : <a href='tp3-B-bascule-D.html'>tp3-B-bascule-D.html</a> (câbles de la table, alimentation, ordre de câblage). "
             "Placement des trous = proposition « à confirmer sur la plaque ».</p></div></div></div>" % (
                 "<b style='color:#0a6b34'>aucune erreur de câblage</b>" if not nerr else "<b style='color:#a30d0d'>%d ERREUR(S)</b>" % nerr,
                 render.board_svg(m, hw, 520), rows))

    # ④ réglages
    b.append("<div class='sec' id='s7'><h3><span class='num'>7</span>Réglages des appareils <span class='pill p-dedu'>déduit</span></h3><table>"
             "<tr><td>GBF</td><td>sortie <b>SYNC</b> (créneau TTL 0–5 V), <b>100 kHz</b></td></tr>"
             "<tr><td>Oscilloscope</td><td>voie 1 = CLK (2 V/div) · voie 2 = Q (2 V/div) · base de temps <b>5 ns/div</b> · déclenchement voie 1, front montant, 2,5 V</td></tr>"
             "<tr><td>Mesure</td><td>curseurs X : de 50 % du front de CLK à 50 % du front de Q</td></tr></table></div>")

    # ⑤ résultat
    b.append("<div class='sec' id='s8'><h3><span class='num'>8</span>Ce que l'oscilloscope doit afficher <span class='pill p-gen'>écran calculé, non mesuré</span></h3>"
             "<div class='row'><div style='max-width:760px'>%s</div><div>"
             "<table><tr><td>Voie 1 (jaune)</td><td>CLK : front montant au centre de l'écran (t = 0)</td></tr>"
             "<tr><td>Voie 2 (vert)</td><td>Q : monte un peu après, de 0,25 V à %.2f V</td></tr>"
             "<tr><td>Écart entre curseurs</td><td><b>tpd = %.0f ns</b> (ici : front montant de Q = tPLH)</td></tr></table>"
             "<p><b>Comment lire :</b> les deux lignes pointillées orange sont les curseurs. Le premier est sur le front de CLK, le second sur le front de Q ; leur écart est le retard de propagation.</p>"
             "<p class='src'>Hypothèses du modèle (non issues d'une mesure) : front de CLK %.0f ns ; front de Q %.0f ns ; niveaux de Q « typiques » (la fiche garantit seulement ≥ 2,7 V et ≤ 0,4 V).</p></div></div></div>" % (
                 scope, VOH_Q, TPLH_TYP * 1e9, T_RISE_CLK * 1e9, T_RISE_Q * 1e9))

    # ⑥ cohérence
    b.append("<div class='sec' id='s9'><h3><span class='num'>9</span>Cohérence des valeurs : d'où vient chaque chiffre ?</h3><table>"
             "<tr><th>Grandeur</th><th>Affichée ici</th><th>Datasheet 74LS74</th><th>Inventaire des manipulations</th><th>Verdict</th></tr>"
             "<tr><td>Retard CLK ↑ → Q ↑ (tPLH)</td><td><b>13 ns</b></td><td>typ 13 ns, max 25 ns <span class='pill p-ds'>guide banc TP3</span></td><td>15 à 25 ns</td><td class='ecart'>Écart mineur : l'inventaire donne une plage ; la fiche donne le typique. On affiche 13 ns et on signale le max 25 ns.</td></tr>"
             "<tr><td>Retard CLK ↑ → Q ↓ (tPHL)</td><td>non affiché (Q monte ici)</td><td>typ 25 ns, max 40 ns <span class='pill p-ds'>guide banc TP3</span></td><td>—</td><td class='ecart'>À montrer au cycle suivant (Q descend) : <b>le retard n'est pas le même sur les deux fronts</b>.</td></tr>"
             "<tr><td>Fréquence de Q</td><td>CLK / 2 (non visible dans cette fenêtre de 50 ns)</td><td>—</td><td>f(CLK)/2</td><td>cohérent — vu dans le bloc B « Diviseur par 2 »</td></tr></table>"
             "<p class='src'>Les valeurs 13 / 25 / 40 ns viennent de <code>hardware/behavior.yaml</code> (statut « vérifié », source : guide du banc TP3). Aucune n'est issue de tes mesures : dans ta copie perso, « le temps de propagation t<sub>pd</sub> n'a pas été relevé, par manque de temps ».</p></div>")

    # ⑦ validation
    b.append("<div class='valid'><b>Validation de ce bloc (B.2)</b><br><br>"
             "<label><input type='radio' name='v' value='ok'> ✅ Cohérent</label>"
             "<label><input type='radio' name='v' value='ko'> ❌ Pas cohérent</label>"
             "<label><input type='radio' name='v' value='q'> ❓ À discuter</label>"
             "<textarea id='note' placeholder='Remarque ou correction demandée (schéma, valeur, réglage…)'></textarea>"
             "<p class='src'>L'état est gardé dans ce navigateur. Le futur bouton « Exporter » produira un fichier texte avec tous les blocs, leur état et les remarques.</p></div>")
    b.append("""<script>(function(){var K='labdec-ex-B2';
function ld(){try{return JSON.parse(localStorage.getItem(K)||'{}')}catch(e){return {}}}
function sv(o){try{localStorage.setItem(K,JSON.stringify(o))}catch(e){}}
var s=ld();document.querySelectorAll('input[name=v]').forEach(function(r){if(s.v===r.value)r.checked=true;r.onchange=function(){s.v=r.value;sv(s);up()}});
var n=document.getElementById('note');n.value=s.n||'';n.oninput=function(){s.n=n.value;sv(s)};
function up(){document.getElementById('cnt').textContent=(s.v==='ok')?1:0}up();})();</script>""")
    b.append("<script>(function(){document.querySelectorAll('.sec').forEach(function(sec){var h=sec.querySelector(':scope>h3');if(!h)return;\nif(!sec.querySelector(':scope>.body')){var d=document.createElement('div');d.className='body';while(h.nextSibling)d.appendChild(h.nextSibling);sec.appendChild(d);}\nh.onclick=function(){sec.classList.toggle('closed')};});\nwindow.tg=function(c){document.querySelectorAll('.sec').forEach(function(s){s.classList.toggle('closed',c)})};\nif(location.hash){var t=document.querySelector(location.hash);if(t&&t.classList.contains('sec'))t.classList.remove('closed');}})();</script>")
    return render.page("Exemple de bloc — TP3 B.2", "".join(b))


if __name__ == "__main__":
    out = ROOT / "out" / "exemple_bloc_tp3_B2.html"
    out.write_text(build(), encoding="utf-8")
    print("écrit", out)
