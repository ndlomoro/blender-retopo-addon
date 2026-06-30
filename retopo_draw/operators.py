import bpy
import bmesh
from mathutils import Vector
import numpy as np
from scipy.spatial import Delaunay
import bpy_extras.view3d_utils

# ─────────────────────────────────────────────────────────────
# Retopo Draw Stroke — Modal drawing operator
# ─────────────────────────────────────────────────────────────

class RetopoDrawStroke(bpy.types.Operator):
    """Draw strokes on mesh surface. Shift+Click to start, drag to draw, release to finish."""
    bl_idname = "retopo_draw.stroke"
    bl_label = "Retopo Draw Stroke"
    bl_options = {'UNDO', 'REGISTER'}

    _draw_handle = None
    target_obj = None
    current_stroke = []
    all_strokes = []
    is_drawing = False

    def modal(self, context, event):
        context.area.tag_redraw()

        # Start drawing on Shift+LMB press
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS' and event.shift and not self.is_drawing:
            pt = self._raycast(context, event.mouse_x, event.mouse_y)
            if pt:
                self.is_drawing = True
                self.current_stroke = [pt]
            return {'RUNNING_MODAL'}

        # Add points while dragging
        if self.is_drawing and event.type == 'MOUSEMOVE':
            pt = self._raycast(context, event.mouse_x, event.mouse_y)
            if pt and self.current_stroke:
                last = self.current_stroke[-1]
                spacing = self.target_obj.retopo_draw.vertex_spacing
                if (pt - last).length > spacing:
                    self.current_stroke.append(pt)
            return {'RUNNING_MODAL'}

        # Finish stroke on release
        if event.type == 'LEFTMOUSE' and event.value == 'RELEASE' and self.is_drawing:
            if len(self.current_stroke) >= 3:
                self.all_strokes.append(list(self.current_stroke))
                rd = self.target_obj.retopo_draw
                rd.stroke_count += 1
                self._save_strokes()
                if rd.auto_generate:
                    self._do_generate(context)
            self.current_stroke = []
            self.is_drawing = False
            return {'RUNNING_MODAL'}

        # Cancel
        if event.type in {'RIGHTMOUSE', 'ESC'}:
            self._cleanup(context)
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        if not context.active_object or context.active_object.type != 'MESH':
            self.report({'ERROR'}, "Select a mesh object first!")
            return {'FINISHED'}

        self.target_obj = context.active_object
        self.current_stroke = []
        self.all_strokes = []
        self.is_drawing = False

        # Load existing strokes
        stored = self.target_obj.get("retopo_strokes_data", [])
        self.all_strokes = [[Vector(pt) for pt in stroke] for stroke in stored]

        # Register draw handler
        self._draw_handle = bpy.types.SpaceView3D.draw_handler_add(
            self._draw_callback, (context,), 'WINDOW', 'POST_VIEW'
        )
        context.window_manager.modal_handler_add(self)

        return {'RUNNING_MODAL'}

    def _raycast(self, context, mx, my):
        """Raycast from mouse position to target mesh surface."""
        if not self.target_obj:
            return None

        region = context.region
        rv3d = context.region_data
        if not rv3d:
            return None

        depsgraph = context.evaluated_depsgraph_get()
        success, ray_origin, ray_direction = bpy_extras.view3d_utils.mouse_region_3d(
            context, region, rv3d, mx, my
        )
        if not success:
            return None

        # Raycast against scene
        hit, location, normal, face_idx, hit_obj, matrix, _ = \
            context.scene.ray_cast(depsgraph, ray_origin, ray_direction, max_distance=10000.0)

        if hit and hit_obj == self.target_obj:
            return location

        # Fallback: direct mesh raycast
        mesh = self.target_obj.evaluated_get(depsgraph).to_mesh()
        if mesh:
            world_mat = self.target_obj.matrix_world
            inv_mat = world_mat.inverted()
            ray_orig_local = inv_mat @ ray_origin
            ray_dir_local = (inv_mat.to_3x3() @ ray_direction).normalized()
            hit, loc, norm, fi = mesh.ray_cast(ray_orig_local, ray_dir_local)
            if hit:
                mesh.clear_override()
                return world_mat @ loc
            mesh.clear_override()

        return None

    def _draw_callback(self, context):
        """Draw stroke visualization in 3D viewport."""
        import gpu
        from gpu_extras.batch import batch_for_shader

        color = list(self.target_obj.retopo_draw.stroke_color)
        all_pts = []
        for stroke in self.all_strokes:
            all_pts.extend(stroke)
        if self.current_stroke:
            all_pts.extend(self.current_stroke)

        if not all_pts:
            return

        # Draw vertices
        shader_pt = gpu.shader.from_builtin('UNIFORM_COLOR')
        shader_pt.bind()
        shader_pt.uniform_float("color", color)
        pts_data = [c for p in all_pts for c in (p.x, p.y, p.z)]
        batch_pts = batch_for_shader(shader_pt, 'POINTS', {"pos": pts_data})
        batch_pts.draw(shader_pt)

        # Draw stroke lines
        shader_ln = gpu.shader.from_builtin('UNIFORM_COLOR')
        for stroke in self.all_strokes + ([self.current_stroke] if self.current_stroke else []):
            if len(stroke) > 1:
                ln_data = [c for p in stroke for c in (p.x, p.y, p.z)]
                batch_ln = batch_for_shader(shader_ln, 'LINE_STRIP', {"pos": ln_data})
                shader_ln.bind()
                shader_ln.uniform_float("color", color)
                batch_ln.draw(shader_ln)

    def _save_strokes(self):
        """Save all strokes to object custom properties."""
        data = [[[v.x, v.y, v.z] for v in stroke] for stroke in self.all_strokes]
        self.target_obj["retopo_strokes_data"] = data

    def _do_generate(self, context):
        """Generate mesh from strokes."""
        all_pts = []
        for stroke in self.all_strokes:
            all_pts.extend(stroke)
        if len(all_pts) >= 3:
            mesh_data = _build_quad_mesh(all_pts, self.target_obj.retopo_draw.quad_fill_mode)
            if mesh_data:
                self._create_mesh_obj(context, mesh_data)

    def _create_mesh_obj(self, context, mesh_data):
        """Create a new mesh object from generated data."""
        mesh = bpy.data.meshes.new(f"{self.target_obj.name}_retopo")
        mesh.from_pydata(mesh_data['verts'], mesh_data['edges'], mesh_data['faces'])
        mesh.calc_loop_normals()
        mesh.calc_vertex_normals()
        obj = bpy.data.objects.new(f"{self.target_obj.name}_retopo", mesh)
        context.collection.objects.link(obj)
        context.view_layer.objects.active = obj
        obj.select_set(True)
        self.target_obj.select_set(False)

    def _cleanup(self, context):
        if self._draw_handle:
            bpy.types.SpaceView3D.draw_handler_remove(self._draw_handle, 'WINDOW')
            self._draw_handle = None


