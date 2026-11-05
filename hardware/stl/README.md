# Printing and assembly (v1)

STLs exported from the Fusion 360 design `BTL Ripe-O-Matic` (Default Project). Everything fits a 180 × 180 mm bed (Bambu A1 mini). Designed for 0.4 mm nozzle, 0.2 mm layers, no supports.

## Print list

| File | Material | Orientation | Settings | ~Time |
|---|---|---|---|---|
| `base.stl` | PLA/PETG | As is (flat) | 3 walls, 15 % infill | 3–4 h |
| `board-cover.stl` | PLA/PETG | **Open side up** (roof on the bed) | 2 walls, 10 % | 20 min |
| `u-yoke.stl` | PLA/PETG | **Lay flat** on the big face (the U lying down) | 4 walls, 20 % | 45 min |
| `nest.stl` | PLA/PETG | **Opening up**, like a cup (rotate so the flat cut face is on top) | 3 walls, 10 %, 3 mm wall is mostly perimeters | 2 h |
| `sled.stl` | PETG preferred | As is (runner pads down) | 4 walls, 30 % | 1 h |
| `lead-screw-TR10x2.stl` | PETG preferred | Standing, socket end down | 100 % infill or 6 walls, 0.12 mm layers for a smoother thread | 40 min |
| `blade.stl` | PLA | **Flat** on its 12 mm face (thickness in Z, stem pointing up) | 100 % infill | 10 min |
| `thumbscrew-knob.stl` | any | Flat | default | 5 min |
| `pad-TPU.stl` | TPU 95A | Dome down or socket down | 2 walls, 15 % | 10 min |
| `nest-liner-TPU.stl` | TPU 95A (or skip: use 3 mm craft foam) | Opening up, same as the nest | 2 walls, vase-ish | 1.5 h |
| `servo-horn-v2.stl` | any | Flat | default | 5 min — **v2 only** |

Print the base and the sled first and test the slide before printing the rest. If the sled binds, scale it 99.5 % in X/Y or sand the lips. If the lead screw won't turn in the sled's nut, print the screw at 98 % X/Y.

## Hardware

| Qty | Item | Where |
|---|---|---|
| 2 | M4 × 8 (or M3 × 8 with nuts) | 28BYJ-48 ears (35 mm apart) into the motor plate; plate holes are 3.5 mm so M4 self-taps |
| 4 | M3 × 6 | U-yoke into the base, from underneath (holes 2.5 mm, self-tap) |
| 1 | M3 × 10 | Blade clamp, from the front of the riser, self-taps into the block |
| 1 | M3 × 8 | Board cover, from underneath the base into the cover's boss (hole 2.5 mm, self-tap) |
| 2 | M5 × 20 hex-head (or socket) | Nest pins. One gets the printed knob on its head; one plain |
| 1 | 3 × 2 mm magnet | Blade back face, in the shallow pocket at pad height |
| 1 | SS49E hall sensor | Post front pocket, legs out the top |

Both boards slide into printed rails, no screws: the ESP32 from the nest end of its cradle, the ULN2003 from the edge of the base. **Measure your boards before printing the base.** The rails are cut for a 28.3 mm wide ESP32 and a 32 mm wide ULN2003 (some ULN2003 boards are 30 mm). The widths are single values in the base sketches.

**Slide the ESP32 in with its USB port toward the nest end** (the open end of the cradle). The cover's cable notch is on that end.

The board cover is a 1.2 mm lid, 104 × 43 × 23 mm, that drops over both cradles. Vent slots in the roof, a 1.4 mm gap along the inner edge for the motor ribbon and the hall sensor wires, a notch for the USB cable at the nest end, a tab at the same end that hooks into the base's window, and a boss at the other end for one M3 from below. Lift the tab end, hook it in, lower the far end, one screw.

## Assembly order

1. Press the motor's shaft boss through the plate hole from behind and screw the ears down.
2. Slide the sled into the channel from the nest end, runner pads down.
3. Thread the lead screw through the sled's nut from the nest end, pass its socket through the end-stop hole and push it onto the motor shaft (D-socket; a drop of glue optional).
4. Drop the blade into the riser slot and fit the clamp screw from the front. Glue the magnet in its pocket on the blade's back, pole marked.
5. Glue the hall sensor in the post pocket, legs up; wire it.
6. Press the pad onto the stem.
7. Fit the liner (or foam) into the nest.
8. Set the U-yoke into its recess and screw it from below.
9. Hang the nest between the arms: M5 bolt through each arm into the nest ear. Fit the knob on one bolt head and snug it so the nest rests on the stop tab.
10. Boards: slide the ESP32 (USB toward the nest) and the ULN2003 into their rails. Wire per `../README.md`. The 0.1 µF capacitor on the hall sensor output is optional. Route the motor ribbon and the hall wires out through the gap on the cover's inner edge.
11. Hook the cover's tab into the base window at the nest end, lower it over the boards, and fit the M3 × 8 from below.

## v2

Servo boss, M2 holes and the horn pocket are already in the yoke. Add the SG90, press the servo horn onto the bolt head on that side, and plug the servo into GPIO 25.
