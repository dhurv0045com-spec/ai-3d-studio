import bpy
import bmesh
import math
OUTPUT_PATH = r"C:\Users\user\Desktop\ai-3d-project\_temp_output.glb"


bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()


mat = bpy.data.materials.new(name="MainMat")
mat.use_nodes = True
bsdf = mat.node_tree.nodes.get("Principled BSDF")
if bsdf:
    bsdf.inputs["Base Color"].default_value = (0.2667, 0.5333, 1.0000, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.4
    bsdf.inputs["Metallic"].default_value = 0.1

def apply_mat(obj):
    if obj.data and hasattr(obj.data, "materials"):
        obj.data.materials.clear()
        obj.data.materials.append(mat)


# Core sphere
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.8, location=(0,0,0))
cs = bpy.context.active_object; apply_mat(cs)
# Equatorial ring
bpy.ops.mesh.primitive_torus_add(major_radius=0.88, minor_radius=0.06, location=(0,0,0))
eq = bpy.context.active_object; apply_mat(eq)
# Polar axis
bpy.ops.mesh.primitive_cylinder_add(radius=0.04, depth=2.0, location=(0,0,0))
pa = bpy.context.active_object; apply_mat(pa)
# Node balls (6)
for ang in [0,60,120,180,240,300]:
    rad = math.radians(ang)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.1, location=(math.cos(rad)*0.88,math.sin(rad)*0.88,0))
    nb = bpy.context.active_object; apply_mat(nb)
# Top cap
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.15, location=(0,0,0.85))
tc = bpy.context.active_object; apply_mat(tc)
# Bottom cap
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.15, location=(0,0,-0.85))
bc = bpy.context.active_object; apply_mat(bc)
# Latitude rings
for lat in [30,60,-30,-60]:
    z = 0.8*math.sin(math.radians(lat))
    cr = 0.8*math.cos(math.radians(lat))
    bpy.ops.mesh.primitive_torus_add(major_radius=cr*1.02, minor_radius=0.035, location=(0,0,z))
    lr = bpy.context.active_object; apply_mat(lr)
# Decorative spikes (4)
for ang in [0,90,180,270]:
    rad = math.radians(ang)
    bpy.ops.mesh.primitive_cone_add(radius1=0.06, radius2=0.0, depth=0.35,
        location=(math.cos(rad)*0.88,math.sin(rad)*0.88,0))
    sp = bpy.context.active_object
    sp.rotation_euler=(0, math.radians(-90+ang), 0)
    apply_mat(sp)

bpy.ops.export_scene.gltf(filepath=OUTPUT_PATH, export_format='GLB')
