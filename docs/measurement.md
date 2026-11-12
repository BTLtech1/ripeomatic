# Measurement routine

This describes how Ripe-O-Matic takes a reading.

## Goals

- Work with avocados of any size, lying in the soft-lined nest.
- Never press hard enough to bruise.
- Produce a number that tracks ripening day by day.

## Steps

1. **Home.** Drive the sled back to position 0 by step count. Home is set once by the user with the sled touching the printed end stop, and the count is saved after every move (see [firmware/README.md](../firmware/README.md#home)). The machine never drives into the stop on purpose: stalling the 28BYJ-48 there pulls the lead screw off the motor shaft.
2. **Tare.** With the pad in the air, zero the hall sensor reading. Doing this every reading cancels temperature drift in the sensor and the PLA blade.
3. **Approach.** Drive toward the fruit at full speed (~0.5 mm/s) to `last_contact_pos - safety_margin` (a few mm). On the first run, creep from home.
4. **Creep.** Step forward slowly, reading force after each small increment.
5. **Contact.** Contact = force above `contact_threshold` (~0.1 N) for 3 consecutive readings. Record `contact_pos`.
6. **Preload.** Continue to `preload_force` (~0.2 N). This pushes the avocado snug into the back of the nest and takes up any settling. Set this point as travel zero.
7. **Measure.** Continue stepping, logging `(travel, force)` pairs, until `force_cap` (~2.5 N) is reached.
8. **Retract.** Back off to position 0 (just clear of the end stop) and cut motor power.

## The blade correction

The blade bends too, so part of the sled travel after contact is the spring bending, not the avocado squishing:

```
squish = travel - force / blade_k
```

`blade_k` (about 3 N/mm for a 3 × 12 × 42 mm vertical PLA blade) comes from the coin calibration. Because the blade is in series with the avocado, the raw travel-vs-force slope would read softer than the fruit really is; the correction fixes that.

## Result

- **Stiffness** = slope of a straight-line fit to force vs. squish (N/mm). This is the main number; it drops as the avocado ripens.
- **Squish at cap** = squish at the force cap (mm). A simpler backup number.
- **Contact position** = for detecting swaps and an empty nest.

## Automatic events

| Condition | Meaning | Action |
|---|---|---|
| Contact position jumps by more than a few mm | New avocado | Start a new baseline |
| No contact before the end of travel | Nest empty | Pause testing |
| Stiffness below `ripe_threshold` | Ripe | Send notification |
| Stiffness dropping fast | Close to ripe | Increase test frequency or switch to gentler testing |

## Calibration

**Force sensor (once):** lay the machine on its back so the blade points up and the pad faces the ceiling, read the hall sensor with nothing on the pad, then with coins stacked on the pad (US nickel = 5.000 g; 20 nickels = 100 g ≈ 0.98 N). Fit counts vs. force. Also note how far the tip moves per newton, which is `blade_k`.

**Ripeness threshold:**

1. Run 5–10 avocados through, logging every reading.
2. Each day, also do the thumb test and note when each one was perfect.
3. Use those notes to set `ripe_threshold` as a stiffness value or as a percent drop from day one.

## Avoiding bruising

- Wide, soft, domed pad (~20 mm).
- Hard force cap; never position-only control.
- Rotate the contact spot between readings if the design allows it.
- Test less often once the avocado is close to ripe.
- Check early test avocados by cutting them open and looking under the pressed spots.
