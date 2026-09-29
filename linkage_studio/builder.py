"""
Linkage Studio — Blender sahne kurucu.

build_walker(): Jansen bacaklarından yürüyen makine kurar. Hareket keyframe
hilesi DEĞİL: her karedeki çubuk konumu linkage.solve_jansen() kapalı-form
çözümünden yazılır ve LINEAR anahtarlanır — anahtar sayısı arttıkça mekanizma
çözümüne yakınsar (varsayılan 96 anahtar/tur).
"""

import math

import bpy

try:
    from . import linkage
except ImportError:  # headless / repo kökünden çalıştırma
    import linkage

RAW2M = 0.03          # Jansen birimi -> metre (bacak düşüşü ~2.8 m)
CYCLE_FRAMES = 48     # tam krank turu = kaç kare (GIF döngüsü tam tur olsun)
BAR_THICKNESS = 2.4   # çubuk çapı, ham birim
LEG_GAP = 34.0        # ardışık bacak çiftleri arası mesafe (ham, X yönü)
HALF_WIDTH = 26.0     # sol/sağ sıra arası (ham, Y yönü)

BAR_MESH = "LS_CubukBirim"
FOOT_MESH = "LS_AyakBirim"


def _birim_cubuk_meshi():
    """+X boyunca 0..1 uzanan sekizgen prizma (çapı 1 ham birim)."""
    if BAR_MESH in bpy.data.meshes:
        return bpy.data.meshes[BAR_MESH]
    n = 8
    verts, faces = [], []
    for i in range(n):
        a = 2 * math.pi * i / n
        verts.append((0.0, 0.5 * math.cos(a), 0.5 * math.sin(a)))
    for i in range(n):
        a = 2 * math.pi * i / n
        verts.append((1.0, 0.5 * math.cos(a), 0.5 * math.sin(a)))
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    faces.append(tuple(range(n - 1, -1, -1)))
    faces.append(tuple(range(n, 2 * n)))
    mesh = bpy.data.meshes.new(BAR_MESH)
    mesh.from_pydata(verts, [], faces)
    return mesh


def _birim_ayak_meshi():
    if FOOT_MESH in bpy.data.meshes:
        return bpy.data.meshes[FOOT_MESH]
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=6, radius=0.5)
    obj = bpy.context.active_object
    mesh = obj.data.copy()
    mesh.name = FOOT_MESH
    bpy.data.objects.remove(obj)
    return mesh


def _mat(name, color, metallic=0.2, rough=0.55):
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1.0)
    try:
        b.inputs["Metallic"].default_value = metallic
        b.inputs["Roughness"].default_value = rough
    except KeyError:
        pass
    return m


def _cubuk_kur(coll, leg_id, bar_id, mat):
    ob = bpy.data.objects.new(f"Bacak{leg_id:02d}_Cubuk{bar_id:02d}", _birim_cubuk_meshi())
    ob.data.materials.append(mat)
    coll.objects.link(ob)
    return ob


def _lineer_yap(ob):
    """Tüm anahtarları LINEAR yap — Bezier ease sahte yumuşatmadır (5.2 slotted API)."""
    ad = ob.animation_data
    if not (ad and ad.action):
        return
    act = ad.action
    if hasattr(act, "fcurves"):  # <= 4.3
        fcs = list(act.fcurves)
    else:
        fcs = [fc for layer in act.layers for strip in layer.strips
               for bag in strip.channelbags for fc in bag.fcurves]
    for fc in fcs:
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"


def _anahtarla(ob, loc, rot_y, sx, sy, frame):
    ob.location = loc
    ob.rotation_euler = (0.0, rot_y, 0.0)
    ob.scale = (sx, sy, sy)
    ob.keyframe_insert("location", frame=frame)
    ob.keyframe_insert("rotation_euler", frame=frame)
    ob.keyframe_insert("scale", frame=frame)


