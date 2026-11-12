# TBH06 installation audit and external cooling alternative

This directory adds current-board installation evidence and a separate, editable external-fan housing candidate. **It does not replace the sealed r6 fit prototype or release a powered enclosure.** No PCB, prior print package or root documentation is changed.

## Current connector and service evidence

`installation-audit.json` captures all 78 connector, probe and force-terminal footprints from the signal-main and TBP66 boards, including actual pad coordinates and net names. It binds both native files and the r6 geometry by SHA-256. The count is not 78 required cables: some are test points or legacy interfaces awaiting consolidation.

Thirty footprints have obstacles within a conservative upward service prism (existing allocated body footprint expanded 0.5 mm in XY, from body top to the 42.2 mm guide plane). This is a headroom warning, not proof that a particular plug cannot fit. A real mate may be smaller or side-entry; removable lid controls change the service sequence. No generic header has been silently assigned a commercial mate. `installation.scad` exposes those exact probe volumes for integration.

Examples: D_J1001 has 8.09 mm allocated extra vertical room before a scene-switch/holder reserve; E_J10 lies below the X-pitch pot; E_J11 lies below a pad switch/holder. The actual board-to-board digital feed is E_J4 (`PWR_5V_DIG`, `PWR_AGND`) to a yet-finalized signal destination such as D_J1001 (`D__5V_DIG`, `LINK_AGND`). Those different namespaces are recorded, not automatically declared equivalent. Multiple signal power ports and explicitly unselected NF interfaces remain. A pin-approved harness, conductor sizing, bend radii, retention and installed routing must follow the electrical interface decision.

The r6 source includes only allocated component heights, not received supplier-exact solids. The new carrier/sensor work must be added to this audit before claiming complete installed fit.

## Concrete cooling alternative

The existing cavity cannot receive a vertical 40.5 mm maximum fan body plus 0.5 mm reserve on each face between its floor and guide/lid. A conservative 2 mm grid search tests 144,130 horizontal body placements and finds 1,587 free body boxes. These are not fan assemblies: ducts, guards, mounts and airflow are absent. The search intentionally overexcludes concave board regions and cannot prove absence at unsampled positions.

`cooling_candidate.scad` instead places two external intake pods on the **left** wall, centred at Y45/Y145 and Z22.8. They feed 36 ×30 mm slots at Z8..38. Matching opposite-side exhaust slots avoid the retained lever reserve. The shell is a derived `difference()` of r6: PCB supports, lid interfaces and prior source remain unchanged. New sidewall holes and vents mean this is a **different shell**, not an add-on that can simply bolt onto an unmodified r6 print.

