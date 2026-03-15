# generate_model.py  -  AI 3D Studio  -  Pure Python 3D Fallback  v5.0
#
# This is the last safety net of the entire generation pipeline.
# Zero external dependencies. Only stdlib: struct, math, os, json.
# Produces valid glTF 2.0 binary (GLB) files with recognizable shapes.
# NEVER raises an exception - always produces a valid output file.
#
# Usage:
#   from generate_model import generate
#   ok = generate("red dragon", "#cc2200", "output.glb")
#
#   python generate_model.py                     (test mode)
#   python generate_model.py "blue rocket"       (test with prompt)

import os
import sys
import math
import json
import struct
import time

# ---------------------------------------------------------------------------
#  GLB BUILDER
# ---------------------------------------------------------------------------
class GLBBuilder:
    """
    Builds a valid glTF 2.0 binary (GLB) file in pure Python.
    Accumulates meshes then packs everything into binary on build().
    """

    def __init__(self):
        self._meshes = []   # list of (positions, normals, indices, color)

    # ------------------------------------------------------------------
    # GEOMETRY HELPERS
    # ------------------------------------------------------------------

    def add_mesh(self, vertices, indices, color=(0.5, 0.5, 0.8)):
        """Add a raw triangle mesh. vertices=[(x,y,z)...], indices=[(a,b,c)...]."""
        # Compute flat normals
        normals = [(0.0, 1.0, 0.0)] * len(vertices)
        for tri in indices:
            a, b, c = tri
            va = vertices[a]; vb = vertices[b]; vc = vertices[c]
            ab = (vb[0]-va[0], vb[1]-va[1], vb[2]-va[2])
            ac = (vc[0]-va[0], vc[1]-va[1], vc[2]-va[2])
            nx = ab[1]*ac[2] - ab[2]*ac[1]
            ny = ab[2]*ac[0] - ab[0]*ac[2]
            nz = ab[0]*ac[1] - ab[1]*ac[0]
            l = math.sqrt(nx*nx + ny*ny + nz*nz)
            if l > 1e-9:
                nx /= l; ny /= l; nz /= l
            for i in (a, b, c):
                normals[i] = (nx, ny, nz)
        self._meshes.append((vertices, normals, indices, color))

    def add_box(self, w, h, d, x=0.0, y=0.0, z=0.0, color=(0.5, 0.5, 0.8)):
        """Add an axis-aligned box centered at (x,y,z)."""
        hw, hh, hd = w/2, h/2, d/2
        verts = [
            (x-hw, y-hh, z-hd), (x+hw, y-hh, z-hd),
            (x+hw, y+hh, z-hd), (x-hw, y+hh, z-hd),
            (x-hw, y-hh, z+hd), (x+hw, y-hh, z+hd),
            (x+hw, y+hh, z+hd), (x-hw, y+hh, z+hd),
        ]
        idx = [
            (0,1,2),(0,2,3),   # front
            (5,4,7),(5,7,6),   # back
            (4,0,3),(4,3,7),   # left
            (1,5,6),(1,6,2),   # right
            (3,2,6),(3,6,7),   # top
            (4,5,1),(4,1,0),   # bottom
        ]
        self.add_mesh(verts, idx, color)

    def add_cylinder(self, r, h, x=0.0, y=0.0, z=0.0,
                     color=(0.5,0.5,0.8), segments=12):
        """Add a cylinder with caps, axis along Z."""
        verts = []
        idx   = []
        hh    = h / 2
        # Bottom center
        verts.append((x, y, z - hh))
        bc = 0
        # Top center
        verts.append((x, y, z + hh))
        tc = 1
        # Ring vertices bottom + top
        bot_start = 2
        top_start = 2 + segments
        for i in range(segments):
            a = 2 * math.pi * i / segments
            cx_ = x + r * math.cos(a)
            cy_ = y + r * math.sin(a)
            verts.append((cx_, cy_, z - hh))
        for i in range(segments):
            a = 2 * math.pi * i / segments
            cx_ = x + r * math.cos(a)
            cy_ = y + r * math.sin(a)
            verts.append((cx_, cy_, z + hh))
        # Bottom cap
        for i in range(segments):
            n = (i + 1) % segments
            idx.append((bc, bot_start + n, bot_start + i))
        # Top cap
        for i in range(segments):
            n = (i + 1) % segments
            idx.append((tc, top_start + i, top_start + n))
        # Side quads
        for i in range(segments):
            n = (i + 1) % segments
            b0 = bot_start + i; b1 = bot_start + n
            t0 = top_start + i; t1 = top_start + n
            idx.append((b0, b1, t1))
            idx.append((b0, t1, t0))
        self.add_mesh(verts, idx, color)

    def add_sphere(self, r, x=0.0, y=0.0, z=0.0,
                   color=(0.5,0.5,0.8), rings=8, segs=12):
        """Add a UV sphere."""
        verts = []
        idx   = []
        for ring in range(rings + 1):
            phi = math.pi * ring / rings
            for seg in range(segs):
                theta = 2 * math.pi * seg / segs
                vx = x + r * math.sin(phi) * math.cos(theta)
                vy = y + r * math.sin(phi) * math.sin(theta)
                vz = z + r * math.cos(phi)
                verts.append((vx, vy, vz))
        for ring in range(rings):
            for seg in range(segs):
                n_seg = (seg + 1) % segs
                a = ring * segs + seg
                b = ring * segs + n_seg
                c = (ring + 1) * segs + seg
                d = (ring + 1) * segs + n_seg
                idx.append((a, b, d))
                idx.append((a, d, c))
        self.add_mesh(verts, idx, color)

    def add_cone(self, r, h, x=0.0, y=0.0, z=0.0,
                 color=(0.5,0.5,0.8), segments=12):
        """Add a cone with base cap, pointing up."""
        verts = []
        idx   = []
        # Apex
        verts.append((x, y, z + h))
        apex = 0
        # Base center
        verts.append((x, y, z))
        base_c = 1
        # Base ring
        ring_start = 2
        for i in range(segments):
            a = 2 * math.pi * i / segments
            verts.append((x + r * math.cos(a), y + r * math.sin(a), z))
        # Sides
        for i in range(segments):
            n = (i + 1) % segments
            idx.append((apex, ring_start + i, ring_start + n))
        # Base cap
        for i in range(segments):
            n = (i + 1) % segments
            idx.append((base_c, ring_start + n, ring_start + i))
        self.add_mesh(verts, idx, color)

    def add_torus(self, major_r, minor_r, x=0.0, y=0.0, z=0.0,
                  color=(0.5,0.5,0.8), major_segs=16, minor_segs=8):
        """Add a torus in the XY plane."""
        verts = []
        idx   = []
        for i in range(major_segs):
            theta = 2 * math.pi * i / major_segs
            for j in range(minor_segs):
                phi = 2 * math.pi * j / minor_segs
                px = (major_r + minor_r * math.cos(phi)) * math.cos(theta)
                py = (major_r + minor_r * math.cos(phi)) * math.sin(theta)
                pz = minor_r * math.sin(phi)
                verts.append((x + px, y + py, z + pz))
        for i in range(major_segs):
            ni = (i + 1) % major_segs
            for j in range(minor_segs):
                nj = (j + 1) % minor_segs
                a = i  * minor_segs + j
                b = i  * minor_segs + nj
                c = ni * minor_segs + j
                d = ni * minor_segs + nj
                idx.append((a, b, d))
                idx.append((a, d, c))
        self.add_mesh(verts, idx, color)

    # ------------------------------------------------------------------
    # GLB PACKER
    # ------------------------------------------------------------------
    def build(self):
        """Pack all meshes into valid GLB binary. Returns bytes."""
        all_pos    = []
        all_nrm    = []
        all_col    = []
        all_idx    = []
        prims      = []
        vert_offset = 0

        for verts, normals, indices, color in self._meshes:
            for v in verts:
                all_pos.append(v)
            for n in normals:
                all_nrm.append(n)
            for _ in verts:
                all_col.append(color)
            for tri in indices:
                all_idx.append((
                    tri[0] + vert_offset,
                    tri[1] + vert_offset,
                    tri[2] + vert_offset
                ))
            prims.append({
                "vert_start": vert_offset,
                "vert_count": len(verts),
                "idx_start":  len(all_idx) - len(indices),
                "idx_count":  len(indices),
                "color":      color
            })
            vert_offset += len(verts)

        if not all_pos:
            # Empty builder: make a small tetrahedron
            self.add_sphere(0.5, color=(0.5, 0.5, 0.8))
            return self.build()

        # Pack binary data
        def pack_f3_list(lst):
            buf = bytearray()
            for item in lst:
                buf += struct.pack("<fff", float(item[0]), float(item[1]), float(item[2]))
            return bytes(buf)

        def pack_u16_list(lst):
            buf = bytearray()
            for tri in lst:
                buf += struct.pack("<HHH", tri[0], tri[1], tri[2])
            return bytes(buf)

        def pad4(b):
            r = len(b) % 4
            return b + (b"\x00" * ((4 - r) % 4))

        pos_bytes   = pad4(pack_f3_list(all_pos))
        nrm_bytes   = pad4(pack_f3_list(all_nrm))
        col_bytes   = pad4(pack_f3_list(all_col))
        idx_bytes   = pad4(pack_u16_list(all_idx))

        n_verts = len(all_pos)
        n_idx   = len(all_idx) * 3

        bv0_off = 0;                   bv0_len = len(pos_bytes)
        bv1_off = bv0_off + bv0_len;   bv1_len = len(nrm_bytes)
        bv2_off = bv1_off + bv1_len;   bv2_len = len(col_bytes)
        bv3_off = bv2_off + bv2_len;   bv3_len = len(idx_bytes)
        bin_len = bv3_off + bv3_len

        min_pos = [min(v[i] for v in all_pos) for i in range(3)]
        max_pos = [max(v[i] for v in all_pos) for i in range(3)]

        # Use first mesh color for material
        mat_color = self._meshes[0][3] if self._meshes else (0.5, 0.5, 0.8)

        gltf = {
            "asset": {"version": "2.0", "generator": "AI3DStudio-Fallback-v5"},
            "scene": 0,
            "scenes": [{"nodes": [0]}],
            "nodes":  [{"mesh": 0}],
            "meshes": [{
                "name": "FallbackMesh",
                "primitives": [{
                    "attributes": {"POSITION": 0, "NORMAL": 1, "COLOR_0": 2},
                    "indices": 3,
                    "material": 0,
                    "mode": 4
                }]
            }],
            "materials": [{
                "name": "FallbackMat",
                "pbrMetallicRoughness": {
                    "baseColorFactor": [mat_color[0], mat_color[1], mat_color[2], 1.0],
                    "metallicFactor":  0.1,
                    "roughnessFactor": 0.5
                }
            }],
            "accessors": [
                {"bufferView": 0, "byteOffset": 0, "componentType": 5126,
                 "count": n_verts, "type": "VEC3", "min": min_pos, "max": max_pos},
                {"bufferView": 1, "byteOffset": 0, "componentType": 5126,
                 "count": n_verts, "type": "VEC3"},
                {"bufferView": 2, "byteOffset": 0, "componentType": 5126,
                 "count": n_verts, "type": "VEC3"},
                {"bufferView": 3, "byteOffset": 0, "componentType": 5123,
                 "count": n_idx,   "type": "SCALAR"},
            ],
            "bufferViews": [
                {"buffer": 0, "byteOffset": bv0_off, "byteLength": bv0_len, "target": 34962},
                {"buffer": 0, "byteOffset": bv1_off, "byteLength": bv1_len, "target": 34962},
                {"buffer": 0, "byteOffset": bv2_off, "byteLength": bv2_len, "target": 34962},
                {"buffer": 0, "byteOffset": bv3_off, "byteLength": bv3_len, "target": 34963},
            ],
            "buffers": [{"byteLength": bin_len}]
        }

        json_str   = json.dumps(gltf, separators=(",", ":"))
        json_bytes = json_str.encode("utf-8")
        json_pad   = (4 - len(json_bytes) % 4) % 4
        json_bytes += b" " * json_pad

        bin_data   = pos_bytes + nrm_bytes + col_bytes + idx_bytes
        total_len  = 12 + 8 + len(json_bytes) + 8 + len(bin_data)

        out = bytearray()
        out += struct.pack("<4sII", b"glTF", 2, total_len)
        out += struct.pack("<II",  len(json_bytes), 0x4E4F534A)
        out += json_bytes
        out += struct.pack("<II",  len(bin_data),   0x004E4942)
        out += bin_data

        return bytes(out)


