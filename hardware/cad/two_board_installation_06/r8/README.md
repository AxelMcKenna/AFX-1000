# TBH06 r8 — retained internal routing and separate terminal wires

This follow-on preserves r7. It adds two removable brackets carrying three closed routing eyelets and replaces the former broad terminal fanout with six separate smooth wire paths. The external lead-bay route and final factory lead trimming remain open; this is not a fully released fan harness.

`supports.scad` provides `tbh08_installed()`, replacing the complete older `tbh06_installed()` cooling assembly with relocated nuts, longer local shafts and the new brackets. The original shell and fan bodies remain unchanged. `tbh08_supports()` and `tbh08_replacement_fasteners()` expose the new parts separately. `terminal_harness.scad` provides `tbh08_harness()` in place of `tbh06_harness()`.

## Internal support assembly

The brackets seat against the inner left wall at the existing upper pod attachment holes Y118.5 and Y171.5, Z38. Replace these two M3×8 fasteners with M3×10. The 1.6 mm bracket plates occupy X2.8..4.4; nuts relocate to X4.5..6.9 and screw tips end X8. A source-supported low-head candidate is [Accu SSCL-M3-10-A2](https://www.accu.co.uk/low-head-cap-screws/8723-SSCL-M3-10-A2), specified head maximum Ø5.5×2 mm, fitting the existing Ø5.5×2.5 head allocation. Availability is not claimed.

Thread the uncrimped fan leads through the closed eyes before fitting XHP-3 housings. The eyes guide the bundle transversely; the external bay tie provides axial strain retention. Native export has exactly two connected watertight printed parts, confirming that the three eyelets are attached to their brackets. The eye passages follow the frozen bundle curves with a nominal 2.95 mm channel radius. A deliberately shifted harness intersects the rings, confirming geometric capture rather than relying on open saddle friction.

Plate-to-shell contact is intentional. The shell clearance check excludes only a 0.02 mm slab around the two exact seating faces, not arbitrary nearby volume. The previous unmasked result was zero-volume coincident geometry and is retained under `native-third/`. Root integration separately found the new supports/fasteners clear the latest lid and guide; the inherited pod/lid coplanar boundary is unchanged from r7.

## Individual terminal transitions

The six wires are separate quintic paths from a packed triangular bundle entry to actual XH pin spacing. The maximum allowed insulation OD is 1.9 mm, matching the legacy contact receiving limit. Source data and controls are in `terminal-routes.json`; the path ends vertically at Z22.3 and continues 3 mm straight to the Z19.3 housing top. This avoids inventing a 12.8 mm connector height.

Continuous derivative bounds establish minimum individual bend radius 9.596 mm and minimum wire-to-wire clearance 0.0645 mm. The latter is a nominal geometric clearance between insulating jackets, not an electrical creepage claim or a tolerance guarantee. The project minimum bend allocation is 9.5 mm; physical receiving/formation must establish compatibility with the actual fan lead insulation. The terminal curves are tangent-continuous into the straight entries. `build_terminals.py` calculates chord/facet allowance and uses native sphere radius 0.97 mm to enclose each nominal 0.95 mm wire radius.

The verified pin mapping remains rear pod→F_J202 and front pod→F_J203; pin1 black/ground, pin2 red/switched5V, pin3 yellow/tach. Native tests exclude only each wire set's own intentional mating connector and preserve all other captured obstacles.

## Evidence and remaining work

`verify.py` verifies source hashes, eight strictly empty checks, three positive checks, two closed exports and the exact two-part bracket topology. Earlier failed saddle/strap candidates remain under `native-first`, `native-second` and `native-third`. They are not assembly alternatives.

External bay routing is still being revised. `external-route-search.json` is a failed single-lead search in the old bay: it finds only about 4.9 mm radius under the conservative cavity screen. That is not a proof of impossibility and is not accepted. The bay bridge obstructs a direct descent from the fan slot to the port; a follow-on must address that before assigning cut lengths. Keep factory leads untrimmed until the complete route, contact preparation and service method are established. Manufacturer fan lead-emergence coordinates are not dimensioned; receiving must resolve that short transition.