- Fan candidate: retained Sunon MF40100V1-1000U-G99, maximum 40.5 mm square ×10.5 mm thickness; 32±0.3 mm mounting pitch and 4.3±0.3 mm holes, from the source-pinned [SF01 review](../a12/thermal/forced_air_sunon/README.md) and [manufacturer drawing](https://www.sunon.com/PROSEARCH_FILES/%28D04114160G-02%29-1.pdf).
- Cavity: 41.5 mm square ×12 mm axial. Measure fan thickness and use rigid perimeter shims to remove axial slack without crushing the frame. Blades must remain unobstructed. Fan label, flow direction, lead exit and actual frame corner details require receiving checks.
- Overall envelope: **359 ×192.4 ×45.6 mm**, including modeled left-side M4 bolt heads, excluding external wires/plugs and feet. Pods are above the original floor plane; retained ≥6 mm feet remain necessary. Fans consume outside desk space and need additional unobstructed intake/exhaust space, not included in that body envelope.
- Each pod uses four M3×8 sidewall bolts, head envelope Ø5.5×2.5, with M3 AF5.5×2.4 nuts inside. Screw tips reach X6; native component/control collision checks pass.
- Each fan/guard uses four **M4×20 bolts**, head envelope Ø7×4, with captive AF7×3.2 nuts behind the pod. Pod/guard clearance holes areØ4.8; AF7.8 nut pockets permit alignment before tightening. Assemble loosely, align bolts to actual fan holes, then tighten to an approved fan/frame torque. The supplier's minimum4.0 mm hole extreme provides no positive clearance to a nominal4.0 mm bolt: check actual receiving fit rather than forcing the bolt or calling the contact a native collision failure. Fan clamping, torque and vibration acceptance remain physical tests.
- The selected mesh candidate is [Howard Wire Cloth304 stainless woven10 mesh/.010-inch wire](https://howardwire.com/products/304-ss-woven-10-mesh-010). The [IWM technical table](https://www.iwmesh.com/technical-mesh/) gives the matching nominal2.286 mm aperture and81% open fraction. Cut two41×41 mm sheets, withØ4.8 clearance at the four fan-bolt centres; deburr and trap all edges between the guard and fan perimeter with measured rigid shims. The source explicitly models wire and bolt cutouts. No loose mesh edge may project into the blades. The2.286 mm nominal openings geometrically exclude larger objects, but no finger-probe, strength, loose-wire or guarding certification is claimed.
- The guard is a36 mm circular opening without printed cross-ribs; the metal mesh supplies the screen. `mesh-area.json` subtracts both wire directions from the finite circle: **824.097 mm²** at the authored phase; a16×16 phase sensitivity spans823.932..825.204 mm². The phase grid is not a continuous bound. Supplier wire tolerances and received weave remain to be measured. Nominal open area does not establish mesh pressure loss.
- Intake and exhaust wall slots each total **2,160 mm²** before screens. Exhaust mesh can use the same receiving specification, but its attachment, edge retention and full installed collision checks remain unfinished. Do not treat the current naked exhaust opening as a finished guard.
- Fan-wire exit/strain relief, dust performance, exhaust retention frames, mounting/clamp durability, and detailed airflow baffles remain unfinished. These parts are explicitly not in a print-ready or operational package.

This geometry provides a checkable alternative without assuming that more interior height alone solves cooling. Select the architecture only after source-loaded pressure/flow and thermal review. A revised shell may still need different openings, pod orientation or dimensions.

## Verification and honest limits

The current `native/` records use only the pinned, network-disabled isolated Linux OpenSCAD image. Seven checks must be strictly empty: hardware versus components, hardware versus retained controls, revised shell versus components, pods versus components, fan versus pod, mesh versus fan, and mesh versus hardware. Intentional fan-bolt/hole engagement is excluded from the clearance test and instead has the receiving check above. A deliberate positive collision must be nonempty. Shell, pod and guard exports must be closed oriented boundaries with positive volume. `verify.py` validates these expectations and every native source hash. No positive-volume tolerance is used to declare collision clearance.

An earlier nominal M4/zero-clearance hole intersection produced a small nonempty mesh and was rejected. `cooling-r2-rejected-coincident-holes.scad.txt` and `native/r2-*` preserve it. R1 throughR5 evidence is superseded. The first attempt only encountered a Docker socket permission denial; no CAD process started. Its record is retained separately. The current verification uses only the final unsuffixed native directories.

The exported meshes retain assembly coordinates and are **engineering review meshes**, not bed-oriented deliveries. The independent mesh check is topological, not material/strength validation. No physical fan, print or powered hardware has been tested.

## Thermal inputs and next gates

Do not use the earlier10.5578 W selected-supply heat map as the full heat load. The historical [whole-unit allocation](../a12/thermal/whole_unit/README.md) is35.4315 W, including endpoint consumption and reserved distribution losses. It is a conservative source-bound scenario, not a measured upper bound. Its old metal-base convection result and the old two-fan pressure study are not evidence for this new plastic-shell/PCB assembly.

The retained fan maximum-current planning provision is376.8 mA for two fans (2×157 mA×1.2). Current TBP66 source distribution, startup voltage, hot restart, locked-rotor/fault operation and fan harness still need acceptance. Fan ports F_J202/F_J203 are captured with actual 5V/tach/ground pins in the inventory.

Before this becomes a complete design:

1. Freeze the inter-board and panel pin-to-pin harness, exact mates, terminals and wire receiving bounds; remove only electrically verified redundant headers.
2. Model all real mates and service loops, including the new carrier/sensor assemblies. Route wires with their actual bend limits and positive retention; rerun full installed fit.
3. Refresh simultaneous heat/current provisions against the integrated boards. Establish each critical package-to-air/copper path; a plastic floor supplies no metal heat-spreader credit.
4. Receive the selected mesh and finish retention/lead exits; derive the actual installed pressure network and compare against the exact-part fan curve with documented uncertainty.
5. Verify airflow, temperature, fault behavior, noise, structural mounting and real assembly on a prototype. Passing CAD cannot supply those physical results.

Reproduce the inventory with `python3 -m hardware.cad.two_board_installation_06.audit`, each fresh native case with `python3 -m hardware.cad.two_board_installation_06.run PART`, and the evidence audit with `python3 -m hardware.cad.two_board_installation_06.verify`. Native runs refuse existing evidence directories; preserve a changed revision separately.
