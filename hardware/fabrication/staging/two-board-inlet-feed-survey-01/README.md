# Inlet feed and return survey after TBP32

The selected two-board design still has **no connected fused feed or jack
return to its input-protection cell**. Both TVS pads are also isolated.
The jack-positive to fuse-input connection survives as four front-side
tracks; the final 2.545 mm section is only 1.2 mm wide. Its capacity needs
to be checked with the accepted stack and operating/fault conditions.

The [captured geometry/connectivity review](review.json) identifies every
relevant terminal and computes shortest paths within an inset board outline.
This is a geometric planning model, not authored or clearance-checked copper.

| Endpoint pair | Straight-line distance | Minimum in the 0.5 mm inset outline model | 8 mm-wide corridor model |
| --- | --- | --- | --- |
| Fuse output to Q101 source pin 1 | 125.8 mm | 489.0 mm | 506.5 mm |
| Jack return to U101 GND pin 8 | 150.1 mm | 508.1 mm | 526.6 mm |

The C-shaped cutout forces a PCB-only route around the top and left arms.
The model uses mitred outline offsets and ignores existing copper, holes,
component bodies and layer transitions. Its wide paths do not prove that
usable power copper fits, and the terminal-center endpoints still require
local attachment design. The straight lines cross the cutout and are not
PCB routes; they also do not establish a fitted harness length.

The next design step is to compare a paired, adequately sized PCB feed and
return with a paired jumper across the opening, including connector losses,
physical clearance, serviceability, fault protection and EMI. Neither option
is adopted by this survey, and the two-main-board partition is unchanged.
A jumper could shorten the electrical path but requires reviewed connectors,
strain relief and an installed cable envelope. The PCB-only option requires
a long, coordinated copper corridor with verified loss and temperature rise.

TI's [TPS2663 layout guidance, section 9.6.1](https://www.ti.com/lit/ds/symlink/tps2663.pdf)
calls for short power connections sized for at least twice the full-load
current. Track width alone does not establish that capacity. Check every
neck-down, via transition and shared-return section, the complete source
and startup/fault current profile, the fuse, and the TVS return loop. Preserve
AUX's intended local return topology while joining the complete source return.

This survey changes no PCB, selects no manufacturing stack and releases
nothing for fabrication. The selected project remains
[TBP32](../two-board-power-fast-ov-return-native-02/README.md).