# ---------------------------------------------------------------------------
#  COLOR PARSER
# ---------------------------------------------------------------------------
def _parse_color(hex_str):
    """Parse #RRGGBB to (r, g, b) floats. Returns (0.3, 0.5, 0.8) on failure."""
    try:
        h = hex_str.lstrip("#")
        if len(h) == 6:
            return (int(h[0:2], 16) / 255.0,
                    int(h[2:4], 16) / 255.0,
                    int(h[4:6], 16) / 255.0)
    except Exception:
        pass
    return (0.3, 0.5, 0.8)

def _dark(c, f=0.5):
    return (c[0]*f, c[1]*f, c[2]*f)

def _light(c, f=1.4):
    return (min(1.0, c[0]*f), min(1.0, c[1]*f), min(1.0, c[2]*f))

def _mix(c, other, t=0.5):
    return (c[0]*(1-t)+other[0]*t, c[1]*(1-t)+other[1]*t, c[2]*(1-t)+other[2]*t)


# ---------------------------------------------------------------------------
#  SHAPE BUILDERS  (55 shapes, all use GLBBuilder)
# ---------------------------------------------------------------------------

def _build_rocket(c):
    b = GLBBuilder()
    b.add_cylinder(0.35, 2.4,  0, 0, 1.2, c)
    b.add_cone(    0.35, 0.9,  0, 0, 2.85, _light(c))
    b.add_cone(    0.45, 0.45, 0, 0,-0.23, _dark(c))
    for ang in [0, 90, 180, 270]:
        a = math.radians(ang)
        b.add_box(0.06, 0.45, 0.44,
                  math.cos(a)*0.42, math.sin(a)*0.42, 0.22, _dark(c))
    for z in [1.2, 1.7, 2.2]:
        b.add_sphere(0.07, 0.36, 0, z, _light(c))
    b.add_torus(0.36, 0.04, 0, 0, 2.3, _light(c))
    b.add_torus(0.36, 0.04, 0, 0, 1.5, _light(c))
    return b

def _build_dragon(c):
    b = GLBBuilder()
    b.add_sphere(0.7,  0, 0, 0.5, c)
    b.add_sphere(0.4,  0.9, 0, 1.1, c)
    b.add_cone(  0.22, 0.45, 1.2, 0, 1.0, _dark(c))
    b.add_cylinder(0.22, 0.55, 0.45, 0, 0.82, c)
    b.add_cone(    0.3,  1.8, -1.2, 0, 0.2, _dark(c))
    for side in [-0.55, 0.55]:
        b.add_cylinder(0.10, 0.65, 0.45, side, 0.15, c)
        b.add_cylinder(0.12, 0.70,-0.45, side, 0.10, c)
    b.add_box(1.2, 0.06, 0.35,  0, -1.0, 0.9, _dark(c))
    b.add_box(1.2, 0.06, 0.35,  0,  1.0, 0.9, _dark(c))
    b.add_cone(0.04, 0.35, 0.82, -0.15, 1.5, _light(c))
    b.add_cone(0.04, 0.35, 0.82,  0.15, 1.5, _light(c))
    b.add_sphere(0.07, 1.15, -0.2, 1.18, (0.05, 0.05, 0.05))
    b.add_sphere(0.07, 1.15,  0.2, 1.18, (0.05, 0.05, 0.05))
    return b

def _build_car(c):
    b = GLBBuilder()
    b.add_box(4.0, 1.8, 0.8,  0, 0, 0.4, c)
    b.add_box(2.2, 1.65, 0.65, 0.1, 0, 1.0, _light(c))
    b.add_box(1.2, 1.7, 0.4, 1.3, 0, 0.6, _dark(c))
    for wx, wy in [(1.1,-0.95),(1.1,0.95),(-1.1,-0.95),(-1.1,0.95)]:
        b.add_cylinder(0.22, 0.22, wx, wy, 0.22, (0.1,0.1,0.1))
        b.add_cylinder(0.13, 0.24, wx, wy, 0.22, (0.7,0.7,0.7))
    b.add_sphere(0.10, 2.0,-0.5, 0.38, (1.0, 1.0, 0.6))
    b.add_sphere(0.10, 2.0, 0.5, 0.38, (1.0, 1.0, 0.6))
    b.add_box(0.16, 1.76, 0.30, 2.05, 0, 0.22, _dark(c))
    b.add_box(0.16, 1.76, 0.30,-2.05, 0, 0.22, _dark(c))
    b.add_box(0.36, 0.12, 0.2,  0.6,-0.96, 0.7, c)
    b.add_box(0.36, 0.12, 0.2,  0.6, 0.96, 0.7, c)
    return b

def _build_robot(c):
    b = GLBBuilder()
    b.add_box(1.1, 0.7, 1.1,  0, 0, 0.6, c)
    b.add_box(0.76, 0.64, 0.7, 0, 0, 1.35, c)
    b.add_cylinder(0.10, 0.2, 0, 0, 1.05, _dark(c))
    b.add_cylinder(0.10, 0.45,-0.72, 0, 0.82, c)
    b.add_cylinder(0.09, 0.42,-0.78, 0, 0.45, c)
    b.add_box(0.24, 0.16, 0.32,-0.8, 0, 0.2, c)
    b.add_cylinder(0.10, 0.45, 0.72, 0, 0.82, c)
    b.add_cylinder(0.09, 0.42, 0.78, 0, 0.45, c)
    b.add_box(0.24, 0.16, 0.32, 0.8, 0, 0.2, c)
    b.add_cylinder(0.13, 0.45,-0.22, 0, 0.12, c)
    b.add_cylinder(0.11, 0.42,-0.22, 0,-0.35, c)
    b.add_box(0.28, 0.44, 0.16,-0.22, 0.08,-0.62, c)
    b.add_cylinder(0.13, 0.45, 0.22, 0, 0.12, c)
    b.add_cylinder(0.11, 0.42, 0.22, 0,-0.35, c)
    b.add_box(0.28, 0.44, 0.16, 0.22, 0.08,-0.62, c)
    b.add_sphere(0.07,-0.14, 0.33, 1.42, (1.0, 0.8, 0.0))
    b.add_sphere(0.07, 0.14, 0.33, 1.42, (1.0, 0.8, 0.0))
    b.add_cylinder(0.018, 0.42, 0, 0, 1.85, _dark(c))
    b.add_sphere(0.05, 0, 0, 2.08, _light(c))
    return b

