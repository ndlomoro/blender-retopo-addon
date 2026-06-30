# Retopo Draw — Blender Re-topology Addon

**Draw strokes on a mesh and automatically generate clean quad-dominant topology.**

---

## Features

- **Draw strokes** directly on mesh surface — vertices snap to geometry via raycasting
- **Auto-generate quads** from your drawn strokes using Delaunay triangulation + triangle-to-quad merging
- **Real-time visualization** of strokes in the 3D viewport
- **Project to surface** — snap retopo mesh vertices onto the original mesh
- **Merge** retopo result back into the original mesh
- **Configurable** vertex spacing, fill mode, stroke color

---

## Installation

1. **Download** the `retopo_draw.zip` file (or zip the `retopo_draw/` folder)
2. In Blender: `Edit > Preferences > Add-ons`
3. Click **Install...** → select the `.zip` file
4. Enable the addon by checking the box next to **Mesh: Retopo Draw**

---

## Usage

### Drawing Strokes

1. **Select** your high-poly mesh object
2. Open the sidebar (`N`) → **Retopo** tab
3. Click **Draw Stroke** (or press `Shift+Left Click` on the mesh)
4. **Drag** your mouse to draw — vertices snap to the mesh surface
5. **Release** to finish the stroke
6. Repeat to draw more strokes — follow edge flows, silhouettes, and feature lines

### Generating Mesh

1. After drawing strokes, click **Generate Retopo Mesh** (or press `G`)
2. A new mesh object (`*_retopo`) is created with clean topology
3. Choose fill mode:
   - **Quads** — quad-dominant (triangles merged where possible)
   - **Triangles** — pure triangulation
   - **Grid** — grid-like layout

### Post-Processing

- **Project to Surface** (`P`) — projects retopo vertices onto the original mesh for perfect surface alignment
- **Merge** (`M`) — replaces the original mesh with the retopo mesh
- **Undo Last Stroke** (`Ctrl+Z`) — removes the last drawn stroke
- **Clear All** (`X`) — removes all strokes

### Settings

Click the **Settings** button (or `retopo_draw.settings`) to configure:
- **Vertex Spacing** — minimum distance between stroke vertices
- **Snap to Surface** — toggle raycasting snap
- **Auto Generate** — automatically generate mesh when a stroke ends
- **Fill Mode** — topology generation strategy
- **Stroke Color** — visualization color

---

## Shortcuts

| Key | Action |
|-----|--------|
| `Shift+Left Click` | Draw stroke |
| `G` | Generate retopo mesh |
| `Ctrl+Z` | Undo last stroke |
| `X` | Clear all strokes |
| `P` | Project to surface |
| `M` | Merge retopo into original |

---

## Tips

- Draw strokes along **edge flows** and **silhouettes** for best results
- More strokes = denser topology. Start with major feature lines, then add detail
- Use **Project to Surface** after generating to ensure the retopo mesh hugs the original geometry
- Adjust **Vertex Spacing** based on your mesh scale — smaller values = denser strokes
- The retopo mesh is a separate object — you can edit it further before merging

---

## Requirements

- Blender 4.0+
- Python 3.12+ (bundled with Blender)
- `scipy` (for Delaunay triangulation) — install via Blender's built-in Python or system Python

---

## License

MIT License — free to use, modify, and distribute.
