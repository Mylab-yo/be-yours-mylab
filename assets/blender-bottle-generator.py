"""
Blender Python Script — MyLab Boston Round Bottle with Screw Cap
================================================================
Generates a cosmetic bottle matching MyLab's actual product:
  - Amber glass Boston round body (rounded shoulders)
  - Black flat screw cap
  - White rectangular label zone (UV-mapped for Zakeke)

Compatible with Blender 5.0+

Usage:
  1. Open Blender (5.0+)
  2. File → New → General
  3. Select & delete the default cube (X)
  4. Switch to Scripting workspace (top tabs)
  5. Click "New" to create a new text block
  6. Paste this entire script
  7. Click "Run Script" (▶)
  8. Export via: Fichier → Exporter → glTF 2.0 (.glb)
"""

import bpy
import math
import os

# ─── CONFIG ──────────────────────────────────────────────────────────
BOTTLE_RADIUS = 0.42       # Body radius (narrower, taller shape)
BOTTLE_BODY_TOP = 1.55     # Where shoulder starts
NECK_RADIUS = 0.15         # Neck opening radius
NECK_BOTTOM = 1.75         # Where neck starts
NECK_TOP = 1.95            # Top of neck (where cap sits)
CAP_RADIUS = 0.17          # Cap radius (slightly wider than neck)
CAP_HEIGHT = 0.22          # Cap height
LABEL_BOTTOM = 0.40        # Label zone start (from bottom)
LABEL_TOP = 1.40           # Label zone end
SEGMENTS = 64              # Smoothness (number of radial segments)

# ─── CLEANUP ─────────────────────────────────────────────────────────
def cleanup_scene():
    """Remove all objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)
    for block in bpy.data.materials:
        if block.users == 0:
            bpy.data.materials.remove(block)

# ─── MATERIALS ───────────────────────────────────────────────────────
def create_amber_glass_material():
    """Dark amber glass — matches MyLab's actual bottle color."""
    mat = bpy.data.materials.new(name="AmberGlass")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    # Darker amber to match the real bottle
    bsdf.inputs['Base Color'].default_value = (0.30, 0.14, 0.04, 1.0)
    bsdf.inputs['Metallic'].default_value = 0.0
    bsdf.inputs['Roughness'].default_value = 0.08  # Very glossy glass
    if 'IOR' in bsdf.inputs:
        bsdf.inputs['IOR'].default_value = 1.52
    if 'Alpha' in bsdf.inputs:
        bsdf.inputs['Alpha'].default_value = 0.88

    output = nodes.new('ShaderNodeOutputMaterial')
    output.location = (300, 0)
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    return mat

def create_label_material():
    """White label — the customizable zone for Zakeke."""
    mat = bpy.data.materials.new(name="Label")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    bsdf.inputs['Base Color'].default_value = (0.97, 0.97, 0.97, 1.0)
    bsdf.inputs['Metallic'].default_value = 0.0
    bsdf.inputs['Roughness'].default_value = 0.45  # Slightly matte paper

    output = nodes.new('ShaderNodeOutputMaterial')
    output.location = (300, 0)
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    return mat

def create_black_plastic_material():
    """Matte black plastic for screw cap."""
    mat = bpy.data.materials.new(name="BlackPlastic")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    bsdf.inputs['Base Color'].default_value = (0.015, 0.015, 0.015, 1.0)
    bsdf.inputs['Metallic'].default_value = 0.0
    bsdf.inputs['Roughness'].default_value = 0.35

    output = nodes.new('ShaderNodeOutputMaterial')
    output.location = (300, 0)
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    return mat