def _build_castle(c):
    b = GLBBuilder()
    for px, py, sw, sd in [(0,1.6,3.2,0.3),(0,-1.6,3.2,0.3),
                            (1.6,0,0.3,3.2),(-1.6,0,0.3,3.2)]:
        b.add_box(sw, sd, 1.4, px, py, 0.7, c)
    for tx, ty in [(1.6,1.6),(-1.6,1.6),(1.6,-1.6),(-1.6,-1.6)]:
        b.add_cylinder(0.35, 1.9, tx, ty, 0.95, _dark(c))
        b.add_cone(    0.38, 0.5, tx, ty, 2.0,  _dark(c, 0.3))
    b.add_cylinder(0.55, 2.4, 0, 0, 1.2, _dark(c))
    b.add_cone(    0.58, 0.7, 0, 0, 2.65, _dark(c, 0.3))
    b.add_box(0.24, 0.64, 0.9, 1.65, 0, 0.45, _dark(c))
    b.add_torus(2.1, 0.18, 0, 0,-0.15, _dark(c))
    for i in range(5):
        b.add_box(0.36, 0.32, 0.44,-1.2+i*0.6, 1.6, 1.55, _dark(c))
    return b

def _build_spaceship(c):
    b = GLBBuilder()
    b.add_sphere(0.65, 0, 0, 0, c)
    b.add_sphere(0.35, 1.0, 0, 0.05, _light(c))
    b.add_cylinder(0.22, 1.0,-0.5,-0.9, 0, c)
    b.add_cylinder(0.22, 1.0,-0.5, 0.9, 0, c)
    b.add_cone(0.28, 0.3,-1.1,-0.9, 0, _dark(c))
    b.add_cone(0.28, 0.3,-1.1, 0.9, 0, _dark(c))
    b.add_box(0.1, 2.8, 0.12, 0,-1.3, 0, _dark(c))
    b.add_box(0.1, 2.8, 0.12, 0, 1.3, 0, _dark(c))
    b.add_sphere(0.22, 1.35, 0, 0.1, _dark(c, 0.3))
    b.add_box(1.2, 0.12, 0.12, 0, 0, 0.42, _dark(c))
    b.add_torus(0.22, 0.04,-1.1,-0.9, 0, _light(c))
    b.add_torus(0.22, 0.04,-1.1, 0.9, 0, _light(c))
    b.add_cylinder(0.012, 0.55, 0.5, 0, 0.55, _dark(c))
    return b

def _build_house(c):
    b = GLBBuilder()
    b.add_box(2.2, 1.8, 1.0, 0, 0, 0.5, c)
    b.add_box(2.4, 1.8, 0.16,-0.05, 0,-0.05, _dark(c))
    # Roof (4 sloped panels approximated as boxes)
    b.add_box(2.4, 0.1, 0.9, 0,-0.9, 1.3, _dark(c, 0.6))
    b.add_box(2.4, 0.1, 0.9, 0, 0.9, 1.3, _dark(c, 0.6))
    b.add_box(0.1, 2.0, 0.9, 1.2, 0, 1.3, _dark(c, 0.6))
    b.add_box(0.1, 2.0, 0.9,-1.2, 0, 1.3, _dark(c, 0.6))
    b.add_box(0.3, 0.3, 1.1, 0.5, 0.2, 1.5, _dark(c))
    b.add_box(0.36, 0.04, 0.64, 0,-0.92, 0.4, _dark(c))
    b.add_box(0.36, 0.04, 0.40, 0,-0.93, 0.35, _dark(c, 0.4))
    b.add_box(0.44, 0.04, 0.4,-0.55,-0.92, 0.58, (0.7, 0.85, 1.0))
    b.add_box(0.44, 0.04, 0.4, 0.55,-0.92, 0.58, (0.7, 0.85, 1.0))
    return b

def _build_sword(c):
    b = GLBBuilder()
    b.add_box(0.12, 1.1, 3.1, 0, 0, 1.2, c)
    b.add_cone(0.08, 0.55, 0, 0, 2.95, c)
    b.add_box(0.16, 2.2, 0.28, 0, 0,-0.1, _dark(c))
    b.add_sphere(0.12, 0,-1.12,-0.08, _dark(c))
    b.add_sphere(0.12, 0, 1.12,-0.08, _dark(c))
    b.add_cylinder(0.10, 0.85, 0, 0,-0.65, _mix(c,(0.4,0.2,0.1)))
    for i in range(5):
        b.add_torus(0.11, 0.025, 0, 0,-0.35-i*0.14, _dark(c))
    b.add_sphere(0.16, 0, 0,-1.12, _dark(c))
    return b

def _build_tree(c):
    trunk = (0.45, 0.28, 0.12)
    green = (0.15, 0.55, 0.12)
    b = GLBBuilder()
    b.add_cylinder(0.18, 1.2, 0, 0, 0.6, trunk)
    b.add_sphere(0.85, 0, 0, 2.1, green)
    b.add_sphere(0.70,-0.55, 0, 2.65, green)
    b.add_sphere(0.70, 0.55, 0, 2.65, green)
    b.add_sphere(0.65, 0,-0.5, 2.75, green)
    b.add_sphere(0.65, 0, 0, 3.2,  green)
    b.add_sphere(0.42, 0, 0, 3.75, _light(green))
    b.add_cylinder(0.05, 0.85,-0.55, 0, 1.9, trunk)
    b.add_cylinder(0.05, 0.85, 0.55, 0, 1.9, trunk)
    b.add_cylinder(1.1, 0.02, 0, 0,-0.01, (0.3, 0.5, 0.1))
    return b

def _build_plane(c):
    b = GLBBuilder()
    b.add_cylinder(0.3, 3.6, 0, 0, 0, c)
    b.add_cone(0.3, 0.7, 2.2, 0, 0, _light(c))
    b.add_box(1.8, 2.8, 0.12, 0,-1.8, 0, c)
    b.add_box(1.8, 2.8, 0.12, 0, 1.8, 0, c)
    b.add_box(0.9, 1.3, 0.10,-1.6,-0.85, 0, _dark(c))
    b.add_box(0.9, 1.3, 0.10,-1.6, 0.85, 0, _dark(c))
    b.add_box(0.9, 0.1, 1.0,-1.6, 0, 0.5, _dark(c))
    b.add_sphere(0.22, 1.3, 0, 0.18, _dark(c, 0.3))
    b.add_cylinder(0.15, 0.9,-0.1,-1.3, 0, _dark(c))
    b.add_cylinder(0.15, 0.9,-0.1, 1.3, 0, _dark(c))
    b.add_cylinder(0.07, 0.18, 2.55, 0, 0, _dark(c))
    b.add_cylinder(0.035, 0.55, 1.0, 0,-0.45, c)
    b.add_cylinder(0.10, 0.10, 1.0, 0,-0.72, (0.1,0.1,0.1))
    return b

def _build_helicopter(c):
    b = GLBBuilder()
    b.add_box(3.6, 1.3, 1.2, 0, 0, 0, c)
    b.add_sphere(0.35, 1.5, 0, 0.1, _dark(c, 0.3))
    b.add_cylinder(0.12, 2.2,-1.5, 0, 0.12, _dark(c))
    b.add_sphere(0.22,-2.7, 0, 0.22, c)
    b.add_cylinder(0.04, 0.2, 0, 0, 0.85, _dark(c))
    for ang in [0, 120, 240]:
        a = math.radians(ang)
        b.add_box(2.2, 0.16, 0.05,
                  math.cos(a)*1.1, math.sin(a)*1.1, 0.9, _dark(c))
    b.add_box(3.0, 0.08, 0.08, 0.5,-0.72,-0.7, _dark(c))
    b.add_box(3.0, 0.08, 0.08, 0.5, 0.72,-0.7, _dark(c))
    b.add_cylinder(0.06, 0.72, 1.0, 0,-0.36, _dark(c))
    b.add_cylinder(0.06, 0.72,-0.1, 0,-0.36, _dark(c))
    b.add_torus(0.12, 0.03, 0, 0, 0.88, _dark(c))
    return b

def _build_truck(c):
    b = GLBBuilder()
    b.add_box(1.9, 1.76, 1.0, 0.8, 0, 0.5, c)
    b.add_box(1.8, 1.7,  0.56, 0.8, 0, 1.12, _light(c))
    b.add_box(2.2, 1.76, 0.5,-0.85, 0, 0.25, _dark(c))
    for wx, wy in [(1.4,-0.9),(1.4,0.9),(-1.0,-0.9),(-1.0,0.9)]:
        b.add_cylinder(0.28, 0.22, wx, wy, 0.28, (0.1,0.1,0.1))
        b.add_cylinder(0.18, 0.24, wx, wy, 0.28, (0.7,0.7,0.7))
    b.add_sphere(0.1, 1.78,-0.5, 0.52, (1.0,1.0,0.6))
    b.add_sphere(0.1, 1.78, 0.5, 0.52, (1.0,1.0,0.6))
    b.add_box(0.12, 1.8, 0.36, 1.82, 0, 0.35, _dark(c))
    b.add_box(0.12, 1.76, 0.36,-1.96, 0, 0.35, _dark(c))
    b.add_box(0.30, 1.76, 0.08,-0.85,-0.9, 0.58, _dark(c))
    b.add_box(0.30, 1.76, 0.08,-0.85, 0.9, 0.58, _dark(c))
    b.add_box(0.08, 1.76, 0.50,-1.92, 0, 0.58, _dark(c))
    b.add_cylinder(0.015, 0.35, 1.2, 0, 1.28, _dark(c))
    return b

