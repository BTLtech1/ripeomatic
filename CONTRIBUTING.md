# Contributing

The most valuable contribution is **readings from real avocados**. See [`data/README.md`](data/README.md): download the CSV from your device, drop it in `data/contrib/<device id>/`, open a pull request. CI checks the format and the dashboard updates itself.

## Build reports

Built one? Open an issue titled *Build report* with: which parts gave trouble, your board widths (ESP32, ULN2003), filament, what you changed, and a photo. First-build fixes go straight into the STLs and the docs.

## Firmware

- Everything runs in CI without hardware: `firmware/test/test_measure.cpp` (unit tests for the measurement logic), `firmware/test/check_sketch.sh` (type-checks the whole sketch with a desktop g++), and `firmware/test/ui_smoke.js` (drives the web page in headless Chromium against `tools/mock_device.py`). Run them before a PR; CI runs them on every PR.
- Edit the page in `firmware/ui/index.html`, then `python3 tools/build_ui.py` and commit the regenerated `ui.h`.
- Keep the measurement logic in `measure.h` free of Arduino calls so it stays testable.
- Pins and compile-time options live in `config.h`; anything a user might tune belongs in the settings table in `settings.h` (NVS keys ≤ 15 chars).

## Hardware

The CAD is Fusion 360 (`BTL Ripe-O-Matic`). STLs are exported into `hardware/stl/`. If you change a part, update the print table in `hardware/stl/README.md` and the part description in `hardware/README.md`. Hardware files are CC BY-SA 4.0, code is MIT.