# ─── BOTTLE BODY (revolution profile) ───────────────────────────────
def create_bottle_body():
    """
    Boston round bottle via lathe revolution.
    Profile matches MyLab's actual bottle: rounded shoulders, narrow neck.
    """
    profile = [
        # Bottom
        (0.0,   0.0),           # Center bottom
        (0.20,  0.0),           # Bottom flat area
        (0.35,  0.02),          # Bottom curve start
        (0.40,  0.06),          # Bottom curve
        (BOTTLE_RADIUS, 0.14),  # Lower body transition

        # Straight body (where label goes)
        (BOTTLE_RADIUS, 0.25),  # Below label
        (BOTTLE_RADIUS, LABEL_BOTTOM),   # === LABEL START ===
        (BOTTLE_RADIUS, 0.60),  # Label zone
        (BOTTLE_RADIUS, 0.80),  # Label zone
        (BOTTLE_RADIUS, 1.00),  # Label zone
        (BOTTLE_RADIUS, 1.20),  # Label zone
        (BOTTLE_RADIUS, LABEL_TOP),      # === LABEL END ===
        (BOTTLE_RADIUS, BOTTLE_BODY_TOP), # Above label

        # Rounded shoulder (Boston round signature shape)
        (0.41, 1.58),
        (0.39, 1.61),
        (0.36, 1.64),
        (0.33, 1.66),
        (0.29, 1.68),
        (0.25, 1.70),
        (0.21, 1.72),
        (NECK_RADIUS + 0.02, 1.74),

        # Neck
        (NECK_RADIUS, NECK_BOTTOM),     # Neck start
        (NECK_RADIUS, 1.80),            # Neck mid
        (NECK_RADIUS + 0.015, 1.82),    # Thread ridge 1
        (NECK_RADIUS, 1.84),            # Thread valley
        (NECK_RADIUS + 0.015, 1.86),    # Thread ridge 2
        (NECK_RADIUS, 1.88),            # Thread valley
        (NECK_RADIUS + 0.01, 1.90),     # Thread ridge 3
        (NECK_RADIUS, NECK_TOP),        # Neck top
        (NECK_RADIUS - 0.01, NECK_TOP + 0.01),  # Lip
        (0.0, NECK_TOP + 0.01),         # Center top (close mesh)
    ]

    verts = []
    faces = []
    n_profile = len(profile)

    for i in range(SEGMENTS):
        angle = 2 * math.pi * i / SEGMENTS
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        for r, z in profile:
            verts.append((r * cos_a, r * sin_a, z))

    for i in range(SEGMENTS):
        next_i = (i + 1) % SEGMENTS
        for j in range(n_profile - 1):
            v1 = i * n_profile + j
            v2 = i * n_profile + j + 1
            v3 = next_i * n_profile + j + 1
            v4 = next_i * n_profile + j
            faces.append((v1, v4, v3, v2))

    mesh = bpy.data.meshes.new("BottleBody")
    mesh.from_pydata(verts, [], faces)
    mesh.update()

    obj = bpy.data.objects.new("BottleBody", mesh)
    bpy.context.collection.objects.link(obj)

    return obj, profile

# ─── MATERIAL ASSIGNMENT & UV ────────────────────────────────────────
def assign_bottle_materials(obj, profile):
    """Assign amber glass + label materials, UV map the label zone."""
    amber_mat = create_amber_glass_material()
    label_mat = create_label_material()

    obj.data.materials.append(amber_mat)   # Index 0
    obj.data.materials.append(label_mat)   # Index 1

    n_profile = len(profile)

    # Find label zone indices in profile
    label_start_idx = None
    label_end_idx = None
    for idx, (r, z) in enumerate(profile):
        if abs(z - LABEL_BOTTOM) < 0.001 and label_start_idx is None:
            label_start_idx = idx
        if abs(z - LABEL_TOP) < 0.001:
            label_end_idx = idx

    if label_start_idx is None or label_end_idx is None:
        print("Warning: Could not find label zone in profile")
        return

    # Assign materials per face
    for i in range(SEGMENTS):
        for j in range(n_profile - 1):
            face_idx = i * (n_profile - 1) + j
            if face_idx < len(obj.data.polygons):
                if label_start_idx <= j < label_end_idx:
                    obj.data.polygons[face_idx].material_index = 1  # Label
                else:
                    obj.data.polygons[face_idx].material_index = 0  # Glass

    # UV unwrap
    uv_unwrap_label(obj, profile, label_start_idx, label_end_idx, n_profile)

def uv_unwrap_label(obj, profile, label_start_idx, label_end_idx, n_profile):
    """Clean cylindrical UV projection for the label zone."""
    if not obj.data.uv_layers:
        obj.data.uv_layers.new(name="UVMap")
    uv_layer = obj.data.uv_layers.active

    label_rows = label_end_idx - label_start_idx

    for i in range(SEGMENTS):
        for j in range(n_profile - 1):
            face_idx = i * (n_profile - 1) + j
            if face_idx < len(obj.data.polygons):
                poly = obj.data.polygons[face_idx]

                if label_start_idx <= j < label_end_idx:
                    u_left = i / SEGMENTS
                    u_right = (i + 1) / SEGMENTS
                    v_bottom = (j - label_start_idx) / label_rows
                    v_top = (j - label_start_idx + 1) / label_rows

                    loop_indices = list(poly.loop_indices)
                    if len(loop_indices) == 4:
                        uv_layer.data[loop_indices[0]].uv = (u_left, v_bottom)
                        uv_layer.data[loop_indices[1]].uv = (u_left, v_top)
                        uv_layer.data[loop_indices[2]].uv = (u_right, v_top)
                        uv_layer.data[loop_indices[3]].uv = (u_right, v_bottom)
                else:
                    for loop_idx in poly.loop_indices:
                        vert = obj.data.vertices[obj.data.loops[loop_idx].vertex_index]
                        uv_layer.data[loop_idx].uv = (
                            vert.co.x * 0.5 + 0.5,
                            vert.co.z / 2.2
                        )

