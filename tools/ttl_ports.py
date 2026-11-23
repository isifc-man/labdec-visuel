"""Branchement des ports (broches) des puces TTL 74LS00 / 74LS74 : brochage DIP-14, tableau, schéma à la façon
de la Figure 2 de la copie perso (04_CR_v3/images/tp3_sch_nand_led.png : chaque fil porte son numéro de broche).
Brochage = tableau de ta copie perso (04_CR_v3/TP3.md, l.17-25), identique aux datasheets 74LS00 / 74LS74.
Utilisé par tools/exemple_bloc.py ; destiné à TOUS les blocs TP3.
"""
from html import escape as E

PINOUT = {
    "TL081": {1: "OFFSET N1", 2: "IN−", 3: "IN+", 4: "V−", 5: "OFFSET N2", 6: "OUT", 7: "V+", 8: "NC"},
    "74LS00": {1: "1A", 2: "1B", 3: "1Y", 4: "2A", 5: "2B", 6: "2Y", 7: "GND",
               8: "3Y", 9: "3A", 10: "3B", 11: "4Y", 12: "4A", 13: "4B", 14: "VCC"},
    "74LS74": {1: "1CLR", 2: "1D", 3: "1CLK", 4: "1PRE", 5: "1Q", 6: "1Q̄", 7: "GND",
               8: "2Q̄", 9: "2Q", 10: "2PRE", 11: "2CLK", 12: "2D", 13: "2CLR", 14: "VCC"},
}
ROLE_COL = {"alim": "#d62424", "masse": "#222", "entree": "#2a63b4", "sortie": "#1f9d3a", "libre": "#aaa"}
ROLE_TXT = {"alim": "alimentation", "masse": "masse", "entree": "entrée", "sortie": "sortie", "libre": "non utilisée"}


def dip_svg(chip, use):
    """use : {broche: (role, 'relié à ...')}. Puce vue de dessus, encoche en haut, broche 1 en haut à gauche. 8 ou 14 broches."""
    names = PINOUT[chip]
    n = len(names)
    h = n // 2
    step = 34
    by, bx, bw = 40, 150, 130
    bh = 44 + (h - 1) * step
    H = by + bh + 50
    o = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 430 %d" width="100%%" style="max-width:430px;background:#fff;border:1px solid #ccc;border-radius:8px" font-family="Arial" fill="#111">' % H]
    o.append('<text x="215" y="22" font-size="14" font-weight="700" text-anchor="middle">%s — vue de dessus (DIP-%d)</text>' % (chip, n))
    o.append('<rect x="%d" y="%d" width="%d" height="%d" rx="4" fill="#2b2b2b" stroke="#000" stroke-width="2"/>' % (bx, by, bw, bh))
    o.append('<path d="M%d,%d a14,14 0 0 0 28,0" fill="#fff" stroke="#000"/>' % (bx + bw / 2 - 14, by))
    o.append('<circle cx="%d" cy="%d" r="4" fill="#fff"/>' % (bx + 14, by + 16))
    o.append('<text x="215" y="%d" font-size="15" fill="#fff" text-anchor="middle" transform="rotate(-90 215 %d)" letter-spacing="2">%s</text>' % (by + bh / 2, by + bh / 2, chip))
    for p in range(1, n + 1):
        left = p <= h
        i = (p - 1) if left else (n - p)
        y = by + 22 + i * step
        role, rel = use.get(p, ("libre", "non utilisée"))
        col = ROLE_COL[role]
        x0 = bx - 22 if left else bx + bw
        o.append('<rect x="%d" y="%d" width="22" height="12" fill="%s" stroke="#000"/>' % (x0, y - 6, col))
        o.append('<text x="%d" y="%d" font-size="11" font-weight="700" fill="#fff" text-anchor="middle">%d</text>' % (x0 + 11, y + 4, p))
        if left:
            o.append('<text x="%d" y="%d" font-size="12" text-anchor="end">%s</text>' % (x0 - 6, y + 4, E(names[p])))
        else:
            o.append('<text x="%d" y="%d" font-size="12">%s</text>' % (x0 + 28, y + 4, E(names[p])))
    lx = 10
    ly = by + bh + 22
    for r in ("alim", "masse", "entree", "sortie", "libre"):
        o.append('<rect x="%d" y="%d" width="12" height="12" fill="%s"/><text x="%d" y="%d" font-size="11">%s</text>' % (lx, ly, ROLE_COL[r], lx + 16, ly + 10, ROLE_TXT[r]))
        lx += 84
    o.append('</svg>')
    return "".join(o)


