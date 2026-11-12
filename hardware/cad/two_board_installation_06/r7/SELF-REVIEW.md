# Antagonistic self-review — installation06 r7

This is the implementing agent's self-review, not an independent audit. The release target is a reviewable cooling mechanical candidate and fan routing checkpoint. It does not establish a fully installed or thermally qualified product.

## Unresolved findings

1. **Assembly release blocked:** the fan bundle curves have no internal supports enforcing their calculated shape. Terminal fanout is an envelope, not a proven bend transition. Motor exit to retained bay routing, service allowance and cut lengths are not completed. Full-system carrier/guide/spring/harness cross-fit is a separate integration check. See `HARNESS.md`.
2. **Operating release blocked:** whole-unit dissipated heat, installed fan airflow/pressure, startup/stall allowance and physical temperature tests remain unqualified. Historical heat allocations and fan free-air figures cannot substitute for this new plastic enclosure.
3. **Whole-harness release blocked:** current generic and NF physical interfaces remain individually unselected; source inventory is not a complete cable topology. `interface-manifest.json` identifies each entry rather than pretending all 78 are required cables or assigning guessed mates.
4. **Hardware receiving:** the frozen M4 bolt-head allocation is Ø7×4. The fan drawing recommends M4 pan-head hardware, but no exact manufacturer part with that head envelope has been adopted. Do not claim a generic pan-head screw fits this allocation. Exact fastener selection or a revised head envelope remains necessary. Printed clamping torque, shim seating, mesh retention and cable-tie receiving/pull tests remain physical checks.

## Concrete findings fixed

- Independently clear fan routes collided with each other (2.286 mm centreline separation for Ø5 mm bundles). Simultaneous optimization now gives a continuous conservative mutual clearance lower bound of 0.485 mm. Original searches remain explicitly rejected.
- The XH assembled-height assumption was corrected from an unverified 12.8 mm to the official 9.8 mm. The existing Z22.3 route datum is now explicitly a breakout 3 mm above housing top Z19.3, with separate individual terminal envelopes.
- Initial native inflation of 2.55 mm was 0.0048 mm short of the worst-case sufficient chord/facet bound. Final geometry uses 2.56 mm. Earlier native evidence is retained under `native-harness-first/`; all affected checks were rerun.
- The new native harness runner checks the global isolated-run failure latch as well as local failure/policy state. Frozen earlier runners and their hashes remain historical evidence and should not be reused for new revisions without equivalent guarding.

## Validation

- Frozen cooling mechanical evidence: 17 strictly empty checks, 6 positive/retention tests, 6 closed solid exports; current source hashes verified.
- Fan harness: 5 strictly empty native checks, a positive collision control, and a closed oriented harness export; source hashes verified. Continuous component/bundle clearance and bend bounds verified independently of native polygonal intersections.
- Native-only Linux CAD image pinned by digest; no Mac native CAD used. All native harness processes completed normally. The harness mesh validator excludes two degenerate STL triangles and finds no bad directed edges; no geometric clearance claim is based on those triangles.
- Preview generated from native exported triangles and visually inspected. Supports and other components are intentionally omitted and clearly labeled; this is not a complete assembly render.

These checks support a geometry checkpoint. The unresolved findings above must remain visible in any integrated release description.
