# The electronics boxes and the keyhole mount

The base does not hold the boards itself. Each board lives in its own box, and each box slides onto a pair of **mushroom studs** printed into the base through two **keyholes** in its floor: drop the box over the studs, push it toward the motor end until it clicks, done. Push it back the other way to lift it off. No screws, no tools. The stud and keyhole are the *BTL universal mount* (the v3 stud and the v6 keyhole), shared with other BTL projects, so any box with those two keyholes fits either spot.

Two boxes, side by side on the board side of the channel, so every wire stays on one side:

| Box | Holds | Where | Files |
|---|---|---|---|
| **ESP32 case** | the ELEGOO ESP32 DevKit, USB-C out the motor end of the base, BOOT keycap on the lid (short press = measure now, hold = "it was perfect") | the board side of the base (the side with the hall-sensor wiring) | [`stl/esp32-case/`](stl/esp32-case/): BTL's *ESP32 case for the ELEGOO DevKit v6*, printed as supplied: base, lid with the firm key, keycap and one of the three MX adapters |
| **Avocado holder** | the V-shaped corner with the back gate | the avocado end of the base, where the old yoke slot was | [`stl/gate-frame.stl`](stl/gate-frame.stl): four keyholes in its underside, slots 9 mm long toward the pad. Drop it on 9 mm toward the pad from its place and push it back until it clicks; the pad's push is in the locking direction |
| **Driver box** | the ULN2003 board | right beside the ESP32 case on its nest end, turned crosswise | [`stl/driver-box.stl`](stl/driver-box.stl) and [`stl/driver-box-lid.stl`](stl/driver-box-lid.stl) |

Why boxes and not rails in the base: dev boards have their pin headers right at the board edge, so there is no edge for a groove to grip. A box can hold the board any way it likes and can be swapped without reprinting the 3–4 hour base.

## The studs (on the base, printed with it)

The avocado holder has its own four studs at x 76 and 92, 30 mm either side of the middle (its keyholes' slot ends). The boxes use two pairs, each pair 26 mm apart, standing on the 5 mm deck: the ESP32 pair along the press axis, the driver pair across it. Each stud:

| | mm |
|---|---|
| Stem | Ø 5.0, 1.4 tall |
| Head | 45° cone from Ø 5.0 to Ø 8.0 over the next 1.5 |
| Crown | Ø 8.0, 0.4 tall, 0.35 chamfer on the top edge |
| Total height above the deck | 3.3 |

Positions, measured from the base's corner at the motor end on the board side (X along the press axis toward the nest, Z across toward the other side):

| Pair | Stud centres (X) | Z from the board-side edge | Box when seated (X) |
|---|---|---|---|
| ESP32 case | 20 and 46 | 28.25 | 4 to 62 |
| Driver box | 81.5 (both) | 12.5 and 38.5 | 63 to 100; across, 6.5 to 54.5 from the board-side edge |

The ESP32 case is dropped on 9 mm toward the nest from where it ends up and slid toward the motor end; its USB-C end then sits 4 mm inside the end of the base, so the plug stands out of the machine's end next to the motor. Put it on first and take it off last: its runway is where the driver box sits. The driver box is dropped on 9 mm toward the outer edge (it hangs 2.5 mm over the edge for a moment) and slid toward the channel.

## The keyholes (in the floor of any box)

Measured from the v6 case. The floor is **4 mm** thick where the keyholes are, and the stud disappears into it completely, so the board above is unaffected.

| | mm |
|---|---|
| Round opening | Ø 8.8, through the floor |
| Slot | 5.4 wide, running from the round toward the nest end of the box (the round is the end nearer the motor); slot-end centre **9.0** from the round's centre, full-round end |
| 45° flare | from 1.5 above the floor's underside the slot widens at 45° until it is 8.8 wide (at 3.2), then stays 8.8 up to the floor top: the stud's cone seats in it and pulls the box flat |
| Detent nibs | two half-round bumps, r 0.35, on the slot's sides 2.45 before the slot-end centre, in the bottom 1.5 mm; the stem clicks past them and is held between them and the slot end |
| Spacing | the two slot-end centres 26 apart; the box ends up with the studs at the slot ends |

The pattern takes 42 mm of floor length (4.4 beyond the first round, 2.7 beyond the second slot end), so a box is at least 46 mm long. The driver box is 48 × 37 × 26 mm with the pattern 2.6 mm from its motor end.

## The driver box

Shell 48 × 37 × 26 mm, 2.2 mm walls, R4 corners, keyhole floor; inside, four 3 mm ledges in the corners of the board pocket and a rib behind it, so the ULN2003 (32 × 35 mm) lies on the ledges with its solder side clear of the floor and cannot slide. Two notches open to the top: one in the motor-end wall for the six wires to the ESP32 (IN1–IN4, 5 V, GND), one in the channel-side wall near the nest end for the motor's ribbon. The lid snaps in: a 1.3 mm lip with 0.4 mm bumps on the long sides that drop into a groove inside the walls, four Ø3 pegs that come down to 0.4 mm above the board's corners and keep it on its ledges, five vent slots over the chip. Print the lid upside down (flat top on the bed, pegs up), no supports. If the lid is hard to push on, scale it 99.5 % in X–Y; if it rattles, 100.5 %.

Wiring: the driver box's small notch faces the ESP32 case, so the six wires (IN1–IN4, 5 V, GND) run a few centimetres along the outside of the case into its USB opening next to the plug; the hall wires use the same opening. The wider notch faces the channel for the motor's ribbon, which plugs straight into the ULN2003.

## Screwing the base down

Four ears at the corners (6.5 mm beyond each end of the base, so it is 178 × 165 and still fits a 180 mm bed) each carry a keyhole for a pan- or round-head screw up to Ø8 mm head, Ø4.2 mm shank (#6/#8 wood screw, M3.5/M4):

- **Hang it over screws:** drive four screws into the shelf, heads standing 2.5 mm proud, lower the base so the heads go up through the round holes, slide the base 9 mm toward the nest end. The heads sit in a pocket under a 2.2 mm lip. Screw centres (the slot ends): 156.5 mm apart along the press axis, 151.5 mm across.
- **Or screw it down tight** through the slots from above.

## If you printed a base without the studs

The first base print had slide-in cradles for both boards instead. They are still in the Fusion history (suppressed features `Extrude30`–`Extrude48` in the `Base` component, plus the cover screw hole `Extrude49`), with the matching `board-cover` lid; unsuppress them if you want that version back. On an existing print, cut the two thin lips off the ESP32 cradle rails and the board drops in between them.
