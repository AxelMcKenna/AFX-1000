# TBH05 sensor carrier and magnet escape barrier

**Current spring completion candidate:** see [SPRING.md](SPRING.md) for the selected spring, positive custom clevis-pin anchors, replacement bracket/arm and final `spring-verified-r2` evidence. The r3 carrier below remains unchanged. Its original-anchor spring discussion is retained as reference and superseded by that add-on.

This is a new **unpowered mechanical interface candidate**, fitted to the unchanged TBH01 r6 housing and TBH03 r5 lever. It closes the modeled carrier attachment and adds positive axial magnet capture. It does **not** supply a routed/populated angle-sensor PCB, a qualified magnet bond, or a selected return spring.

The existing source specified a custom AS5600 PCB reserve, not an off-the-shelf board. This design therefore specifies a **new 20 × 18 × 1.6 mm PCB**, instead of guessing holes in an existing board. Its sensor axis is unchanged at Y82/Z31.6. The original 20 mm-tall reserve had insufficient room for an actual top clamp below the button guide; shortening its top edge by 2 mm fixes that interface. A PCB designer must accept and implement this contract before printing for an actual populated board.

## Files and geometry

- `carrier.scad`: editable geometry. `tbh05_installed()` exposes the complete nominal assembly, hardware-head and electrical-envelope allocations for integration. Include the source with a nonmatching `part` selector, or use modules with all inherited housing definitions available.
- `mechanical-contract.json`: dimensions, PCB edge keepouts, component/lead/wiring reserves, fasteners and spring geometry.
- `verified-r3/review.json`: final native cases and recursively bound source hashes. Nine empty interference checks, two printable solids and one positive magnet-capture control.
- `verified-r3/sensor_carrier/sensor_carrier.stl` and `verified-r3/sensor_cap/sensor_cap.stl`: native print candidates, millimetres, base at Z0.
- `preview-r3.png`: exact exported carrier/cap meshes with the nominal custom PCB/package and original lever; omitted wiring/spring/fasteners are identified.
- `analysis.py`, `run.py`, `preview.py`: regenerate scalar evidence, isolated native checks and preview. Run native checks with a fresh output name; prior evidence is never overwritten.

The carrier uses the existing **left lever bolts at (306,69) and (306,102)**. Replace those two M3×20 bolts with **M3×25** and retain 0.5 mm washers, head OD≤5.5 mm and washer OD≤7 mm. The 2 mm feet sit on top of the existing bracket. Screw tips reach Z−4.9, giving 1.1 mm nominal clearance with the existing ≥6 mm feet. Measure actual thread engagement and tip clearance.

Two horizontal **M2×5 screws**, head OD≤3.8 mm and height≤2 mm, secure the removable cap. Tap the two Ø1.6 pilots M2 after printing. The cap enters from above; its tabs lie outside the end rails, so no screw passes through the PCB. Do not substitute taller vertical cap screws: the guide is directly above this assembly. Inspect the thin features, holes and magnet-barrier supports in the slicer; no printer/material process is qualified here.

## Sensor PCB receiving contract

The board is vertical: X299.7..301.3, Y72..92, Z21.6..39.6. It slides into 2 mm-wide X slots with no drilled mounting holes. Nominal 1.6 mm stock and the 1.5–1.7 mm receiving interval leave play; printed dimensions must be measured and shims or a dimensionally corrected carrier used to achieve alignment. Do not infer precise sensor centering from loose slots.

Keep both Y-edge margins and top/bottom margins free of copper, pads and components as specified in the JSON. The sensor and its lands receive a conservative 6.4 × 6.4 mm YZ envelope, projecting 1.75 mm toward +X. That is an allocation, not an approved supplier maximum. The board rear has a 1.5 mm-deep central population/lead reserve and a separate X293.7..299.7/Y76..88/Z23..28 wiring/connector reserve. The eventual board and selected connector must fit those bounds or the carrier must be revised. The rest of the harness is not defined by this local reserve.

