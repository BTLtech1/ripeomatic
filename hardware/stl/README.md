# Printing and assembly (v1)

STLs exported from the Fusion 360 design `BTL Ripe-O-Matic` (Default Project) and **already rotated into print orientation** (`tools/orient_stl.py`): drop them on the plate as they are. Everything fits a 180 × 180 mm bed (Bambu A1 mini). Designed for 0.4 mm nozzle, 0.2 mm layers.

## Print list

| File | Material | How it sits | Settings | ~Time |
|---|---|---|---|---|
| `base.stl` | PLA/PETG | Flat | 3 walls, 15 % infill, no supports. The four keyhole studs for the two boxes print with it | 3–4 h |
| `driver-box.stl` | PLA/PETG | Flat, keyhole floor down | 2 walls, 10 %, no supports | 45 min |
| `driver-box-lid.stl` | PLA/PETG | Upside down: flat top on the bed, pegs up | 2 walls, 10 %, no supports | 20 min |
| `esp32-case/esp32-case-base.stl` | PLA/PETG | As supplied (floor down) | 2 walls, 10 %, no supports | 1 h |
| `esp32-case/esp32-case-lid-firm-key.stl` | PLA/PETG | As supplied (top down) | 2 walls, 10 %, no supports | 25 min |
| `esp32-case/esp32-case-keycap.stl` + one `mx-adapter` | any | As supplied | default. Print the 1.30 adapter first; 1.25 / 1.35 are looser / tighter on the keycap stem | 10 min |
| `u-yoke.stl` | PLA/PETG | Standing on its cross-bar | 4 walls, 20 %, **supports: on build plate only** (for the servo boss, which overhangs the arm) | 50 min |
| `nest.stl` | PLA/PETG | Upside down: the flat top edge on the bed, the shell's back up | 3 walls, 10 %, no supports. The front lip overhangs at ~45°, which is fine | 2 h |
| `sled.stl` | PETG preferred | Standing on its motor end (already oriented): the nut thread prints vertical like the screw's | 4 walls, 30 %, **no supports** | 1 h |
| `lead-screw-TR10x2.stl` | PETG preferred | Standing, socket end down | 100 % infill or 6 walls, 0.12 mm layers for a smoother thread, **brim** | 40 min |
| `blade.stl` | PLA | Flat on its 12 mm face, stem up | 100 % infill. The magnet pocket faces the bed | 10 min |
| `thumbscrew-knob.stl` | any | Flat | default | 5 min |
| `pad-TPU.stl` | TPU 95A | Socket down, dome up | 2 walls, 15 % | 10 min |
| `nest-liner-TPU.stl` | TPU 95A (or skip: use 3 mm craft foam) | Upside down, same as the nest | 2 walls, vase-ish, **brim** (it stands on a 2 mm edge) | 1.5 h |
| `servo-horn-v2.stl` | any | Flat | default | 5 min — **v2 only** |

Print the base and the sled first and test the slide before printing the rest. If the sled binds, scale it 99.5 % in X/Y or sand the lips. The sled's nut is threaded only for its first 10 mm at the motor end (the rest is a Ø10.8 clearance bore), since a 50 mm long printed nut got tighter and tighter as the screw went in. If the screw still binds, reprint the screw with an X–Y contour compensation of −0.15 mm (Bambu Studio: the object's *Quality → Precision* settings) rather than scaling it, so the motor socket stays 5.0 mm; 0.12 mm layers and a random seam help too.

**The boards live in two boxes** that slide onto keyhole studs on the base: the ESP32 in BTL's *ESP32 case v6* (`esp32-case/`, with the keycap on the lid for the BOOT button), the ULN2003 in the driver box. Stud and keyhole dimensions, positions and how the boxes go on: [`../keyhole-mount.md`](../keyhole-mount.md). Any box with those two keyholes fits either spot.

If you re-export from Fusion, run `python3 tools/orient_stl.py` afterwards to put the new files back into print orientation.

## Hardware

| Qty | Item | Where |
|---|---|---|
| 2 | M4 × 8 (or M3 × 8 with nuts) | 28BYJ-48 ears (35 mm apart) into the motor plate; plate holes are 3.5 mm so M4 self-taps |
| 4 | M3 × 6 | U-yoke into the base, from underneath (holes 2.5 mm, self-tap) |
| 1 | M3 × 10 | Blade clamp, from the front of the riser, self-taps into the block |
| 2 | M5 × 20 hex-head (or socket) | Nest pins. One gets the printed knob on its head; one plain |
| 1 | 3 × 2 mm magnet | Blade back face, in the shallow pocket at pad height |
| 1 | SS49E hall sensor | Post front pocket, legs out the top |

Each box goes on the same way: set it over its pair of studs 9 mm toward the nest from its final spot, push it toward the motor end until it clicks (the cone under each stud head pulls it flat, two little nibs in the slots hold it), lift the lid, put the board in. Nothing on the base needs to match your particular boards; only the box does. Details: [`../keyhole-mount.md`](../keyhole-mount.md).

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
10. Boxes: click the ESP32 case onto the studs on the board side (USB opening toward the motor end) and the driver box onto the studs on the other side. ESP32 on its pins in the case, ULN2003 on the ledges in the driver box.
11. Wire per `../README.md` (the 0.1 µF capacitor on the hall sensor output is optional): the six driver wires leave the driver box through its motor-end notch, go round the end of the base and enter the ESP32 case through the USB opening next to the plug; the hall wires use the same opening. The motor's ribbon plugs into the ULN2003 through the driver box's channel-side notch. Snap both lids on; keycap on the ESP32 lid.

## v2

Servo boss, M2 holes and the horn pocket are already in the yoke. Add the SG90, press the servo horn onto the bolt head on that side, and plug the servo into GPIO 25.
