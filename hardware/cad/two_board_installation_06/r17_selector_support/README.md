# Conditional release wire positional guide

A curved, closed guide follows the frozen R13 wire near the release selector. Its bore radius is 0.85 mm around a receiving wire radius of 0.6 mm; outer radius is 1.7 mm. The generated path comes directly from r15 right-routes.json, so no electrical adjacency or wire bend is changed. This loose guide limits transverse displacement; it is not an axial pull-rated strain relief.

The bracket mounts under the release selector PCB at the existing rear hole [316,63.5]. Replace that M2x10 screw with M2x12. Original head datum Z45.6 is preserved, new foot Z36.5..38.1, washer Z36..36.5, nut Z34.4..36 and shaft tip Z33.6. This provides full 1.6 mm nut engagement and 0.8 mm protrusion; retaining the old screw would provide only 0.4 mm engagement. Front release hardware and r16 settings hardware remain unchanged. `release_supported_selectors()` replaces the complete r16 selector role; do not overlay both. The r16 splice support remains separately installed.

Thread the wire through this closed guide before soldering the selector end. There is no lateral snap-in opening. The entire guide, selector and splice share the lid frame. Neither L01 nor R01 is clamped, rerouted or shortened. Service opening is not qualified by installed clearance checks.

Native r1 checks have empty intersections against replacement selectors (only exact PCB/washer seat planes excluded), both frozen ground branches, board receiving geometry, selector wiring receiving rows, r16 splice cage/splice, and local enclosure/mechanical structure. The guide is one watertight connected solid, volume271.904 mm3. Root full assembly screening is still required.

The single mounting screw relies on clamp friction for rotational stability. PCB load capacity, printed bracket stiffness, screw preload, printed bore finishing, insulation abrasion, vibration and actual wire routing must be tested. The sleeve cage and this guide do not yet qualify terminal strain relief. No fabrication release, complete harness or opening clearance is claimed.
