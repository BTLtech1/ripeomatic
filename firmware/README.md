# Firmware

ESP32 firmware will live here.

## Planned features

- [ ] Home by running the sled back against the printed end stop
- [ ] Tare the hall sensor before each reading
- [ ] Drive toward the fruit, creep near the last contact position, detect contact
- [ ] Preload, then measure force vs. travel up to a force cap
- [ ] Subtract the blade bend from the travel to get the avocado squish
- [ ] Stiffness calculation (linear fit)
- [ ] Detect new avocado / empty nest from contact position
- [ ] Scheduled readings (e.g. twice a day)
- [ ] Log readings to CSV (see `../data/README.md`)
- [ ] Wi-Fi notification when ripe
- [ ] Simple web page showing the ripening curve

## Tunable settings

| Setting | Starting value | Notes |
|---|---|---|
| `steps_per_mm` | 683 | 28BYJ-48 at 2048 full steps/turn on a 3 mm pitch screw |
| `hall_n_per_count` | from calibration | Newtons per ADC count. Calibrate with coins (US nickel = 5.000 g = 0.049 N) |
| `blade_k` | ~3 N/mm | Blade stiffness, from the same calibration. Used to subtract the bend from the travel |
| `contact_threshold` | 0.1 N | Must be above sensor noise |
| `preload_force` | 0.2 N | Seats the avocado |
| `force_cap` | 2.5 N | Lower = gentler |
| `creep_speed` | 0.3 mm/s | Approach speed near contact |
| `safety_margin` | 4 mm | Where to switch from full speed to creep, short of the last contact position |
| `ripe_threshold` | TBD | Set from calibration data |

## Hall sensor notes

- The ESP32 ADC is noisy. Average 64–256 samples per reading and use `analogSetAttenuation(ADC_11db)`.
- Tare before every reading (pad in the air) so temperature drift cancels out.
- The sensor response is not perfectly linear over a big gap, but over the ~1 mm of bend it is close enough. A two-point calibration (0 g and ~250 g) is fine to start.

See [`../docs/measurement.md`](../docs/measurement.md) for the full routine.