def pin_table(chip, use, only_used=False):
    names = PINOUT[chip]
    rows = []
    for p in range(1, len(names) + 1):
        role, rel = use.get(p, ("libre", "non utilisée"))
        if only_used and role == "libre":
            continue
        rows.append("<tr><td><b>%d</b></td><td>%s</td><td><span class='sw' style='background:%s'></span>%s</td><td>%s</td></tr>" % (
            p, E(names[p]), ROLE_COL[role], ROLE_TXT[role], E(rel)))
    return "<table><tr><th>Broche</th><th>Signal</th><th>Type</th><th>Relié à</th></tr>%s</table>" % "".join(rows)


def bar(x, y, txt, anchor="start", size=12):
    """Texte avec barre au-dessus (signal actif à l'état bas)."""
    w = 6.6 * len(txt)
    x1 = x if anchor == "start" else x - w
    return ('<text x="%.1f" y="%.1f" font-size="%d" text-anchor="%s">%s</text><line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#111" stroke-width="1.4"/>'
            % (x, y, size, anchor, E(txt), x1, y - size + 1, x1 + w, y - size + 1))


def gnd_symbol(x, y):
    return ('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#111" stroke-width="2"/><line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#111" stroke-width="2"/>'
            '<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#111" stroke-width="2"/><line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#111" stroke-width="2"/>') % (
        x - 12, y, x + 12, y, x - 8, y + 5, x + 8, y + 5, x - 4, y + 10, x + 4, y + 10, x, y - 14, x, y)


