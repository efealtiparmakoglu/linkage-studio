"""Linkage Studio — Blender add-on: Jansen bacaklı yürüyen makine stüdyosu.

N-panel'de bacak sayısını seç, "Yürüyen Makine Kur" bas; çubuklar mekanizmanın
kapalı-form kinematik çözümüyle anahtarlanır (easing yok, sahte yok).

Kurulum: Edit > Preferences > Add-ons > Install -> linkage_studio.zip
"""

bl_info = {
    "name": "Linkage Studio",
    "author": "efealtiparmakoglu",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "3D View > N-panel > Linkage",
    "description": "Jansen bacaklı yürüyen makineler — gerçek bağlantı kinematiğiyle",
    "category": "Object",
}

import importlib
import math
import sys
import os

import bpy

from . import builder


def _reload():
    importlib.reload(builder)


# ---------------------------------------------------------------- properties

class LS_Props(bpy.types.PropertyGroup):
    leg_count: bpy.props.IntProperty(
        name="Bacak sayısı", default=6, min=2, max=12, step=2,
        description="Çift sayı olmalı: sol/sağ sıralar hâlinde dizilir")
    scale: bpy.props.FloatProperty(
        name="Ölçek (m/birim)", default=builder.RAW2M, min=0.005, max=0.2,
        description="Jansen biriminden metreye; 0.03 -> kalça yüksekliği ~2.5 m")
    bar_thickness: bpy.props.FloatProperty(
        name="Çubuk çapı (ham)", default=builder.BAR_THICKNESS, min=0.8, max=8.0)
    cycle_frames: bpy.props.IntProperty(
        name="Çevrim karesi", default=builder.CYCLE_FRAMES, min=12, max=192,
        description="Tam krank turu kaç kare sürsün")


# ---------------------------------------------------------------- operatorler

class LS_OT_build(bpy.types.Operator):
    """Jansen bacaklarından yürüyen makineyi kurar ve anahtarlar"""
    bl_idname = "linkage.build_walker"
    bl_label = "Yürüyen Makine Kur"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, ctx):
        p = ctx.scene.ls_props
        old = bpy.data.collections.get("Strandbeest")
        if old:
            for ob in list(old.objects):
                bpy.data.objects.remove(ob)
            bpy.data.collections.remove(old)
        info = builder.build_walker(
            leg_count=p.leg_count, cycle_frames=p.cycle_frames,
            scale=p.scale, bar_thickness=p.bar_thickness)
        ctx.scene.frame_set(1)
        self.report({"INFO"},
                    f"{info['legs']} bacak | adım {info['stride_m']:.2f} m | "
                    f"yükseklik {info['lift_m']:.2f} m | kare {info['frame_start']}-{info['frame_end']}")
        return {"FINISHED"}


class LS_OT_range(bpy.types.Operator):
    """Kare aralığını çevrime göre ayarla (döngü kapanır)"""
    bl_idname = "linkage.set_range"
    bl_label = "Kare Aralığını Ayarla"

    def execute(self, ctx):
        sc = ctx.scene
        sc.frame_start = 1
        sc.frame_end = sc.ls_props.cycle_frames + 1
        return {"FINISHED"}


# ---------------------------------------------------------------- panel

class LS_PT_panel(bpy.types.Panel):
    bl_label = "Linkage Studio"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Linkage"

    def draw(self, ctx):
        lay = self.layout
        p = ctx.scene.ls_props
        lay.prop(p, "leg_count")
        lay.prop(p, "scale")
        lay.prop(p, "bar_thickness")
        lay.prop(p, "cycle_frames")
        col = lay.column(align=True)
        col.operator("linkage.build_walker", icon="OUTLINER_OB_ARMATURE")
        col.operator("linkage.set_range", icon="TIME")
        info = lay.box()
        info.label(text="Jansen bacağı: 11 çubuk, 1 serbestlik")
        info.label(text="konum = gerçek çözüm, easing yok")


classes = (LS_Props, LS_OT_build, LS_OT_range, LS_PT_panel)


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.ls_props = bpy.props.PointerProperty(type=LS_Props)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
    del bpy.types.Scene.ls_props