# ─────────────────────────────────────────────────────────────
# Generate Quads — standalone operator
# ─────────────────────────────────────────────────────────────

class RetopoGenerateQuads(bpy.types.Operator):
    """Generate clean quad-dominant topology from all drawn strokes."""
    bl_idname = "retopo_draw.generate"
    bl_label = "Generate Retopo Mesh"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == 'MESH'

    def execute(self, context):
        obj = context.active_object
        rd = obj.retopo_draw

        if rd.stroke_count == 0:
            self.report({'WARNING'}, "No strokes drawn. Draw some first!")
            return {'FINISHED'}

        strokes = obj.get("retopo_strokes_data", [])
        if not strokes:
            self.report({'WARNING'}, "No stroke data found.")
            return {'FINISHED'}

        all_pts = []
        for stroke in strokes:
            for pt in stroke:
                all_pts.append(Vector(pt))

        if len(all_pts) < 3:
            self.report({'WARNING'}, "Need at least 3 points.")
            return {'FINISHED'}

        mesh_data = _build_quad_mesh(all_pts, rd.quad_fill_mode)
        if mesh_data:
            mesh = bpy.data.meshes.new(f"{obj.name}_retopo")
            mesh.from_pydata(mesh_data['verts'], mesh_data['edges'], mesh_data['faces'])
            mesh.calc_loop_normals()
            mesh.calc_vertex_normals()
            new_obj = bpy.data.objects.new(f"{obj.name}_retopo", mesh)
            context.collection.objects.link(new_obj)
            context.view_layer.objects.active = new_obj
            new_obj.select_set(True)
            obj.select_set(False)
            self.report({'INFO'}, f"Generated: {len(mesh_data['verts'])} verts, {len(mesh_data['faces'])} faces")

        return {'FINISHED'}


