# Independent EB01 read-only review

Audited handoff: `daeb19a1f8eb5ae0f07b3f467a0cfcd35384e3e570007d8397b4182cdc8352cf`.

No EB01 file was edited. No OpenSCAD/native geometry case was rerun. Independent parsers inspected actual existing STL and 3MF bytes; CadQuery only loaded the existing STEP files and read their BREP validity, volume and foot-pilot radius.

The 440-file inventory is complete and every hash matches. All 137 original captures and 137 derived-context hashes match; the derived differences exactly follow the declared absolute-path rebinding and thermal-base changes. The original live files also still match at this review point.

The 42 native outcomes are supported by actual logs/artifacts: seven strict geometry outputs, 23 empty intersections, seven detected controls and five retained review groups. Every strict mesh has zero degenerate triangles, closed directed edges and positive orientation of every connected boundary. These are output groups, not necessarily single parts: metal1, feet4, carrier1, attachment22 and interface14 connected boundaries. Both existing BASE and FOOT STEP files independently load as valid single solids and match the stated volumes. The FOOT STEP has the correct 1.25 mm pilot radius, with no 1.51 mm assembly-clearance radius.

All **698,922** source triangles in the ten-object component 3MF are preserved in exact order and global coordinates, with ten identity build items. The retained controls/wires/power groups have the documented mesh caveats. The fused whole-unit STL independently fails the mesh gate: 11,678 degenerate triangles and 1,636 bad directed edges. The packet correctly declares it invalid as one fabrication part; no deleted/repaired faces are hidden by the component review.

Nominal seating is coherent: support6.3 +shim0.2 =PCBbottom6.5, land5.28 +TIM1.22 =6.5. Nominal1.524 mm stock compresses19.9475%. The6.3/6.7 mm height endpoints instead give33.0709%/6.82415% with that same nominal sheet. The packet explicitly leaves fixed-stack range, pressure, creep, flatness, isolation and material acceptance unqualified. All physical/thermal/structural/build/release flags checked remain false. The actual scene remains fed E28/groundY126.5 with45 electrical opens, not U14/P9/J8.

## Findings

**EB-I01 — description/abstraction mismatch.** `eb_feet_assembly()` removes Ø3.02 for10 mm, Z−16.2..−6.19998. Actual M3×12 tip is Z−12, giving5.8 mm engagement. The text saying the abstraction covers “only engaged” thread is inaccurate: it covers the10 mm available-thread region, including4.2 mm below the tip. That removes9.46851 mm³ extra per foot relative to an engagement-only abstraction. The manufacturing STEP still has its Ø2.5 pilot. No concealed external collision is demonstrated; this is not a newly failed fit.

**EB-I02 — replay usage/reproducibility defect.** The first documented replay command invokes `stage.py`, which reads live EI/thermal design/dimensions/code and overwrites EB01 design/sources/context/capture. It does not rebuild from EB01's frozen `sources`. Existing captured native verification can be used without staging, but absolute include/import paths require explicit rebinding on relocation. The documented full recipe therefore performs a recapture, rather than an immutable captured replay. This does not disprove current native outcomes.

**EB-I03 — assembly-role advisory.** `feet_assembly_geometry` is flagged `new_manufacturing_part=true` despite its assembly-only thread abstraction; interface output similarly groups fourteen separate pads/shims. These flags must not be read as fabrication instructions. Use the exact standalone FOOT STEP for the manufacturing pilot and distinguish output groups from a fabrication bill of parts. Overall release remains false.

The independent review grants no physical, electrical, thermal, structural, material or fabrication qualification. Root should retain this review outside the immutable EB01 packet and address findings through a new addendum/proposal.
