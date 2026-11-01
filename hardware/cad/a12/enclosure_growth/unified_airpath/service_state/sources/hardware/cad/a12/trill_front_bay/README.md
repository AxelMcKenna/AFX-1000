# TC02 — front-bay Trill Craft floor-post candidate

The new front-bay arrangement clears all15 declared primary native interference/fit checks. It places the current C3 board at **[82,158,20] mm** above two insulating floor posts, leaving the earlier TC01/C8 conflict unchanged in its sealed historical trial. This remains a proposed mounting contract, with no selected post material, screw, washer or thread process and no physical approval.

| Requirement | Candidate value |
| --- | --- |
| C3 nominal PCB |53.848 ×21.844 ×1.6 mm, component face upward |
| Origin / far front edge |[82,158,20] /Y179.844 mm; inner front wall Y185.6 |
| Actual H1 / H2 centres |[130.0871,168.922] /[93.0871,168.9352] mm |
| Nominal insulating posts |Ø7.2 mm, Z2.7..20.0;0.1 mm overlap into nominal floor topZ2.8 |
| Blind pilot requirement |Ø2.05 mm, Z15.3..20; actual thread/tapping process unselected |
| Proposed M2.5×6-class screw |Maximum shank2.5 mm;6 mm nominal under-head length; actual part/tolerance unselected |
| Head plus washer requirement |MaximumØ6.4 mm /height2.2 mm above PCBtop21.6 |
| Nominal engagement |4.4 mm **minus actual washer thickness**; tolerance/bottoming/retention/torque unapproved |
| Controller displacement from TC01 |[0,+34.5,−10.6] mm; electrode/I²C leads require fresh design |

The [STEP posts](generated/posts.step), [dimensioned SVG](generated/dimensions.svg), [PNG](generated/dimensions.png) and [native scene](generated/geometry.stl) are provided. STEP has two valid nominal post solids. The native post clearance envelope is deliberately circumscribed; its volume differs from the nominal analytic STEP by0.0214%. These are nominal/envelope models, not a fabrication drawing with approved tolerances.

The manufacturer source establishes nominal **3.2 mm** mounting holes, not guaranteed minimum bores. This candidate proposes a **minimum3.1 mm acceptance requirement** and maximum2.5 mm shank; neither is presently a proven production bound. At0.2 mm relative centering plus0.005 mm geometry provision, the radial arithmetic leaves0.095 mm before the native polygon conservatism. The actual native bore check is empty. Increasing centering to0.3 mm makes the arithmetic margin−0.005 mm and produces **0.170649614 mm³** interference. That sensitivity is explicitly **rejected**, with its mesh retained. Nominal3.2 mm was not silently promoted to a guarantee or substituted to pass the worst-case check.

The exact additional E28 board material is reconstructed from the three changed native Edge.Cuts in growth candidate67b746d0… relative to its43-open parent outline. It is a151 ×9.25 mm band endingY163, checked with the existing board-height/thickness envelopeZ4.8..6.9. The nearer post nominal edgeY165.322 leaves2.322 mm. Both0.45 mm and0.90 mm additional XY post envelopes clear the slab; the latter retains approximately1.4206 mm after native circumscriptive conservatism. These are sensitivity scenarios, not manufacturer/process tolerance guarantees. The43-open source's P9 ground port atY129.5, power loss, copper or wire acceptance is **not inherited**. The operating input-wire scene remains E28 fed47258… with its separate45-open scope and Y126.5 ground origin.

The context also refreshes J29 from the actual electrically closed302ec64b… source. Its saved courtyard yields service bounds[163.05,97.53]..[172.67,102.07],5 µm outward per side from the preliminary analytical contract. Actual serialized dimensions are used. This is an obstacle update for TC02; the complete J29/retainer repair and enlarged-unit integration still need their separate combined native renewal.

Tool envelopeØ6.5 mm clears existing electronics and power/case material **after the lid and guide/control assembly are removed**. Leaving the enlarged guide plate in place obstructs the tool by **92.875169657 mm³**. That blocked-access witness remains in the report; removing only the metal panel does not establish access. The actual removal path, loose harness lengths, driver and assembly order are unqualified.

The native record contains25 validated evidence cases:3 required solids,15 empty primary checks, the rejected centering sensitivity, the blocked-guide witness, the8.144635895 mm³ floor-bond witness and four0.008 mm³ positive controls. Boolean solids require native `NoError`. The growth slab alone is emitted as a convex primitive; it is accepted only after independent validation of its closed topology, eight vertices, exact bounds and151×9.25×2.1 mm volume. The first unreviewed-primitive run is retained as rejected evidence.

The C3 board,13 actual terminal-derived component reserves and36 tail reserves retain TC01's declared geometry and move together. The6.4 mm above-face and3 mm tail provisions remain project allocations, not measured supplier assembly limits. I²C/electrode routes,8-channel foil mapping, grounding, noise/ESD, touch tuning, supply/firmware operation and strain relief remain open. The proposed floor bosses require selected insulating material, integrated-floor construction, thread/torque/creep/pull-out and dimensional qualification. A native0.1 mm floor overlap proves geometric continuity only.

The larger front floor/base load path and whole-unit heat rejection remain open; TC02 does not close those issues. PM01, TC01 and the failed EI01 unit trial remain unchanged. No canonical board or shared CAD file was edited.

```sh
python3 -S -m unittest hardware.cad.a12.trill_front_bay.test_review
python3 -S -m hardware.cad.a12.trill_front_bay.review
```

Eleven independent portable checks cover actual raw mesh metadata/topology, source/artifact integrity, missing solids, a forged empty row, incorrect pose, false guaranteed hole limits, failed-sensitivity/access promotion and false physical claims. All physical, electrical, thermal and fabrication-release flags remain false.
