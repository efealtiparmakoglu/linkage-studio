"""Blender içi e2e: add-on'u kaydet, operatörü çalıştır, saneyi doğrula.

    blender --background --python tests/e2e_addon.py
"""

import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import bpy  # noqa: E402

import linkage_studio  # noqa: E402

linkage_studio.register()

errs = []

bpy.ops.linkage.build_walker()
coll = bpy.data.collections.get("Strandbeest")
if coll is None:
    errs.append("Strandbeest koleksiyonu yok")
else:
    n_bars = sum(1 for o in coll.objects if "_Cubuk" in o.name)
    n_feet = sum(1 for o in coll.objects if "_Ayak" in o.name)
    if n_bars != 6 * 11:  # 10 bağlantı çubuğu + 1 krank
        errs.append(f"çubuk sayısı {n_bars} != 66")
    if n_feet != 6:
        errs.append(f"ayak sayısı {n_feet} != 6")
if bpy.context.scene.frame_end != 49:
    errs.append(f"frame_end {bpy.context.scene.frame_end} != 49")
anim = sum(1 for o in bpy.data.objects if o.animation_data and o.animation_data.action)
if anim != 6 * 12:  # 10 çubuk + krank + ayak = 12 hareketli/bacak
    errs.append(f"animasyonlu nesne {anim} != 72")
# anahtarlar gerçekten LINEAR mı? (easing yasağı — 5.2 slotted action API)
def _fcurves(ob):
    act = ob.animation_data.action
    if hasattr(act, "fcurves"):
        return list(act.fcurves)
    return [fc for layer in act.layers for strip in layer.strips
            for bag in strip.channelbags for fc in bag.fcurves]

for o in bpy.data.objects:
    if not (o.animation_data and o.animation_data.action):
        continue
    for fc in _fcurves(o)[:1]:
        for kp in fc.keyframe_points:
            if kp.interpolation != "LINEAR":
                errs.append(f"{o.name}: LINEAR olmayan anahtar")
                break
        break

# 2 bacak + farklı ölçekle yeniden kur (undo akışı / property yolu)
bpy.context.scene.ls_props.leg_count = 2
bpy.ops.linkage.build_walker()
n_bars2 = sum(1 for o in bpy.data.collections["Strandbeest"].objects if "_Cubuk" in o.name)
if n_bars2 != 2 * 11:
    errs.append(f"2 bacakta çubuk {n_bars2} != 22")

if errs:
    print("E2E KIRIK:")
    for e in errs:
        print("  " + e)
    sys.exit(1)
print("E2E YEŞİL: add-on kurulumu, 6 ve 2 bacaklı makine, LINEAR anahtarlar tamam")
