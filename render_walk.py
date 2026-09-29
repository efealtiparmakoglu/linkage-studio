"""
Yürüyen makineyi kurar, kamerayı takip ayarlar, render alır.

    blender --background --python render_walk.py -- --preview   # 4 kare 640x360
    blender --background --python render_walk.py               # 48 kare 960x540
"""

import math
import os
import sys

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)

import bpy  # noqa: E402

from linkage_studio import builder  # noqa: E402


def args():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return {"preview": "--preview" in a}


def render_setup(preview):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "METAL"
    prefs.get_devices()
    for d in prefs.devices:
        d.use = True
    sc.cycles.device = "GPU"
    if preview:
        sc.render.resolution_x, sc.render.resolution_y = 640, 360
        sc.cycles.samples = 32
    else:
        sc.render.resolution_x, sc.render.resolution_y = 960, 540
        sc.cycles.samples = 64
    sc.cycles.use_denoising = True
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    sc.view_settings.exposure = -0.3
    sc.render.image_settings.file_format = "PNG"


def dunya():
    w = bpy.data.worlds.new("Gokyuzu")
    bpy.context.scene.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.45, 0.58, 0.75, 1.0)
    bg.inputs[1].default_value = 0.45

    sun = bpy.data.lights.new("Gun", "SUN")
    sun.energy = 5.0
    sun.angle = math.radians(2.0)
    sun.color = (1.0, 0.87, 0.72)
    so = bpy.data.objects.new("Gun", sun)
    bpy.context.scene.collection.objects.link(so)
    # makinenin ön-solundan alçak gelir: gövde aydınlanır, gölgeler sağa uzanır
    so.rotation_euler = (math.radians(66), 0.0, math.radians(200))


def _lineer(ob, index=0):
    """İlk fcurve'ün anahtarlarını LINEAR yap (5.2 slotted action API)."""
    act = ob.animation_data.action
    if hasattr(act, "fcurves"):  # <= 4.3
        fcs = list(act.fcurves)
    else:
        fcs = [fc for layer in act.layers for strip in layer.strips
               for bag in strip.channelbags for fc in bag.fcurves]
    for kp in fcs[index].keyframe_points:
        kp.interpolation = "LINEAR"


def kamera(track_x_hizi, cycle):
    """Makinenin yanında koşan kamera: alçak açı, gövde çizgisi ortada."""
    cam = bpy.data.cameras.new("Cam")
    cam.lens = 30
    co = bpy.data.objects.new("Kamera", cam)
    bpy.context.scene.collection.objects.link(co)

    hedef = bpy.data.objects.new("KameraHedef", None)
    bpy.context.scene.collection.objects.link(hedef)
    tr = co.constraints.new("TRACK_TO")
    tr.target = hedef

    # başlangıç konumları (yürüme x'i frame 1'de 0) — ayak bölgesi + gölge payı çerçevede
    co.location = (-6.4, -6.8, 0.5)
    hedef.location = (0.35, 0.0, -1.0)
    # LINEAR: aynı hızla ilerler, makine karede kalır
    end = (cycle + 1)
    co.keyframe_insert("location", frame=1)
    co.location.x += track_x_hizi * end
    co.keyframe_insert("location", frame=end)
    _lineer(co)
    hedef.keyframe_insert("location", frame=1)
    hedef.location.x += track_x_hizi * end
    hedef.keyframe_insert("location", frame=end)
    _lineer(hedef)

    bpy.context.scene.camera = co


def main():
    opts = args()
    sc = bpy.context.scene
    sc.frame_start = 1

    # default küp/kamera/ışık temizliği (json-cinema dersleri)
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)

    info = builder.build_walker(leg_count=6)
    sc.frame_end = info["frame_end"]
    cycle = info["cycle_frames"]

    # gerçek yürüme: gövde çevrim başına stride ilerler (stance ayağı yerde sabit kalır)
    speed = info["stride_m"] / cycle  # metre/kare
    body = bpy.data.objects.new("Yuruyuscu", None)
    bpy.context.scene.collection.objects.link(body)
    for ob in bpy.data.collections["Strandbeest"].objects:
        ob.parent = body
    body.keyframe_insert("location", frame=1)
    body.location.x = speed * (cycle + 1)
    body.keyframe_insert("location", frame=cycle + 1)
    _lineer(body)

    dunya()
    kamera(speed, cycle)
    render_setup(opts["preview"])

    out = os.path.join(REPO, "renders")
    os.makedirs(out, exist_ok=True)
    frames = [1, 13, 25, 37] if opts["preview"] else range(1, cycle + 1)
    for f in frames:
        sc.frame_set(f)
        sc.render.filepath = os.path.join(
            out, "preview" if opts["preview"] else "walk", f"frame_{f:04d}.png")
        bpy.ops.render.render(write_still=True)
        print(f"[kare {f}] bitti", flush=True)
    print(f"== BİTTİ -> {out} ==")


main()
