# Firmware

ESP32 firmware for the Ripe-O-Matic. One sketch, no libraries beyond the Arduino-ESP32 core. The device serves its own web app; there is no phone app to install.

**Status: first pass, untested on hardware.** The measurement logic is unit-tested on a simulated avocado (`test/`), the web page is tested in a headless browser against `tools/mock_device.py`, and the whole sketch type-checks against an API shim. It has not yet run on a real ESP32. Expect to fix small things on first flash; please open an issue with the serial output if something is off.

## What it does

- **Measures** on a schedule (default every 12 h, every 6 h once the fruit is almost ripe; only once both calibrations are done) and on demand: homes against the end stop, zeroes the hall sensor, approaches, creeps to contact, preloads, presses to the force cap, retracts. ~1–2 minutes.
- **Reports stiffness in N/mm** with the blade's own bend subtracted, fits a line, and judges `hard / softening / almost ripe / ripe`. Guesses days-to-ripe from the fruit's own decay once it has two readings a day apart.
- **Knows when you swap avocados** (contact position jumps, or the fruit got much stiffer) and starts a new fruit id. Notices an empty nest.
- **Logs** every reading to a CSV on the ESP32's flash in the shared schema (`docs/data-sharing.md`), downloadable from the page as `/data.csv`.
- **Pushes to your phone** through [ntfy](https://ntfy.sh): "almost ripe", "ripe", "nest is empty". Free, no account: pick a topic name, subscribe in the ntfy app.
- **Web app** at `http://ripeomatic.local`: verdict, trend chart, last press curve, one-tap rating buttons (the labels that make pooled data useful), calibration wizard, motor jog, all settings, Wi-Fi. Add it to your home screen and it behaves like an app.
- **BOOT button**: short press = measure now, hold 2 s = "it was perfect".
- **Wi-Fi setup** without editing code: the web installer asks for it over USB (Improv); otherwise first boot opens an access point `RipeOMatic-xxxxxx`; join it and pick your network.
- **OTA** updates from the IDE after the first USB flash.
- **Simulation mode** (`SIMULATE 1` in `config.h`) runs the whole thing on a bare ESP32 with a virtual avocado so you can try the UI before the printer is done.
- **v2 servo** (`ENABLE_SERVO 1`): "Tip the nest" button and an `/api/tip` endpoint.

## Flashing

**Easiest: the web installer.** Plug the ESP32 into a computer, open **https://btltech1.github.io/ripeomatic/install/** in Chrome or Edge, click *Install*, pick the port. It flashes the latest build from `main` (GitHub Actions compiles it on every change), then asks for your Wi-Fi over the same cable and shows a link to the device. There is a second button that installs the simulation build for a bare board. The whole thing is about two minutes and needs nothing installed.

**Arduino IDE**

1. Boards manager: install *esp32 by Espressif* (2.0.x or 3.x both work).
2. Open `ripeomatic/ripeomatic.ino`. Board: *ESP32 Dev Module*. Partition scheme: **Minimal SPIFFS (1.9MB APP with OTA/190KB SPIFFS)**: the sketch is ~1.25 MB, too big for the default scheme.
3. Upload. Open the serial monitor at 115200.

**PlatformIO**: `cd firmware && pio run -t upload && pio device monitor`.

No libraries to install. If you edit `ui/index.html`, run `python3 tools/build_ui.py` to regenerate `ripeomatic/ui.h` (committed, so Arduino IDE users never need Python). CI (`.github/workflows/build.yml`) compiles both variants with the real toolchain and keeps the merged `.bin` files as artifacts; the `pages` workflow puts them behind the installer.

## First run

The device page opens with a **setup checklist** that walks through everything, one step at a time:

1. **Phone alerts.** *Set up alerts* creates a private ntfy topic; install the free ntfy app, tap the link to subscribe, *Send a test alert*. (Or skip.)
2. **Motor direction.** *Nudge the sled 1 mm*, then answer *Toward the nest* or *Away from the nest*; the firmware flips the direction itself if needed.
3. **Force calibration.** Machine on its motor end, bottle cap on the pad: *Capture zero*; add nickels (5.000 g each), type the grams, *Capture*. Two amounts are better than one.
4. **Blade calibration.** Machine upright, a glass jar in the nest: *Measure the blade*. Records the machine's own spring (`blade_k`) so it can be subtracted from every reading. (If you redo the force calibration later, `blade_k` is rescaled automatically.)
5. **First avocado.** Put one in, *Measure now*. From then on readings run every 12 h.

Until steps 3 and 4 are done the force cap is a guess, the squish backstop is shortened to 3 mm, and automatic readings stay off. Wi-Fi was already set by the installer; without it, the device starts an access point `RipeOMatic-xxxxxx` with a setup page (or open `http://192.168.4.1`).

When you eat the avocado, tap how it was (**Perfect** is the label that matters), and whether it bruised if you looked. That row is what turns everyone's readings into a real ripeness threshold.

## Files

| File | What |
|---|---|
| `ripeomatic/ripeomatic.ino` | setup/loop, button, LED, OTA |
| `ripeomatic/config.h` | pins, `SIMULATE`, `ENABLE_SERVO`, defaults |
| `ripeomatic/measure.h` | the measurement state machine, verdict, days-to-ripe, CSV rows. Pure C++, no Arduino; unit-tested |
| `ripeomatic/machine.h` | the job task: home, tare, press, log, notify; calibration capture |
| `ripeomatic/settings.h` | settings and fruit state in NVS, table-driven |
| `ripeomatic/stepper.h` | 28BYJ-48 half-step driver with mm positioning |
| `ripeomatic/hall.h` | SS49E on ADC1, averaging, tare; virtual fruit in `SIMULATE` |
| `ripeomatic/storage.h` | CSV log on LittleFS with one rotation |
| `ripeomatic/net.h` | Wi-Fi, setup AP + captive portal, mDNS, NTP, ntfy |
| `ripeomatic/web.h` | HTTP API (below) and the captive-portal redirects |
| `ripeomatic/servo.h` | v2 SG90 on LEDC |
| `ripeomatic/improv.h` | Improv Wi-Fi over serial: what the web installer talks to. Framing is host-tested in `test/test_improv.cpp` |
| `ripeomatic/ui.h` | generated from `ui/index.html` |
| `test/test_measure.cpp`, `test/test_improv.cpp` | `cd test && g++ -std=c++17 -I../ripeomatic test_measure.cpp && ./a.out` (same for improv) |
| `test/check_sketch.sh` | type-checks the whole sketch with a desktop g++ against `test/shim/` |
| `../tools/mock_device.py` | fake device for working on the page: `python3 tools/mock_device.py`, open localhost:8080 |

## HTTP API

Everything the page does. Handy for Home Assistant or a script.

| Method | Path | Does |
|---|---|---|
| GET | `/api/status` | Everything: job/stage, live force, fruit (id, readings, first/last stiffness, verdict, days to ripe), last reading, calibration state |
| GET | `/api/live` | The force-vs-squish points of the press in progress (or the last one) |
| POST | `/api/measure` | Start a reading (409 if busy) |
| POST | `/api/newfruit` | Start tracking a new avocado and measure |
| POST | `/api/abort` | Stop the current job; the sled retracts |
| POST | `/api/rate` | `r=hard|firm|ready|perfect|overripe`, optional `cut=no_bruise|bruise_at_pad|bruise_elsewhere`, `notes=` |
| GET | `/data.csv` | Current fruit's rows. `?fruit=all` for everything, `&old=1` to include the rotated file |
| GET/POST | `/api/settings` | All settings as JSON; POST form fields to change any of them |
| POST | `/api/jog` | `mm=±5` manual move |
| POST | `/api/home` | Home against the end stop |
| POST | `/api/cal/zero`, `/api/cal/mass` (`g=`), `/api/cal/clear`, `/api/cal/blade` | Calibration |
| POST | `/api/tip` | v2: tip the nest |
| GET | `/api/scan` · POST `/api/wifi` (`ssid`, `pass`) | Wi-Fi |
| POST | `/api/reset` (`what=fruit|data|settings|all`), `/api/reboot` | Housekeeping |

## Tunable settings

All in the Settings panel; defaults in `measure.h` and `config.h`.

| Setting | Default | Notes |
|---|---|---|
| `steps_per_mm` | 2048 | Half-stepped 28BYJ-48 (4096 half steps/turn) on the TR10×2 screw (2 mm/turn). The true gear ratio is 63.68:1, not 64:1; the stiffness slope doesn't care |
| `fast_mm_s`, `creep_mm_s` | 0.45, 0.25 | The 28BYJ-48 runs out of torque around 15 rpm ≈ 0.5 mm/s |
| `hall_n_per_count` | 0.0035 | Newtons per ADC count, **sign included**. Overwritten by the coin calibration |
| `blade_k_n_per_mm` | 0 (off) | Set by the blade calibration. 0 = no correction |
| `contact_threshold_n` | 0.1 | Three consecutive samples above this = contact |
| `preload_force_n` | 0.2 | Seats the fruit; travel zero |
| `force_cap_n` | 2.5 | Lower = gentler |
| `sample_step_mm` | 0.05 | One force sample per step while creeping and pressing |
| `approach_step_mm` | 0.5 | Force is checked between approach steps; a touch backs off and creeps, so this is the worst-case overshoot |
| `safety_margin_mm` | 2 | Creep starts this far before last time's contact |
| `max_travel_mm` | 42 | Past this with no contact = empty nest |
| `max_squish_mm` | 12 | Past this without reaching the cap = give up (mush, or a sensor problem) |
| `ripe_abs_n_per_mm` | 1.5 | **Placeholder** until there is pooled data. 0 = off |
| `ripe_pct_of_first` | 45 | Ripe when below this % of the fruit's first reading; whichever threshold is higher wins. 0 = off |
| `swap_contact_mm`, `swap_stiffer_pct` | 6, 60 | New-fruit detection |
| `interval_h` | 12 | Halved once the fruit is almost ripe |

## Hall sensor notes

- **Wiring (optional):** a 0.1 µF ceramic capacitor ("104") from the SS49E output to GND, right at the sensor, before the ESP32 ADC pin. The averaging below handles most noise; add the cap if readings jump around, especially while Wi-Fi is busy. Use GPIO 34 (ADC1); ADC2 pins stop working when Wi-Fi is on.
- The ADC is noisy; the firmware averages 48 samples per live reading and 256 for the tare, at 11 dB attenuation.
- It tares before every reading with the pad in the air, so temperature drift in the sensor and the PLA blade cancels.
- If a press aborts with *force reads negative*, the magnet is the wrong way round or `hall_n_per_count` needs its sign flipped. The coin calibration sets the sign automatically.
- Every plain move (homing, retracting, jogging) also watches the sensor and stops if the reading changes by more than the force cap: an inverted motor or a fruit in the way can't be pushed through. *Unexpected force during a plain move* means check `motor_invert` first.
- *Hall sensor saturated* means the ADC is pinned at 0 or 4095: the magnet is too close or too far, or the sensor isn't wired.
- The response is not perfectly linear over a big gap, but over the ~1 mm of blade bend it's close enough; two or three coin masses give a good enough fit.

## Not done yet

- Temperature sensor (`room_temp_c` in the log). `PIN_TEMP` is reserved for a DS18B20.
- MQTT / Home Assistant discovery. Use the API above for now.
- Opt-in automatic sharing of readings (v2 of `docs/data-sharing.md`). For now: download the CSV, open a pull request into `data/contrib/<device_id>/`.
- Hardware validation of the defaults (speeds, thresholds, the 0.0035 N/count guess).

See [`../docs/measurement.md`](../docs/measurement.md) for the routine and the blade correction.
