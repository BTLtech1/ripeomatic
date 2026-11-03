# Hardware

Design goal: **as cheap and as 3D-printable as possible.** A low, horizontal caliper-style press, about 7 cm tall. Every structural and mechanical part is printed, including the lead screw, the guide channel, the force-sensing blade and the avocado nest. No bearings, no metal load cell, no power brick.

Interactive 3D assembly (orbit, explode, simulated reading): https://claude.ai/artifact/XxPCr4hXQnpZJonZaod3w8

## Layout

```
 side view (press axis left → right)

  motor ─ screw ────▶ [sled] ─ blade ─ pad ─▶ ( avocado )╮ nest
  └──────── guide channel in base ─────────┘  yoke arm ┤o── pin at fruit centre
 ═══════════════════════ base plate ═══════════════════════
```

The avocado lies in a printed half-shell nest with a soft liner, opening toward the pad. The sled drives a soft pad on a short stem into the fruit's side, pushing it into the curved back of the nest. Pressing sideways means the reaction spreads over the nest's whole back wall instead of cradle pins, the whole thing stays low, and gravity acts perpendicular to the measurement. The nest hangs between two yoke arms on M5 pins at the height of the pad, so the pivot axis runs through the avocado's centre of gravity. In v1 the pins are tight; in v2 a servo on one pin swings the nest back to drop a ripe avocado into a bowl below.

## Printed parts

All PLA or PETG unless noted. Roughly 150 g of filament total.

| Part | Qty | Print notes |
|---|---|---|
| Base plate | 1 | Flat, ~185 × 150 × 6 mm. One print carries the guide channel (two rails with inward lips), motor plate, end stop, yoke arms and board mounts. The nest hangs clear of the base, so nothing else is needed under it. |
| Avocado nest | 1 | Half-shell shaped like a half avocado. Liner-surface cavity 80 × 80 × 120 mm (takes up to an 80 mm fruit; a 55 mm one just sits deeper), shell wall 3 mm outside a 3 mm liner, with a low front lip and a Ø8 mm trunnion boss on each end at equator height, the pin bore 3 mm behind the cavity centre. Print bowl-up like a cup, no supports. |
| Yoke arms | 2 | ~16 × 64 × 6 mm uprights either side of the nest with an M5 bore at pad height. Part of the base print if your bed allows; otherwise screw on. |
| Nest liner | 1 | 3 mm TPU shell to match the cavity, or craft foam glued in. The fruit only needs to touch at the back and bottom, so one liner fits all sizes. |
| Lead screw | 1 | Ø8 mm, 3 mm pitch, ~90 mm, printed vertically. D-socket at one end pushes onto the 28BYJ-48 shaft (no coupler). Push reaction pulls the screw toward the motor, so no retaining flange is needed. Only ~40 mm of sled travel is needed: 10 mm loading clearance in front of the biggest fruit the nest takes, ~20 mm for the spread in where smaller fruit settle, and the squish. |
| Sled | 1 | One print: ~50 × 14 × 40 mm block with lips that ride under the channel rails, four small runner pads underneath, the nut thread running its full length, a post at the back and a short sensor bridge on top. 50 mm long on purpose: the pad pushes ~50 mm above the channel, and a longer sled halves the tipping forces on the rails. The screw's free end rides inside the sled, so no far bracket. |
| Blade (flexure) | 1 | 3 × 12 × 42 mm PLA, standing vertical from the sled, thin along the push direction. About 3 N/mm. Printed flat; glues or screws into a slot on the sled. Pocket for a 3 × 2 mm magnet on its back face near the tip. |
| Pad | 1 | 16 mm dome on a 12 mm stem printed with the blade, at avocado-equator height, so it reaches 20 mm ahead of the sled and small fruit is still in reach. TPU dome if you have it; otherwise a pencil eraser cap or a stick-on silicone bumper on a PLA disc. |
| Hinge thumbscrew | 1 | Printed M5 knob for one side; a plain M5 bolt and nut on the other. |

Fallback if the printed lead screw is rough: an **M8 threaded rod and nut** from the hardware store (~$1.50), 1.25 mm pitch.

## Bought parts

| Qty | Part | Notes | Rough cost |
|---|---|---|---|
| 1 | 28BYJ-48 stepper + ULN2003 driver | Sold as a pair. 5 V, geared 64:1, 2048 steps/turn. | $2–4 |
| 1 | ESP32 dev board | Any ESP32-WROOM board (an ESP8266 D1 mini or ESP32-C3 also works). | $3–6 |
| 1 | SS49E linear hall sensor | Sold in 10- or 20-packs. 49E / OH49E clones work the same. | $4–6 / pack |
| 1 | Neodymium magnet, 3 × 2 mm | The size in every "magnets for 3D printing" kit. Glue to the back of the blade tip. | ~$3 / 50 |
| ~8 | M3 screws | Motor ears, blade clamp. Or design printed dovetails/snap fits. | ~$1 |
| 2 | M5 × 16 bolt + nut | Nest trunnion pins. One can be a printed thumbscrew. | ~$0.40 |
| 1 | USB cable + phone charger | Powers everything at 5 V. | have |

