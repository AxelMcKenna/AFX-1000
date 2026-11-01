# PM01 — raised-panel attachment audit

The low E19 processor carrier, E18 input daughterboard and E20 LED driver can remain at their current datums as a **candidate arrangement**. Their native BOMs contain engineering headers for remote panel controls; they contain no panel potentiometer or switch footprints. This preserves E19's low processor/receiver interface. It requires renewed actual loose harness routing and qualification.

[report.json](report.json) is the explicit transform contract for the private 334 ×188.4 ×45.6 mm housing. It enumerates all **11 boards, 750 envelopes, 34 floor mounts and four daughter mounts** in the captured `other` packet. Every row has its original index, exact ID, original geometry, candidate geometry, source origin and translation. Original XY remains fixed; the added 31.4 mm depth is at the front (+Y).

| Assembly | Source-derived instruction |
| --- | --- |
| E19 / E18 / E20 and their bodies, tails and fixings | Keep Z6.5 /12.1 /6.5 mm candidates; retain E18's 8.1→12.1 mm relative support stack |
| Audio, rear inlet, P03 and actual E28 | Keep current source-defined floor/rear datums; existing native/body packets remain necessary |
| Ten separate pot reserves, knobs and two selector assemblies | Raise 7.6 mm to preserve panel-relative geometry; shaft, actuator and fastening fit remain unqualified |
| 29 button mechanisms, holders, keys and controlled switch bodies/leads | Follow `panel_z` by 7.6 mm, preserving actual centres and rotations; retain the 10×10 mm body/terminal reserve and 4.5 mm downward lead/solder allocation |
| Guide plate, touch backer, optical lenses | Follow panel by 7.6 mm; enlarged guide-plate stiffness and mounting remain open |
| Meter/BPM board and display reserves | Raise 7.6 mm **if preserving the existing optical geometry**; these remain placement reserves rather than qualified emitter assemblies |
| Lever, bracket, pivot, magnet, spring geometry and sensor | Coherent 7.6 mm rise, including four floor post seating planes and both AS5600 board/body reserves |
| Trill Craft controller and connector reserve | **Unknown**. The controller is distinct from the panel touch backer. No explicit mounting/harness contract determines whether it should stay or rise |
| Rear cassette and its port axes | Keep original Z; no recentering or automatic upward translation |

The lever modules contain absolute Z coordinates and do **not** follow `panel_z` automatically. The report supplies module IDs, pivot/spring/bracket coordinates, sensor envelope IDs and mount indices. An analytic witness proves that at 35° the unchanged stem intersects the raised panel outside the unchanged slot. Moving the entire mechanism is the candidate for retaining existing panel-relative kinematics; redesigning its slot/lever would require a separate analysis.

`panel_modules` maps the SCAD-only geometry absent from the rectangular `other` rows, including the controlled rotated B3F bank. Do not apply the same translation twice to modules already driven by `panel_z`/`shell_height`. The legacy `disconnect_*` envelopes are explicitly marked as superseded; they must not replace actual repaired E28 both-face records. The supported private E19 ear/J13 is likewise a separate native source, whose nominal low datum can be retained without claiming a new whole-route pass.

The exact current J20–J29 pot labels are checked against actual BOM notes. E18 J1/J2/J3 and E20 J2–J5 serve offboard panel controls/emitters. The header list is a mechanical interface audit, not permission to improvise electrical pin order. Exact production connectors, retained mating bodies, slack, strain, lightguides, shaft/bushing/socket engagement, switch travel, touch performance and lever magnetic alignment remain unqualified. H9's vertical tool access is still obstructed by actual DIG copper; extra shell height does not resolve that obstruction.

All 76 source inputs are copied unchanged under `sources/` and hash-bound in the report. `baseline-other.json` preserves the exact input packet. The new audit does not modify baseline CAD, canonical PCBs or sealed routing evidence. No new CAD collision, structural, physical or fabrication pass is claimed.

```sh
python3 -S -m hardware.cad.a12.panel_mount_audit.review
python3 -S -m unittest hardware.cad.a12.panel_mount_audit.test_audit
```

Ten checks cover captured-source integrity, complete row mapping, fixed low boards, unresolved Trill placement, coupled lever/sensor/posts, the controlled switch lead reserve, and rejection of false qualification claims. This is an independent source audit, not a native geometry renewal.
