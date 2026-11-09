# TBP35 inlet copper resistance screen

**A conditional design calculation, not a current rating or fabrication release.**
This analysis uses [TBP35](../two-board-power-inlet-fuse-native-01/README.md).
No copper, component or schematic changes were made for the calculation.
The subsequent [TBP36 distribution revision](../two-board-power-regulator-distribution-native-04/README.md)
adds regulator feed/return copper and slightly refills In2. Recompute the
coupled path before using these historical values for the newer full network.

The [calculation](review.json) uses captured native filled polygons, lands and
tracks for four internal inlet planes and five front-copper sections. Each
section is a uniform two-dimensional resistive sheet with ideal equipotential
contact ports. Feed layers In2/In3 are placed in parallel, as are return layers
In4/In5. The five front sections cover jack-to-fuse, fuse-to-inlet-vias,
source-vias-to-Q101, Q101-to-U101 and U101-to-bulk-capacitor copper.

| Assumed copper on every modeled layer | Imposed copper temperature | Modeled copper resistance | Drop at 4 A | Dissipation at 4 A |
| --- | --- | --- | --- | --- |
| 35 µm | 20 °C | 37.17 mΩ | 148.7 mV | 0.595 W |
| 35 µm | 85 °C | 46.66 mΩ | 186.6 mV | 0.747 W |
| 70 µm | 20 °C | 18.58 mΩ | 74.3 mV | 0.297 W |
| 70 µm | 85 °C | 23.33 mΩ | 93.3 mV | 0.373 W |

At 4.83 A, the 35 µm/85 °C case gives approximately 225.4 mV and 1.089 W.
The 4 A load and 4.83 A current-limit screen are conditional design scenarios;
the integrated whole-unit normal/startup load envelope remains to be reconciled.
Neither copper thickness is an accepted manufacturing minimum. Temperature is
an input, not a predicted rise. The model assumes 100% IACS copper and uses the
[NBS copper resistance reference](https://nvlpubs.nist.gov/nistpubs/Legacy/hb/nbshandbook100.pdf).

## What the model reveals

The paired planes split total current approximately evenly, but individual
contacts do not. Under ideal contact assumptions at 4 A, the source via at
(189.95, 112.75) carries about 1.740 A combined across the two feed sheets;
the return via at (197.95, 111.3) carries about 1.841 A across the return
sheets. These are **ideal-port currents**, not validated barrel currents.
Do not size a transition by dividing total load evenly by via count.

The separate In5 fill piece at the (194, 126.7) return via carries no current
in the isolated-sheet inlet model. Native connectivity still joins it through
other copper. This distinction prevents counting every connected fill piece
as an independent inlet path.

The calculated copper drop alone does not justify redesigning the C-shaped
corridor. Continue from its current geometry, resolve the actual stack and
complete the local/main returns and distribution. The paired-plane path,
transition banks and surface entries still require a thermal/current review
against the integrated load and fault envelope.

## Verification and limits

The [independent review](independent-review.json) verifies native contacts,
net/group identity, conservation of current, dissipated energy and scenario
arithmetic. Four tests cover a rectangular conductor's analytical resistance,
parallel sheets, rotation/floating copper, and rejection of open circuits or
overlapping contacts. Final grids are 0.0625 mm for planes and 0.00625 mm for
local surfaces. Each case has three refinements and a shifted final grid;
the largest final refinement/shift difference is 1.332%. This is a numerical
consistency screen, not a rigorous physical error bound.

The [first coarse calculation](../two-board-inlet-resistance-01/review.json)
is retained as preliminary evidence. During refinement, a run was stopped
because distant, electrically separate surface polygons produced unnecessarily
large raster arrays. The completed run removes only surface components that
cannot carry current between its modeled terminals; all selected contacts
remain. No failed run or partial output is used as the selected result.

Excluded: jack/plug and solder resistance; hot fuse resistance; all via
barrels; MOSFET/eFuse on-resistance; local bulk return and downstream
distribution; adapter/cable behavior; intermediate interlayer coupling and
other parallel copper paths; temperature rise, surge inductance and fault
energy. Ideal equipotential banks allow current redistribution that must be
replaced by the actual coupled copper/barrel network for a complete loop
model. The mesh also approximates boundaries and contacts. Results therefore
are estimates, not guaranteed upper or lower bounds.

Next: finish the force/quiet return topology and remaining distribution;
reconcile actual load states; combine accepted copper/plating with local
return, transition and component losses; define prototype current steps and
temperature/voltage checks. The signal board still has 251 opens and the
power board 2,372. Full installed fit, ESS package inputs and manufacturing
outputs remain unfinished.