Insert the populated board with the cap removed. Its component side faces the magnet (+X). There is no retained board polarity/connector design yet. After assembly, confirm the package center actually aligns to Y82/Z31.6 and measure the magnet/package gap throughout lever endplay.

## Magnet capture and magnetic alignment

A stationary polymer ring lies at X303.5..304.3, with a Ø4 opening in front of the existing Ø6 magnet pocket. It blocks a Ø6 magnet from leaving axially. The ring and both supports are physically part of the carrier, not floating preview geometry. The native positive control overlaps the barrier with an escaping magnet; full lever sweep includes ±0.5 mm axial motion and the earlier 0.1 mm rotor expansion.

**The ring does not transmit torque.** A compatible selected adhesive and verified bond to the rotor are still required; a loose magnet can remain captured while giving a wrong angle. Install and bond the magnet before fitting the carrier. Do not change magnet thickness or polarity silently: the existing pocket is for Ø6 × 2 mm diametric magnetization. Grade, dimensional tolerances, adhesive compatibility, retention under shock and the magnetic field remain unqualified.

At the allocated package face and a nominal seated magnet front of X305.1, the nominal physical gap is 2.05 mm, ranging 1.55–2.55 mm across the ±0.5 mm geometric allowance. This arithmetic does not prove acceptable field strength. The manufacturer's [AS5600 evaluation-board manual](https://look.ams-osram.com/m/4f8342513a447495/original/AS5600_UG000254_2-00.pdf) illustrates a nonmagnetic holder, a 6 × 2.5 mm reference magnet and 0.5–2.5 mm gap; it instructs alignment using the AGC reading. Its reference magnet is **not** the current 2 mm-thick design magnet. Select and test the actual magnet, verify magnet-present/field status and angle through the full stroke, and adjust the carrier if required.

## Return spring: concrete remaining work

The unchanged fixed eye is (316,70,35.6); the rotating eye follows (316,82+10sin(a),31.6+10cos(a)). Eye spacing rises monotonically from **13.4164 to 18.2243 mm** over 0–35°, requiring **4.8079 mm travel**. The restoring moment arm is 8.9443 to 6.6527 mm. `analysis.py` checks the geometry independently; a conservative Ø4.02 mm corridor covers a ≤4 mm spring through continuous motion using hulls between 1° poses (0.01 mm radial reserve exceeds the chord error).

That corridor clears the modeled shell, controls, PCB envelopes and new carrier. It is not the actual spring, hooks or attachment design. The existing Ø2.2 cross holes do not automatically accept a catalogue spring's closed loops. Final spring selection needs the actual hook/clevis attachment geometry, preload, load/stroke rating, fatigue life and desired hand force; then repeat the local anchor/lever interference and physical return tests. The [Lee Spring catalogue](https://www.leespring.fr/download/Lee_Spring_Catalog_US_Eng.pdf) provides dimensional/load candidates, but no catalogue part has been adopted or ordered here.

## Validation scope and remaining gates

Final native evidence checks nominal carrier/cap/PCB allocations and hardware heads against shell, current component/lead envelopes, controls and the expanded moving lever. The intentional bracket seating contact uses the same 0.01 mm contact-plane exclusion as earlier packages. These are geometric checks, not a blanket manufacturing tolerance proof.

Remaining gates are: accept and electrically implement the custom sensor PCB and connector; select magnet/adhesive and exact spring/hooks; verify actual print fit, alignment, AGC/field status, rotation, return force, wear and retention; integrate the full harness. No powered or full-unit fabrication release is claimed. Prior r6/r5 packages were not modified.

Trial01 failed at sandbox Docker socket access and trial02 found the daemon stopped; no CAD process started in either case. These are recorded separately from CAD failures. Trial03 found an actual cap/guide interference; trial04 corrected it, and subsequent revisions strengthened cap screw bosses and added explicit electrical envelopes. Only `verified-r3` is the current evidence.
