# Hardware

Design goal: **as cheap and as 3D-printable as possible.** A low, horizontal caliper-style press, about 7 cm tall. Every structural and mechanical part is printed, including the lead screw, the guide channel and the force-sensing blade. No bearings, no metal load cell, no power brick.

Interactive 3D assembly (orbit, explode, simulated reading): https://claude.ai/artifact/XxPCr4hXQnpZJonZaod3w8

## Layout

```
 side view (press axis left → right)

  motor ─ screw ────▶ [sled] ─ blade/pad ─▶ ( avocado ) │ backstop
  └──────── guide channel in base ────────┘  └ V-trough ┘│
 ═══════════════════════ base plate ═════════════════════╧══
```

The avocado lies across the machine in a V-trough with its side against a soft backstop. The sled drives a soft pad into the opposite side. Pressing sideways means the reaction goes into a broad backstop instead of cradle pins, the whole thing stays low, and gravity acts perpendicular to the measurement.

## Printed parts

All PLA or PETG unless noted. Roughly 150 g of filament total.

| Part | Qty | Print notes |
|---|---|---|
| Base plate | 1 | Flat, ~250 × 120 × 6 mm. One print carries everything: guide channel (two rails with inward lips), motor plate, end stop, far screw bracket, V-trough, backstop, board mounts. Split at the trough if your bed is under 250 mm. |
| Lead screw | 1 | Ø8 mm, 3 mm pitch, ~115 mm, printed vertically. D-socket at one end pushes onto the 28BYJ-48 shaft (no coupler). Push reaction pulls the screw toward the motor, so no retaining flange is needed. |
| Sled | 1 | One print: ~30 × 14 × 40 mm block with lips that ride under the channel rails, printed nut thread, a post at the back and a short sensor bridge on top. |
| Blade (flexure) | 1 | 3 × 12 × 42 mm PLA, standing vertical from the sled, thin along the push direction. About 3 N/mm. Printed flat; glues or screws into a slot on the sled. Pocket for a 3 × 2 mm magnet on its back face near the tip. |
| Pad | 1 | 16 mm dome on the blade's front face at avocado-equator height. TPU if you have it; otherwise a pencil eraser cap or a stick-on silicone bumper on a PLA disc. |
| Backstop face | 1 | Flat 2 mm TPU pad, or craft foam, on the backstop wall. |

Fallback if the printed lead screw is rough: an **M8 threaded rod and nut** from the hardware store (~$1.50), 1.25 mm pitch.

## Bought parts

| Qty | Part | Notes | Rough cost |
|---|---|---|---|
| 1 | 28BYJ-48 stepper + ULN2003 driver | Sold as a pair. 5 V, geared 64:1, 2048 steps/turn. | $2–4 |
| 1 | ESP32 dev board | Any ESP32-WROOM board (an ESP8266 D1 mini or ESP32-C3 also works). | $3–6 |
| 1 | SS49E linear hall sensor | Sold in 10- or 20-packs. 49E / OH49E clones work the same. | $4–6 / pack |
| 1 | Neodymium magnet, 3 × 2 mm | The size in every "magnets for 3D printing" kit. Glue to the back of the blade tip. | ~$3 / 50 |
| ~8 | M3 screws | Motor ears, blade clamp. Or design printed dovetails/snap fits. | ~$1 |
| 1 | USB cable + phone charger | Powers everything at 5 V. | have |

**Total: about $15–20** plus filament.

### Optional upgrade

If the printed blade drifts too much (PLA creeps and softens a little when warm), a **1 kg bar load cell + HX711** (~$7) mounts horizontally on the sled in place of the blade, magnet and hall sensor.

## Why these choices

- **Horizontal, not a tower.** Low and stable, fits under a cabinet, loads from the top, and the three frame parts of the tower design collapse into one flat base print. The reaction to the push goes into a broad soft backstop rather than three cradle pins under the fruit.
- **28BYJ-48.** The cheapest stepper there is, and it runs on USB 5 V. Gear backlash doesn't matter because every measurement moves in one direction (toward the fruit, through contact, to the force cap). It is slow (about 0.5 mm/s), so a full reading takes 1–2 minutes. That's fine twice a day.
- **Printed lead screw on the motor shaft.** One turn = 3 mm, so one of the motor's 2048 steps = 0.0015 mm. More resolution than the sensor can use. In this orientation the push reaction seats the screw on the shaft instead of pulling it off.
- **Printed channel, no posts or bearings.** The sled rides between two rails printed into the base, with ~0.3 mm clearance and lips that stop it lifting. Sideways play doesn't affect the along-axis measurement. A dab of grease keeps it smooth.
- **Vertical printed blade + hall sensor instead of a load cell.** A 3 mm thick blade standing up from the sled bends about 0.75 mm at the 2.5 N cap. A 3 × 2 mm magnet on its back face sits ~1.5 mm from an SS49E on the sled's bridge; the ESP32's ADC reads the gap. Standing vertical, the blade carries its own weight along its length, so there is no gravity sag to drift. Calibrate once with coins (a US nickel is exactly 5.000 g).
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
