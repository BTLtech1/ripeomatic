# BTL Ripe-O-Matic

**An open-source countertop gadget that watches your avocado and tells you when it's ripe, so you stop forgetting about them until they're brown mush.**

> **Status: designed, not yet built.** The CAD is done and the STLs are in [`hardware/stl/`](hardware/stl/), the firmware is written and tested in simulation, and the data pipeline and dashboard are live. Nothing has been printed, flashed or calibrated on a real avocado yet. Expect the first build to turn up small fixes.

---

## The idea

Store ripeness scanners (NIR, acoustic, laser vibrometry) judge a stranger's avocado from a single reading, so they need big trained models. Ripe-O-Matic has an easier job: it measures **the same avocado every day** and watches the trend. It doesn't need to know exactly how ripe the fruit is, only that it has been softening and just crossed your "perfect" line.

## How it works

A soft pad presses very gently on the avocado once or twice a day and measures **how much it squishes for a given force**, the same way you'd test it with your thumb. As the avocado ripens, it gets softer, and when it crosses your threshold you get a notification.

The machine is a low, horizontal press about 7 cm tall. The avocado lies in a printed half-shell nest with a soft liner, and a sled drives the pad into its exposed side, pushing it gently into the curved back of the nest.

- **Push:** a $2 geared stepper turns a printed lead screw that moves the sled along a channel in the base in tiny, known steps, so step count = travel.
- **Feel:** a thin printed blade standing up from the sled carries the pad. It bends back as the avocado pushes. A magnet on its back and a $0.50 hall sensor on the sled measure the bend, which gives the force.
- **Result:** a force-vs-squish curve. Its slope (stiffness) drops day by day as the avocado ripens.

The base (with its guide channel and nest pedestal), the nest, the lead screw, the sled and the blade are all 3D printed. There are no bearings and no metal load cell, and everything runs on 5 V from a phone charger.

### Measurement routine

1. **Home** by running the sled gently back against the printed end stop.
2. **Tare** the hall sensor with the pad in the air.
3. **Approach** to just short of the last known contact position, then creep slowly.
4. **Detect contact** when force rises above ~0.1 N for 3 readings in a row.
5. **Preload** to ~0.2 N to seat the avocado into the back of the nest; call this zero.
6. **Measure** step by step up to a force cap (~2.5 N), logging force at each step. Avocado squish = travel minus the blade's own bend.
7. **Back off** and record the stiffness (slope of force vs. squish).

Because everything is measured from the contact point, avocado size doesn't matter. Contact position is logged too, so the device can tell when an avocado has been swapped (position jumps) or removed (no contact).

See [`docs/measurement.md`](docs/measurement.md) for details.

### Being gentle

Squeezing can bruise avocados, especially ripe ones. Ripe-O-Matic limits **force**, not just distance, and uses a **wide soft pad** (about 2 cm) to spread the load. The reaction spreads over the nest's soft curved back rather than small cradle pins. Rotate the avocado between tests where possible.

## Hardware

| Part | Purpose | Rough cost |
|---|---|---|
| 28BYJ-48 stepper + ULN2003 driver | Pushing + distance (2048 steps/turn) | $2–4 |
| ESP32 dev board | Brains, Wi-Fi notifications | $3–6 |
| SS49E hall sensor + 3 × 2 mm magnet | Force, via the printed blade | ~$1 (sold in packs) |
| USB cable + phone charger | 5 V power for everything | have |
| Base (channel, pedestal), nest, lead screw, sled, blade, pad | Everything else | printed |

Approximate total: **$15–20** plus about 150 g of filament. Full list, print notes and wiring in [`hardware/`](hardware/).

Optional upgrade if the printed blade drifts: a 1 kg load cell + HX711 (~$7) mounts in the same spot.

## Build it

1. **Print** the parts in [`hardware/stl/`](hardware/stl/) (base and sled first; test the slide before printing the rest).
2. **Assemble** in the order in [`hardware/stl/README.md`](hardware/stl/README.md#assembly-order), wire per [`hardware/README.md`](hardware/README.md#wiring) (don't forget the 0.1 µF capacitor on the hall sensor).
3. **Flash** `firmware/ripeomatic/ripeomatic.ino` from the Arduino IDE or PlatformIO; no libraries needed. Join the `RipeOMatic-xxxxxx` Wi-Fi it creates and give it your network.
4. **Calibrate** from the web page: blade (press a jar), then force (coins on the pad). Ten minutes.
5. **First avocado.** Tap *Measure now*, then let it run twice a day. When you eat it, tap how it was.

Steps 3–5 in detail: [`firmware/README.md`](firmware/README.md#first-run).

## Firmware and app

There is no app to install. The ESP32 serves its own web app at `http://ripeomatic.local`: the verdict (hard / softening / almost ripe / ripe), the ripening curve, one-tap "how was it?" buttons, calibration, settings. Add it to your phone's home screen and it behaves like an app. Push notifications ("almost ripe", "ripe", "nest is empty") go through [ntfy](https://ntfy.sh), free, no account. Readings are logged on the device in a shared format and downloadable as CSV. Details, first-run steps and the HTTP API in [`firmware/`](firmware/).

## Pooled data and the dashboard

Every build measures stiffness in the same units (N/mm, after a coin calibration and a blade correction), so readings from different machines are comparable. Contributed logs go through a pull request into [`data/contrib/`](data/), get validated and merged by CI, and show up on the dashboard:

**https://btltech1.github.io/ripeomatic/** — every avocado's ripening curve, the stiffness people called *perfect*, days-to-ripe vs. room temperature.

That pooled "perfect" number is what replaces the placeholder ripeness threshold in the firmware. See [`docs/data-sharing.md`](docs/data-sharing.md).

## Repo layout

```
ripeomatic/
├── firmware/   ESP32 sketch (ripeomatic/), web UI source (ui/), host tests (test/)
├── hardware/   STLs, print and assembly guide, BOM, wiring (CAD: Fusion 360)
├── dashboard/  The community data page (GitHub Pages)
├── data/       Contributed readings, merged all.csv, synthetic sample
├── docs/       Measurement routine, data sharing plan
└── tools/      merge_data.py, make_sample.py, build_ui.py, mock_device.py
```

## Data wanted!

The most useful thing anyone can contribute is **readings from real avocados**, and above all the tap that says it was *perfect* to eat. Download the CSV from your device's page and open a pull request into `data/contrib/<device id>/`; CI checks the format. See [`data/README.md`](data/README.md).

## Planned: tipping nest (v2)

The nest hangs on two side pins through the avocado's centre of gravity, at the height of the pad. That makes the loaded nest nearly balanced and means the pad's push can't tip it. A $2 micro servo on one pin will swing the nest backward when the avocado is ripe, so it rolls off the back of the base into a bowl below. The notification becomes physical.

## Prior art

- **AvoRipe** (2020): DIY ESP8266 gripper with a force sensor and color sensor. Great inspiration.
- Commercial retail and packhouse scanners (NIR, acoustic tap, laser vibrometry) work on the same physics but are built for stores.

## License

- **Firmware / code:** [MIT](LICENSE)
- **Hardware designs** (CAD, STL, drawings): [CC BY-SA 4.0](hardware/LICENSE.md)

---

Made by **BTL (Bring the Light)** · [YouTube](https://www.youtube.com/@BTLPhotoTech)
