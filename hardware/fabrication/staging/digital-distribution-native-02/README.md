# DC03 digital distribution candidate

The selected combined digital PCB now connects every pad on AGND, 5V_DIG,
SEED_VIN, V3V3_IO and V3V3_ANALOG. It is not released for fabrication.

| Check | Result |
| --- | --- |
| Electrical parts / physical terminals | 138 / 709 |
| Unrouted connections | 255, reduced from DC02's 427 |
| Native geometry / schematic parity / ERC findings | 0 / 0 / 0; all categories enabled |
| Native power/ground witnesses | 201 pads on five nets |
| Original DC02 objects | All footprints, 59 tracks, eight vias and root geometry preserved exactly |
| Added copper | 186 tracks, 128 vias, two planes |
| Total tracks / vias | 245 / 136 |
| LED-driver thermal vias | U3001: 9; U3002: 6; U3003: 11; U3004: 7 |

In1 is the continuous AGND reference plane; In2 distributes 5V_DIG. Both native
filled zones form one valid polygon with holes. Outer-layer branches distribute
both 3.3 V rails; a 1 mm-wide, 31.615 mm Seed VIN feed joins R1001 to U1001. All
39 previously verified bypass/filter/reference connections remain connected.

The drill map distinguishes 115 conventional vias whose holes clear every SMD
copper land by at least 0.15 mm from 21 thermal vias in the four drivers'
mask-covered EP copper. These 21 clear the package's actual mask/paste openings
by at least 0.98 mm and all other SMD copper by at least 0.15 mm. They explicitly
request tenting on both faces; no filled/capped process is assumed. Twelve
additional thermal connections use 1 mm-wide copper branches to vias beyond
the EP copper. Native connectivity verifies all 33 connections to the EP and
input ground. Mask registration, tenting and assembled thermal performance
still require acceptance.

The partial Seed-feed sensitivity model includes 32.815 mm of 1 mm copper,
two full-length via barrels and R1001 at its initial high 1% tolerance. At the
retained 1 A engineering allocation, it gives 0.493 V drop for illustrative
35 µm copper/25 µm plating at 20°C, or 0.508 V for 25 µm copper/15 µm plating at
85°C. R1001 contributes 0.4747 W. These are conditional calculations, excluding
plane/return/harness/source losses, resistor TCR and self-heating. They do not
establish an acceptable installed VIN interval or current capacity.

The separate 0.764 A LED allocation and 1 A Seed allocation remain unchanged.
Actual LED voltage/current, Seed output-current limits, current-reference
return/noise, power-plane reference transitions, copper stack, temperature rise,
fault behavior and final assembly receiving remain unresolved. The remaining
255 opens are outside the five completed supply/ground nets. Final signal
routing must preserve the local cells and these power paths, followed by fresh
native, drill, signal/return and power/thermal review.

Evidence: [native checks](review.json), [native connectivity](distribution-connectivity-review.json),
[independent handoff and drill map](handoff.json), [visual review](visual-review.json).
The four [copper plots](plots/) were rendered at 300 dpi and inspected. Crowded
Fab annotations remain unsuitable as final assembly drawings.

Reproduce the independent audit with
`python -m hardware.fabrication.audit_digital_distribution` only in a fresh
output context, or call its `check()` function to compare with `handoff.json`.
Mac CAD remains disabled; all native evidence uses the authorized pinned Linux
KiCad container. No fabrication order, upload or supplier message was made.