# ─────────────────────────────────────────────────────────────
# Mesh generation — Delaunay triangulation + quad merging
# ─────────────────────────────────────────────────────────────

def _build_quad_mesh(points, mode):
    """Build quad-dominant mesh from stroke points."""
    if len(points) < 3:
        return None

    coords = np.array([[p.x, p.y, p.z] for p in points], dtype=np.float64)

    try:
        tri = Delaunay(coords)
    except Exception as e:
        print(f"[RetopoDraw] Delaunay failed: {e}")
        return None

    triangles = [list(simplex) for simplex in tri.simplices]
    edges = set()
    for t in triangles:
        for i in range(3):
            edge = tuple(sorted([t[i], t[(i + 1) % 3]]))
            edges.add(edge)

    if mode == 'TRIANGLE':
        return {'verts': list(points), 'edges': [list(e) for e in edges], 'faces': triangles}

    # Merge triangles into quads
    quads = _merge_triangles_to_quads(triangles)
    return {'verts': list(points), 'edges': [list(e) for e in edges], 'faces': quads}


def _merge_triangles_to_quads(triangles):
    """Merge adjacent triangles into quads where they share exactly 2 vertices."""
    used = set()
    quads = []

    for i, t1 in enumerate(triangles):
        if i in used:
            continue
        merged = False
        for j in range(i + 1, len(triangles)):
            if j in used:
                continue
            t2 = triangles[j]
            shared = set(t1) & set(t2)
            if len(shared) == 2:
                quad = sorted(list(set(t1) | set(t2)))
                if len(quad) == 4:
                    quads.append(quad)
                    used.add(i)
                    used.add(j)
                    merged = True
                    break
        if not merged and i not in used:
            quads.append(t1)

    return quads


# ─────────────────────────────────────────────────────────────
# Clear / Undo strokes
# ─────────────────────────────────────────────────────────────

class RetopoClearStrokes(bpy.types.Operator):
    """Clear all drawn strokes."""
    bl_idname = "retopo_draw.clear"
    bl_label = "Clear All Strokes"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        obj = context.active_object
        rd = obj.retopo_draw
        obj["retopo_strokes_data"] = []
        rd.stroke_count = 0
        self.report({'INFO'}, "All strokes cleared")
        return {'FINISHED'}


class RetopoDeleteLastStroke(bpy.types.Operator):
    """Delete the last drawn stroke."""
    bl_idname = "retopo_draw.undo_stroke"
    bl_label = "Undo Last Stroke"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        obj = context.active_object
        rd = obj.retopo_draw
        strokes = obj.get("retopo_strokes_data", [])
        if strokes:
            strokes.pop()
            obj["retopo_strokes_data"] = strokes
            rd.stroke_count = max(0, rd.stroke_count - 1)
            self.report({'INFO'}, f"Deleted last stroke ({rd.stroke_count} remaining)")
        return {'FINISHED'}


# ─────────────────────────────────────────────────────────────
# Merge retopo mesh into original
# ─────────────────────────────────────────────────────────────

class RetopoMergeMesh(bpy.types.Operator):
    """Replace original mesh topology with the retopo mesh."""
    bl_idname = "retopo_draw.merge"
    bl_label = "Merge Retopo Mesh"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == 'MESH'

    def execute(self, context):
        obj = context.active_object
        name = obj.name
        if '_retopo' in name:
            orig_name = name.replace('_retopo', '')
            orig_obj = bpy.data.objects.get(orig_name)
            if orig_obj:
                orig_obj.data = obj.data.copy()
                orig_obj.data.name = orig_name
                bpy.data.objects.remove(obj, do_unlink=True)
                context.view_layer.objects.active = orig_obj
                self.report({'INFO'}, "Retopo merged into original mesh")
            else:
                self.report({'WARNING'}, "Original mesh not found")
        else:
            self.report({'WARNING'}, "Not a retopo mesh (name should contain '_retopo')")
        return {'FINISHED'}