def bascule_d_schema(feedback=True):
    """Bascule 1 du 74LS74, tous les ports numérotés (style Figure 2 de la copie perso).
    feedback=True : D reliée à Q̄ (diviseur par 2, retard de propagation)."""
    o = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 740 330" width="100%" style="max-width:740px;background:#fff;border:1px solid #ccc;border-radius:8px" font-family="Arial" fill="#111">']
    o.append('<rect x="250" y="80" width="130" height="120" fill="none" stroke="#111" stroke-width="2.4"/>')
    o.append('<text x="315" y="142" font-size="12" font-weight="700" text-anchor="middle">74LS74</text><text x="315" y="157" font-size="11" text-anchor="middle" fill="#555">bascule 1</text>')
    # rail +5 V haut : PRE (4) et Vcc (14)
    o.append('<line x1="270" y1="44" x2="345" y2="44" stroke="#d62424" stroke-width="2.5"/><text x="307" y="36" font-size="12" font-weight="700" fill="#d62424" text-anchor="middle">+5 V</text>')
    o.append('<line x1="270" y1="44" x2="270" y2="80" stroke="#111" stroke-width="2"/><line x1="345" y1="44" x2="345" y2="80" stroke="#111" stroke-width="2"/>')
    o.append(bar(264, 64, "PRE (4)", "end"))
    o.append('<text x="351" y="64" font-size="12">VCC (14)</text>')
    # bas : CLR (1) au +5 V, GND (7) masse
    o.append('<line x1="270" y1="200" x2="270" y2="236" stroke="#111" stroke-width="2"/><line x1="345" y1="200" x2="345" y2="226" stroke="#111" stroke-width="2"/>')
    o.append(bar(264, 222, "CLR (1)", "end"))
    o.append('<text x="351" y="222" font-size="12">GND (7)</text>')
    o.append('<text x="270" y="252" font-size="12" font-weight="700" fill="#d62424" text-anchor="middle">+5 V</text>')
    o.append(gnd_symbol(345, 240))
    # entrées D (2), CLK (3)
    o.append('<line x1="190" y1="110" x2="250" y2="110" stroke="#111" stroke-width="2"/><text x="198" y="104" font-size="12">D (2)</text>')
    o.append('<path d="M60,170 L182,170 A8,8 0 0 1 198,170 L250,170" fill="none" stroke="#111" stroke-width="2"/><path d="M250,162 L261,170 L250,178" fill="none" stroke="#111" stroke-width="2"/>')
    o.append('<text x="203" y="164" font-size="12">CLK (3)</text><text x="60" y="190" font-size="12">SYNC du GBF</text><text x="60" y="204" font-size="11" fill="#555">(créneau TTL, 100 kHz)</text>')
    o.append('<circle cx="110" cy="170" r="4"/><line x1="110" y1="170" x2="110" y2="128" stroke="#c9b800" stroke-width="3"/><text x="110" y="120" font-size="12" font-weight="700" text-anchor="middle">→ voie 1 (CLK)</text>')
    # sorties Q (5), Q̄ (6)
    o.append('<line x1="380" y1="110" x2="470" y2="110" stroke="#111" stroke-width="2"/><text x="388" y="104" font-size="12">Q (5)</text>')
    o.append('<circle cx="470" cy="110" r="4"/><line x1="470" y1="110" x2="560" y2="110" stroke="#4cf04c" stroke-width="3"/><text x="566" y="114" font-size="13" font-weight="700">→ voie 2 (Q)</text>')
    o.append('<line x1="380" y1="170" x2="410" y2="170" stroke="#111" stroke-width="2"/>' + bar(388, 164, "Q (6)"))
    if feedback:
        o.append('<path d="M410,170 L410,285 L190,285 L190,110" fill="none" stroke="#d6246e" stroke-width="3"/><circle cx="410" cy="170" r="4" fill="#d6246e"/>')
        o.append('<text x="300" y="306" font-size="12" font-weight="700" fill="#d6246e" text-anchor="middle">fil de rebouclage : broche 6 (Q barre) → broche 2 (D)</text>')
    o.append('</svg>')
    return "".join(o)


USE_74LS74_B2 = {
    1: ("entree", "+5 V (CLR inactive : active à 0)"),
    2: ("entree", "broche 6 (Q̄) : fil de rebouclage D = Q̄"),
    3: ("entree", "SYNC du GBF (et voie 1 de l'oscillo)"),
    4: ("entree", "+5 V (PRE inactive : active à 0)"),
    5: ("sortie", "voie 2 de l'oscillo"),
    6: ("sortie", "broche 2 (D)"),
    7: ("masse", "0 V (masse commune)"),
    14: ("alim", "+5 V (alimentation stabilisée)"),
}


# ---------------------------------------------------------------- schémas NAND et compteur (ports numérotés)
def _gate(x0, y0):
    """Symbole NAND : corps x0..x0+80, hauteur 80 ; sortie en (x0+95, y0+40)."""
    return ('<path d="M%d,%d L%d,%d A40,40 0 0 1 %d,%d L%d,%d Z" fill="none" stroke="#111" stroke-width="2.4"/>'
            '<circle cx="%d" cy="%d" r="7" fill="#fff" stroke="#111" stroke-width="2.4"/>'
            '<text x="%d" y="%d" font-size="13" text-anchor="middle">NAND</text>') % (
        x0, y0, x0 + 40, y0, x0 + 40, y0 + 80, x0, y0 + 80, x0 + 87, y0 + 40, x0 + 36, y0 + 45)


