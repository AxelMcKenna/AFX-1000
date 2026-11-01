# Private bounded source-wire exit search

This study ranks two Alpha6715 AWG18 quarter profiles leaving the unchanged fed-R58 J4 pads at world (161,120.5,6.62) and (161,126.5,6.62). It changes no PCB, housing, shared helper, shared `PROFILES` entry or sealed source. A screened source exit is not a complete route into the proposed J13 receiver.

The actual native case, return hardware and positive-link STL exports are copied under `inputs/`, with source/evidence hashes in `capture.json`. Actual component envelopes, switch diagnostic boxes, mount cylinders and board reserves come from the frozen formed-wire snapshot with its fed-R58 override. VTK9.6.2 computes distance to the actual captured surfaces. No radius, 0.65mm independent position allocation, 0.25mm clearance or 0.005mm geometry reserve was reduced.

The search bounds are R10/12/14/16 mm, azimuth−90..+30° and end planes18..32mm, with nonnegative initial straight `endplane−6.62−R`. The minimum allowed centreline radius remains9.6393mm. Every inflated quarter must remain wholly inside [154,104,3]..[185,139,37]; artificial clipping faces never create permission to leave this window. The receiver ear starts at X180, beyond the maximum possible inflated quarter extent X178.787, but its receiving/free-span geometry remains a separate native check.

The coarse 0.25mm arc-length sample grid tested1326 valid-radius/height profiles, rejected30 at the clipped window, retained49 positive/64 return individual profiles and found262 pairs. Refinement around the strongest coarse neighborhoods used0.08mm sampling and retained14989 pairs. Six candidates were rechecked with0.02mm maximum arc-length spacing.

| Candidate | Positive: radius / azimuth / end plane | Return: radius / azimuth / end plane | Tight minimum screen margin | Tight pair margin |
|---|---|---|---:|---:|
| Coarse native candidate |10mm /0° /25mm|16mm /−40° /31mm|0.5342mm|0.8478mm|
| Refined candidate |10mm /+7.5° /25.25mm|16mm /−42.5° /31.75mm|0.6643mm|0.7467mm|

`selected-coarse-pair.json` and `selected-refined-pair.json` provide exact wrapper-friendly `PROFILES` tuples, fed source hash and source/evidence maps. The coarse receipt stays immutable while root validates it natively. `selected-refined-pairs.json` retains all six tight checks and nearest-point details.

Clearance sampling subtracts half the maximum arc-length spacing for each independent curve, using the distance function's1-Lipschitz property. Pair checks subtract both position allocations and both sample covers. The native circumscribed-sphere factor and native polyline chord bound are included. The bare3.1mm section uses its own maximum conductor radius; the insulation cut is conservatively enclosed by a capsule, so this screen can reject usable profiles. Switch AABBs remain diagnostics; the exact rotated switch solids are contained in the case STL.

The return STL has zero boundary edges and three nonmanifold assembly-contact edges. It was not smoothed or repaired. `outside-witness.json` independently connects each nominal source centre to a point below all captured closed solids without crossing a triangle surface. That mathematical zero-radius witness is not a wire route and does not exempt actual wire from the window rule. Positive surface-distance covers plus those outside witnesses avoid relying only on pseudonormal sign at contact edges. The known original east pair reproduces its28.6584mm³ native hardware collision while case/component/pair screens remain clear.

Four boundary/reference/evidence tests pass. They cover clipped-window rejection, radius/straight limits, both independent wire position allocations, open-surface rejection, known native failure and current evidence hashes. These are screening tests, not physical qualification.

Full native case/hardware/component/pair, source joint, bare conductor, flat cut, actual minimum bores and the complete C1 free span into J13 still require root's checks. Any new geometry/current source snapshot requires rebinding. Forming accuracy, insulation/solder/strain, contact resistance, current/temperature/lifetime and fabrication remain unqualified. This bounded search makes no global impossibility claim.
