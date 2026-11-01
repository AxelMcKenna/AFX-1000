# Selected R1 local CAD result

All **15 fresh native cases** pass using the independently proved pinned Linux OpenSCAD 2026.10.26 Manifold runner: one actual receiver solid, ten required empty intersections, and four real 0.008 mm³ positive controls. Both portable local tests and both runner tests pass, including rejection of corrupted/missing evidence and unauthorized/existing output paths. Ruff passes for the active local source.

The exact selected-part PCB is `dc559bd94d0decdb89ee647cde00709f15463304e051497bf8b7dacc719194c8`. Frozen CP01 contains the revised enlarged base and pot hardware; its 598-file seal remains current. All 87 other complete E19 footprints match the central baseline. Only the old R1 component row is excluded from the private copied scene. New R1 uses the actual serialized courtyard `[107.91,78.07 .. 112.09,85.93]` mm and a 1.0 mm receiving projection at PCB top Z8.1 mm.

The 0.25 mm external clearance and ±0.2 mm PCB Z sweep are clear against the captured electronics, revised controls, case/base/interfaces, power hardware, wires/joints and mount/tool envelopes. Three correlated own-PCB seating cases are clear. Deliberately shifting only the component into its PCB produces the required witness; retaining a neighbouring C6 and the original old-R1 solid are independently witnessed. The old-R1-only exclusion control is empty.

This is an actual **local source applicability check**, not canonical source adoption or a new whole-unit physical, cooling, noise, current, fabrication or assembly qualification. The R1 body-temperature, pulse/startup, effective-capacitance and source/ground budget holds in the separate Seed3 and finite-PDN reports remain open. No previous macOS failed launch or earlier prospective fit result contributes accepted geometry evidence.

Authoritative raw commands, source and artifact hashes, strict STL statistics and case roles are in `generated/verification.json`. `handoff.json` seals this packet, including the rejected histories and independent runner proof.
