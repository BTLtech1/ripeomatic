# Measurement routine

This describes how Ripe-O-Matic takes a reading.

## Goals

- Work with avocados of any size, in a cradle that won't fit every one perfectly.
- Never press hard enough to bruise.
- Produce a number that tracks ripening day by day.

## Steps

1. **Home.** Move up until the microswitch triggers, or (no switch) run up for more than the full travel so the carriage rests against the top plate; the 28BYJ-48 just slips harmlessly. Set position = 0.
2. **Tare.** With the pad in the air, zero the hall sensor reading. Doing this every reading cancels temperature drift in the sensor and the PLA flexure.
3. **Approach.** Move down at full speed (~0.5 mm/s) to `last_contact_height - safety_margin` (a few mm). On the first run, creep from the top.
4. **Creep.** Step down slowly, reading force after each small increment.
5. **Contact.** Contact = force above `contact_threshold` (~0.1 N) for 3 consecutive readings. Record `contact_height`.
6. **Preload.** Continue to `preload_force` (~0.2 N). This seats the avocado and takes up cradle wobble. Set this point as travel zero.
7. **Measure.** Continue stepping, logging `(travel, force)` pairs, until `force_cap` (~2.5 N) is reached.
8. **Retract.** Back off to the top and cut motor power.

## The flexure correction

The flexure bends too, so part of the carriage travel after contact is the spring bending, not the avocado squishing:

```
squish = travel - force / flexure_k
```

`flexure_k` (about 2.7 N/mm for a 12 × 4 × 54 mm PLA beam) comes from the coin calibration. Because the flexure is in series with the avocado, the raw travel-vs-force slope would read softer than the fruit really is; the correction fixes that.

## Result

- **Stiffness** = slope of a straight-line fit to force vs. squish (N/mm). This is the main number; it drops as the avocado ripens.
- **Squish at cap** = squish at the force cap (mm). A simpler backup number.
- **Contact height** = for detecting swaps and an empty cradle.

## Automatic events

| Condition | Meaning | Action |
|---|---|---|
| Contact height jumps by more than a few mm | New avocado | Start a new baseline |
| No contact before bottom limit | Cradle empty | Pause testing |
| Stiffness below `ripe_threshold` | Ripe | Send notification |
| Stiffness dropping fast | Close to ripe | Increase test frequency or switch to gentler testing |

## Calibration

**Force sensor (once):** with the carriage parked and the flexure horizontal, read the hall sensor with nothing on the pad, then with coins stacked on the pad (US nickel = 5.000 g; 20 nickels = 100 g ≈ 0.98 N). Fit counts vs. force. Also note how far the tip drops per newton, which is `flexure_k`.

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