def build_walker(leg_count=6, cycle_frames=CYCLE_FRAMES, scale=RAW2M,
                 bar_thickness=BAR_THICKNESS, collection_name="Strandbeest"):
    """Yürüyen makineyi kurar; rapor döndürür (boyutlar, kare aralığı)."""
    stats = linkage.analyze_walk(720)
    z_ground = stats["y_min"] * scale

    coll = bpy.data.collections.new(collection_name)
    bpy.context.scene.collection.children.link(coll)

    m_bar = _mat("LS_Boru", (0.72, 0.69, 0.62), metallic=0.0, rough=0.45)
    m_foot = _mat("LS_Ayak", (0.10, 0.075, 0.045), metallic=0.0, rough=0.85)

    bar_mesh = _birim_cubuk_meshi()
    foot_mesh = _birim_ayak_meshi()

    pairs = leg_count // 2
    bars = []   # (obj, u, v, leg, x_off, y_off)
    feet = []
    crank_objs = []
    for leg in range(leg_count):
        side = 1.0 if leg % 2 == 0 else -1.0
        p = leg // 2
        x_off = (p - (pairs - 1) / 2) * LEG_GAP
        y_off = side * HALF_WIDTH

        leg_bars = []
        for bar_id, (u, v) in enumerate(linkage.BARS):
            ob = bpy.data.objects.new(f"Bacak{leg:02d}_Cubuk{bar_id:02d}", bar_mesh)
            ob.data.materials.append(m_bar)
            coll.objects.link(ob)
            leg_bars.append((ob, u, v))

        # krank: PIVOT_1 -> eklem 2 (11. çubuk, sürekli döner)
        crank = bpy.data.objects.new(f"Bacak{leg:02d}_Cubuk_Krank", bar_mesh)
        crank.data.materials.append(_mat("LS_Krank", (0.55, 0.12, 0.02), metallic=0.3, rough=0.5))
        coll.objects.link(crank)
        crank_objs.append(crank)

        foot = bpy.data.objects.new(f"Bacak{leg:02d}_Ayak", foot_mesh)
        foot.data.materials.append(m_foot)
        coll.objects.link(foot)

        # gövde kolu: PIVOT_0 -> PIVOT_1 arası, sabit (keyframesiz)
        base = bpy.data.objects.new(f"Bacak{leg:02d}_Govde", bar_mesh)
        base.data.materials.append(m_bar)
        coll.objects.link(base)
        dx = linkage.PIVOT_1[0] - linkage.PIVOT_0[0]
        dy = linkage.PIVOT_1[1] - linkage.PIVOT_0[1]
        ln = math.hypot(dx, dy)
        base.location = ((x_off + linkage.PIVOT_0[0]) * scale,
                         y_off * scale, linkage.PIVOT_0[1] * scale)
        base.rotation_euler = (0.0, -math.atan2(dy, dx), 0.0)
        base.scale = (ln * scale, bar_thickness * scale, bar_thickness * scale)

        bars.extend((ob, u, v, leg, x_off, y_off) for ob, u, v in leg_bars)
        feet.append((foot, leg, x_off, y_off))

    # ---- animasyon: her karede gerçek mekanizma çözümü, LINEAR anahtar
    sc = bpy.context.scene
    phases = linkage.leg_phases(leg_count)
    foot_r = 1.6 * scale
    crank_len = 15.0 * scale
    for k in range(cycle_frames + 1):
        frame = k + 1
        theta = k * 360.0 / cycle_frames
        solved = {}
        for leg in range(leg_count):
            solved[leg] = linkage.solve_jansen((theta + phases[leg]) % 360.0)
        for ob, u, v, leg, x_off, y_off in bars:
            pu, pv = solved[leg][u], solved[leg][v]
            dx, dy = pv[0] - pu[0], pv[1] - pu[1]
            _anahtarla(ob,
                       ((x_off + pu[0]) * scale, y_off * scale, pu[1] * scale),
                       -math.atan2(dy, dx),
                       math.hypot(dx, dy) * scale, bar_thickness * scale, frame)
        # krank: pim eklemi 2, PIVOT_1'den döner
        for leg in range(leg_count):
            crank = crank_objs[leg]
            p2 = solved[leg][2]
            dx, dy = p2[0] - linkage.PIVOT_1[0], p2[1] - linkage.PIVOT_1[1]
            _anahtarla(crank,
                       ((x_off + linkage.PIVOT_1[0]) * scale,
                        y_off * scale, linkage.PIVOT_1[1] * scale),
                       -math.atan2(dy, dx), crank_len, bar_thickness * scale, frame)
        for ob, leg, x_off, y_off in feet:
            px, py = solved[leg][linkage.FOOT]
            ob.location = ((x_off + px) * scale, y_off * scale, py * scale - foot_r)
            ob.scale = (foot_r / 0.5,) * 3
            ob.keyframe_insert("location", frame=frame)
            ob.keyframe_insert("scale", frame=frame)

    for ob in coll.objects:
        _lineer_yap(ob)

    sc.frame_start = 1
    sc.frame_end = cycle_frames + 1
    sc.render.fps = 24

    # zemin (kum-toprak dokusu: noise ile renk + pürüz)
    bpy.ops.mesh.primitive_plane_add(size=400)
    ground = bpy.data.objects["Plane"]
    ground.name = "Zemin"
    ground.location = (0, 0, z_ground - 0.01)
    gm, gnt = None, None
    gm = bpy.data.materials.new("LS_Zemin")
    gm.use_nodes = True
    gnt = gm.node_tree
    gnt.nodes.remove(gnt.nodes["Principled BSDF"])
    out = gnt.nodes["Material Output"]
    bsdf = gnt.nodes.new("ShaderNodeBsdfPrincipled")
    noise = gnt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 0.8
    noise.inputs["Detail"].default_value = 6.0
    ramp = gnt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.150, 0.135, 0.112, 1)
    ramp.color_ramp.elements[1].color = (0.225, 0.205, 0.172, 1)
    gnt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    gnt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.95
    gnt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    ground.data.materials.append(gm)
    for c in list(ground.users_collection):
        c.objects.unlink(ground)
    coll.objects.link(ground)

    return {
        "legs": leg_count, "cycle_frames": cycle_frames,
        "frame_start": 1, "frame_end": cycle_frames + 1,
        "z_ground": z_ground, "scale": scale,
        "stride_m": stats["stride"] * scale, "lift_m": stats["lift"] * scale,
        "footprint_x": (min(stats["x_min"], linkage.PIVOT_0[0]) * scale,
                        max(stats["x_max"], linkage.PIVOT_1[0]) * scale),
    }