def nand_schema(variant="led"):
    """74LS00 porte 1, chaque fil porte son numéro de broche (style Figure 2 de la copie : 1A (1), 1B (2), 1Y (3), +5 V (14), GND (7))."""
    o = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 300" width="100%" style="max-width:760px;background:#fff;border:1px solid #ccc;border-radius:8px" font-family="Arial" fill="#111">']
    o.append(_gate(250, 120))
    o.append('<line x1="290" y1="86" x2="290" y2="120" stroke="#111" stroke-width="2"/><text x="290" y="78" font-size="12" font-weight="700" fill="#d62424" text-anchor="middle">+5 V (broche 14)</text>')
    o.append('<line x1="290" y1="200" x2="290" y2="224" stroke="#111" stroke-width="2"/>' + gnd_symbol(290, 226))
    o.append('<text x="310" y="232" font-size="12">GND (broche 7)</text>')
    if variant == "seuils":
        o.append('<line x1="110" y1="140" x2="250" y2="140" stroke="#111" stroke-width="2"/><text x="190" y="134" font-size="12">1A (1)</text>')
        o.append('<text x="30" y="144" font-size="12" font-weight="700">GBF triangle</text><text x="30" y="158" font-size="11" fill="#555">0–5 V, 1 kHz</text>')
        o.append('<circle cx="150" cy="140" r="4"/><line x1="150" y1="140" x2="150" y2="96" stroke="#c9b800" stroke-width="3"/><text x="150" y="88" font-size="12" font-weight="700" text-anchor="middle">→ voie 1</text>')
        o.append('<line x1="130" y1="180" x2="250" y2="180" stroke="#111" stroke-width="2"/><text x="190" y="174" font-size="12">1B (2)</text><text x="124" y="184" font-size="12" font-weight="700" fill="#d62424" text-anchor="end">+5 V</text>')
        o.append('<line x1="345" y1="160" x2="560" y2="160" stroke="#111" stroke-width="2"/><text x="360" y="152" font-size="12">1Y (3)</text>')
        o.append('<circle cx="450" cy="160" r="4"/><line x1="450" y1="160" x2="560" y2="160" stroke="#4cf04c" stroke-width="3"/><text x="566" y="164" font-size="13" font-weight="700">→ voie 2 (Y)</text>')
    else:
        o.append('<line x1="110" y1="140" x2="250" y2="140" stroke="#111" stroke-width="2"/><text x="190" y="134" font-size="12">1A (1)</text>')
        o.append('<line x1="110" y1="180" x2="250" y2="180" stroke="#111" stroke-width="2"/><text x="190" y="174" font-size="12">1B (2)</text>')
        o.append('<text x="30" y="144" font-size="11" fill="#555">0 V ou +5 V</text><text x="30" y="184" font-size="11" fill="#555">0 V ou +5 V</text>')
        o.append('<line x1="345" y1="160" x2="470" y2="160" stroke="#111" stroke-width="2"/><text x="352" y="152" font-size="12">1Y (3)</text>')
        o.append('<path d="M410,205 L410,176" stroke="#111" stroke-width="2" fill="none"/><path d="M404,184 L410,172 L416,184 Z" fill="#111"/><text x="420" y="200" font-size="13">U<tspan font-size="9" dy="3">Y</tspan></text>')
        o.append('<rect x="470" y="148" width="80" height="24" fill="none" stroke="#111" stroke-width="2"/><text x="510" y="190" font-size="12" text-anchor="middle">R = 330 Ω</text>')
        o.append('<line x1="550" y1="160" x2="600" y2="160" stroke="#111" stroke-width="2"/>')
        o.append('<path d="M600,144 L600,176 L628,160 Z" fill="none" stroke="#111" stroke-width="2"/><line x1="628" y1="144" x2="628" y2="176" stroke="#111" stroke-width="2"/><text x="614" y="196" font-size="12" text-anchor="middle">LED rouge</text>')
        o.append('<line x1="628" y1="160" x2="690" y2="160" stroke="#111" stroke-width="2"/><line x1="690" y1="160" x2="690" y2="214" stroke="#111" stroke-width="2"/>' + gnd_symbol(690, 216) + '<text x="690" y="250" font-size="12" text-anchor="middle">Masse</text>')
        o.append('<path d="M480,128 L520,128" stroke="#111" stroke-width="2"/><path d="M516,123 L526,128 L516,133 Z" fill="#111"/><text x="536" y="132" font-size="13">I</text>')
    o.append('</svg>')
    return "".join(o)


