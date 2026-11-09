# Eight-layer digital checkpoint — 52 opens

The latest separate digital trial has **52 open connections across 51 nets**,
down from the retained six-layer board’s 71. Native KiCad 10.0.7 reports zero
geometry, schematic-parity and ERC findings with all categories enabled.
The complete board and unit remain unfinished; this is not a fabrication release.
Selected DC04 and AP04 remain unchanged.

The eight-layer comparison first reached [56 opens](../digital-eight-routed-native-01/README.md).
Four coordinated escapes and In5 routes now connect LED_04, LED_06, LED_08 and
LED_71. Removing the three unused escape branches eliminated their dangling-via
warnings. This final step adds 104 segments and four conventional 0.60/0.30 mm
vias while preserving every object and connected pad group in the 56-open parent.
Total copper is 2,530 tracks and 461 vias.

| Verified property | Result |
| --- | --- |
| Native geometry / parity / ERC | 0 / 0 / 0 |
| Open connections / open nets | 52 / 51 |
| Remaining LED output nets | 35 |
| LED_SCK planar copper / vias | 46.620 mm / 2; formerly 96.178 mm / 9 |
| Preserved power-ground pads / local pairs / thermal branches | 201 / 39 / 33 |
| SD carrier spread / vias per signal | 5.999 mm / 1 |
| Physically connected plane fills | Four; one polygon union per plane |
| Minimum non-exempt drill-edge-to-SMD-copper gap | 0.154984 mm |
| Retained mask-covered heat-spreader vias | 21, with process acceptance outstanding |
| Conditional AP04 receiving | 138 parts and five mounts clear retained context/floor |

The four new LED nets have total planar copper lengths 75.544, 76.961, 79.773
and 49.333 mm respectively, with one via each. Their loading, compliance margin,
transients, coupling and installed harness behavior remain unqualified.
The 46.620 mm clock is a geometric improvement; it still needs an electrical
interface budget. Adding layers does not itself validate impedance or return paths.

The [checkpoint audit](checkpoint-review.json) replays the complete 71 → 56 → 52
chain. Supporting evidence includes [native results](review.json),
[net-by-net connectivity](stage-connectivity-review.json),
[placement/drill/SD/plane checks](corridor-audit.json),
[exact additive LED delta](additive-route-review.json),
[conditional receiving](conditional-assembly-review.json), and
[eight visually inspected copper plots](visual-review.json).

The first broad search hit its 500,000-node bounds on all seven LED escapes.
A finer geometry diagnostic showed that four had inner-layer access; confining
the search to In5 routed those four without additional layer-transition vias.
The other three escapes were removed. None of the remaining sixteen non-output
control nets has In5 contacts in every disconnected group. They need explicit
new escapes, coordinated local rework or placement changes before repeating
that search. The thirty-five remaining LED outputs also need renewed escape
planning. A search failure is not proof that the board is unroutable.

The physical sequence is F / In1 AGND / In2 power / In3 signal / In4 AGND /
In5 signal / In6 AGND / B. The file’s nominal 1.6 mm thickness is a placeholder;
real copper/dielectric thicknesses, stack/process, cost, mask/tenting, stencil,
parts, mating connectors, harness and supports remain unaccepted.

For the complete unit, the current selected audio board has 267 opens and the
missing ESS footprint; the negative-startup board has 138 opens and two explicit
isolated-domain ground warnings. Existing closed individual board checks do not
establish complete installed power, noise, stability, fault or thermal behavior.
Next work is coordinated remaining escapes/routing, the exact ESS land/interface
data, one coherent physical-board selection and stack, followed by current
assembly receiving, inspected manufacturing outputs and a bounded first-article
inspection/bring-up package. See the [full-unit inventory](../../README.md).
