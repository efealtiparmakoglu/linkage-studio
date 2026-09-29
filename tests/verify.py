"""
Linkage Studio — doğrulama kapıları.

    python3 tests/verify.py

Blender gerekmez: linkage.py saf matematiktir. Bir kapı kırmızıysa add-on
kurulmaz ve render açılmaz; sayısal teşhis basılır.
"""

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import linkage  # noqa: E402

GATES = []


def gate(name):
    def deco(fn):
        GATES.append((name, fn))
        return fn
    return deco


@gate("G1 kapanma: tüm çubuklar 360° boyunca boylarını koruyor")
def g1_closure():
    errs = []
    worst, worst_th = 0.0, None
    for i in range(720):
        th = i * 0.5
        e = linkage.bar_error(linkage.solve_jansen(th))
        if e > worst:
            worst, worst_th = e, th
    if worst > 1e-6:
        errs.append(f"kapanma hatası {worst:.3e} (θ={worst_th}) > 1e-6")
    return errs


@gate("G2 sabit mafsallar: zemin noktaları krankla birlikte sürüklenmiyor")
def g2_ground():
    errs = []
    for i in range(0, 720, 7):
        pts = linkage.solve_jansen(i * 0.5)
        if math.hypot(pts[0][0] - linkage.PIVOT_0[0], pts[0][1] - linkage.PIVOT_0[1]) > 1e-12:
            errs.append(f"eklem 0 kaydı θ={i * 0.5}: {pts[0]}")
            break
        if math.hypot(pts[1][0] - linkage.PIVOT_1[0], pts[1][1] - linkage.PIVOT_1[1]) > 1e-12:
            errs.append(f"eklem 1 kaydı θ={i * 0.5}: {pts[1]}")
            break
    return errs


@gate("G3 süreklilik: her krank açısında tek dalda çözüm var (dal sıçraması yok)")
def g3_continuity():
    errs = []
    prev = None
    max_jump = 0.0
    n = 1440
    for i in range(n):
        try:
            foot = linkage.solve_jansen(i * 360.0 / n)[linkage.FOOT]
        except ValueError as e:
            errs.append(f"θ={i * 360.0 / n:.2f}: {e}")
            continue
        if prev is not None:
            jump = math.hypot(foot[0] - prev[0], foot[1] - prev[1])
            max_jump = max(max_jump, jump)
            if jump > 1.0:  # 0.25°'lik adımda ayak santimetrelere fırlamaz
                errs.append(f"ayak θ={i * 360.0 / n:.2f}'de {jump:.2f} birim sıçradı — dal değişti")
                break
        prev = foot
    return errs


@gate("G4 yürüyüş: ayak izi gerçek adım profili (stance + kaldırma + adım boyu)")
def g4_gait():
    w = linkage.analyze_walk(720)
    errs = []
    # döngü kapalı olmalı: ilk ve son nokta (bir adım öncesi) çakışık
    p0 = linkage.solve_jansen(0.0)[linkage.FOOT]
    p1 = linkage.solve_jansen(360.0)[linkage.FOOT]
    if math.hypot(p0[0] - p1[0], p0[1] - p1[1]) > 1e-6:
        errs.append("yörünge kapalı değil: θ=0 ve θ=360 farklı")
    if not 0.35 <= w["stance_frac"] <= 0.65:
        errs.append(f"stance oranı {w['stance_frac']:.2f} 0.35-0.65 dışında (ölçüm {0.52})")
    if not 15.0 <= w["lift"] <= 30.0:
        errs.append(f"adım yüksekliği {w['lift']:.2f} 15-30 dışında (ölçüm 22.46)")
    if not 40.0 <= w["stride"] <= 90.0:
        errs.append(f"adım boyu {w['stride']:.2f} 40-90 dışında (ölçüm 64.88)")
    return errs


@gate("G5 fazlar: antifaz bacaklar zemini her an örtüyor")
def g5_phases():
    errs = []
    lifts = []
    for i in range(36):
        th = i * 10.0
        ya = linkage.solve_jansen(th)[linkage.FOOT][1]
        yb = linkage.solve_jansen(th + 180.0)[linkage.FOOT][1]
        lifts.append(abs(ya - yb))
    w = linkage.analyze_walk(720)
    mean_sep = sum(lifts) / len(lifts)
    if mean_sep < w["lift"] / 4:
        errs.append(f"antifaz ortalama ayırma {mean_sep:.2f} < lift/4 ({w['lift'] / 4:.2f}) —"
                    f" iki bacak aynı anda havada kalabilir")
    for n in (2, 4, 6, 8):
        ph = linkage.leg_phases(n)
        if any(not 0.0 <= p < 360.0 for p in ph):
            errs.append(f"n={n}: faz 0-360 dışında: {ph}")
    return errs


@gate("G6 çok bacak: 6 bacaklı dizilimde zemin her an temas altında")
def g6_multileg():
    w = linkage.analyze_walk(720)
    phases = linkage.leg_phases(6)
    errs = []
    worst = -1e9
    worst_th = None
    for i in range(360):
        th = i * 1.0
        low = min(linkage.solve_jansen((th + p) % 360.0)[linkage.FOOT][1] for p in phases)
        if low > worst:
            worst, worst_th = low, th
    # en kötü karede bile bir ayak zemin şeridine değmeli (görsel temas)
    if worst > w["y_min"] + 3.0:
        errs.append(f"θ={worst_th}: en düşük ayak {worst:.2f} zemin+3'ün üstünde —"
                    f" makine havada sallanıyor")
    return errs


def main():
    failures = 0
    for name, fn in GATES:
        errs = fn()
        if errs:
            failures += 1
            print(f"❌ {name}")
            for e in errs[:10]:
                print(f"   {e}")
        else:
            print(f"✅ {name}")
    print(f"\n{'KAPILAR KIRIK' if failures else 'TÜM KAPILAR YEŞİL'} ({failures} kırık)")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
