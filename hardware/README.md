# Hardware

Design goal: **as cheap and as 3D-printable as possible.** A low, horizontal caliper-style press, about 7 cm tall. Every structural and mechanical part is printed, including the lead screw, the guide channel, the force-sensing blade and the avocado nest. No bearings, no metal load cell, no power brick.

Interactive 3D assembly (orbit, explode, simulated reading): https://claude.ai/artifact/XxPCr4hXQnpZJonZaod3w8

## Layout

```
 side view (press axis left → right)

  motor ─ screw ────▶ [sled] ─ blade ─ pad ─▶ ( avocado )╮ nest
  └──────── guide channel in base ─────────┘  saddle ╰─o hinge
 ═══════════════════════ base plate ═══════════════════════
```

The avocado lies in a printed half-shell nest with a soft liner, opening toward the pad. The sled drives a soft pad on a short stem into the fruit's side, pushing it into the curved back of the nest. Pressing sideways means the reaction spreads over the nest's whole back wall instead of cradle pins, the whole thing stays low, and gravity acts perpendicular to the measurement. The nest is bolted to its pedestal through a GoPro-style knuckle at its rear bottom edge; in v1 the bolt is tight, in v2 a servo on that axis tips the nest back to drop a ripe avocado into a bowl below.

## Printed parts

All PLA or PETG unless noted. Roughly 150 g of filament total.

| Part | Qty | Print notes |
|---|---|---|
| Base plate | 1 | Flat, ~260 × 120 × 6 mm. One print carries the guide channel (two rails with inward lips), motor plate, end stop, far screw bracket, nest pedestal with saddle and two hinge prongs, and board mounts. Split at the pedestal if your bed is under 260 mm. |
| Avocado nest | 1 | Half-shell shaped like a half avocado, inner cavity ~77 × 77 × 102 mm (fits up to an 85 mm fruit with the liner), wall 3 mm, with a low front lip and three hinge prongs under the rear edge. Print bowl-up like a cup, no supports. |
| Nest liner | 1 | 3 mm TPU shell to match the cavity, or craft foam glued in. The fruit only needs to touch at the back and bottom, so one liner fits all sizes. |
| Lead screw | 1 | Ø8 mm, 3 mm pitch, ~115 mm, printed vertically. D-socket at one end pushes onto the 28BYJ-48 shaft (no coupler). Push reaction pulls the screw toward the motor, so no retaining flange is needed. |
| Sled | 1 | One print: ~30 × 14 × 40 mm block with lips that ride under the channel rails, printed nut thread, a post at the back and a short sensor bridge on top. |
| Blade (flexure) | 1 | 3 × 12 × 42 mm PLA, standing vertical from the sled, thin along the push direction. About 3 N/mm. Printed flat; glues or screws into a slot on the sled. Pocket for a 3 × 2 mm magnet on its back face near the tip. |
| Pad | 1 | 16 mm dome on a 12 mm stem printed with the blade, at avocado-equator height, so it reaches 20 mm ahead of the sled and small fruit is still in reach. TPU dome if you have it; otherwise a pencil eraser cap or a stick-on silicone bumper on a PLA disc. |
| Hinge thumbscrew | 1 | Printed M5 knob, or a regular M5 bolt and nut. |

Fallback if the printed lead screw is rough: an **M8 threaded rod and nut** from the hardware store (~$1.50), 1.25 mm pitch.

## Bought parts

| Qty | Part | Notes | Rough cost |
|---|---|---|---|
| 1 | 28BYJ-48 stepper + ULN2003 driver | Sold as a pair. 5 V, geared 64:1, 2048 steps/turn. | $2–4 |
| 1 | ESP32 dev board | Any ESP32-WROOM board (an ESP8266 D1 mini or ESP32-C3 also works). | $3–6 |
| 1 | SS49E linear hall sensor | Sold in 10- or 20-packs. 49E / OH49E clones work the same. | $4–6 / pack |
| 1 | Neodymium magnet, 3 × 2 mm | The size in every "magnets for 3D printing" kit. Glue to the back of the blade tip. | ~$3 / 50 |
| ~8 | M3 screws | Motor ears, blade clamp. Or design printed dovetails/snap fits. | ~$1 |
| 1 | M5 × 30 bolt + nut | Nest hinge. A printed thumbscrew works too. | ~$0.20 |
| 1 | USB cable + phone charger | Powers everything at 5 V. | have |

**Total: about $15–20** plus filament.

### Optional upgrade

If the printed blade drifts too much (PLA creeps and softens a little when warm), a **1 kg bar load cell + HX711** (~$7) mounts horizontally on the sled in place of the blade, magnet and hall sensor.

## Why these choices

- **Horizontal, not a tower.** Low and stable, fits under a cabinet, loads from the top, and the three frame parts of the tower design collapse into one flat base print.
- **Nest, not rails and a wall.** The half-shell spreads the reaction over the whole back of the fruit, self-centres any size, looks like what it is, and the liner takes up the size difference. A smaller avocado sits a little lower, so the pad presses slightly above its equator; that is the same with any passive cradle and the calibration absorbs it.
- **Hinged for v2.** Pushing the fruit backward also tries to tip the nest backward, so during a reading the nest must be held upright: in v1 by the tight hinge bolt and the saddle, in v2 by the tipping servo or a small front latch. The holding force is only about 2 N. For the drop to work, the base should end just behind the hinge, or the machine sits at a shelf edge with a bowl below.
- **28BYJ-48.** The cheapest stepper there is, and it runs on USB 5 V. Gear backlash doesn't matter because every measurement moves in one direction (toward the fruit, through contact, to the force cap). It is slow (about 0.5 mm/s), so a full reading takes 1–2 minutes. That's fine twice a day.
- **Printed lead screw on the motor shaft.** One turn = 3 mm, so one of the motor's 2048 steps = 0.0015 mm. More resolution than the sensor can use. In this orientation the push reaction seats the screw on the shaft instead of pulling it off.
- **Printed channel, no posts or bearings.** The sled rides between two rails printed into the base, with ~0.3 mm clearance and lips that stop it lifting. Sideways play doesn't affect the along-axis measurement. A dab of grease keeps it smooth.
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
