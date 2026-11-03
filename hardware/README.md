# Hardware

CAD and print files will live here as the design develops.

## Planned files

- Frame, carriage, load cell mount, pad, cradle (STL + Fusion 360 export)
- `wiring.md`: wiring diagram for ESP32, HX711, stepper driver, limit switch

## Bill of materials

| Qty | Part | Notes | Rough cost |
|---|---|---|---|
| 1 | ESP32 dev board | Any common ESP32-WROOM board | ~$8–10 |
| 1 | NEMA 8 or 11 stepper with lead screw | A spare 3D printer Z-axis stepper + T8 lead screw works too. Avoid 28BYJ-48 (gear backlash is bigger than the squish being measured). | ~$15–25 |
| 1 | Stepper driver | TMC2209 (quiet) or A4988 | ~$5 |
| 1 | Bar load cell, 1 kg | Small straight-bar type | ~$5 |
| 1 | HX711 amplifier board | Often sold bundled with the load cell | ~$3 |
| 1 | Microswitch / endstop | Top-of-travel homing | ~$1 |
| 1 | Soft pad | Silicone or TPU, about 20 mm diameter, domed | printed |
| 1 | Frame, carriage, cradle | Printed. Cradle uses 3-point support or a soft TPU/foam lining. | printed |
| 1 | 12 V power supply | For the stepper; buck converter to 5 V for the ESP32 | ~$8 |

Prices are rough estimates and will vary by supplier.
