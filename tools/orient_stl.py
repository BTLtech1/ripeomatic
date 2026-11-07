#!/usr/bin/env python3
"""Rotate the Fusion exports in hardware/stl/ into print orientation, resting on Z = 0.

Fusion exports the assembly as modelled (X = press axis, Y = up, Z = across), so
every part lands on its side in a slicer. This puts each one the way the print
guide says to print it, with its bottom on the bed and centred on the plate, and
rewrites the file in place.

    python3 tools/orient_stl.py            # all parts
    python3 tools/orient_stl.py base.stl   # one part
    python3 tools/orient_stl.py --check    # just report orientation, don't write

Run it on fresh Fusion exports only: the files in hardware/stl/ are already
oriented, so running it on them again (with or without --check) turns them
on their side.

"down" below is the model-space axis that should face the bed. "auto" tries both
signs of that axis and keeps whichever puts more flat area on the bed.
"""
import sys
import pathlib
import numpy as np
import trimesh

ROOT = pathlib.Path(__file__).resolve().parent.parent
STL = ROOT / "hardware" / "stl"

# part -> model axis that goes DOWN (toward the bed)
DOWN = {
    "base.stl":              (0, -1, 0),   # flat, bottom face down
    "sled.stl":              (0, -1, 0),   # runner pads down
    "u-yoke.stl":            (0, -1, 0),   # standing on its cross-bar (the servo boss is wider than the arm, so it can't lie flat)
    "nest.stl":              (0, +1, 0),   # upside down: the flat top-cut face on the bed, the shell's back is a dome on top
    "nest-liner-TPU.stl":    (0, +1, 0),
    "lead-screw-TR10x2.stl": (-1, 0, 0),   # standing, motor socket (the -x end) down
    "blade.stl":             (-1, 0, 0),   # flat on its 12 mm face, stem pointing up
    "pad-TPU.stl":           (-1, 0, 0),   # socket down, dome up
    "thumbscrew-knob.stl":   "auto-z",     # flat
    "servo-horn-v2.stl":     "auto-z",     # flat
}


def rotation_taking(axis_down):
    """Proper rotation that maps the model-space unit vector `axis_down` to print -Z."""
    a = np.asarray(axis_down, dtype=float)
    a /= np.linalg.norm(a)
    return trimesh.geometry.align_vectors(a, np.array([0.0, 0.0, -1.0]))


def bed_area(mesh):
    """Area of faces lying flat on the lowest plane (what the first layer will be)."""
    z0 = mesh.bounds[0][2]
    normals = mesh.face_normals
    down = normals[:, 2] < -0.999
    low = np.all(np.abs(mesh.vertices[mesh.faces][:, :, 2] - z0) < 0.05, axis=1)
    return float(mesh.area_faces[down & low].sum())


def orient(path, write=True):
    m = trimesh.load(path, force="mesh")
    spec = DOWN[path.name]
    candidates = []
    if isinstance(spec, str):
        axis = {"auto-x": (1, 0, 0), "auto-y": (0, 1, 0), "auto-z": (0, 0, 1)}[spec]
        candidates = [tuple(axis), tuple(-np.array(axis))]
    else:
        candidates = [spec]
    best = None
    for c in candidates:
        mm = m.copy()
        mm.apply_transform(rotation_taking(c))
        area = bed_area(mm)
        if best is None or area > best[1]:
            best = (mm, area, c)
    mm, area, c = best
    # rest on the bed, centred on the plate
    lo, hi = mm.bounds
    mm.apply_translation([-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]])
    ext = mm.extents
    print(f"{path.name:26s} down={str(c):14s} footprint {ext[0]:6.1f} x {ext[1]:6.1f} mm, height {ext[2]:5.1f} mm, bed contact {area:7.0f} mm^2"
          f"{'' if mm.is_watertight else '  NOT WATERTIGHT'}")
    if write:
        mm.export(path)
    return mm


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    write = "--check" not in sys.argv
    names = args or sorted(DOWN)
    for n in names:
        p = STL / n
        if not p.exists():
            print(f"{n}: missing")
            continue
        if n not in DOWN:
            print(f"{n}: no orientation rule in DOWN")
            continue
        orient(p, write)


if __name__ == "__main__":
    main()
