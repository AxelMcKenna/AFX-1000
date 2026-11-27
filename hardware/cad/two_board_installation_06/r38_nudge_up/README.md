# NUDGE UP panel input candidate

S07 connects D_J2001:5 `/D_CONTROLS/CONTROL_04` to `button_nudge_up:1` with unchanged native net and terminal positions. Its independent +Z source emergence turns through a tangent R12 arc at azimuth 150 degrees. The wire descends to Z29.6, turns west, then approaches the button from +Y with a tangent S-rise to Z31.6. Exact installed centerline length is 101.624406 mm, excluding preparation, termination and service allowances; this is not a cut length.

The Alpha 5853 maximum insulation diameter is 1.0922 mm, inside the modeled radius 0.6 envelope after sphere-facet and curve-sampling errors. All bends are R12 or greater with tangent continuity. Host checks retain r22 ground, S01–S04, both unselected r37 TAP/AUTO routes and all 29 input-terminal reservations. Minimum wire surface gap after chord errors is 0.786828 mm; minimum other input-terminal gap is 4.659983 mm. Expanded control and future-touch probes provide at least 0.260895 mm modeled margin.

The native route is a closed oriented 12,256-triangle boundary with no excluded degenerates or bad directed edges. Six native intersections are empty: revised controls, allocations/connector reservations/supports, existing wires including S04/r37, structural geometry, r33 touch swept wires, and a separate expanded-route audit against all ORIGINAL unrelieved button mechanisms, clips and motion. This last audit proves the route does not depend on the r36 holder channels. No holder or board modification is proposed here.

Source and target identities, source/terminal tangents, sampled geometry, minimum curvature, all prerequisite geometry hashes and native artifacts are checked. Five mutations reject wrong cavity, wrong net, moved terminal, tight bend and changed source tangent. Original failed source/holder evidence in r35 remains preserved; it applies to other source cavities and is not reused as this route's clearance authority.

Local evidence is conditional. Full root assembly screening, physical connector termination, installation support, tolerance and lid-opening slack remain open. r37 is reserved as a candidate, not represented as selected. No root selection or completed-edge count changes here.

Run `python -m hardware.cad.two_board_installation_06.r38_nudge_up.verify`, `...test_contract`, `...verify_native`, then `...export_adapter`. Native checks use the bounded pinned Linux `...run CASE --revision REVISION`; the independent original-control audit uses `...run_source_audit original_controls --revision REVISION`. Use fresh revision names and retain failures.