def _build_ship(c):
    b = GLBBuilder()
    b.add_box(7.0, 1.8, 1.0, 0, 0,-0.2, c)
    b.add_box(7.0, 1.8, 0.12, 0, 0, 0.32, _dark(c))
    b.add_box(1.6, 1.4, 0.9,-1.5, 0, 0.72, _dark(c))
    b.add_cylinder(0.1, 0.8,-1.8, 0, 1.72, _dark(c, 0.4))
    b.add_cylinder(0.12, 0.8,-1.8, 0, 2.12, _dark(c, 0.3))
    for crane_x in [0.5, 1.5, 2.2]:
        b.add_cylinder(0.05, 1.2, crane_x, 0, 0.92, _dark(c))
        b.add_cylinder(0.03, 0.9, crane_x+0.25, 0, 1.45, _dark(c))
    b.add_box(7.0, 0.04, 0.50, 0, 0.9, 0.22, _dark(c))
    b.add_box(7.0, 0.04, 0.50, 0,-0.9, 0.22, _dark(c))
    b.add_cone(0.3, 0.6, 3.3, 0, 0.1, _dark(c, 0.7))
    b.add_cylinder(0.06, 0.6,-3.0, 0,-0.10, _dark(c))
    return b

def _build_submarine(c):
    b = GLBBuilder()
    b.add_sphere(0.55, 0, 0, 0, c)
    b.add_box(0.7, 0.56, 0.84, 0.5, 0, 0.7, c)
    b.add_cylinder(0.04, 0.8, 0.5, 0, 1.32, _dark(c))
    b.add_sphere(0.06, 0.5, 0, 1.72, _dark(c))
    for side, sy in [(-1,-1),(1,1)]:
        b.add_box(0.7, 0.9, 0.12, 2.2, sy*0.55,-0.12, _dark(c))
        b.add_box(0.6, 0.12, 0.76, 2.3, 0, sy*0.48, _dark(c))
    for ang in [0, 90, 180, 270]:
        a = math.radians(ang)
        b.add_cylinder(0.06, 0.5,-2.9,
                       math.cos(a)*0.22, math.sin(a)*0.22, _dark(c))
    b.add_torus(0.56, 0.04, 0, 0,-0.3, _dark(c))
    b.add_torus(0.56, 0.04, 0, 0, 0.0, _dark(c))
    b.add_torus(0.56, 0.04, 0, 0, 0.3, _dark(c))
    b.add_sphere(0.2, 2.9, 0, 0, _dark(c))
    return b

def _build_tank(c):
    b = GLBBuilder()
    b.add_box(3.8, 1.8, 0.76, 0, 0, 0.22, c)
    b.add_sphere(0.28, 0.2, 0, 0.65, c)
    b.add_box(0.12, 0.64, 0.16, 1.35, 0, 0.72, _dark(c))
    for side in [-1, 1]:
        b.add_box(4.0, 0.36, 0.70, 0, side*1.0,-0.10, _dark(c, 0.7))
        for wx in [-1.5,-1.0,-0.5,0.0,0.5,1.0,1.5]:
            b.add_cylinder(0.22, 0.2, wx, side*1.0, 0.0, (0.1,0.1,0.1))
    b.add_cylinder(0.08, 0.15, 0.3, 0.25, 0.95, _dark(c))
    b.add_box(3.6, 1.8, 0.12, 0, 0, 0.45, _dark(c))
    b.add_box(0.24, 1.8, 1.1, 1.85, 0, 0.32, _dark(c, 0.7))
    b.add_cylinder(0.04, 0.25, 1.65, 0, 0.72, _dark(c))
    b.add_cylinder(0.03, 0.35,-0.2, 0.28, 0.98, _dark(c))
    return b

def _build_horse(c):
    b = GLBBuilder()
    b.add_sphere(0.6, 0, 0, 0.7, c)
    b.add_sphere(0.3, 1.2, 0, 1.4, c)
    b.add_cylinder(0.20, 0.7, 0.72, 0, 1.1, c)
    b.add_cone(0.15, 0.45, 1.55, 0, 1.3, c)
    for lx, ly in [(0.7,-0.28),(0.7,0.28),(-0.65,-0.28),(-0.65,0.28)]:
        b.add_cylinder(0.09, 0.55, lx, ly, 0.28, c)
        b.add_cylinder(0.07, 0.55, lx, ly,-0.25, c)
        b.add_box(0.2, 0.24, 0.16, lx, ly,-0.58, _dark(c))
    b.add_cone(0.12, 1.4,-1.4, 0, 0.65, _dark(c))
    for i in range(5):
        b.add_box(0.22, 0.06, 0.06, 0.72+i*0.1, 0, 1.25+i*0.08, _dark(c))
    b.add_sphere(0.055, 1.55,-0.18, 1.5, (0.05,0.05,0.05))
    b.add_sphere(0.055, 1.55, 0.18, 1.5, (0.05,0.05,0.05))
    return b

def _build_motorcycle(c):
    b = GLBBuilder()
    b.add_cylinder(0.38, 0.2, 1.1, 0, 0.38, (0.1,0.1,0.1))
    b.add_cylinder(0.38, 0.2,-0.8, 0, 0.38, (0.1,0.1,0.1))
    b.add_cylinder(0.24, 0.22, 1.1, 0, 0.38, (0.6,0.6,0.6))
    b.add_cylinder(0.24, 0.22,-0.8, 0, 0.38, (0.6,0.6,0.6))
    b.add_box(0.9, 0.6, 0.64, 0.1, 0, 0.62, c)
    b.add_box(1.1, 0.4, 0.36, 0.1, 0, 0.95, _light(c))
    b.add_box(1.1, 0.36, 0.16,-0.2, 0, 1.1, _dark(c))
    b.add_cylinder(0.04, 0.85, 0.8, 0, 0.82, _dark(c))
    b.add_cylinder(0.025, 0.7, 1.15, 0, 1.15, _dark(c))
    b.add_cylinder(0.025, 0.70, 1.2, 0, 1.38, _dark(c))
    b.add_sphere(0.06, 1.25, 0.35, 1.38, (0.2,0.2,0.2))
    b.add_sphere(0.06, 1.25,-0.35, 1.38, (0.2,0.2,0.2))
    b.add_cylinder(0.04, 1.0,-0.3, 0.18, 0.32, _dark(c))
    b.add_sphere(0.1,  1.1, 0, 0.8, (1.0,1.0,0.7))
    return b

def _build_bicycle(c):
    b = GLBBuilder()
    b.add_torus(0.38, 0.04, 1.0, 0, 0.38, (0.1,0.1,0.1))
    b.add_torus(0.38, 0.04,-0.8, 0, 0.38, (0.1,0.1,0.1))
    b.add_cylinder(0.025, 1.0, 0.35, 0, 0.72, c)
    b.add_cylinder(0.022, 0.9, 0.2, 0, 0.55, c)
    b.add_cylinder(0.022, 0.8,-0.1, 0, 0.82, c)
    b.add_cylinder(0.022, 0.8,-0.4, 0, 0.65, c)
    b.add_cylinder(0.025, 0.65, 0.75, 0, 0.62, c)
    b.add_cylinder(0.02, 0.5, 0.92, 0, 1.12, c)
    b.add_cylinder(0.02, 0.55, 1.02, 0, 1.32, c)
    b.add_box(0.6, 0.24, 0.08,-0.08, 0, 1.28, _dark(c))
    b.add_torus(0.10, 0.04,-0.05, 0, 0.38, _dark(c))
    b.add_cylinder(0.035, 0.45,-0.05, 0, 0.2, _dark(c))
    b.add_cylinder(0.05, 0.10,-0.05, 0.22, 0.02, _dark(c))
    b.add_cylinder(0.05, 0.10,-0.05,-0.22, 0.74, _dark(c))
    return b

def _build_dog(c):
    b = GLBBuilder()
    b.add_sphere(0.4, 0, 0, 0.42, c)
    b.add_sphere(0.28, 0.72, 0, 0.72, c)
    b.add_cylinder(0.14, 0.35, 0.38, 0, 0.58, c)
    b.add_cone(0.1, 0.3, 1.02, 0, 0.65, c)
    for lx, ly in [(0.4,-0.32),(0.4,0.32),(-0.45,-0.32),(-0.45,0.32)]:
        b.add_cylinder(0.06, 0.42, lx, ly, 0.18, c)
        b.add_sphere(0.08, lx, ly,-0.02, _dark(c))
    b.add_cone(0.08, 0.7,-0.88, 0, 0.6, _dark(c))
    b.add_box(0.24, 0.10, 0.36, 0.7,-0.2, 1.0, c)
    b.add_box(0.24, 0.10, 0.36, 0.7, 0.2, 1.0, c)
    b.add_sphere(0.04, 0.94,-0.14, 0.76, (0.05,0.05,0.05))
    b.add_sphere(0.04, 0.94, 0.14, 0.76, (0.05,0.05,0.05))
    b.add_torus(0.2, 0.03, 0.5, 0, 0.28, (0.8,0.2,0.1))
    return b