**Total: about $15–20** plus filament.

### Optional upgrade

If the printed blade drifts too much (PLA creeps and softens a little when warm), a **1 kg bar load cell + HX711** (~$7) mounts horizontally on the sled in place of the blade, magnet and hall sensor.

## Why these choices

- **Horizontal, not a tower.** Low and stable, fits under a cabinet, loads from the top, and the three frame parts of the tower design collapse into one flat base print.
- **Nest, not rails and a wall.** The half-shell spreads the reaction over the whole back of the fruit, self-centres any size, looks like what it is, and the liner takes up the size difference. A smaller avocado sits a little lower, so the pad presses slightly above its equator; that is the same with any passive cradle and the calibration absorbs it.
- **Trunnion hinge through the fruit's centre.** The pivot axis is at pad height, so the pad's push passes straight through it and a reading cannot tip the nest. The loaded nest is nearly balanced, so in v2 a $2 micro servo on one pin can swing it backward to drop a ripe avocado. Put the axis 3–5 mm behind the cavity centre so the loaded nest rests forward against a small stop on its own. For the drop to work, the base should end just behind the nest, or the machine sits at a shelf edge with a bowl below. The nest never touches the floor beneath it, so it can swing freely.
- **28BYJ-48.** The cheapest stepper there is, and it runs on USB 5 V. Gear backlash doesn't matter because every measurement moves in one direction (toward the fruit, through contact, to the force cap). It is slow (about 0.5 mm/s), so a full reading takes 1–2 minutes. That's fine twice a day.
- **Printed lead screw on the motor shaft, not a rack and pinion.** One turn = 3 mm, so one of the motor's 2048 steps = 0.0015 mm, and the thread multiplies the little motor's torque into 10+ N of push with smooth, stiction-free creep near contact. It also holds position with the motor off. A rack and pinion would be 10× faster but gives only 3–7 N from this motor, back-drives under load, and loads the sled sideways, which makes the slow creep jerky. If the 80 s reading feels slow, print the screw as a 2-start thread (6 mm lead) rather than switching to gears. In this orientation the push reaction seats the screw on the shaft instead of pulling it off. PETG wears better than PLA for the thread and nut; add a dab of grease.
- **Printed channel, no posts or bearings.** The sled rides between two rails printed into the base, with ~0.3 mm clearance and lips that stop it lifting. Sideways play doesn't affect the along-axis measurement, and channel friction never reaches the force reading (that's measured at the blade), it only loads the motor. The pad pushes ~50 mm above the channel, so the 2.5 N push becomes a tipping couple of a few newtons on the rails; dry PLA-on-PLA that's ~2 N of drag with the 50 mm sled, ~0.7 N with PTFE plumber's tape on the rails or a dab of grease. The thing to avoid is stick-slip during the slow creep, hence the runner pads, the clearance and the lube. If a print binds anyway, two 8 mm smooth rods with printed bushings fit the same footprint.
- **Vertical printed blade + hall sensor instead of a load cell.** A 3 mm thick blade standing up from the sled bends about 0.75 mm at the 2.5 N cap. A 3 × 2 mm magnet on its back face sits ~1.5 mm from an SS49E on the sled's bridge; the ESP32's ADC reads the gap. Standing vertical, the blade carries its own weight along its length, so there is no gravity sag to drift. Calibrate once with coins (a US nickel is exactly 5.000 g).
- **Sled can run under the fruit.** The pedestal is clear between the sled channel and the nest, and the far screw bracket sits just past the sled's longest travel, so a 55 mm avocado is still reachable.
- **No home switch.** The sled homes by running gently back against the printed end stop; the 28BYJ-48 just slips a few steps.
- **All 5 V.** The ESP32's 5 V pin powers the ULN2003. No PD trigger, no buck converter.

## Wiring

| From | To |
|---|---|
| ESP32 5V (VIN), GND | ULN2003 VCC, GND |
| ESP32 GPIO 16, 17, 18, 19 | ULN2003 IN1–IN4 |
| ULN2003 motor header | 28BYJ-48 plug |
| ESP32 3V3, GND | SS49E pins 1, 2 |
| SS49E pin 3 (out) | ESP32 GPIO 34 (ADC1, input-only) |

Keep the hall sensor on GPIO 32–39 (ADC1); the ADC2 pins stop working while Wi-Fi is on. Pins are suggestions; change them in the firmware config.
