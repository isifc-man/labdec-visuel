# -*- coding: utf-8 -*-
"""Moteur de prédiction : à partir du circuit + des réglages GBF, calcule ce que l'oscilloscope affichera.

Modèles (assumés, tous réglables dans predictions/*.yaml) :
  - GBF : source de tension + résistance de sortie rout (50 Ω). « High Z » : l'affichage = tension à vide ;
          « 50 Ω » : tension à vide = 2 × l'affichage.
  - Entrée oscillo : 1 MΩ ∥ 16 pF, sonde 1:1.
  - AOP TL081 : un seul pôle (GBW / gain de bruit), vitesse de montée limitée (SR), saturation (vsat).
  - Circuits RC : première ordre exact.
"""
import math


def clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x


def par(a, b):
    return a * b / float(a + b)


def nice_floor(x):
    e = math.floor(math.log10(x))
    m = x / 10 ** e
    for c in (5, 2, 1):
        if m >= c - 1e-9:
            return c * 10 ** e
    return 10 ** e


def nice_ceil(x):
    e = math.floor(math.log10(x))
    m = x / 10 ** e
    for c in (1, 2, 5, 10):
        if m <= c + 1e-9:
            return c * 10 ** e
    return 10 ** (e + 1)


def gbf_unit(sp, t):
    """Tension telle que RÉGLÉE sur le GBF (offset inclus), front montant / passage à zéro montant en t = 0."""
    if sp["kind"] == "dc":
        return sp["v"]
    f = sp["f"]
    a = sp["vpp"] / 2.0
    x = (f * t) % 1.0
    if sp["kind"] == "sine":
        v = math.sin(2 * math.pi * x)
    elif sp["kind"] == "square":
        e = max(sp.get("tr", 1e-8) * f, 1e-9)
        up = clamp(x / e, 0.0, 1.0)
        dn = clamp((x - 0.5) / e, 0.0, 1.0)
        v = 2 * (up - dn) - 1
    else:  # triangle
        y = (x + 0.25) % 1.0
        v = -1 + 4 * y if y < 0.5 else 3 - 4 * y
    return sp.get("offset", 0.0) + a * v


def lowpass(x, tau, dt):
    a = 1 - math.exp(-dt / tau)
    y = x[0]
    out = []
    for v in x:
        y += (v - y) * a
        out.append(y)
    return out


def opamp(vin, gain, ng, dt, tl):
    """TL081 : un pôle à GBW/ng, vitesse de montée SR, saturation ±vsat."""
    wc = 2 * math.pi * tl["gbw_hz"] / ng
    a = 1 - math.exp(-wc * dt)
    lim = tl["slew_vus"] * 1e6 * dt
    vs = tl["vsat"]
    vo = clamp(gain * vin[0], -vs, vs)
    out = []
    for x in vin:
        target = clamp(gain * x, -vs, vs)
        d = clamp((target - vo) * a, -lim, lim)
        vo += d
        out.append(vo)
    return out


def disp(arr, tdiv, n0, dt, n=900):
    out = []
    for i in range(n + 1):
        tt = (-5 + 10.0 * i / n) * tdiv
        x = tt / dt + n0
        k = max(0, min(len(arr) - 2, int(math.floor(x))))
        fr = x - k
        out.append(arr[k] * (1 - fr) + arr[k + 1] * fr)
    return out


def vpp(a):
    return max(a) - min(a)


def mid(a):
    return (max(a) + min(a)) / 2.0


def rising(a, tdiv):
    """Instants (s) des passages montants par le milieu de la courbe."""
    m = mid(a)
    res = []
    n = len(a) - 1
    for i in range(n):
        if a[i] < m <= a[i + 1]:
            fr = (m - a[i]) / (a[i + 1] - a[i])
            res.append((-5 + 10.0 * (i + fr) / n) * tdiv)
    return res


def phase_deg(ref, sig, f, tdiv):
    cr, cs = rising(ref, tdiv), rising(sig, tdiv)
    if not cr or not cs:
        return None
    t0 = min(cr, key=abs)
    T = 1.0 / f
    best = None
    for t in cs:
        lag = (t - t0 + T / 2.0) % T - T / 2.0
        if best is None or abs(lag) < abs(best):
            best = lag
    ph = -360.0 * f * best
    ph = (ph + 180.0) % 360.0 - 180.0
    return ph


