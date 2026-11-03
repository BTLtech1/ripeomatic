# Data

Readings from real avocados. This is how a good ripeness threshold gets found, so contributions are very welcome. The full record format, how readings from different builds are made comparable, and what pooled data is for are in [`../docs/data-sharing.md`](../docs/data-sharing.md). Contributed logs go in `contrib/<device_id>/`.

## Format

One CSV file per avocado, named like `2026-11-03_hass_01.csv`. Use [`readings_template.csv`](readings_template.csv) as a starting point.

| Column | Meaning |
|---|---|
| `timestamp` | ISO date/time of the reading |
| `hw_version` | Hardware revision, e.g. `v1` |
| `variety` | e.g. `hass` |
| `contact_height_mm` | Where the pad first touched |
| `stiffness_n_per_mm` | Slope of force vs. distance |
| `squish_mm` | Distance from preload to force cap |
| `force_cap_n` | Force cap used for this reading |
| `room_temp_c` | Optional, ripening speed depends on temperature |
| `human_rating` | Optional thumb-test rating: `hard`, `firm`, `ready`, `perfect`, `overripe` |
| `notes` | Anything else, e.g. "cut open, no bruising" |

Mark the reading where the avocado was actually perfect to eat with `human_rating = perfect`. That's the most valuable data point.
