import bpy

class VIEW3D_PT_retopo_draw(bpy.types.Panel):
    """Sidebar panel for Retopo Draw controls."""
    bl_label = "Retopo Draw"
    bl_idname = "VIEW3D_PT_retopo_draw"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Retopo'
    bl_context = 'mesh_edit'

    def draw(self, context):
        layout = self.layout
        obj = context.active_object

        if not obj or obj.type != 'MESH':
            layout.label(text="Select a mesh object")
            return

        rd = obj.retopo_draw

        # Status
        box = layout.box()
        row = box.row(align=True)
        row.label(text=f"Strokes: {rd.stroke_count}")
        row = box.row()
        row.prop(rd, "vertex_spacing")
        row.prop(rd, "snap_enabled")

        # Drawing
        box = layout.box()
        box.label(text="Drawing")
        box.operator("retopo_draw.stroke", icon='BRUSH_STROKE')
        box.operator("retopo_draw.undo_stroke", icon='UNDO')
        box.operator("retopo_draw.clear", icon='X')

        # Generate
        box = layout.box()
        box.label(text="Generate")
        row = box.row()
        row.prop(rd, "quad_fill_mode")
        box.operator("retopo_draw.generate", icon='MOD_BUILD')
        row = box.row()
        row.prop(rd, "auto_generate")

        # Post-processing
        box = layout.box()
        box.label(text="Post-Process")
        box.operator("retopo_draw.project", icon='MOD_SHRINKWRAP')
        box.operator("retopo_draw.merge", icon='GROUP_VCOL')

        # Settings
        layout.operator("retopo_draw.settings", icon='PRESET')
