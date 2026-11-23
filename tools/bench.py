# -*- coding: utf-8 -*-
"""Carte de la table : photos des ports des appareils (GBF, oscilloscope, alimentation) + plaque + câbles."""
import math
import render as R

PH = {"gbf": "gbf_ports", "scope": "scope_ports", "psu": "psu_ports"}
NAMES = {"gbf": "GBF Keysight EDU33211A — ports", "scope": "Oscilloscope Keysight DSOX1202A — entrées",
         "psu": "Alimentation Keysight EDU36311A — sorties"}
COLORS = ["#c2410c", "#7c3aed", "#047857", "#b45309", "#1d4ed8", "#be185d", "#0f766e", "#4d7c0f", "#9333ea", "#0369a1"]
PORT_LABEL = {"out1": "sortie 1", "ch1": "voie 1", "ch2": "voie 2",
              "ch1_plus": "ch1 +", "ch1_moins": "ch1 −", "ch2_plus": "ch2 +", "ch2_moins": "ch2 −", "ch3_plus": "ch3 +", "ch3_moins": "ch3 −"}


def parse(e):
    if "." in e and e.split(".")[0] in PH:
        return tuple(e.split(".", 1))
    return None, e


def bench_svg(m, hw, devs):
    cables = m.get("cables", [])
    conns = R.conn_geom(hw)
    used = []
    for c in cables:
        for e in (c["de"], c["vers"]):
            d, _ = parse(e)
            if d and d not in used:
                used.append(d)
    order = [d for d in ("gbf", "scope", "psu") if d in used]
    pw, ph_h, gap = 420, 315, 40
    sc = pw / 2048.0
    ypos = dict((d, 10 + i * (ph_h + gap)) for i, d in enumerate(order))

    def dev_pt(e):
        d, p = parse(e)
        zone = ("bnc_" + p) if d == "scope" else p
        zx, zy = devs[d]["photos"][PH[d]]["zones"][zone]
        return (zx * sc, ypos[d] + zy * sc)

    board_cables = [c for c in cables if c.get("type") != "strap" and (c["de"] in conns or c["vers"] in conns)]
    top = 26 + 14 * max(1, len(board_cables))
    k = 0.8
    bx0 = 680
    W = int(bx0 + R.PLATE_W * k + 20)
    H = int(max(top + R.PLATE_H * k + 20, 10 + len(order) * (ph_h + gap)))
    inner, _ = R.board_inner(m, hw)
    o = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" style="max-width:100%%;height:auto;background:#fafafa;border:1px solid #ddd;border-radius:8px" font-family="Arial">' % (W, H, W)]
    for d in order:
        ph = devs[d]["photos"][PH[d]]
        o.append('<image href="../assets/photos/%s" x="0" y="%d" width="%d" height="%d"/>' % (ph["file"], ypos[d], pw, ph_h))
        o.append('<text x="6" y="%d" font-size="13" font-weight="700" fill="#111">%s</text>' % (ypos[d] + ph_h + 16, R.E(NAMES[d])))
    o.append('<svg x="%d" y="%d" width="%.1f" height="%.1f" viewBox="0 0 %d %d">%s</svg>' % (bx0, top, R.PLATE_W * k, R.PLATE_H * k, R.PLATE_W, R.PLATE_H, inner))

    def bpt(cid):
        g = conns[cid]
        return bx0 + g["cx"] * k, top + (g["cy"] + 12) * k

    def badge(x, y, lab, col):
        return ('<circle cx="%.1f" cy="%.1f" r="12" fill="%s" stroke="#fff" stroke-width="2"/>'
                '<text x="%.1f" y="%.1f" font-size="13" font-weight="700" fill="#fff" text-anchor="middle">%s</text>') % (x, y, col, x, y + 4.5, lab)

    ends_used = []
    ranked = sorted(board_cables, key=lambda c: -(bpt(c["vers"] if c["vers"] in conns else c["de"])[0]))
    rank = dict((c["id"], i) for i, c in enumerate(ranked))
    for idx, c in enumerate(cables):
        col = COLORS[idx % len(COLORS)]
        if c.get("type") == "strap":
            p1, p2 = dev_pt(c["de"]), dev_pt(c["vers"])
            d = "M%.1f,%.1f Q%.1f,%.1f %.1f,%.1f" % (p1[0], p1[1], (p1[0] + p2[0]) / 2.0, max(p1[1], p2[1]) + 46, p2[0], p2[1])
            o.append('<path d="%s" fill="none" stroke="#fff" stroke-width="10" stroke-linecap="round"/><path d="%s" fill="none" stroke="%s" stroke-width="5" stroke-linecap="round" stroke-dasharray="2,7"/>' % (d, d, col))
            o.append(badge((p1[0] + p2[0]) / 2.0, max(p1[1], p2[1]) + 24, c["id"], col))
            ends_used += [c["de"], c["vers"]]
        elif c["id"] in rank:
            dev_e, board_e = (c["de"], c["vers"]) if c["vers"] in conns else (c["vers"], c["de"])
            s, e = dev_pt(dev_e), bpt(board_e)
            r = rank[c["id"]]
            lx, ly = 462 + 14 * r, 12 + 14 * r
            pts = [s, (lx, s[1]), (lx, ly), (e[0], ly), e]
            d = R.rounded(pts)
            o.append('<path d="%s" fill="none" stroke="#fff" stroke-width="11" stroke-linecap="round" opacity=".9"/><path d="%s" fill="none" stroke="%s" stroke-width="6" stroke-linecap="round"/>' % (d, d, col))
            o.append(badge(lx, (s[1] + ly) / 2.0, c["id"], col))
            ends_used.append(dev_e)
        else:
            p1, p2 = dev_pt(c["de"]), dev_pt(c["vers"])
            d = "M%.1f,%.1f C%.1f,%.1f %.1f,%.1f %.1f,%.1f" % (p1[0], p1[1], p1[0] - 60, p1[1] + 80, p2[0] + 60, p2[1] - 120, p2[0], p2[1])
            o.append('<path d="%s" fill="none" stroke="#fff" stroke-width="11" stroke-linecap="round" opacity=".9"/><path d="%s" fill="none" stroke="%s" stroke-width="6" stroke-linecap="round"/>' % (d, d, col))
            o.append(badge((p1[0] + p2[0]) / 2.0, (p1[1] + p2[1]) / 2.0, c["id"], col))
            ends_used += [c["de"], c["vers"]]
            if c.get("via") == "T":
                o.append('<text x="%.1f" y="%.1f" font-size="12" font-weight="700" fill="%s" stroke="#fff" stroke-width="3" paint-order="stroke">T (à confirmer)</text>' % (p1[0] + 24, p1[1] + 4, col))
    seen = set()
    for e in ends_used:
        if e in seen:
            continue
        seen.add(e)
        p = dev_pt(e)
        o.append('<circle cx="%.1f" cy="%.1f" r="14" fill="none" stroke="#111" stroke-width="3"/>' % p)
        o.append('<text x="%.1f" y="%.1f" font-size="11" font-weight="700" fill="#111" stroke="#fff" stroke-width="3" paint-order="stroke" text-anchor="middle">%s</text>' % (p[0], p[1] - 19, R.E(PORT_LABEL.get(parse(e)[1], parse(e)[1]))))
    o.append('</svg>')
    return "".join(o)
