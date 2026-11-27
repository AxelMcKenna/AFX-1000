# Formed ground connector exits

Alpha 5853 specifies a bend radius of **10× cable diameter**, both in the cached
manufacturer PDF's Properties section and on the manufacturer product page:
https://www.alphawire.com/products/wire/hook-up-wire/premium/5853 . At maximum
1.0922 mm OD this requires 10.922 mm. This study selects **12 mm centerline
radius**, leaving an 11.4 mm inside radius even for the inflated Ø1.2 mm model.

The r12 candidate cannot simply be rounded: the independent tangent-length
audit rejects in-place radius12 fillets for all 32 paths. It remains an electrical
and receiving-space study, not a fabrication-ready route.

The first tested +X exit arcs hit holder structure (2.6133 mm³). Two -X exits
from D_J2002 also hit structure (5.2563 mm³). Parallel -Y turns cleared structure
but converge too closely to accept as a wire pair. Those trials are historical;
use the `selected-final` evidence and the selected no-argument module below.

`panel_ground_selected_exits()` exports two actual quarter-circle receiving
curves:

| Source | Direction | End XYZ, mm |
|---|---:|---|
| D_J2002:15 | 250° | 234.675758, 39.723689, 39.04 |
| D_J2002:16 | 270° | 238.78, 36.46, 39.04 |

Both begin at the r12 provisional Z27.04 wire exit datum. They clear frozen
local structure and conservative allocation sources. The minimum centerline
separation is 2.38184 mm, giving 1.18184 mm modeled surface gap. Curves are
sampled every 3°; the maximum chord sagitta is 0.004113 mm. The verifier bounds
sampling/faceting error and confirms the inflated model still encloses an ideal
arc swept with the manufacturer's maximum wire radius.

Proposed next topology uses these two native LINK_AGND pins for 19 non-scene
buttons and 10 scene buttons plus two selector commons, respectively. D_J2001
pins 15/16 and D_J2003 pin 1 would be externally unused. This removes the blocked
source region and the unselected five-pin mate from the ground harness without
changing PCB nets. **Only the connector escape geometry is implemented here.**
The remaining chain order, terminal 3/4 approach direction, complete formed
routes, strain supports, opening slack and current/fault acceptance are pending.
The selected tall female stack and exact wire exits remain receiving conditions.

Do not overlay these curves onto all r12 wires and call that a complete harness.
They replace the initial root transitions, not the rest of the design. Native
checks do not yet include the root assembly's latest moving mechanism, ribbon,
LED carriers or cooling harness; that integration must precede any fit claim.
