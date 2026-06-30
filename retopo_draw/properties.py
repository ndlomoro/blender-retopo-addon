import bpy

class RetopoDrawProperties(bpy.types.PropertyGroup):
    """Per-object settings for Retopo Draw addon."""
    stroke_count: bpy.props.IntProperty(
        name="Strokes", default=0,
        description="Number of drawn strokes",
    )
    vertex_spacing: bpy.props.FloatProperty(
        name="Vertex Spacing", default=0.05, min=0.001, max=1.0, step=10,
        description="Minimum distance between vertices in a stroke",
    )
    snap_enabled: bpy.props.BoolProperty(
        name="Snap to Surface", default=True,
        description="Snap vertices to mesh surface via raycasting",
    )
    auto_generate: bpy.props.BoolProperty(
        name="Auto Generate", default=False,
        description="Auto-generate mesh when stroke ends",
    )
    quad_fill_mode: bpy.props.EnumProperty(
        name="Fill Mode",
        items=[
            ('QUAD', "Quads", "Quad-dominant topology"),
            ('TRIANGLE', "Triangles", "Triangle mesh"),
            ('GRID', "Grid", "Grid-like quad layout"),
        ],
        default='QUAD',
        description="How to fill between stroke vertices",
    )
    stroke_color: bpy.props.FloatVectorProperty(
        name="Stroke Color", default=(1.0, 0.3, 0.1, 1.0),
        min=0.0, max=1.0, size=4, subtype='COLOR',
        description="Color of stroke visualization",
    )