def compteur_schema():
    """Compteur modulo 4, montage de gauche de la Figure 3 du sujet, avec les broches du 74LS74."""
    o = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 340" width="100%" style="max-width:760px;background:#fff;border:1px solid #ccc;border-radius:8px" font-family="Arial" fill="#111">']
    for bx, tag, d, clk, q, qb, pre, clr in ((170, "bascule 1 (Q0)", 2, 3, 5, 6, 4, 1), (450, "bascule 2 (Q1)", 12, 11, 9, 8, 10, 13)):
        o.append('<rect x="%d" y="90" width="110" height="110" fill="none" stroke="#111" stroke-width="2.4"/><text x="%d" y="146" font-size="12" font-weight="700" text-anchor="middle">74LS74</text><text x="%d" y="161" font-size="11" text-anchor="middle" fill="#555">%s</text>' % (bx, bx + 55, bx + 55, tag))
        o.append('<text x="%d" y="115" font-size="12">D (%d)</text><text x="%d" y="190" font-size="12">CLK (%d)</text>' % (bx + 6, d, bx + 14, clk))
        o.append('<path d="M%d,%d L%d,%d L%d,%d" fill="none" stroke="#111" stroke-width="2"/>' % (bx, 162, bx + 11, 170, bx, 178))
        o.append('<text x="%d" y="115" font-size="12" text-anchor="end">Q (%d)</text>' % (bx + 104, q))
        o.append(bar(bx + 104, 190, "Q (%d)" % qb, "end"))
        o.append('<line x1="%d" y1="62" x2="%d" y2="90" stroke="#111" stroke-width="2"/><text x="%d" y="54" font-size="11" fill="#d62424" font-weight="700" text-anchor="middle">+5 V</text>' % (bx + 25, bx + 25, bx + 25))
        o.append(bar(bx + 31, 84, "PRE (%d)" % pre, "start", 11))
        o.append('<line x1="%d" y1="200" x2="%d" y2="228" stroke="#111" stroke-width="2"/><text x="%d" y="244" font-size="11" fill="#d62424" font-weight="700" text-anchor="middle">+5 V</text>' % (bx + 25, bx + 25, bx + 25))
        o.append(bar(bx + 31, 216, "CLR (%d)" % clr, "start", 11))
    # entrées D, CLK, sorties
    o.append('<line x1="140" y1="120" x2="170" y2="120" stroke="#111" stroke-width="2"/><line x1="420" y1="120" x2="450" y2="120" stroke="#111" stroke-width="2"/>')
    o.append('<path d="M40,170 L170,170" fill="none" stroke="#111" stroke-width="2"/><text x="40" y="196" font-size="12" font-weight="700">Horloge TTL</text><text x="40" y="210" font-size="11" fill="#555">(SYNC du GBF)</text>')
    # Q̄0 -> CLK1 (avec saut au croisement x=420) et Q̄0 -> D0
    o.append('<path d="M280,170 L412,170 A8,8 0 0 1 428,170 L450,170" fill="none" stroke="#d6246e" stroke-width="3"/><circle cx="310" cy="170" r="4" fill="#d6246e"/>')
    o.append('<path d="M310,170 L310,30 L140,30 L140,120" fill="none" stroke="#d6246e" stroke-width="3"/>')
    o.append('<text x="225" y="24" font-size="11" fill="#d6246e" font-weight="700" text-anchor="middle">Q barre 0 (6) → D0 (2)</text><text x="372" y="162" font-size="11" fill="#d6246e" font-weight="700" text-anchor="middle">→ CLK1 (11)</text>')
    # Q̄1 -> D1
    o.append('<path d="M560,170 L590,170 L590,276 L420,276 L420,120" fill="none" stroke="#d6246e" stroke-width="3"/><circle cx="590" cy="170" r="4" fill="#d6246e"/>')
    o.append('<text x="505" y="294" font-size="11" fill="#d6246e" font-weight="700" text-anchor="middle">Q barre 1 (8) → D1 (12)</text>')
    # Q0 -> voie 1 (saut au croisement de x=310), Q1 -> voie 2
    o.append('<path d="M280,120 L302,120 A8,8 0 0 1 318,120 L395,120" fill="none" stroke="#111" stroke-width="2"/><circle cx="395" cy="120" r="4"/>')
    o.append('<line x1="395" y1="120" x2="395" y2="84" stroke="#c9b800" stroke-width="3"/><text x="395" y="76" font-size="12" font-weight="700" text-anchor="middle">→ voie 1 (Q0)</text>')
    o.append('<path d="M560,120 L640,120" fill="none" stroke="#4cf04c" stroke-width="3"/><text x="646" y="124" font-size="13" font-weight="700">→ voie 2 (Q1)</text>')
    o.append('<text x="380" y="318" font-size="11" fill="#555" text-anchor="middle">Un seul boîtier 74LS74 : Vcc (14) = +5 V, GND (7) = 0 V ; PRE (4, 10) et CLR (1, 13) reliées au +5 V</text>')
    o.append('<text x="380" y="330" font-size="11" fill="#555" text-anchor="middle">Sondes ci-dessus = chronogrammes Q0, Q1. LED : Q0 et Q1 → 330 Ω → LED → masse (suivi du comptage à quelques Hz).</text>')
    o.append('</svg>')
    return "".join(o)


