"""
Linkage Studio — saf matematik mekanizma çözücü.

Blender'a bağımlılığı yok; tests/verify.py kapıları doğrudan bu modülü test eder.
Jansen (Strandbeest) bacağı: 11 çubuk + zemin, 1 serbestlik derecesi. Krank açısı
verilir, 8 eklemin düzlem konumu kapalı formda (çember-çember kesişimi) çözülür.
Kural: easing yok, keyframe hilesi yok — konum = mekanizmanın gerçek çözümü.

Kaynak ölçüler: Theo Jansen'in standart oranları (a=38.0, l=7.8 zemin ofseti).
"""

import math

# ---------------------------------------------------------------- tanım

# Zemin: eklemin 0 = krank ekseni, 1 = ikinci sabit mafsal
PIVOT_0 = (0.0, 0.0)
PIVOT_1 = (38.0, 7.8)
CRANK = 15.0          # krank uzunluğu (m), PIVOT_1 etrafında döner

# Çubuklar: (u, v): uzunluk — bd_topology; ayak = eklemin 7
BARS = {
    (0, 3): 41.5,   # b: zemin 0 -> üst üçgen (krank pimi 2 DEĞİL)
    (2, 3): 50.0,   # j: krank pimi -> üst üçgen
    (3, 4): 55.8,   # e: üst üçgen kenarı
    (4, 0): 40.1,   # d: üst üçgen -> zemin 0
    (0, 5): 39.3,   # c: zemin 0 -> alt üçgen
    (2, 5): 61.9,   # k: krank pimi -> alt üçgen
    (4, 6): 39.4,   # f: üst üçgen -> alt üçgen
    (5, 6): 36.7,   # g: alt üçgen kenarı
    (6, 7): 65.7,   # h: alt üçgen -> ayak
    (7, 5): 49.0,   # i: ayak -> alt üçgen
}

FOOT = 7

# Çözüm sırası: her adım (merkez0, r0, merkez1, r1, dalga) — dalga ±1 Bourke dalı
SOLVE_STEPS = [
    (3, ((0, None), (2, None)), +1),   # p3: çember(0, b) ∩ çember(2, j), dal +1
    (4, ((0, None), (3, None)), +1),   # p4: çember(0, d) ∩ çember(3, e), dal +1
    (5, ((0, None), (2, None)), -1),   # p5: çember(0, c) ∩ çember(2, k), dal -1
    (6, ((4, None), (5, None)), -1),   # p6: çember(4, f) ∩ çember(5, g), dal -1
    (7, ((5, None), (6, None)), +1),   # p7 = AYAK: çember(5, i) ∩ çember(6, h), dal +1
]

# çubuk uzunluğu, çözüm adımındaki rolüyle eşleşmeli
STEP_RADII = {
    3: ((0, 41.5), (2, 50.0)),
    4: ((0, 40.1), (3, 55.8)),
    5: ((0, 39.3), (2, 61.9)),
    6: ((4, 39.4), (5, 36.7)),
    7: ((5, 49.0), (6, 65.7)),
}


# ---------------------------------------------------------------- matematik

def circle_intersect(p0, r0, p1, r1, branch):
    """Bourke çember-çember kesişimi; branch=+1/-1 iki çözümden birini seçer.

    Kesişim yoksa ValueError — kapı buradan yakalar (çözülemez krank açısı).
    """
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    d = math.hypot(dx, dy)
    if d > r0 + r1 or d < abs(r0 - r1) or d == 0:
        raise ValueError(f"çemberler kesişmiyor: d={d:.3f} r0={r0} r1={r1}")
    a = (r0 * r0 - r1 * r1 + d * d) / (2 * d)
    h = math.sqrt(max(r0 * r0 - a * a, 0.0))
    bx, by = p0[0] + a * dx / d, p0[1] + a * dy / d
    ox, oy = -dy * h / d * branch, dx * h / d * branch
    return (bx + ox, by + oy)


def solve_jansen(theta_deg):
    """Krank açısına (derece) 8 eklemin konumunu döndürür: liste[(x, y)] × 8."""
    th = math.radians(theta_deg)
    pts = [None] * 8
    pts[0] = PIVOT_0
    pts[1] = PIVOT_1
    pts[2] = (PIVOT_1[0] + CRANK * math.cos(th), PIVOT_1[1] + CRANK * math.sin(th))
    for joint, ((ca, _), (cb, _)), branch in SOLVE_STEPS:
        (pa, ra), (pb, rb) = STEP_RADII[joint]
        pts[joint] = circle_intersect(pts[pa], ra, pts[pb], rb, branch)
    return pts


def bar_error(pts):
    """Tüm çubukların gerçek uzunluk sapması (maksimum) — kapı ölçeri."""
    worst = 0.0
    for (u, v), ln in BARS.items():
        err = abs(math.hypot(pts[u][0] - pts[v][0], pts[u][1] - pts[v][1]) - ln)
        worst = max(worst, err)
    return worst


# ---------------------------------------------------------------- yürüyüş analizi

def foot_path(n=720):
    """Tam turda ayak yörüngesi: [(theta, x, y)] × n (kapalı döngü)."""
    return [(theta, *solve_jansen(theta)[FOOT])
            for theta in (i * 360.0 / n for i in range(n))]


def analyze_walk(n=720):
    """Ayak izinin yürüyüş istatistikleri — kapılar buradan beslenir.

    stance: ayağın yerde kaldığı (en alt şerit) kesintisiz yay — makineyi
    ileri iten faz. stride: stance boyunca x ilerlemesi. lift: adım yüksekliği.
    Döngü sınırını aşan yaylar ikiye katlanmış periyotla unwrapped ölçülür.
    """
    path = foot_path(n)
    xs = [x for _, x, _ in path]
    ys = [y for _, _, y in path]
    y_min, y_max = min(ys), max(ys)

    band = 2.0
    stance = [i for i, (_, _, y) in enumerate(path) if y <= y_min + band]
    if not stance:
        raise ValueError("stance boş — mekanizma yürümüyor")

    # periyodu ikiye kat: 360->0 sınırını aşan yaylar tek parça görünür
    stance2 = stance + [i + n for i in stance]
    xs2 = xs + xs
    best_start, best_len = stance2[0], 1
    run_start, run_len = stance2[0], 1
    for prev, i in zip(stance2, stance2[1:]):
        if i == prev + 1:
            run_len += 1
        else:
            run_start, run_len = i, 1
        if run_len > best_len:
            best_start, best_len = run_start, run_len

    stride = xs2[best_start + best_len - 1] - xs2[best_start]
    return {
        "y_min": y_min, "y_max": y_max,
        "lift": y_max - y_min,
        "stance_frac": best_len / n,
        "stride": stride,
        "stance_band": band,
        "x_min": min(xs), "x_max": max(xs),
    }


def leg_phases(n_legs, phase_offset_deg=None):
    """n bacaklı makinenin krank faz ofsetleri.

    Sol/sağ çiftler AYNI fazda yürür (gerçek strandbeest dizilimi); ardışık
    çiftler eşit arayla kayar. n=2 özel: tek çift antifaz — zemin sürekli
    destek altında kalır.
    """
    if n_legs == 2:
        return [0.0, 180.0]
    pairs = n_legs // 2
    return [((i // 2) * 360.0 / pairs) % 360.0 for i in range(n_legs)]