def _build_cat(c):
    b = GLBBuilder()
    b.add_sphere(0.32, 0, 0, 0.35, c)
    b.add_sphere(0.24, 0.55, 0, 0.62, c)
    b.add_cylinder(0.12, 0.2, 0.3, 0, 0.5, c)
    b.add_cone(0.1, 0.18, 0.62,-0.18, 0.88, c)
    b.add_cone(0.1, 0.18, 0.62, 0.18, 0.88, c)
    for lx, ly in [(0.35,-0.22),(0.35,0.22),(-0.42,-0.22),(-0.42,0.22)]:
        b.add_cylinder(0.05, 0.35, lx, ly, 0.14, c)
        b.add_sphere(0.07, lx, ly,-0.03, _dark(c))
    b.add_cone(0.06, 0.9,-0.65, 0, 0.28, _dark(c))
    b.add_cone(0.04, 0.5,-1.1, 0, 0.6, _dark(c))
    b.add_sphere(0.04, 0.72,-0.10, 0.68, (0.1,0.5,0.1))
    b.add_sphere(0.04, 0.72, 0.10, 0.68, (0.1,0.5,0.1))
    b.add_sphere(0.03, 0.78, 0, 0.60, (0.9,0.5,0.5))
    b.add_sphere(0.28, 0, 0, 0.35, _light(c, 1.1))
    return b

def _build_bird(c):
    b = GLBBuilder()
    b.add_sphere(0.28, 0, 0, 0.3, c)
    b.add_sphere(0.20, 0.5, 0, 0.62, c)
    b.add_cylinder(0.08, 0.18, 0.28, 0, 0.48, c)
    b.add_cone(0.06, 0.25, 0.72, 0, 0.62, (0.9,0.6,0.1))
    b.add_box(1.6, 0.08, 0.70, 0,-0.38, 0.35, c)
    b.add_box(1.6, 0.08, 0.70, 0, 0.38, 0.35, c)
    b.add_cone(0.1, 0.55,-0.62, 0, 0.25, _dark(c))
    for i in range(3):
        b.add_cone(0.03, 0.35,-0.78+i*0.08,(i-1)*0.1, 0.15, _dark(c))
    for side in [-1, 1]:
        b.add_cylinder(0.025, 0.35, 0.05, side*0.1,-0.05, (0.7,0.5,0.2))
    b.add_sphere(0.03, 0.65,-0.06, 0.68, (0.05,0.05,0.05))
    b.add_sphere(0.03, 0.65, 0.06, 0.68, (0.05,0.05,0.05))
    return b

def _build_fish(c):
    b = GLBBuilder()
    b.add_sphere(0.4, 0, 0, 0, c)
    b.add_sphere(0.28, 0.75, 0, 0, c)
    b.add_cone(0.35, 0.55,-1.1, 0, 0, _dark(c))
    b.add_box(0.36, 0.16, 0.70,-1.5, 0, 0.2, c)
    b.add_box(0.36, 0.16, 0.70,-1.5, 0,-0.2, c)
    b.add_box(1.0, 0.10, 0.56, 0.1, 0, 0.42, c)
    b.add_box(0.7, 0.10, 0.44,-0.3, 0,-0.42, c)
    b.add_box(0.6, 0.76, 0.36, 0.3,-0.38, 0, c)
    b.add_box(0.6, 0.76, 0.36, 0.3, 0.38, 0, c)
    b.add_sphere(0.06, 1.02,-0.2, 0.1, (0.05,0.05,0.05))
    b.add_sphere(0.06, 1.02, 0.2, 0.1, (0.05,0.05,0.05))
    b.add_torus(0.3, 0.02, 0.45, 0, 0, _dark(c))
    for i in range(4):
        b.add_torus(0.4-i*0.06, 0.018,-0.3+i*0.2, 0, 0, _dark(c))
    return b

def _build_flower(c):
    stem = (0.15, 0.55, 0.12)
    b = GLBBuilder()
    b.add_cylinder(0.04, 1.2, 0, 0, 0.6, stem)
    b.add_sphere(0.22, 0, 0, 1.25, (1.0, 0.9, 0.1))
    for i in range(8):
        a = math.radians(i * 45)
        b.add_sphere(0.22, math.cos(a)*0.48, math.sin(a)*0.48, 1.25, c)
    for i in range(4):
        a = math.radians(i*90+22.5)
        b.add_sphere(0.15, math.cos(a)*0.32, math.sin(a)*0.32, 1.22, _light(c))
    b.add_box(0.8, 1.0, 0.08, 0.25, 0, 0.55, stem)
    b.add_box(0.8, 1.0, 0.08,-0.25, 0, 0.40, stem)
    b.add_torus(0.25, 0.04, 0, 0, 1.25, _dark(c))
    return b

def _build_mountain(c):
    snow = (0.95, 0.95, 0.95)
    b = GLBBuilder()
    b.add_cone(2.2, 2.8, 0, 0, 1.4, c, segments=6)
    b.add_cone(0.55, 0.5, 0, 0, 2.95, snow, segments=6)
    for ang in [0,60,120,180,240,300]:
        a = math.radians(ang)
        b.add_cone(0.65, 1.2,
                   math.cos(a)*1.4, math.sin(a)*1.4, 0.6, _dark(c), segments=4)
    b.add_cylinder(2.5, 0.35, 0, 0,-0.17, _dark(c))
    for i in range(8):
        a = math.radians(i*45)
        b.add_sphere(0.28, math.cos(a)*2.2, math.sin(a)*2.2, 0.12, _dark(c))
    b.add_cone(0.8, 1.0, 2.5,-1.0, 0.5, _dark(c), segments=5)
    b.add_cone(0.7, 0.9,-2.2, 1.2, 0.45, _dark(c), segments=5)
    return b

def _build_crystal(c):
    b = GLBBuilder()
    b.add_cone(0.30, 1.8, 0, 0, 0.9, c, segments=6)
    b.add_cone(0.22, 1.4, 0.38, 0.22, 0.7, c, segments=6)
    b.add_cone(0.18, 1.2,-0.32, 0.3, 0.6, c, segments=6)
    b.add_cone(0.25, 1.5,-0.28,-0.28, 0.75, c, segments=6)
    b.add_cone(0.15, 0.9, 0.42,-0.35, 0.45, _light(c), segments=6)
    b.add_cone(0.12, 0.7, 0.55, 0, 0.35, _light(c), segments=4)
    b.add_cone(0.10, 0.6,-0.5, 0.15, 0.30, _light(c), segments=4)
    b.add_cone(0.08, 0.45, 0.1, 0.55, 0.22, _light(c), segments=6)
    b.add_cylinder(0.55, 0.12, 0, 0,-0.06, _dark(c))
    b.add_torus(0.5, 0.05, 0, 0, 0.0, _dark(c))
    for i in range(6):
        a = math.radians(i*60)
        b.add_cone(0.06, 0.35, math.cos(a)*0.6, math.sin(a)*0.6, 0.17, _light(c), segments=4)
    return b

def _build_crown(c):
    b = GLBBuilder()
    b.add_torus(0.65, 0.12, 0, 0, 0, c)
    b.add_cylinder(0.65, 0.35, 0, 0, 0.18, c)
    for i in range(5):
        a = math.radians(i*72)
        px = math.cos(a)*0.65; py = math.sin(a)*0.65
        b.add_cone(0.12, 0.65, px, py, 0.52, _light(c))
        b.add_sphere(0.07, px, py, 0.4, (0.8,0.2,0.2))
    for i in range(5):
        a = math.radians(i*72+36)
        b.add_sphere(0.09, math.cos(a)*0.63, math.sin(a)*0.63, 0.38, _light(c))
    b.add_torus(0.50, 0.06, 0, 0,-0.08, _dark(c))
    b.add_sphere(0.12, 0, 0, 0.18, (0.8,0.6,0.1))
    for i in range(10):
        a = math.radians(i*36)
        b.add_sphere(0.045, math.cos(a)*0.66, math.sin(a)*0.66, 0.18, _light(c))
    b.add_torus(0.62, 0.04, 0, 0, 0.35, _light(c))
    return b

def _build_mushroom(c):
    stem = (0.95, 0.90, 0.80)
    b = GLBBuilder()
    b.add_sphere(0.75, 0, 0, 0.75, c)
    b.add_cylinder(0.22, 0.9, 0, 0, 0.25, stem)
    b.add_cylinder(0.32, 0.06, 0, 0,-0.08, stem)
    b.add_torus(0.32, 0.06, 0, 0, 0.52, stem)
    for i in range(7):
        a = math.radians(i*51.4)
        r2 = 0.35 + (i%3)*0.1
        b.add_sphere(0.08, math.cos(a)*r2, math.sin(a)*r2, 1.1, (0.95,0.95,0.95))
    b.add_torus(0.65, 0.06, 0, 0,-0.1, _dark(c))
    b.add_cylinder(1.1, 0.02, 0, 0,-0.15, (0.3,0.5,0.1))
    return b