# ─────────────────────────────────────────────────────────────
# Project retopo vertices to target surface
# ─────────────────────────────────────────────────────────────

class RetopoProjectToSurface(bpy.types.Operator):
    """Project retopo mesh vertices onto the target mesh surface."""
    bl_idname = "retopo_draw.project"
    bl_label = "Project to Surface"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == 'MESH'

    def execute(self, context):
        obj = context.active_object
        target_name = obj.name.replace('_retopo', '')
        target = bpy.data.objects.get(target_name)
        if not target:
            self.report({'ERROR'}, f"Target mesh '{target_name}' not found")
            return {'FINISHED'}

        depsgraph = context.evaluated_depsgraph_get()
        target_mesh = target.evaluated_get(depsgraph).to_mesh()
        target_inv = target.matrix_world.inverted()

        bm = bmesh.new()
        bm.from_mesh(obj.data)

        projected = 0
        for v in bm.verts:
            world_co = obj.matrix_world @ v.co
            local_co = target_inv @ world_co
            local_dir = (target_inv.to_3x3() @ Vector((0, 0, 1))).normalized()

            hit, loc, norm, fi = target_mesh.ray_cast(local_co, local_dir)
            if not hit:
                hit, loc, norm, fi = target_mesh.ray_cast(local_co, -local_dir)

            if hit:
                new_world = target.matrix_world @ loc
                v.co = obj.matrix_world.inverted() @ new_world
                projected += 1

        bm.to_mesh(obj.data)
        bm.free()
        target_mesh.clear_override()
        obj.data.update_tag()

        self.report({'INFO'}, f"Projected {projected} vertices to surface")
        return {'FINISHED'}


# ─────────────────────────────────────────────────────────────
# Settings popup
# ─────────────────────────────────────────────────────────────

class RetopoSettings(bpy.types.Operator):
    """Retopo Draw settings."""
    bl_idname = "retopo_draw.settings"
    bl_label = "Retopo Settings"

    vertex_spacing: bpy.props.FloatProperty(name="Vertex Spacing", default=0.05, min=0.001, max=1.0, step=10)
    snap_enabled: bpy.props.BoolProperty(name="Snap to Surface", default=True)
    auto_generate: bpy.props.BoolProperty(name="Auto Generate on Stroke End", default=False)
    fill_mode: bpy.props.EnumProperty(
        name="Fill Mode",
        items=[
            ('TRIANGLE', "Triangles", "Fast triangulation"),
            ('QUAD', "Quads", "Quad-dominant topology"),
            ('GRID', "Grid", "Grid-like quad layout"),
        ],
        default='QUAD',
    )
    stroke_color: bpy.props.FloatVectorProperty(
        name="Stroke Color", default=(1.0, 0.3, 0.1, 1.0),
        min=0.0, max=1.0, size=4, subtype='COLOR',
    )

    def execute(self, context):
        if context.active_object:
            rd = context.active_object.retopo_draw
            rd.vertex_spacing = self.vertex_spacing
            rd.snap_enabled = self.snap_enabled
            rd.auto_generate = self.auto_generate
            rd.quad_fill_mode = self.fill_mode
            rd.stroke_color = self.stroke_color
        return {'FINISHED'}

    def invoke(self, context, event):
        if context.active_object:
            rd = context.active_object.retopo_draw
            self.vertex_spacing = rd.vertex_spacing
            self.snap_enabled = rd.snap_enabled
            self.auto_generate = rd.auto_generate
            self.fill_mode = rd.quad_fill_mode
            self.stroke_color = rd.stroke_color
        context.window_manager.invoke_props_popup(self, event)
        return {'RUNNING_MODAL'}

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "vertex_spacing")
        layout.prop(self, "snap_enabled")
        layout.prop(self, "auto_generate")
        layout.prop(self, "fill_mode")
        layout.prop(self, "stroke_color")
