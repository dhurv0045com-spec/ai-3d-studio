import bpy
import os
import math

# Clear the scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Helper to deselect all
def deselect_all():
    bpy.ops.object.select_all(action='DESELECT')

# --- Rocket Body (main cylinder) ---
bpy.ops.mesh.primitive_cylinder_add(
    radius=0.4,
    depth=2.0,
    location=(0, 0, 1.0)
)
body = bpy.context.active_object
body.name = "RocketBody"

# --- Nose Cone ---
bpy.ops.mesh.primitive_cone_add(
    radius1=0.4,
    radius2=0.0,
    depth=1.0,
    location=(0, 0, 2.5)
)
nose = bpy.context.active_object
nose.name = "NoseCone"

# --- Three Engine Cylinders at the bottom ---
engine_radius = 0.1
engine_depth = 0.4
engine_offset = 0.25
engine_z = 0.2  # slightly above ground, sticking out below body bottom (body bottom is at z=0)

angles = [0, 120, 240]
engines = []
for i, angle_deg in enumerate(angles):
    angle_rad = math.radians(angle_deg)
    x = engine_offset * math.cos(angle_rad)
    y = engine_offset * math.sin(angle_rad)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=engine_radius,
        depth=engine_depth,
        location=(x, y, engine_z - 0.2)
    )
    eng = bpy.context.active_object
    eng.name = f"Engine_{i+1}"
    engines.append(eng)

# --- Join all objects into one ---
deselect_all()
all_objects = [body, nose] + engines
for obj in all_objects:
    obj.select_set(True)
bpy.context.view_layer.objects.active = body
bpy.ops.object.join()

rocket = bpy.context.active_object
rocket.name = "Rocket"

# Move rocket so it sits on the ground (z=0 at bottom)
# Body bottom is at z=0 (center z=1.0, depth=2.0), so it's already grounded.

# --- Export as GLB ---
script_dir = os.path.dirname(os.path.abspath(__file__))
export_path = os.path.join(script_dir, "rocket.glb")

bpy.ops.export_scene.gltf(
    filepath=export_path,
    export_format='GLB',
    use_selection=False
)

print(f"Rocket exported to: {export_path}")