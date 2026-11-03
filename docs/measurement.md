# Measurement routine

This describes how Ripe-O-Matic takes a reading.

## Goals

- Work with avocados of any size, in a cradle that won't fit every one perfectly.
- Never press hard enough to bruise.
- Produce a number that tracks ripening day by day.

## Steps

1. **Home.** Move up until the top limit switch triggers. Set position = 0.
2. **Tare.** With the pad in the air, zero the load cell. Doing this every reading cancels temperature drift.
3. **Fast approach.** Move down quickly to `last_contact_height - safety_margin` (a few mm). On the first run, skip this and creep from the top.
4. **Slow approach.** Step down in small increments (e.g. 0.02–0.05 mm), reading force after each step.
5. **Contact.** Contact = force above `contact_threshold` (~0.05–0.1 N) for 3 consecutive readings. Record `contact_height`.
6. **Preload.** Continue to `preload_force` (~0.2 N). This seats the avocado and takes up cradle wobble. Set this point as distance zero.
7. **Measure.** Continue stepping, logging `(distance, force)` pairs, until `force_cap` (~2–3 N) is reached.
8. **Retract.** Back off to the top.

## Result

- **Stiffness** = slope of a straight-line fit to force vs. distance (N/mm). This is the main number; it drops as the avocado ripens.
- **Squish at cap** = distance from preload to force cap (mm). A simpler backup number.
- **Contact height** = for detecting swaps and an empty cradle.

## Automatic events

| Condition | Meaning | Action |
|---|---|---|
| Contact height jumps by more than a few mm | New avocado | Start a new baseline |
| No contact before bottom limit | Cradle empty | Pause testing |
| Stiffness below `ripe_threshold` | Ripe | Send notification |
| Stiffness dropping fast | Close to ripe | Increase test frequency or switch to gentler testing |

## Calibration

1. Run 5–10 avocados through, logging every reading.
2. Each day, also do the thumb test and note when each one was perfect.
3. Use those notes to set `ripe_threshold` as a stiffness value or as a percent drop from day one.

## Avoiding bruising

- Wide, soft, domed pad (~20 mm).
- Hard force cap; never position-only control.
- Rotate the contact spot between readings if the design allows it.
- Test less often once the avocado is close to ripe.
- Check early test avocados by cutting them open and looking under the pressed spots.
