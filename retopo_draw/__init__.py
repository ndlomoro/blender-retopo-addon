bl_info = {
    "name": "Retopo Draw",
    "author": "LocalLabs",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Retopo",
    "description": "Draw strokes on mesh to auto-generate clean retopology",
    "category": "Mesh",
}

import bpy
import bmesh
from mathutils import Vector

# ── Sub-modules ──
from . import operators
from . import panels
from . import properties

# ── Classes ──
classes = (
    properties.RetopoDrawProperties,
    operators.RetopoDrawStroke,
    operators.RetopoGenerateQuads,
    operators.RetopoClearStrokes,
    operators.RetopoDeleteLastStroke,
    operators.RetopoMergeMesh,
    operators.RetopoProjectToSurface,
    operators.RetopoSettings,
    panels.VIEW3D_PT_retopo_draw,
)

# ── Keymap ──
_keymap_items = []

def register_keymaps():
    wm = bpy.context.window_manager
    km = wm.keyconfigs.addon.keymaps.new(name='Mesh Tool', space_type='EMPTY')
    items = [
        ('retopo_draw.stroke', 'LEFTMOUSE', 'PRESS', {'shift': True}),
        ('retopo_draw.generate', 'G', 'PRESS', {}),
        ('retopo_draw.clear', 'X', 'PRESS', {}),
        ('retopo_draw.undo_stroke', 'Z', 'PRESS', {'ctrl': True}),
        ('retopo_draw.merge', 'M', 'PRESS', {}),
        ('retopo_draw.project', 'P', 'PRESS', {}),
    ]
    for op, key, val, mods in items:
        kmi = km.keymap_items.new(op, key, val, **mods)
        _keymap_items.append((km, kmi))

def unregister_keymaps():
    for km, kmi in _keymap_items:
        km.keymap_items.remove(kmi)
    _keymap_items.clear()

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Object.retopo_draw = bpy.props.PointerProperty(type=properties.RetopoDrawProperties)
    register_keymaps()

def unregister():
    unregister_keymaps()
    if hasattr(bpy.types.Object, 'retopo_draw'):
        del bpy.types.Object.retopo_draw
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
