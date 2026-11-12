# Lid-carried ground splice cage candidate

The frozen r15 electrical graph and wire paths are unchanged. A lower cage and removable cap support the receiving splice at [293,32,29.5], using the existing settings selector PCB holes [307,17.5] and [307,36.5]. Every attachment is lid-carried. L01/R01 cross the fixed/lid boundary and remain unclamped. This is a conditional support candidate, not fabrication release or a service-opening qualification.

The cage accepts the modeled 25 mm by diameter 6.2 mm receiving cylinder with 0.15 mm radial and 0.1 mm axial clearance. Three diameter 1.4 mm wire apertures pass the maximum 1.0922 mm wire diameter. The actual completed TE34130/TE505872P034 splice and sleeve ends must be measured; a smaller or tapered sleeve can move more than the receiving cylinder. The positive translation witnesses establish containment of the modeled cylinder only, not pull resistance or strain relief qualification.

## Hardware and assembly

Replace only the two settings M2x10 screws with M2x12, preserving their original head datum Z45.6. Printed feet occupy Z36.5..38.1 beneath the selector PCB. Washers move to Z36..36.5; nuts occupy Z34.4..36. New shafts extend to Z33.6: full 1.6 mm nut engagement and 0.8 mm protrusion. Original M2x10 would engage only 0.4 mm and is not acceptable in this stack. Release selector hardware remains unchanged. `ground_supported_selectors()` replaces the whole original selector role, preventing duplicate old hardware.

Cap hardware is two M2x8 screws at [289.5,26.5] and [289.5,37.5], shafts Z26..34, heads Z34..36.2; 0.5 mm washers at Z33.5, 1.6 mm nuts at Z26.8. Nut pockets are open below and require holding the nuts until engaged. Both screws have full nut engagement and 0.8 mm protrusion. Threads and screw drive are generic receiving geometry; exact hardware tolerances remain to qualify.

Thread the three unterminated wires through the end apertures before forming/crimping the splice; then lay the completed splice in the lower cage and attach the cap. An already terminated harness cannot be installed through the closed apertures without de-termination. Verify this sequence with the actual crimp tooling and completed sleeve. Remove cap before lifting the splice. Do not infer lid-opening clearance from installed-state checks.

## Verification and limits

Pinned Linux native r4 checks: seven empty collision probes (selectors, ground wires, splice, allocations, structure, cap hardware, halves). Saddle and cap each export as one closed oriented solid. Four 0.3 mm translation probes produce positive closed intersections against axial/vertical stops. Exact seat masks are 0.02 mm planar slabs; no entire pair is waived. Root must recheck current controls, cooling and sensor with the replacement selector role.

The PCB carries bracket loads: PCB strength, printed material/anisotropy, fatigue, screw preload, wire chafe, dimensional tolerance and sleeve retention require physical qualification. Further wire supports and terminal strain relief remain unfinished. No service slack or full harness fit is claimed.