USE_74LS00_A = {
    1: ("entree", "0 V ou +5 V (fil) : entrée A"), 2: ("entree", "0 V ou +5 V (fil) : entrée B"),
    3: ("sortie", "résistance 330 Ω puis LED rouge vers la masse ; mesure UY"),
    7: ("masse", "0 V (masse commune)"), 14: ("alim", "+5 V (alimentation stabilisée)"),
}
USE_74LS00_A2 = {
    1: ("entree", "GBF triangle 0–5 V + voie 1 de l'oscillo"), 2: ("entree", "+5 V (la NAND devient un inverseur)"),
    3: ("sortie", "voie 2 de l'oscillo"), 7: ("masse", "0 V (masse commune)"), 14: ("alim", "+5 V (alimentation stabilisée)"),
}
USE_74LS74_C = {
    1: ("entree", "+5 V (CLR 1 inactive)"), 2: ("entree", "broche 6 (Q̄0)"), 3: ("entree", "Horloge TTL (SYNC du GBF) et voie 1 sur la plaque"),
    4: ("entree", "+5 V (PRE 1 inactive)"), 5: ("sortie", "Q0 : R0 330 Ω + LED0 ; voie 2 sur la plaque (voie 1 pour les chronogrammes)"), 6: ("sortie", "broches 2 (D0) et 11 (CLK1)"),
    7: ("masse", "0 V (masse commune)"), 8: ("sortie", "broche 12 (D1)"), 9: ("sortie", "Q1 : R1 330 Ω + LED1 ; voie 2 pour les chronogrammes"),
    10: ("entree", "+5 V (PRE 2 inactive)"), 11: ("entree", "broche 6 (Q̄0) : horloge de la bascule 2"), 12: ("entree", "broche 8 (Q̄1)"),
    13: ("entree", "+5 V (CLR 2 inactive)"), 14: ("alim", "+5 V (alimentation stabilisée)"),
}
USE_74LS74_B0 = {
    1: ("entree", "CLR : +5 V (puis 0 V pour tester le forçage à 0)"), 2: ("entree", "D : 0 V ou +5 V"),
    3: ("entree", "SYNC du GBF (1 Hz pour les LED)"), 4: ("entree", "PRE : +5 V (puis 0 V pour tester le forçage à 1)"),
    5: ("sortie", "Q : résistance 330 Ω + LED verte"), 6: ("sortie", "Q̄ : résistance 330 Ω + LED rouge"),
    7: ("masse", "0 V (masse commune)"), 14: ("alim", "+5 V (alimentation stabilisée)"),
}
