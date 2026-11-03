# Sharing readings between builds

The threshold for "ripe" and the model for "ripe in about N days" get better with every avocado anyone measures. This is the plan for making readings from different builds comparable, collecting them, and feeding them back into the firmware.

## Why readings from different builds are comparable at all

Every blade prints a little differently, so raw sensor counts mean nothing across builds. Two things fix that:

1. **The coin calibration** turns counts into newtons on every unit (US nickel = 5.000 g). After it, stiffness is in N/mm everywhere.
2. **The blade correction** removes each unit's own spring from the travel, so squish is the fruit's squish, not the blade's.

So the number that gets shared is **stiffness in N/mm**, plus enough context to know how it was measured.

## Record format (v1)

One row per reading, CSV or JSON, same fields either way. Fields marked * are the minimum useful set.

| Field | Example | Notes |
|---|---|---|
| `schema` * | `1` | Bump when fields change |
| `device_id` * | `a3f9c2` | Random 6 hex chars generated on first boot; anonymous, stable per unit |
| `fw_version` * | `0.3.1` | |
| `hw_version` * | `v1` | |
| `timestamp` * | `2026-11-09T07:30:12Z` | NTP time |
| `fruit_id` * | `a3f9c2-0007` | Device id + counter; new id when a swap is detected |
| `variety` | `hass` | Free text, lower case |
| `fruit_mass_g` | `182` | Optional; kitchen scale |
| `room_temp_c` | `21.5` | From the optional temperature sensor; **the most useful optional field** |
| `contact_pos_mm` * | `17.3` | Where the pad met the fruit; detects swaps and settling |
| `stiffness_n_per_mm` * | `1.21` | Slope of force vs. squish |
| `squish_at_cap_mm` * | `2.07` | Squish at `force_cap_n` |
| `force_cap_n` * | `2.5` | |
| `blade_k_n_per_mm` * | `3.3` | This unit's blade spring, from its calibration |
| `cal_points` | `100.0:2281;200.0:2563` | `grams:counts;…` from the coin calibration (counts above the stored zero), so a bad calibration can be spotted later |
| `curve` | `0.00:0.00;0.12:0.21;…` | Optional full force-squish curve, 20–30 points |
| `human_rating` | `perfect` | `hard`, `firm`, `ready`, `perfect`, `overripe`, or blank |
| `cut_open` | `no_bruise` | Optional, if the fruit was cut that day: `no_bruise`, `bruise_at_pad`, `bruise_elsewhere` |
| `notes` | | Free text |

The **human rating** is the label everything else is trained against. The firmware makes it a one-tap action: the rating buttons on the page, or holding the BOOT button for "I ate it, it was perfect". A rating is logged as **its own row** with the measurement columns blank (the log is append-only on the device); analysis joins it to the nearest preceding reading of the same `fruit_id`.

## Collecting

Start simple and only add infrastructure when there are enough users to need it.

1. **v1, done:** the device serves its log as CSV from its web page (`/data.csv`). People contribute by opening a pull request that drops the file into `data/contrib/<device_id>/`. The `data` GitHub Action (`tools/merge_data.py`) validates the schema and merges the CSVs into one `data/all.csv`.
2. **v2:** an opt-in "share readings" toggle in the device settings that POSTs each reading as JSON to a small endpoint (a free-tier serverless function writing to a public bucket or straight into the repo). Default off. Nothing but the fields above is sent: no Wi-Fi name, no IP kept, no location.
3. **Dashboard, done:** `dashboard/index.html`, a static page (GitHub Pages) that reads `data/all.csv` and plots every fruit's stiffness-vs-time curve with the human ratings marked. This is also the project's best marketing.

## What pooled data buys

- **A real ripe threshold.** Today it's a guess. With a few dozen labelled fruit, the threshold becomes "stiffness below X N/mm, or below Y % of the day-1 value, whichever comes first," with a confidence number next to it.
- **Days-to-ripe prediction.** Stiffness decays roughly exponentially and the rate depends on temperature (about 2× per 10 °C). Pooled curves with `room_temp_c` give a decay-rate model, so the device can say "ripe in about 2 days" instead of only "ripe now." This is the feature that makes the device genuinely useful, and it cannot be built from one kitchen's worth of data.
- **Variety and size effects.** Whether a 55 mm fruit and an 80 mm fruit of the same variety read the same stiffness when perfect. Nobody knows yet.
- **Bruising check.** `cut_open` results across builds tell whether the 2.5 N cap and 16 mm pad are gentle enough, or could be pushed higher for a cleaner signal.
- **Bad-unit detection.** A unit whose calibration points or blade_k are far from the crowd gets flagged on its own dashboard: "your blade reads 2× stiffer than typical; re-check the coin calibration."

## Firmware changes this needs

- [x] Generate and persist `device_id` on first boot
- [x] NTP time; include `fw_version`, `hw_version`, `blade_k` and `cal_points` in every record
- [x] `fruit_id` counter that increments when a swap is detected
- [x] One-tap human rating on the web page; hold the BOOT button (GPIO 0) for "perfect"
- [ ] Optional DS18B20 or thermistor for `room_temp_c`
- [x] `/data.csv` endpoint and the download button; later, a "share" toggle
- [ ] Threshold and decay-rate constants loaded from a small JSON that the community model can update, rather than hard-coded (today: two settings, `ripe_abs_n_per_mm` and `ripe_pct_of_first`)

## Privacy

Readings contain nothing personal. The device id is random, the timestamp is UTC, and location is never collected. Contributors can delete their folder from `data/contrib/` at any time and the merge re-runs.
