# Printable lead-screw thread ("V45")

A thread profile for a lead screw and nut that are **both 3D printed standing up** (axis vertical). It replaces the TR10×2 trapezoidal thread from the first build. Status: the test screw and all three test nuts work and feel good (first build, Nov 2026). The full screw through the full sled is the next test. Until that passes, the Fusion design still has the TR thread, and the V45 parts live in [`stl/v45/`](stl/v45/), made by [`../tools/v45_thread.py`](../tools/v45_thread.py).

## Why TR10×2 failed

A trapezoidal (ACME-style) thread has a 30° included angle, so each flank is only **15° off flat**. Printed with the axis vertical, the underside of every ridge is a ~75° overhang. Each ring droops, which matters most inside the nut, where cooling air barely reaches. The first sled's nut came out as a stack of loose loops. The screw started fine and jammed about halfway in, because a nut threaded along its full 50 mm adds friction with every millimetre engaged and needs the screw perfectly straight.

Printing the nut lying down (axis horizontal) doesn't fix it either: the top of the bore sags.

## The V45 profile

| | Value | Why |
|---|---|---|
| Form | symmetric V, **90° included angle** (each flank 45° off the axis) | Every flank is a 45° overhang or better, so it prints cleanly with the axis vertical, inside and out |
| Pitch / lead | **2.0 mm**, single start, right hand | Same lead as TR10×2, so the firmware's `steps_per_mm` (2048) doesn't change |
| Screw crest Ø | **9.9 mm** (radius 4.95) | Matches what the TR screw printed at |
| Thread depth | **0.8 mm** radial | Screw root Ø 8.3 |
| Crest flat / root flat | **0.2 mm** axial each | 0.2 + 0.8 + 0.2 + 0.8 = 2.0 pitch. The flats stop the tips printing as mushy points |
| Nut | the screw profile offset **outward by 0.4 mm radially** | Nut crest Ø 9.1, nut root Ø 10.7. 0.4 radial on a 45° flank = **0.28 mm normal clearance** |
| Nut length | **10 mm** threaded (5 turns), at the motor end of the sled | Rest of the bore is a Ø10.8 clearance hole. Short engagement = little friction, and it doesn't need the screw perfectly straight |
| Nut entry | **45° countersink**, from Ø10.9 at the face | Self-supporting at the bed. A stepped (counterbored) lead-in printed as a loose bridge and was worse than nothing |

Trade-off: the 45° flanks wedge more than a 15° TR flank, so the thread needs roughly a third more torque for the same push. The 28BYJ-48 has far more than the ~2.5 N measuring force needs, so it doesn't matter here. Backlash doesn't matter either, because every reading presses in one direction.

## Clearance test

`v45-test-screw-30mm.stl` + `v45-test-nuts.stl`: three 10 mm nuts at **0.3 / 0.4 / 0.5 mm** radial clearance (1 / 2 / 3 notches on the rim). Print them standing, as supplied (about 20 minutes together).

First build result: **all three turned smoothly**. 0.4 (the middle one) is used for the real sled, because a big part's nut cools slower than a small test nut and tends to print a little tighter.

Printer for that result: a Bambu Lab printer, PLA, Bambu Studio's usual settings (exact layer height not recorded). Add your own result to this file if it differs.

If your printer is tighter or looser, print the test, pick the tightest nut that turns freely by hand, and set `CLEAR` in `tools/v45_thread.py` to it.

## Files

| File | What | Print |
|---|---|---|
| `stl/v45/v45-lead-screw.stl` | 90 mm screw, double-D socket for the 28BYJ-48 shaft (Ø5.2, flats 3.2 apart, 10 deep) | standing, socket down, brim |
| `stl/v45/v45-sled.stl` | the sled with its nut replaced (0.4 clearance) | standing on its motor end, no supports |
| `stl/v45/v45-test-screw-30mm.stl` | short screw for the clearance test | standing |
| `stl/v45/v45-test-nuts.stl` | 0.3 / 0.4 / 0.5 test nuts | as supplied |

Regenerate everything: `python3 tools/v45_thread.py hardware/stl/v45` (needs `pip install build123d bd_warehouse manifold3d trimesh`). The thread itself is `bd_warehouse.thread.Thread(apex_radius, apex_width, root_radius, root_width, pitch, length)`: external `(4.95, 0.2, 4.15, 1.8, 2.0, L)`, internal `(4.15+c, 0.2, 4.95+c, 1.8, 2.0, L)` for radial clearance `c`.

## Rules of thumb (for any printed thread printed axis-vertical)

- Flanks no flatter than 45° off the axis. Standard ISO metric (60° included, 30° flanks) is borderline; TR/ACME (15° flanks) and square threads droop.
- Put the clearance in the model (0.3–0.5 mm radial for a 0.4 nozzle), not in slicer scaling: scaling also shrinks sockets and holes you didn't mean to change.
- Keep the nut short (4–6 turns) unless it carries real load.
- No stepped counterbores at the bed face: use a 45° countersink.
