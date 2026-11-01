# UA01 — source32 unified airpath, return and positive-link candidate

The new source-to-J13 ground route now starts at the **actual E28 J4.2 (161,129.5,6.62)**. R04 ANA return copper and PB27 insulated positive hardware clear that route while preserving all terminal ports. This is a reviewable mechanical candidate; **physical, fabrication, electrical, thermal, installed airflow and complete wiring qualification remain false**.

The [dimensioned review drawing](generated/UA01-dimensioned-review-v2.svg), [separate-object complete assembly](generated/UA01-component-review.3mf) and [new base STEP](generated/UA01-BASE.step) show the actual candidate. The drawing is a routing/interface review, not a complete fabrication drawing or process approval. First drawing and first OPC-namespace-invalid 3MF are retained; the corrected package changes only its content-type namespace, preserving model XML and every triangle.

## Exact evidence scope

| Record | Result |
|---|---|
| [Original full42](generated/current-native/verification.json) | **41 pass / 1 failed**: H9 tool through the guide left in place, 46.4375501051 mm³ |
| [New service8](generated/service-state-native/verification.json) | All8 pass, including two directional owner proofs, retained controls/lever and two actual0.008 mm³ controls |
| [Fresh changed review2](generated/review-native/verification.json) | Both native exports pass |
| [Actual part-mesh audit](generated/production-mesh-audit.json) | 52 strict closed, oriented, nondegenerate meshes:49 actual CAD part shapes and3 clearance/receiving envelopes |
| [Complete assembly manifest](generated/assembly-manifest-corrected.json) | 70 separate objects /856846 triangles, exact coordinate roundtrip;16 explicitly reused AP03 families,5 fresh changed families and49 individual power-part shapes |
| [Base BREP](generated/base-BREP-verification.json) | Valid single solid and STEP roundtrip,474096.6224056 mm³ |

This does **not** mean50 all-pass native cases. The all-controls-present42 remains failed. A11 `PRINTING.md` step4 attaches the holders through the panel and guide with M2 screws; PM01 follows that assembly with the panel. The service state removes the lid/guide/control cohort. Its conservative obstacle test actually leaves **every other control** present, including the floor lever, pots, holders, switches and optics, and proves the guide alone accounts for the failed intersection. An80 mm translated cohort is a static separated review state, **not a proven removal trajectory**. Driver selection, harness disconnection/slack, panel extraction, grip and assembly order remain unqualified. Actual H9 power/case and electronics tool tests are empty at the source-derived (182,92.2) axis.

## Captured sources and actual changes

`capture.json` binds private copies of P03 **aux-u10-combined/db83**, E28 **sealed32/dd6a6f5a**, R1 **dc559bd9**, PB02-WR01, HT01 and AP03. All actual drilled pads are extracted; PCB mounting seats, terminal contacts and rear mating faces retain their stated correlated treatment. P03/E28 both-face envelopes include declared thickness ranges and ±0.2 mm board-Z allocation. Independent source-component0.25 mm external-clearance cases remain in the full42. The scene contains507 source component records. E28 has **32 electrical opens**; it is deliberately not the latest routing development.

R04 replaces the old straight ANA central leg with (153,133.125)→(160,134.625)→(173,134.625), preserves both landing planes/ports, moves its PEEK support and sole metal/floor hole to (166,134.625), and raises both PEEK head bottoms8.7→9.0. No duplicate old support hole is retained. The new base is cut from a new blank; the BREP stock reconstruction is not a proposal to weld/fill an existing plate. Its actual8.46 mm maximum P03 top plus0.41 mm combined return/PCB clearance is screened against the real notched board. The old8.7 mm head failure1.840794523 mm³ remains a positive witness. Original6×3.5 Cu dimensions,Ø10 lands andØ4 holes remain; the analytical worst normal section is20.1425 mm² after the stated edge-break deduction. Matched assembled terminal heights, stud tolerances, plating, mounting isolation, preload and contact resistance still require factory review and measurement.

PB27 raises the ANA road bottom to26.0 mm and moves only its north saddle screw/boss offset−6.8→−6.0 mm, with a real corresponding support riser/keeper. Terminal ports, DIG route and source joints remain fixed. The three covered/receiving envelopes are collision requirements, **not extra physical material** in the70-object assembly. Its nominal6.4×1.2 Cu screen remains≥6 mm²; no old3D current-crowding, noise, joint resistance or PDN proof is inherited. Tape build, dielectric integrity, cap/contact compatibility, torque, material and lifetime are unqualified.

G129 uses the unchangedR16 source quarter, translated+3 mmY, followed by a newly certified C1 cubic and unchanged7 mm receiver vertical stub. Decimal Bernstein continuous curvature certification bounds true radius≥9.9229 mm, above9.6393 mm. Max insulated OD1.7526, core receiving OD1.4, independent position0.65, external clearance0.25, geometry0.005, min prospective bore2.1 and relative bore centering0.3 remain unchanged. Above-face bare lengths remain3.1 mm. Ground length upper80.3032 mm includes maximum board tails; positive remains the PB02-WR01+1 mm lifted curve. Cut slack, retention, solder/trim process, current/voltage drop and physical forming remain unqualified. The old3 mm source misregistration and old return/wire clash are retained controls.

The60 return/PB pair comparisons are covered by source-derived manufacturable-part AABB supersets expanded by the **full0.51 mm combined margin**, tested against actual covered PB solids. Split DIG convex loft/disk boxes and PEEK stem/head boxes are proved to cover whole source triangles, not independently selected vertices. No whole-assembly Minkowski execution failure is called a pass: own identified long-running cases and exit137 records remain in `generated/expensive-comparison-stop.json`; OOM was not established. All intermediate actual clashes, strict importer gate failures and rejected conservative-box comparisons remain in their original folders.

## Deliberate non-adoption and remaining work

NF03P, FPC01, new E28 U35 and later routing/development poses are **not incorporated**. AP03's fan/duct/meter geometry is retained with899 pins and318.2787 mm² total meter area; no thermal or airflow proof is inherited from area or mechanical clearance. No new operating fan harness, Trill electrode bundle, eight complete audio harnesses or J8 return wire is established. The whole3MF is a separate-object review; group envelopes/composites are not asserted to be one manufacturable or manifold part. Every actual production-part mesh retains its strict gate; no surfaces are dropped, decimated, reoriented or repaired for the review package.

## Read-only validation and explicit replay

```sh
python3 -S -m hardware.cad.a12.enclosure_growth.unified_airpath.audit
python3 -S -m unittest hardware.cad.a12.enclosure_growth.unified_airpath.test_audit
```

Do **not** run `unified_airpath_stage.py`, `derive.py`, `variant*_stage.py`, part builders, package builders or drawing builders inside this sealed packet: those are capture/build provenance, not a captured replay entry. A new native replay uses `replay.py --kind service8 --outdir <NEW repository directory outside this packet>` after saved-source/artifact validation. `main42` intentionally returns nonzero for the blocked-guide state; it must not be renamed a success. Existing outputs are refused. Native execution uses the unchanged reviewed, pinned Linux Manifold runner; no failed-signature macOS nightly is launched. A future changed PCB/part adoption needs a new coherent source capture and renewed geometry evidence.
