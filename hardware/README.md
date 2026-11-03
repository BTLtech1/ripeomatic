# Hardware

Design goal: **as cheap and as 3D-printable as possible.** Every structural and mechanical part is printed, including the lead screw, the guide posts and the force-sensing flexure. No bearings, no metal load cell, no power brick.

Interactive 3D assembly (orbit, explode, simulated reading): https://claude.ai/artifact/XxPCr4hXQnpZJonZaod3w8

## Printed parts

All PLA or PETG unless noted. Roughly 150 g of filament total.

| Part | Qty | Print notes |
|---|---|---|
| Base plate | 1 | Flat, ~130 × 160 × 6 mm. Post sockets, screw-tip pocket, cradle, board mounts. |
| Spine | 1 | Flat, ~80 × 180 × 5 mm. Slots into base and top plate. |
| Top plate | 1 | ~90 × 44 × 8 mm. Motor ears mount here; post sockets underneath. |
| Guide posts | 2 | Ø10 × 180 mm, printed vertically. Press into base and top. Any straight rod (old printer rods, hardware-store steel) works too. |
| Lead screw | 1 | Ø8 mm, 3 mm pitch, ~175 mm, printed vertically. D-socket on top fits the 28BYJ-48 shaft directly (no coupler). |
| Carriage | 1 | One print: two Ø10.3 mm bores, printed nut thread, rigid arm, sensor bridge. |
| Flexure | 1 | 12 × 4 × 54 mm PLA leaf spring, printed flat. About 2.7 N/mm. Screws or glues to the arm. |
| Pad | 1 | 16 mm dome. TPU if you have it; otherwise a pencil eraser cap or a stick-on silicone bumper on a PLA disc. |
| Cradle pins | 3 | Rounded tips, printed. Part of the base or separate. |

Fallback if the printed lead screw is rough: an **M8 threaded rod and nut** from the hardware store (~$1.50), 1.25 mm pitch.

## Bought parts

| Qty | Part | Notes | Rough cost |
|---|---|---|---|
| 1 | 28BYJ-48 stepper + ULN2003 driver | Sold as a pair. 5 V, geared 64:1, 2048 steps/turn. | $2–4 |
| 1 | ESP32 dev board | Any ESP32-WROOM board (an ESP8266 D1 mini also works). | $3–6 |
| 1 | SS49E linear hall sensor | Sold in 10-packs. | $4–5 / 10 |
| 1 | Neodymium magnet, 3 × 2 mm | Sold in 50-packs. Glue to the flexure tip. | ~$3 / 50 |
| 1 | Microswitch (optional) | Homing. Skip it and let the firmware crash-home against the top plate. | $0–1 |
| ~8 | M3 screws | Or design printed dovetails/snap fits. | ~$1 |
| 1 | USB cable + phone charger | Powers everything at 5 V. | have |

**Total: about $15–20** plus filament.

### Optional upgrade

If the printed flexure drifts too much (PLA creeps and softens a little when warm), a **1 kg bar load cell + HX711** (~$7) bolts into the same spot on the carriage arm and replaces the flexure, magnet and hall sensor.

## Why these choices

- **28BYJ-48.** It is the cheapest stepper there is and runs on USB 5 V. Its gear backlash doesn't matter because every measurement moves in one direction only (down, through contact, to the force cap). It is slow (about 0.5 mm/s), so a full reading from the top takes 1–2 minutes. That's fine twice a day.
- **Printed lead screw on the motor shaft.** One turn = 3 mm, so one of the motor's 2048 steps = 0.0015 mm. More resolution than the sensor can use.
- **Printed posts, no bearings.** The carriage rides on two printed posts through printed bores with ~0.3 mm clearance. Sideways play doesn't affect the vertical measurement. A dab of grease keeps it smooth.
- **Printed flexure + hall sensor instead of a load cell.** A 4 mm thick PLA beam bends about 1 mm at the 2.5 N force cap. A 3 × 2 mm magnet on its tip sits ~1.5 mm under an SS49E hall sensor; the ESP32's ADC reads the gap. Resolution is a few thousandths of a newton after averaging. Calibrate once with coins (a US nickel is exactly 5.000 g).
- **All 5 V.** The ESP32's 5 V pin powers the ULN2003. No PD trigger, no buck converter.

## Wiring

| From | To |
|---|---|
| ESP32 5V, GND | ULN2003 VCC, GND |
| ESP32 GPIO 16, 17, 18, 19 | ULN2003 IN1–IN4 |
| ULN2003 motor header | 28BYJ-48 plug |
| ESP32 3V3, GND | SS49E pins 1, 2 |
| SS49E pin 3 (out) | ESP32 GPIO 34 (ADC) |
| Microswitch (optional) | ESP32 GPIO 23 + GND (internal pull-up) |

Pins are suggestions; change them in the firmware config.