# ─── SCREW CAP ───────────────────────────────────────────────────────
def create_screw_cap():
    """
    Flat screw cap — matches MyLab's actual black cap.
    Simple cylinder with slightly rounded top edge.
    """
    black_mat = create_black_plastic_material()
    objects = []

    cap_bottom = NECK_TOP - 0.04  # Overlaps neck slightly
    cap_top = cap_bottom + CAP_HEIGHT

    # Cap body (main cylinder)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=CAP_RADIUS,
        depth=CAP_HEIGHT,
        vertices=SEGMENTS,
        location=(0, 0, cap_bottom + CAP_HEIGHT / 2)
    )
    cap_body = bpy.context.active_object
    cap_body.name = "CapBody"
    cap_body.data.materials.append(black_mat)
    objects.append(cap_body)

    # Cap top disc (slightly recessed flat top)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=CAP_RADIUS - 0.01,
        depth=0.01,
        vertices=SEGMENTS,
        location=(0, 0, cap_top - 0.005)
    )
    cap_top_disc = bpy.context.active_object
    cap_top_disc.name = "CapTop"
    cap_top_disc.data.materials.append(black_mat)
    objects.append(cap_top_disc)

    # Grip ridges around the cap (small bumps for texture)
    ridge_count = 48
    ridge_radius = 0.008
    for i in range(ridge_count):
        angle = 2 * math.pi * i / ridge_count
        x = (CAP_RADIUS - 0.003) * math.cos(angle)
        y = (CAP_RADIUS - 0.003) * math.sin(angle)
        bpy.ops.mesh.primitive_cylinder_add(
            radius=ridge_radius,
            depth=CAP_HEIGHT * 0.7,
            vertices=6,
            location=(x, y, cap_bottom + CAP_HEIGHT / 2)
        )
        ridge = bpy.context.active_object
        ridge.name = f"CapRidge_{i}"
        ridge.data.materials.append(black_mat)
        objects.append(ridge)

    return objects

# ─── BOTTOM DISC ─────────────────────────────────────────────────────
def create_bottom():
    """Flat bottom disc."""
    bpy.ops.mesh.primitive_cylinder_add(
        radius=BOTTLE_RADIUS - 0.02,
        depth=0.015,
        vertices=SEGMENTS,
        location=(0, 0, 0.0075)
    )
    bottom = bpy.context.active_object
    bottom.name = "BottleBottom"
    amber_mat = None
    for mat in bpy.data.materials:
        if mat.name == "AmberGlass":
            amber_mat = mat
            break
    if amber_mat:
        bottom.data.materials.append(amber_mat)
    return bottom

# ─── SMOOTH & FINALIZE ───────────────────────────────────────────────
def finalize():
    """Apply smooth shading and join all objects."""
    bpy.ops.object.select_all(action='DESELECT')
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH':
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj

    # Smooth shading
    for obj in bpy.context.selected_objects:
        if obj.type == 'MESH':
            for poly in obj.data.polygons:
                poly.use_smooth = True
            if hasattr(obj.data, 'use_auto_smooth'):
                obj.data.use_auto_smooth = True
                obj.data.auto_smooth_angle = math.radians(60)

    # Join all
    bpy.ops.object.join()
    final_obj = bpy.context.active_object
    final_obj.name = "MyLab_Bottle"

    # Center origin
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')

    print("\n--- MyLab Bottle Ready ---")
    print("Materials: AmberGlass, Label (customizable), BlackPlastic")
    print("\nTo export:")
    print("  Fichier → Exporter → glTF 2.0 (.glb)")
    print("  Format: glTF Binary (.glb)")
    print("  Save to Desktop as: mylab-bottle.glb")

# ─── MAIN ────────────────────────────────────────────────────────────
def main():
    print("\nMyLab Bottle Generator v2 — Starting...\n")

    cleanup_scene()

    print("  Creating bottle body...")
    bottle_obj, profile = create_bottle_body()
    assign_bottle_materials(bottle_obj, profile)

    print("  Creating bottom...")
    create_bottom()

    print("  Creating screw cap...")
    create_screw_cap()

    print("  Finalizing...")
    finalize()

    print("\nDone!")

# Run
main()
