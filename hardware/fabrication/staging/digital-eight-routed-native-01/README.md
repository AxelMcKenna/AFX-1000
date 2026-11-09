# Eight-layer digital routing comparison — 56 opens

This separate development trial reduces the retained six-layer design from 71
to **56 open connections across 55 nets**, with zero native geometry, schematic
parity or ERC findings. It is not a fabrication release or a selected physical
stack. The selected DC04 project remains unchanged.

An added In5 signal layer and In6 AGND layer preserve the existing three plane
layers. Removing the long LED_SCK detour temporarily gives 72 opens; sixteen
new joins then give 56. LED_SCK is connected with 46.620 mm of total planar
copper and two vias, versus 96.178 mm and nine vias. This improves geometry;
loading, timing, impedance and reference transitions remain unqualified.

The board has 2,426 tracks and 457 vias. All 201 power/ground pads, 39 local
connections, 33 thermal connections and every earlier connected pad group
remain intact. SD carrier spread remains 5.999 mm with one via per signal.
All four filled planes have a single physical connected union. The minimum
non-exempt drill-edge-to-SMD-copper gap is 0.154984 mm. The 21 retained
mask-covered heat-spreader vias keep their assembly/process hold.

Independent checks are recorded in [native review](review.json),
[net-by-net connectivity](stage-connectivity-review.json),
[placement/drill/SD/plane audit](corridor-audit.json),
[additive route audit](additive-route-review.json), and
[comparison against the 71-open board](eight-layer-comparison.json).
All three independent audit results replay exactly against their recorded
sources. [Eight rendered copper plots](visual-review.json) were visually
inspected. Conditional AP04 context/floor receiving passes for 138 parts and
five mounts; [actual installed-unit receiving remains unverified](conditional-assembly-review.json).

Thirty-nine LED output nets remain open. Further LED escape trials are kept
separately and do not alter this clean checkpoint. Physical stack, copper and
dielectric dimensions, price/process acceptance, all remaining routing,
complete electrical/thermal/assembly checks and manufacturing outputs remain
unfinished. Nominal 1.6 mm in the board file is not an accepted eight-layer stack.
