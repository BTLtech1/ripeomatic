# Firmware

ESP32 firmware will live here.

## Planned features

- [ ] Home to limit switch
- [ ] Tare HX711 load cell before each reading
- [ ] Fast + slow approach with contact detection
- [ ] Preload, then measure force vs. distance up to a force cap
- [ ] Stiffness calculation (linear fit)
- [ ] Detect new avocado / empty cradle from contact height
- [ ] Scheduled readings (e.g. twice a day)
- [ ] Log readings to CSV (see `../data/README.md`)
- [ ] Wi-Fi notification when ripe
- [ ] Simple web page showing the ripening curve

## Tunable settings

| Setting | Starting value | Notes |
|---|---|---|
| `contact_threshold` | 0.05–0.1 N | Must be above load-cell noise |
| `preload_force` | 0.2 N | Seats the avocado |
| `force_cap` | 2–3 N | Lower = gentler |
| `slow_step` | 0.02–0.05 mm | Approach speed near contact |
| `safety_margin` | 3–5 mm | Fast-approach stop above last contact |
| `ripe_threshold` | TBD | Set from calibration data |

See [`../docs/measurement.md`](../docs/measurement.md) for the full routine.