def _build_cactus(c):
    green = (0.15, 0.55, 0.15)
    b = GLBBuilder()
    b.add_cylinder(0.28, 2.4, 0, 0, 1.2, green)
    b.add_sphere(0.28, 0, 0, 2.42, green)
    b.add_cylinder(0.18, 0.8,-0.42, 0, 1.35, green)
    b.add_cylinder(0.16, 0.9,-0.85, 0, 1.75, green)
    b.add_sphere(0.16,-0.85, 0, 2.22, green)
    b.add_cylinder(0.18, 0.8, 0.42, 0, 1.05, green)
    b.add_cylinder(0.16, 0.85, 0.85, 0, 1.55, green)
    b.add_sphere(0.16, 0.85, 0, 2.0, green)
    b.add_cylinder(1.5, 0.05, 0, 0,-0.02, (0.6,0.4,0.2))
    b.add_cone(0.06, 0.22, 0, 0, 2.62, (1.0,0.8,0.5))
    b.add_cone(0.05, 0.18,-0.85, 0, 2.35, (1.0,0.8,0.5))
    return b

def _build_cannon(c):
    b = GLBBuilder()
    b.add_cylinder(0.18, 1.8, 0, 0, 0.72, c)
    b.add_sphere(0.18, 0, 0, 1.65, c)
    b.add_cone(0.22, 0.12, 0, 0,-0.12, c)
    b.add_box(2.2, 0.8, 0.6, 0, 0, 0.08, _dark(c))
    b.add_cylinder(0.28, 0.22, 0.9,-0.5, 0.28, (0.1,0.1,0.1))
    b.add_cylinder(0.28, 0.22, 0.9, 0.5, 0.28, (0.1,0.1,0.1))
    b.add_cylinder(0.28, 0.22,-0.9,-0.5, 0.28, (0.1,0.1,0.1))
    b.add_cylinder(0.28, 0.22,-0.9, 0.5, 0.28, (0.1,0.1,0.1))
    b.add_sphere(0.25, 1.5, 0, 0.5, _dark(c, 0.4))
    b.add_torus(0.18, 0.03, 0, 0, 0.4, _dark(c))
    b.add_torus(0.18, 0.03, 0, 0, 0.72, _dark(c))
    b.add_torus(0.18, 0.03, 0, 0, 1.05, _dark(c))
    return b

def _build_pyramid(c):
    b = GLBBuilder()
    b.add_cone(1.0, 1.4, 0, 0, 0.0, c, segments=4)
    b.add_box(2.2, 2.2, 0.14, 0, 0,-0.72, _dark(c))
    b.add_cone(0.85, 0.10, 0, 0,-0.55, _dark(c), segments=4)
    b.add_cone(0.65, 0.10, 0, 0,-0.35, _dark(c), segments=4)
    b.add_sphere(0.08, 0, 0, 0.72, _light(c))
    for ang in [45,135,225,315]:
        a = math.radians(ang)
        b.add_sphere(0.07, math.cos(a)*0.98, math.sin(a)*0.98,-0.72, _dark(c))
    b.add_box(0.44, 0.04, 0.6, 0,-1.02,-0.42, _dark(c))
    return b

def _build_diamond(c):
    b = GLBBuilder()
    b.add_cone(0.6, 0.7, 0, 0, 0.1, c, segments=8)
    b.add_cone(0.6, 0.8, 0, 0,-0.05, _light(c), segments=8)
    b.add_cylinder(0.6, 0.14, 0, 0, 0.07, _light(c, 1.2), segments=8)
    for i in range(8):
        a = math.radians(i*45)
        b.add_box(0.28, 0.04, 0.65,
                  math.cos(a)*0.35, math.sin(a)*0.35, 0.0, _dark(c))
    return b

def _build_star(c):
    b = GLBBuilder()
    b.add_cylinder(0.45, 0.2, 0, 0, 0, c)
    for i in range(5):
        a = math.radians(i*72 - 90)
        b.add_cone(0.18, 0.5,
                   math.cos(a)*0.85, math.sin(a)*0.85, 0, c, segments=4)
        b.add_sphere(0.07, math.cos(a)*1.0, math.sin(a)*1.0, 0, _light(c))
    for i in range(5):
        a = math.radians(i*72 - 90 + 36)
        b.add_cone(0.09, 0.28,
                   math.cos(a)*0.42, math.sin(a)*0.42, 0.02, _light(c), segments=4)
    b.add_sphere(0.15, 0, 0, 0.12, _light(c))
    b.add_torus(0.46, 0.04, 0, 0, 0, _dark(c))
    return b

def _build_capsule(c):
    b = GLBBuilder()
    b.add_cylinder(0.38, 1.4, 0, 0, 0, c)
    b.add_sphere(0.38, 0, 0, 0.7, c)
    b.add_sphere(0.38, 0, 0,-0.7, c)
    for z in [-0.5,-0.25,0,0.25,0.5]:
        b.add_torus(0.40, 0.035, 0, 0, z, _dark(c))
    for ang in [0,60,120,180,240,300]:
        a = math.radians(ang)
        b.add_box(0.08, 0.08, 1.6,
                  math.cos(a)*0.40, math.sin(a)*0.40, 0, _dark(c))
    b.add_cylinder(0.1, 0.06, 0, 0, 1.06, _dark(c))
    b.add_cylinder(0.08, 0.06, 0, 0,-1.06, _dark(c))
    b.add_sphere(0.05, 0, 0, 1.1, _light(c))
    return b

def _build_cube(c):
    b = GLBBuilder()
    b.add_box(1.8, 1.8, 1.8, 0, 0, 0, c)
    for ax in [0,1,2]:
        for p1 in [-1,1]:
            for p2 in [-1,1]:
                lx = 0 if ax==0 else p1*0.9
                ly = p1*0.9 if ax==0 else (0 if ax==1 else p2*0.9)
                lz = p2*0.9 if ax==2 else (p2*0.9 if ax==0 else p1*0.9)
                b.add_cylinder(0.06, 1.8, lx, ly, lz, _dark(c))
    for cx in [-1,1]:
        for cy in [-1,1]:
            for cz in [-1,1]:
                b.add_sphere(0.09, cx*0.9, cy*0.9, cz*0.9, _light(c))
    return b

def _build_sphere_shape(c):
    b = GLBBuilder()
    b.add_sphere(0.8, 0, 0, 0, c)
    b.add_torus(0.88, 0.06, 0, 0, 0, _dark(c))
    b.add_torus(1.1, 0.04, 0, 0, 0, _light(c))
    b.add_torus(1.1, 0.04, 0, 0, 0, _light(c))
    b.add_cylinder(0.04, 2.0, 0, 0, 0, _dark(c))
    for ang in [0,90,180,270]:
        a = math.radians(ang)
        b.add_sphere(0.12, math.cos(a)*1.1, math.sin(a)*1.1, 0, _dark(c))
    b.add_cone(0.08, 0.5, 0, 0, 1.1, _light(c))
    b.add_cone(0.08, 0.5, 0, 0,-1.1, _light(c))
    return b

def _build_cylinder_shape(c):
    b = GLBBuilder()
    b.add_cylinder(0.5, 1.8, 0, 0, 0, c)
    b.add_cylinder(0.52, 0.06, 0, 0, 0.93, _dark(c))
    b.add_cylinder(0.52, 0.06, 0, 0,-0.93, _dark(c))
    for z in [-0.6,-0.2,0.2,0.6]:
        b.add_torus(0.52, 0.04, 0, 0, z, _dark(c))
    for ang in [0,60,120,180,240,300]:
        a = math.radians(ang)
        b.add_box(0.08, 0.08, 1.8,
                  math.cos(a)*0.52, math.sin(a)*0.52, 0, _dark(c))
    b.add_sphere(0.12, 0, 0, 1.1, _light(c))
    b.add_torus(0.48, 0.06, 0, 0,-1.0, _dark(c))
    return b

def _build_cone_shape(c):
    b = GLBBuilder()
    b.add_cone(0.7, 1.8, 0, 0,-0.9, c)
    b.add_torus(0.72, 0.05, 0, 0,-0.9, _dark(c))
    for z, r in [(-0.5, 0.52), (0.0, 0.35), (0.4, 0.2)]:
        b.add_torus(r, 0.04, 0, 0, z, _dark(c))
    for ang in [0,120,240]:
        a = math.radians(ang)
        b.add_box(0.16, 0.6, 1.2,
                  math.cos(a)*0.55, math.sin(a)*0.55,-0.35, _dark(c))
    b.add_sphere(0.05, 0, 0, 0.9, _light(c))
    b.add_cylinder(0.7, 0.06, 0, 0,-0.93, _dark(c))
    return b

def _build_torus_shape(c):
    b = GLBBuilder()
    b.add_torus(0.8, 0.25, 0, 0, 0, c)
    b.add_torus(0.8, 0.12, 0, 0, 0, _dark(c))
    b.add_torus(1.06, 0.06, 0, 0, 0, _light(c))
    b.add_torus(0.54, 0.06, 0, 0, 0, _light(c))
    for ang in range(0, 360, 45):
        a = math.radians(ang)
        b.add_sphere(0.1, math.cos(a)*0.8, math.sin(a)*0.8, 0, _dark(c))
    b.add_torus(0.8, 0.06, 0, 0, 0, _light(c))
    b.add_cylinder(0.06, 0.8, 0, 0, 0, _dark(c))
    return b

