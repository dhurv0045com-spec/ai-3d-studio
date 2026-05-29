import bpy
import bmesh
import math
OUTPUT_PATH = r"/data/data/com.termux/files/home/projects/ai-3d-studio/_temp_output.glb"

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()


mat = bpy.data.materials.new(name="MainMat")
mat.use_nodes = True
bsdf = mat.node_tree.nodes.get("Principled BSDF")
if bsdf:
    bsdf.inputs["Base Color"].default_value = (0.0000, 0.8314, 1.0000, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.5
    bsdf.inputs["Metallic"].default_value = 0.0

def apply_mat(obj):
    if obj.data and hasattr(obj.data, "materials"):
        obj.data.materials.clear()
        obj.data.materials.append(mat)


# Body
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.7, location=(0,0,0.5))
body = bpy.context.active_object
body.scale = (1.0, 0.65, 0.6); apply_mat(body)
# Head
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.4, location=(0.9,0,1.1))
head = bpy.context.active_object
head.scale = (1.0, 0.75, 0.8); apply_mat(head)
# Snout
bpy.ops.mesh.primitive_cone_add(radius1=0.22, radius2=0.1, depth=0.45, location=(1.33,0,1.0))
snout = bpy.context.active_object
snout.rotation_euler=(0, math.radians(90), 0); apply_mat(snout)
# Neck
bpy.ops.mesh.primitive_cylinder_add(radius=0.22, depth=0.55, location=(0.45,0,0.82))
neck = bpy.context.active_object
neck.rotation_euler=(0, math.radians(60), 0); apply_mat(neck)
# Tail
bpy.ops.mesh.primitive_cone_add(radius1=0.3, radius2=0.04, depth=1.8, location=(-1.2,0,0.2))
tail = bpy.context.active_object
tail.rotation_euler=(0, math.radians(-30), 0); apply_mat(tail)
# Front left leg
bpy.ops.mesh.primitive_cylinder_add(radius=0.1, depth=0.65, location=(0.45,-0.55,0.15))
fl = bpy.context.active_object
fl.rotation_euler=(math.radians(10),0,0); apply_mat(fl)
# Front right leg
bpy.ops.mesh.primitive_cylinder_add(radius=0.1, depth=0.65, location=(0.45,0.55,0.15))
fr = bpy.context.active_object
fr.rotation_euler=(math.radians(-10),0,0); apply_mat(fr)
# Back left leg
bpy.ops.mesh.primitive_cylinder_add(radius=0.12, depth=0.7, location=(-0.45,-0.55,0.1))
bl = bpy.context.active_object
bl.rotation_euler=(math.radians(10),0,0); apply_mat(bl)
# Back right leg
bpy.ops.mesh.primitive_cylinder_add(radius=0.12, depth=0.7, location=(-0.45,0.55,0.1))
brleg = bpy.context.active_object
brleg.rotation_euler=(math.radians(-10),0,0); apply_mat(brleg)
# Left wing
bpy.ops.mesh.primitive_cone_add(radius1=0.05, radius2=0.0, depth=1.4, location=(0.1,-1.0,1.0))
lw = bpy.context.active_object
lw.rotation_euler=(math.radians(-30), math.radians(15), math.radians(-10)); apply_mat(lw)
# Right wing
bpy.ops.mesh.primitive_cone_add(radius1=0.05, radius2=0.0, depth=1.4, location=(0.1,1.0,1.0))
rw = bpy.context.active_object
rw.rotation_euler=(math.radians(30), math.radians(-15), math.radians(10)); apply_mat(rw)
# Wing membrane L
bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0.1,-1.3,0.9))
wml = bpy.context.active_object
wml.scale=(1.1, 0.6, 0.8); apply_mat(wml)
# Wing membrane R
bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0.1,1.3,0.9))
wmr = bpy.context.active_object
wmr.scale=(1.1, 0.6, 0.8); apply_mat(wmr)
# Horn L
bpy.ops.mesh.primitive_cone_add(radius1=0.04, radius2=0.0, depth=0.35, location=(0.82,-0.15,1.5))
hl = bpy.context.active_object
hl.rotation_euler=(0,math.radians(-20),0); apply_mat(hl)
# Horn R
bpy.ops.mesh.primitive_cone_add(radius1=0.04, radius2=0.0, depth=0.35, location=(0.82,0.15,1.5))
hr = bpy.context.active_object
hr.rotation_euler=(0,math.radians(20),0); apply_mat(hr)
# Eye L
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.07, location=(1.15,-0.2,1.18))
el = bpy.context.active_object; apply_mat(el)
# Eye R
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.07, location=(1.15,0.2,1.18))
er = bpy.context.active_object; apply_mat(er)
# Dorsal spine row
for i in range(5):
    bpy.ops.mesh.primitive_cone_add(radius1=0.04, radius2=0.0, depth=0.25,
        location=(0.6-i*0.25, 0, 0.9+i*0.05))
    sp = bpy.context.active_object; apply_mat(sp)
# Foot claws front L
for c in range(3):
    bpy.ops.mesh.primitive_cone_add(radius1=0.03, radius2=0.0, depth=0.16,
        location=(0.38+c*0.06, -0.58, -0.18))
    cl = bpy.context.active_object; apply_mat(cl)

bpy.ops.export_scene.gltf(filepath=OUTPUT_PATH, export_format='GLB')