def bode(circ, f, tl, glob):
    """Gain (module) et phase (°) petit signal, analytiques. None si non pertinent."""
    typ, C = circ["type"], circ.get("comps", {})
    gbw = tl["gbw_hz"]

    def R(n):
        return C[n]["ohm"]
    if typ == "follower":
        g, ng, sgn = 1.0, 1.0, 1
    elif typ == "inverting":
        g, ng, sgn = R("R2") / R("R1"), 1 + R("R2") / R("R1"), -1
    elif typ == "noninverting":
        g = 1 + R("R2") / R("R1")
        ng, sgn = g, 1
    elif typ == "association":
        g1 = 1 + R("R2") / R("R1")
        g2 = R("R4") / R("R3")
        ng1, ng2 = g1, 1 + R("R4") / R("R3")
        mod = g1 * g2 / math.sqrt((1 + (f * ng1 / gbw) ** 2) * (1 + (f * ng2 / gbw) ** 2))
        ph = -180 - math.degrees(math.atan(f * ng1 / gbw) + math.atan(f * ng2 / gbw))
        return mod, (ph + 180) % 360 - 180
    elif typ == "divider":
        k = R("R2") / float(R("R1") + R("R2"))
        tau = par(R("R1"), R("R2")) * circ["c_charge_pf"] * 1e-12
        return k / math.sqrt(1 + (2 * math.pi * f * tau) ** 2), -math.degrees(math.atan(2 * math.pi * f * tau))
    else:
        return None
    fc = gbw / ng
    mod = g / math.sqrt(1 + (f / fc) ** 2)
    ph = (0 if sgn > 0 else 180) - math.degrees(math.atan(f / fc))
    return mod, (ph + 180) % 360 - 180


def fc_of(circ, tl):
    typ, C = circ["type"], circ.get("comps", {})
    gbw = tl["gbw_hz"]
    if typ == "follower":
        return gbw
    if typ == "inverting":
        return gbw / (1 + C["R2"]["ohm"] / C["R1"]["ohm"])
    if typ == "noninverting":
        return gbw / (1 + C["R2"]["ohm"] / C["R1"]["ohm"])
    if typ == "divider":
        return 1 / (2 * math.pi * par(C["R1"]["ohm"], C["R2"]["ohm"]) * circ["c_charge_pf"] * 1e-12)
    if typ == "association":
        # -3 dB du produit des deux pôles : fc = fc_min * sqrt(sqrt(2) - 1) approché numériquement
        lo, hi = 1.0, gbw
        target = bode(circ, 1.0, tl, {})[0] / math.sqrt(2)
        for _ in range(60):
            m = math.sqrt(lo * hi)
            if bode(circ, m, tl, {})[0] > target:
                lo = m
            else:
                hi = m
        return lo
    return None