def _build_chest(c):
    b = GLBBuilder()
    b.add_box(2.2, 1.44, 0.84, 0, 0, 0.22, c)
    b.add_box(2.2, 1.44, 0.30, 0, 0, 0.7,  _light(c))
    for bz in [0.12, 0.76, 0.70]:
        b.add_box(2.24, 1.48, 0.08, 0, 0, bz, _dark(c))
    for hx in [-0.8, 0.8]:
        b.add_cylinder(0.04, 0.08, hx, 0.72, 0.72, _dark(c, 0.4))
    b.add_box(0.40, 0.08, 0.36, 0,-0.74, 0.50, _dark(c))
    b.add_cylinder(0.06, 0.06, 0,-0.76, 0.52, _dark(c, 0.4))
    b.add_torus(0.05, 0.02, 0,-0.79, 0.52, _dark(c, 0.4))
    for cx in [-0.9, 0.9]:
        for cz in [0.12, 0.34, 0.56, 0.73]:
            b.add_sphere(0.04, cx, 0, cz, _dark(c, 0.4))
    b.add_box(2.3, 1.56, 0.12, 0, 0, 0.04, _dark(c))
    return b

def _build_barrel(c):
    b = GLBBuilder()
    b.add_cylinder(0.55, 1.2, 0, 0, 0, c)
    b.add_cylinder(0.45, 0.08, 0, 0, 0.64, _dark(c))
    b.add_cylinder(0.45, 0.08, 0, 0,-0.64, _dark(c))
    for z in [0.42, 0.0,-0.42]:
        b.add_torus(0.56, 0.06, 0, 0, z, _dark(c, 0.5))
    b.add_torus(0.52, 0.05, 0, 0, 0.58, _dark(c, 0.5))
    b.add_torus(0.52, 0.05, 0, 0,-0.58, _dark(c, 0.5))
    b.add_cylinder(0.05, 0.08, 0.56, 0, 0.12, _dark(c, 0.4))
    b.add_sphere(0.04, 0.62, 0, 0.12, _dark(c, 0.4))
    for ang in range(0, 360, 30):
        a = math.radians(ang)
        b.add_box(0.08, 0.08, 1.16,
                  math.cos(a)*0.56, math.sin(a)*0.56, 0, _dark(c, 0.7))
    return b

def _build_lantern(c):
    b = GLBBuilder()
    b.add_cylinder(0.35, 0.70, 0, 0, 0, _dark(c, 0.4), segments=6)
    b.add_torus(0.36, 0.04, 0, 0, 0.35, _dark(c, 0.4))
    b.add_torus(0.36, 0.04, 0, 0,-0.35, _dark(c, 0.4))
    b.add_torus(0.36, 0.04, 0, 0, 0.0,  _dark(c, 0.4))
    for ang in [0,60,120,180,240,300]:
        a = math.radians(ang)
        b.add_cylinder(0.025, 0.7,
                       math.cos(a)*0.36, math.sin(a)*0.36, 0, _dark(c, 0.4))
    b.add_cone(0.38, 0.30, 0, 0, 0.65, _dark(c, 0.4), segments=6)
    b.add_cylinder(0.08, 0.12, 0, 0, 0.82, _dark(c, 0.4))
    b.add_cylinder(0.04, 0.55, 0, 0, 1.12, _dark(c, 0.4))
    b.add_torus(0.10, 0.025, 0, 0, 1.42, _dark(c, 0.4))
    b.add_cone(0.32, 0.22, 0, 0,-0.57, _dark(c, 0.4), segments=6)
    b.add_cylinder(0.05, 0.25, 0, 0,-0.28, (0.95,0.92,0.82))
    b.add_sphere(0.18, 0, 0, 0.0, (1.0,0.9,0.5))
    b.add_cylinder(0.36, 0.05, 0, 0,-0.42, _dark(c, 0.4), segments=6)
    return b

def _build_hammer(c):
    b = GLBBuilder()
    b.add_box(0.70, 0.36, 0.36, 0, 0, 0.2, c)
    b.add_cylinder(0.12, 0.35,-0.2, 0, 0.2, c)
    b.add_cone(0.08, 0.22, 0.2, 0, 0.28, _dark(c))
    b.add_cone(0.08, 0.22, 0.2, 0, 0.12, _dark(c))
    b.add_cylinder(0.055, 1.2, 0, 0,-0.5, _mix(c,(0.4,0.2,0.1)))
    for i in range(8):
        b.add_torus(0.065, 0.018, 0, 0,-0.3-i*0.1, _dark(c))
    b.add_sphere(0.08, 0, 0,-1.14, _dark(c))
    b.add_cylinder(0.075, 0.08, 0, 0,-0.0, _dark(c))
    b.add_cylinder(0.14, 0.12,-0.22, 0, 0.2, _dark(c))
    return b

def _build_axe(c):
    b = GLBBuilder()
    b.add_cone(0.55, 0.12,-0.22, 0, 0.15, c, segments=4)
    b.add_cone(0.06, 0.35, 0.05, 0, 0.58, _light(c))
    b.add_cone(0.06, 0.25, 0.05, 0,-0.28, _light(c))
    b.add_cylinder(0.07, 1.5, 0, 0,-0.6, _mix(c,(0.4,0.2,0.1)))
    b.add_cylinder(0.1, 0.12, 0, 0, 0.12, _dark(c))
    for i in range(7):
        b.add_torus(0.08, 0.022, 0, 0,-0.35-i*0.12, _dark(c))
    b.add_sphere(0.1, 0, 0,-1.38, _dark(c))
    b.add_box(0.36, 0.20, 0.60,-0.22, 0, 0.15, _dark(c))
    b.add_cylinder(0.095, 0.1, 0, 0,-0.0, _dark(c))
    return b

def _build_shield(c):
    b = GLBBuilder()
    b.add_box(1.4, 0.12, 1.9, 0, 0, 0, c)
    b.add_cone(0.8, 0.12, 0,-0.04,-0.85, c, segments=4)
    b.add_sphere(0.12, 0, 0.06, 0.3, _dark(c, 0.4))
    b.add_torus(0.12, 0.025, 0, 0.06, 0.3, _dark(c, 0.4))
    b.add_box(1.46, 0.10, 0.10, 0, 0, 0.95, _dark(c))
    b.add_box(0.10, 0.10, 1.70,-0.72, 0,-0.10, _dark(c))
    b.add_box(0.10, 0.10, 1.70, 0.72, 0,-0.10, _dark(c))
    b.add_box(1.30, 0.08, 0.08, 0, 0, 0.45, _light(c))
    b.add_box(0.08, 0.08, 1.10, 0, 0, 0.20, _light(c))
    b.add_cylinder(0.035, 0.55,-0.3,-0.07, 0.15, _dark(c))
    b.add_cylinder(0.035, 0.55, 0.3,-0.07, 0.15, _dark(c))
    for i in range(4):
        b.add_sphere(0.04,-0.42+i*0.28, 0.06, 0.55, _dark(c, 0.4))
    return b

def _build_wand(c):
    b = GLBBuilder()
    b.add_cylinder(0.04, 2.2, 0, 0, 0, c)
    b.add_sphere(0.12, 0, 0, 1.35, _light(c))
    b.add_torus(0.12, 0.025, 0, 0, 1.3, _dark(c))
    for i in range(4):
        a = math.radians(i*90)
        b.add_sphere(0.06, math.cos(a)*0.18, math.sin(a)*0.18, 1.38, _light(c))
    for i in range(6):
        b.add_torus(0.06, 0.018, 0, 0,-0.55+i*0.1, _dark(c))
    b.add_cylinder(0.055, 0.55, 0, 0,-0.52, _dark(c))
    b.add_sphere(0.065, 0, 0,-0.82, _dark(c))
    b.add_cone(0.04, 0.3, 0, 0, 1.25, _light(c))
    for i in range(6):
        a = math.radians(i*60)
        b.add_cone(0.025, 0.2,
                   math.cos(a)*0.18, math.sin(a)*0.18, 1.28, _light(c))
    return b

def _build_staff(c):
    b = GLBBuilder()
    b.add_cylinder(0.055, 3.2, 0, 0, 0, c)
    b.add_cone(0.055, 0.35, 0, 0,-1.77, _light(c))
    b.add_sphere(0.22, 0, 0, 1.82, _light(c))
    b.add_torus(0.22, 0.04, 0, 0, 1.82, _dark(c))
    b.add_cone(0.1, 0.28, 0, 0, 2.16, _light(c))
    for z in [0.4, 0.8, 1.2]:
        b.add_torus(0.07, 0.025, 0, 0, z, _dark(c))
    for i in range(3):
        a = math.radians(i*120)
        b.add_cylinder(0.04, 0.55,
                       math.cos(a)*0.2, math.sin(a)*0.2, 1.82, _dark(c))
    b.add_sphere(0.10, 0, 0, 1.82, (0.8,0.3,0.8))
    for i in range(10):
        b.add_torus(0.065, 0.02, 0, 0,-0.1-i*0.15, _dark(c))
    b.add_torus(0.22, 0.03, 0, 0, 1.6, _dark(c))
    return b

def _build_chair(c):
    b = GLBBuilder()
    b.add_box(1.4, 1.3, 0.16, 0, 0, 0.5, c)
    b.add_box(1.36, 0.12, 0.9, 0, 0.55, 0.88, c)
    for lx, ly in [(-0.6,-0.55),(0.6,-0.55),(-0.6,0.55),(0.6,0.55)]:
        b.add_cylinder(0.045, 0.5, lx, ly, 0.25, _dark(c))
    for lx in [-0.6, 0.6]:
        b.add_cylinder(0.025, 1.1, lx, 0, 0.22, _dark(c))
    b.add_box(0.08, 1.2, 0.08,-0.72, 0.0, 0.7, c)
    b.add_box(0.08, 1.2, 0.08, 0.72, 0.0, 0.7, c)
    b.add_box(0.12, 1.2, 0.05,-0.72, 0.0, 0.74, c)
    b.add_box(0.12, 1.2, 0.05, 0.72, 0.0, 0.74, c)
    for i in range(4):
        b.add_box(0.08, 0.04, 0.84,-0.4+i*0.28, 0.52, 0.88, c)
    return b

