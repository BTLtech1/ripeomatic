# BTL Ripe-O-Matic

**An open-source countertop gadget that watches your avocado and tells you when it's ripe, so you stop forgetting about them until they're brown mush.**

> **Status: early / experimental.** The design is being worked out and nothing has been fully built or calibrated yet. Expect things to change.

---

## The idea

Store ripeness scanners (NIR, acoustic, laser vibrometry) judge a stranger's avocado from a single reading, so they need big trained models. Ripe-O-Matic has an easier job: it measures **the same avocado every day** and watches the trend. It doesn't need to know exactly how ripe the fruit is, only that it has been softening and just crossed your "perfect" line.

## How it works

A soft pad presses very gently on the avocado once or twice a day and measures **how much it squishes for a given force**, the same way you'd test it with your thumb. As the avocado ripens, it gets softer, and when it crosses your threshold you get a notification.

- **Push:** a stepper motor on a lead screw lowers the pad in tiny, known steps, so step count = squish distance.
- **Feel:** a load cell between the screw and the pad measures how hard the avocado pushes back.
- **Result:** a force-vs-squish curve. Its slope (stiffness) drops day by day as the avocado ripens.

### Measurement routine

1. **Home** to a top limit switch.
2. **Tare** the load cell with the pad in the air.
3. **Approach** quickly to just above the last known contact height, then creep slowly.
4. **Detect contact** when force rises above ~0.05–0.1 N for 3 readings in a row.
5. **Preload** to ~0.2 N to seat the avocado in the cradle; call this zero.
6. **Measure** step by step up to a force cap (~2–3 N), logging force at each step.
7. **Back off** and record the stiffness (slope of force vs. distance).

Because everything is measured from the contact point, avocado size and cradle fit don't matter. Contact height is logged too, so the device can tell when an avocado has been swapped (height jumps) or removed (no contact).

See [`docs/measurement.md`](docs/measurement.md) for details.

### Being gentle

Squeezing can bruise avocados, especially ripe ones. Ripe-O-Matic limits **force**, not just distance, and uses a **wide soft pad** (about 2 cm) to spread the load. Rotate the avocado between tests where possible.

## Hardware (planned)

| Part | Purpose | Rough cost |
|---|---|---|
| ESP32 dev board | Brains, Wi-Fi notifications | ~$8–10 |
| NEMA 8/11 stepper + lead screw (or a spare printer Z-axis) | Pushing + distance | ~$15–25 |
| Stepper driver (e.g. TMC2209 / A4988) | Motor control | ~$5 |
| 1 kg bar load cell + HX711 | Force measurement | ~$8–10 |
| Limit switch | Homing | ~$1 |
| Silicone / TPU pad | Gentle contact | printed |
| Printed frame + cradle | Structure | printed |

Approximate total: **under $60** plus filament. Full list in [`hardware/`](hardware/).

## Repo layout

```
ripeomatic/
├── firmware/   ESP32 code
├── hardware/   STL / Fusion 360 exports, BOM, wiring
├── docs/       How it works, calibration, build notes
└── data/       Logged readings from real avocados
```

## Data wanted!

The most useful thing anyone can contribute is **readings from real avocados**: daily stiffness values plus a note of when it was actually perfect to eat. See [`data/README.md`](data/README.md) for the format.

## Prior art

- **AvoRipe** (2020): DIY ESP8266 gripper with a force sensor and color sensor. Great inspiration.
- Commercial retail and packhouse scanners (NIR, acoustic tap, laser vibrometry) work on the same physics but are built for stores.

## License

- **Firmware / code:** [MIT](LICENSE)
- **Hardware designs** (CAD, STL, drawings): [CC BY-SA 4.0](hardware/LICENSE.md)

---

Made by **BTL (Bring the Light)** · [YouTube](https://www.youtube.com/@BTLPhotoTech)