def run(circ, sc, tl, glob):
    """Renvoie (noeuds affichés, tdiv, valeurs numériques)."""
    g = sc["gbf"]
    f = g["f"]
    T = 1.0 / f
    typ = circ["type"]
    C = circ.get("comps", {})
    if "ohm" in sc:
        C = dict((k, dict(v)) for k, v in C.items())
        for k, v in sc["ohm"].items():
            C[k]["ohm"] = v
    tdiv = sc.get("tdiv") or nice_floor(3 * T / 10.0)
    window = 10 * tdiv
    dt = min(window / 3600.0, T / 400.0)
    settle = sc.get("settle_periods", 8) * T
    n0 = int(round((5 * tdiv + settle) / dt))
    n1 = int(round(5 * tdiv / dt))
    t = [(k - n0) * dt for k in range(n0 + n1 + 1)]
    rout = glob.get("rout_gbf", 50.0)
    so = 1.0 if g.get("charge", "HighZ") == "HighZ" else 2.0
    unit = [gbf_unit(g, tk) for tk in t]
    rscope = glob.get("r_scope", 1e6)

    def R(n):
        return C[n]["ohm"]

    def load(rl):
        k = rl / (rl + rout)
        return [so * u * k for u in unit]
    nodes = {}
    if typ == "direct":
        nodes["ve"] = load(rscope)
        nodes["vs"] = nodes["ve"]
    elif typ == "divider":
        ve = load(par(R("R1") + R("R2"), rscope))
        k = R("R2") / float(R("R1") + R("R2"))
        tau = par(R("R1"), R("R2")) * circ["c_charge_pf"] * 1e-12
        nodes["ve"] = ve
        nodes["vs"] = lowpass([k * x for x in ve], tau, dt)
    elif typ == "internal":
        nodes["ve"] = load(par(R("Rc"), rscope))
        nodes["vs"] = nodes["ve"]
    elif typ == "led":
        led = circ["led"]
        nvt = led["nvt"]
        isat = led["i_ref"] / math.exp(led["vf"] / nvt)
        rt = R("R") + rout
        e_node, v_led = [], []
        for u in unit:
            vin = so * u
            if vin <= 0:
                e_node.append(vin)
                v_led.append(vin)
                continue
            lo, hi = 0.0, vin
            for _ in range(40):
                m = (lo + hi) / 2.0
                if (vin - m) / rt - isat * (math.exp(min(m / nvt, 60)) - 1) > 0:
                    lo = m
                else:
                    hi = m
            i = (vin - lo) / rt
            e_node.append(vin - i * rout)
            v_led.append(lo)
        nodes["ve"], nodes["vs"] = e_node, v_led
    elif typ == "follower":
        ve = load(rscope)
        nodes["ve"] = ve
        nodes["vs"] = opamp(ve, 1.0, 1.0, dt, tl)
    elif typ == "inverting":
        ve = load(par(R("R1"), rscope))
        nodes["ve"] = ve
        nodes["vs"] = opamp(ve, -R("R2") / R("R1"), 1 + R("R2") / R("R1"), dt, tl)
    elif typ == "noninverting":
        ve = load(rscope)
        g1 = 1 + R("R2") / R("R1")
        nodes["ve"] = ve
        nodes["vs"] = opamp(ve, g1, g1, dt, tl)
    elif typ == "association":
        ve = load(rscope)
        g1 = 1 + R("R2") / R("R1")
        v1 = opamp(ve, g1, g1, dt, tl)
        nodes["ve"], nodes["v1"] = ve, v1
        nodes["vs"] = opamp(v1, -R("R4") / R("R3"), 1 + R("R4") / R("R3"), dt, tl)
    elif typ == "subtractor":
        v1src = sc.get("v1")
        if v1src:
            ve = load(R("R3") + R("R4"))
            v1 = [gbf_unit(v1src, tk) for tk in t]
        else:
            ve = load(par(R("R1"), R("R3") + R("R4")))
            v1 = ve
        a2 = R("R4") / float(R("R3") + R("R4")) * (1 + R("R2") / R("R1"))
        a1 = -R("R2") / R("R1")
        eff = [a2 * x2 + a1 * x1 for x1, x2 in zip(v1, ve)]
        nodes["ve"], nodes["v1"] = ve, v1
        nodes["vs"] = opamp(eff, 1.0, 1 + R("R2") / R("R1"), dt, tl)
    else:
        raise ValueError("type de circuit inconnu : %s" % typ)
    shown = dict((k, disp(v, tdiv, n0, dt)) for k, v in nodes.items())
    vals = {"f": f, "T": T, "tdiv": tdiv, "vsat": tl["vsat"], "sr": tl["slew_vus"], "gbw": tl["gbw_hz"]}
    vals["vpp_in"] = vpp(shown["ve"])
    vals["vpp_out"] = vpp(shown["vs"])
    vals["gain"] = vals["vpp_out"] / vals["vpp_in"] if vals["vpp_in"] > 1e-9 else float("nan")
    vals["phase"] = phase_deg(shown["ve"], shown["vs"], f, tdiv) if g["kind"] != "dc" else None
    vals["fc"] = fc_of(circ, tl)
    gi = bode(circ, 1.0, tl, glob)
    vals["gain_ideal"] = gi[0] if gi else float("nan")
    vals["vpp_demand"] = vals["gain_ideal"] * vals["vpp_in"] if gi else float("nan")
    vals["slew_need"] = math.pi * f * vals["vpp_demand"] / 1e6 if gi else float("nan")
    vals["us_over_ue"] = vals["gain"]
    bd = bode(circ, f, tl, glob)
    vals["gain_bode"] = bd[0] if bd else float("nan")
    vals["phase_bode"] = bd[1] if bd else float("nan")
    vals["vpp_bode"] = vals["gain_bode"] * vals["vpp_in"] if bd else float("nan")
    if "v1" in shown:
        vals["vpp_v1"] = vpp(shown["v1"])
    vals["max_out"] = max(shown["vs"])
    vals["min_out"] = min(shown["vs"])
    return shown, tdiv, vals
