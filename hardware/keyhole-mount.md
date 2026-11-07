# The electronics box and the keyhole mount

The base does not hold the boards itself. Instead the electronics shelf (the flat area beside the channel, on the opposite side from the yoke) carries **two mushroom studs**, and the box with the ESP32 and ULN2003 in it has two matching **keyholes** in its bottom. Drop the box over the studs, slide it 6 mm along the press axis, and the cone under each stud head pulls the box down flat. Slide it back to lift it off. No screws, no tools, and any box with these two keyholes fits: the same mount is used on other BTL projects (it is the *BTL universal mount v3* stud, unchanged), so a box designed for one of them slides onto the Ripe-O-Matic too.

Why a box and not rails in the base: dev boards have their pin headers right at the board edge, so there is no edge for a groove to grip. A box can hold the board any way it likes (pin-row slots, standoffs, a lid pressing it down) and can be swapped without reprinting the 3–4 hour base.

## The studs (on the base, print them with it)

Two identical studs, **26 mm apart** on a line parallel to the press axis, standing up from the shelf (the 5 mm deck).

| | mm |
|---|---|
| Stem | Ø 5.0, 1.4 tall |
| Head | 45° cone from Ø 5.0 to Ø 8.0 over the next 1.5 |
| Crown | Ø 8.0, 0.4 tall, 0.35 chamfer on the top edge |
| Total height above the shelf | 3.3 |

Where they are, measured from the base's corner at the motor end on the shelf side (X along the press axis toward the nest, Z across toward the channel): stud centres at X = 36 and X = 62, Z = 27.5. The usable shelf around them is **98 mm along the press axis** (from the motor end of the base to 4 mm short of where the nest swings) by **56 mm across** (from the base edge to the channel's outer wall), with nothing above it, so the box can be as tall as it needs. The stud line runs down the middle of that strip.

## The keyholes (in the bottom of any box)

| | mm |
|---|---|
| Round opening | Ø 8.6, centred on each stud position (26 mm apart) |
| Slot | 5.4 wide, running 6 mm from the round's centre, full-round end; both slots point the same way, along the 26 mm line |
| Wall thickness at the keyholes | 1.6 (that is where the cone meets the slot edge: the box is pulled flat as it slides) |

Tuning after the first print: if the box won't slide home, open the slot to 5.6; if it rattles, thicken the wall to 1.8 or print the box 0.5 % smaller in X–Y. The studs are symmetric, so the box can be put on facing either way.

The box's outside can be anything. For the Ripe-O-Matic it needs the ESP32 (28.3 × 51.6 mm, 30-pin, USB-C on one short end) and the ULN2003 board (32 × 35 mm), a cut-out for the USB cable, and an exit for the motor ribbon and the three hall-sensor wires toward the channel. Stacking the ULN2003 above the ESP32 keeps the footprint within the shelf; side by side they are too wide.

## If you printed a base without the studs

The first base print had slide-in cradles for both boards instead. They are still in the Fusion history (suppressed features `Extrude30`–`Extrude48` in the `Base` component, plus the cover screw hole `Extrude49`), with the matching `board-cover` lid; unsuppress them if you want that version back. On an existing print, cut the two thin lips off the ESP32 cradle rails and the board drops in between them.
