# Formed nineteen-button ground chain

This candidate supplies all **19 non-scene buttons from D_J2002 pin 15**, verified
as LINK_AGND in the native signal netlist. `left-routes.json` is the exact ordered
endpoint contract: one feed plus 18 inter-button wires, one wire per terminal,
using only the manufacturer's internally connected terminals 3 and 4. Terminal
assignment alternates with approach direction. Hold terminal 4 is externally
unused. The ten scene buttons and selector returns are not included here.

Every continuous wire uses straight lines, circular arcs of at least 12 mm
centerline radius, or smooth height transitions with verified curvature bounds
above that minimum. This implements the Alpha 5853 manufacturer bend requirement
established in r13. Horizontal/tangential wire attachment to the switch leads
is an explicit receiving condition; a qualified solder/strip/insulation process
and local strain support are still required. The internal switch connection is
not a bent external wire.

The feed follows the selected r13 escape, then passes around the front of the
display at Z30 before rising smoothly to the first button. Inter-button wires mostly follow Z31.6; the return to
Hold passes at Z30 and rises smoothly. The wire-to-wire check covers all 171
pairs and finds **0.4 mm minimum surface gap** for the inflated Ø1.2 mm model.
The initial straight crossing and two tighter approaches were corrected rather
than accepted as intentional wire contacts.

The first root assembly screen caught a real collision with the BPM display:
the feed crossed display leads, quantize-to-auto crossed its front post/shaft,
and tap-to-nudge_up crossed the tray underside. The exact display-only probe
reproduced20.72641mm³ with the same bounds as root's20.74830mm³ full-controls
check (different native tessellation). No contacts were waived.

Revision r4 routes the feed and quantize-to-auto wire around the display's front,
and gives tap-to-nudge_up a20.9069mm-radius rear arc around the tray and rear post.
Endpoint adjacency is unchanged. Final local native evidence is `structure-all-r4`,
`allocations-all-r4` and `display-clear-r4`, all empty intersections. The failed
`display-witness-r3` is retained as regression evidence. The prior root sensor
and cooling passes were for r3; repeat full-root checks for r4 before promotion.

Use current original SCAD for Booleans. Historical r3 positive feed STL was closed;
r3 positive links had16badedges (6excludeddegenerate triangles). Those older
STLs are not current-r4 geometry or proof. Root will generate current positive
operands during integration.

`verification.json` checks endpoint coordinates against the frozen world datums,
independent 19-button membership, terminal exclusivity, native source net,
analytic curvature bounds for the height changes, sampled curvature and all
wire pairs. It does not qualify manufacturing tolerances or handling loads.

`workflow_adapter/left-ground-registry.json` supplies separate feed and links
roles, plus the unchanged r13 right-source exit as a temporary partial role.
When selecting these, remove the old combined r13 two-exit role and the r12
whole-ground wire role: the left feed already contains its source turn. The r12
splice is not part of this left-chain candidate.

Remaining: full current root assembly checks; complete scene/selector branch;
wire supports, strain relief and opening/service slack; actual connector exit
and switch solder-joint receiving acceptance; current/fault/pull acceptance.
There is no fabrication release or cut-length instruction.