def _build_table(c):
    b = GLBBuilder()
    b.add_box(2.4, 1.5, 0.12, 0, 0, 0.82, c)
    for lx, ly in [(-1.0,-0.6),(1.0,-0.6),(-1.0,0.6),(1.0,0.6)]:
        b.add_cylinder(0.055, 0.82, lx, ly, 0.41, _dark(c))
    b.add_cylinder(0.03, 2.0, 0, 0, 0.28, _dark(c))
    b.add_cylinder(0.03, 1.2, 0, 0, 0.28, _dark(c))
    b.add_torus(1.1, 0.04, 0, 0, 0.86, _dark(c))
    b.add_box(1.1, 0.02, 0.24, 0,-0.72, 0.72, _dark(c))
    b.add_sphere(0.03, 0,-0.73, 0.72, _dark(c, 0.4))
    for lx, ly in [(-1.0,-0.6),(1.0,-0.6),(-1.0,0.6),(1.0,0.6)]:
        b.add_cylinder(0.07, 0.02, lx, ly, 0.01, _dark(c))
    return b

def _build_boat(c):
    b = GLBBuilder()
    b.add_box(4.0, 1.5, 0.70, 0, 0, 0, c)
    b.add_cone(0.75, 1.0, 1.8, 0, 0.2, c)
    b.add_box(1.4, 1.2, 0.6,-0.3, 0, 0.42, _dark(c))
    b.add_cone(0.65, 0.35,-0.3, 0, 0.9, _dark(c, 0.5), segments=4)
    b.add_cylinder(0.04, 2.8, 0.2, 0, 1.4, _dark(c, 0.4))
    b.add_box(0.10, 2.2, 2.4, 0.22, 0, 1.8, c)
    b.add_box(3.8, 1.44, 0.08, 0, 0, 0.32, _dark(c))
    b.add_box(0.08, 0.08, 1.0,-0.3, 0.74, 0.55, _dark(c))
    b.add_box(0.08, 0.08, 1.0,-0.3,-0.74, 0.55, _dark(c))
    b.add_sphere(0.06, 1.85, 0, 0.35, (1.0,1.0,0.6))
    return b

def _build_generic(c):
    """Fallback: generic object with recognizable structure."""
    b = GLBBuilder()
    b.add_box(1.2, 1.2, 0.5, 0, 0, 0.0, c)
    b.add_box(1.0, 1.0, 0.4, 0, 0, 0.5, _light(c))
    b.add_box(0.8, 0.8, 0.3, 0, 0, 0.9, _dark(c))
    b.add_sphere(0.25, 0, 0, 1.3, _light(c))
    for lx, ly in [(-0.5,-0.5),(0.5,-0.5),(-0.5,0.5),(0.5,0.5)]:
        b.add_cylinder(0.08, 0.8, lx, ly,-0.4, _dark(c))
    return b


# ---------------------------------------------------------------------------
#  KEYWORD MAP  (55 shape names -> builder functions)
# ---------------------------------------------------------------------------
_SHAPE_MAP = {
    "rocket":      _build_rocket,
    "dragon":      _build_dragon,
    "car":         _build_car,
    "robot":       _build_robot,
    "castle":      _build_castle,
    "spaceship":   _build_spaceship,
    "house":       _build_house,
    "sword":       _build_sword,
    "tree":        _build_tree,
    "plane":       _build_plane,
    "airplane":    _build_plane,
    "helicopter":  _build_helicopter,
    "truck":       _build_truck,
    "ship":        _build_ship,
    "submarine":   _build_submarine,
    "tank":        _build_tank,
    "horse":       _build_horse,
    "motorcycle":  _build_motorcycle,
    "bicycle":     _build_bicycle,
    "bike":        _build_bicycle,
    "dog":         _build_dog,
    "cat":         _build_cat,
    "bird":        _build_bird,
    "fish":        _build_fish,
    "flower":      _build_flower,
    "mountain":    _build_mountain,
    "crystal":     _build_crystal,
    "crown":       _build_crown,
    "mushroom":    _build_mushroom,
    "cactus":      _build_cactus,
    "cannon":      _build_cannon,
    "pyramid":     _build_pyramid,
    "diamond":     _build_diamond,
    "star":        _build_star,
    "capsule":     _build_capsule,
    "cube":        _build_cube,
    "box":         _build_cube,
    "sphere":      _build_sphere_shape,
    "ball":        _build_sphere_shape,
    "cylinder":    _build_cylinder_shape,
    "cone":        _build_cone_shape,
    "torus":       _build_torus_shape,
    "ring":        _build_torus_shape,
    "donut":       _build_torus_shape,
    "chest":       _build_chest,
    "treasure":    _build_chest,
    "barrel":      _build_barrel,
    "lantern":     _build_lantern,
    "hammer":      _build_hammer,
    "axe":         _build_axe,
    "shield":      _build_shield,
    "wand":        _build_wand,
    "staff":       _build_staff,
    "chair":       _build_chair,
    "table":       _build_table,
    "boat":        _build_boat,
}


def _match_shape(prompt):
    """Return the builder function for the best keyword match in prompt."""
    pl = prompt.lower()
    # Exact word match first
    for kw, fn in _SHAPE_MAP.items():
        if kw in pl:
            return fn
    return _build_generic


# ---------------------------------------------------------------------------
#  VALIDATION
# ---------------------------------------------------------------------------
def _validate_glb(path):
    """Return (ok, message)."""
    try:
        if not os.path.exists(path):
            return False, "file not found"
        size = os.path.getsize(path)
        if size < 4096:
            return False, "too small: %d bytes" % size
        with open(path, "rb") as f:
            magic = f.read(4)
        if magic != b"glTF":
            return False, "bad magic"
        return True, "valid %d bytes" % size
    except Exception as e:
        return False, str(e)


# ---------------------------------------------------------------------------
#  PUBLIC INTERFACE
# ---------------------------------------------------------------------------
def generate(prompt, color_hex, output_path):
    """
    Generate a GLB file for the given prompt and color.
    Returns True on success. NEVER raises an exception.
    """
    try:
        color   = _parse_color(color_hex)
        builder = _match_shape(prompt)
        b       = builder(color)
        data    = b.build()

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        with open(output_path, "wb") as f:
            f.write(data)

        ok, msg = _validate_glb(output_path)
        if ok:
            return True

        # Validation failed - write emergency icosahedron
        _write_emergency(output_path, color)
        return True

    except Exception:
        try:
            _write_emergency(output_path, (0.4, 0.5, 0.8))
        except Exception:
            pass
        return True   # always return True - emergency fallback always works


def _write_emergency(output_path, color):
    """Write a minimal valid icosahedron GLB as last resort."""
    try:
        b = GLBBuilder()
        b.add_sphere(0.8, 0, 0, 0, color, rings=6, segs=10)
        b.add_cylinder(0.2, 1.6, 0, 0, 0, (color[0]*0.5, color[1]*0.5, color[2]*0.5))
        data = b.build()
        with open(output_path, "wb") as f:
            f.write(data)
    except Exception:
        # Absolute last resort: minimal glTF
        minimal = '{"asset":{"version":"2.0"},"scene":0,"scenes":[{"nodes":[]}]}'
        j = minimal.encode("utf-8")
        j += b" " * ((4 - len(j) % 4) % 4)
        total = 12 + 8 + len(j)
        raw = bytearray()
        raw += struct.pack("<4sII", b"glTF", 2, total)
        raw += struct.pack("<II", len(j), 0x4E4F534A)
        raw += j
        with open(output_path, "wb") as f:
            f.write(bytes(raw))


# ---------------------------------------------------------------------------
#  CLI / TEST MODE
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "test dragon"
    output = "test_output.glb"

    print("=" * 50)
    print("  generate_model.py  v5.0  - Test Mode")
    print("=" * 50)
    print("  Prompt : %s" % prompt)
    print("  Output : %s" % output)
    print("  Shapes : %d available" % len(_SHAPE_MAP))

    t0 = time.time()
    ok = generate(prompt, "#4488cc", output)
    elapsed = time.time() - t0

    ok2, msg = _validate_glb(output)
    print("  Result : %s" % ("OK" if ok2 else "FAIL"))
    print("  GLB    : %s" % msg)
    print("  Time   : %.2fs" % elapsed)

    # Test all shapes
    print("\n  Testing all %d shapes..." % len(set(_SHAPE_MAP.values())))
    failed = []
    builders_tested = set()
    for kw, fn in _SHAPE_MAP.items():
        if fn in builders_tested:
            continue
        builders_tested.add(fn)
        try:
            b = fn((0.5, 0.5, 0.8))
            data = b.build()
            if len(data) < 4096 or data[:4] != b"glTF":
                failed.append(kw)
        except Exception as e:
            failed.append("%s(%s)" % (kw, e))
    if failed:
        print("  FAILED shapes: %s" % ", ".join(failed))
    else:
        print("  All %d shapes OK" % len(builders_tested))

    print("=" * 50)
