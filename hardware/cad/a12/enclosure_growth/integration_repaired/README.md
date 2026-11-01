# EI02 — repaired enlarged-unit geometry trial

**All45 declared native geometry cases pass.** Eleven independent source/artifact/mutation checks also pass. The private334 ×188.4 ×45.6 mm scene combines the actual central J29 PCB, TC02 front-bay Trill mount and raised rear jack row. This establishes the stated geometry and clearance screens; thermal, complete wiring, manufacturing and physical qualification remain false.

The [native scene](generated/whole_geometry.stl), [analysis](generated/analysis.json), [case evidence](generated/verification.json) and raw logs/STLs are provided. No canonical PCB, shared control source or earlier seal was modified. The failed EI01 trial remains intact. The first EI02 attempt is separately reconstructed and sealed under [history/first-J29-other-hardware-clash](history/first-J29-other-hardware-clash/handoff.json).

| Repair | Actual scene input |
| --- | --- |
| Trill C3 | TC02 origin[82,158,20], actual53.848 ×21.844 mm outline reserve and exact source mounting holes; two Ø7.2 mm floor-post candidates |
| E19 J29 | READY PCB3b2a8197… /filled5e5d0d7e…; pin1[105,76], angle0; actual saved service bounds[102.73,73.73]..[107.27,83.35],4.54 ×9.62 mm |
| Rear jacks | All8 audio axes raised13.2→14.0 mm, unchanged apertures/body-class dimensions; DC, power switch, SD and USB remain fixed |
| Controls | Exact PM01 transforms applied once; low E19/E18/E20 stack retained; lever/sensor group raised coherently; touch-backer underside42.2 mm |

The earlier J29 relocation cleared the return retainer but intersected the real **BONDED-PEDESTAL** by25.53750515 mm³. Named-piece native subtraction isolated that failure. The final same-part central placement avoids both obstacles. The original failed scene and prospective geometry diagnostics are retained; prospective checks were not substituted for the actual routed PCB. All87 other complete footprints are independently compared unchanged, and actual new J29 bodies, tails and drilled holes are re-derived from the saved source.

The45 cases contain7 required solids,29 empty collision checks and9 actual0.008 mm³ positive controls. They cover the whole case/controls/electronics, real positive/return hardware, TC02/posts, input wires and joints, three receiver service areas, all six receiving bore fits, H9 post/head and conditional open-lid tool access. Every nonempty output requires native Boolean `NoError`, actual mesh metadata and source/artifact hashes. Collision emptiness requires the documented rc1/no-file result; missing solids or forged empty rows are rejected.

The original P03/E28 **0.25 mm external component-clearance scopes** are carried separately from nominal non-overlap: native components versus case/supports, versus other electronics, and the two native boards mutually. Component boxes already include the actual fabrication-thickness range; their additional±0.2 mm PCBZ provision is retained before the0.25 mm external expansion. The source force connector body/tails are restored to these native component cases even though they are excluded from their own wire-obstacle comparison. Box and capacitor-cylinder margin witnesses lie entirely **outside nominal bodies** and inside the expanded reserve. Their matching nominal-strip checks are empty, proving that the additional clearance is actually applied.

Every actual drilled pad bore is retained:40 P03,45 E28 and142 E19 bores. These are source-derived nominal geometry, not fabrication guarantees. Own PCB seating planes use only the explicit20 nm Boolean guard. Eight matched source/return terminal bodies are omitted only from their intentional hardware-contact comparison; other bodies/tails and real PCB material remain. Rear body requirements keep their correlated mating face atY0 with a20 nm inward contact guard, while retaining the full0.2 mm Z provision and0.25 mm clearance in the separate rear case.

The complete accepted input-wire pair is unchanged: source[161,120.5,6.62] and[161,126.5,6.62], receiver[188,100,8.1] and[188,104,8.1], minimum true centre radius9.6393 mm, independent0.65 mm position provision,0.25 mm clearance and0.005 mm geometry provision. Actual receiving material and every minimum2.1 mm bore are renewed on the new source, with1.4 mm pretinned-core and0.3 mm relative-centering requirements. The continuous-curve proof remains the sealed baseline; this trial renews its native intersections. Neither the43-open growth source nor a new ground-lug source replaces the45-open E28 fed47258… source. Its electrical opens remain unresolved.

Only J13 has a complete input-wire curve. J14/J15 still need full outgoing harnesses and target-board integration. The Trill controller's new location changes electrode/I²C geometry; its complete leads, strain, touch tuning and ESD remain open. H9 and Trill tool access requires removal of the lid **and guide/control assembly**, with the actual removal path and loose harness unqualified. TC02's0.3 mm centering sensitivity remains rejected; proposed minimum hole/material/thread/fastener requirements have not become manufacturer guarantees.

The current metal thermal base is still334 ×157 mm. Its enlarged front load path, cooling hardware and installed heat rejection remain separate unfinished work. Component/mating heights are conditional project requirements wherever supplier approval is missing. No manufactured enclosure, full thermal result, contact resistance, PCB current capacity, electrical performance or physical release is established by these geometry checks.

```sh
python3 -S -m unittest hardware.cad.a12.enclosure_growth.integration_repaired.test_review
python3 -S -m hardware.cad.a12.enclosure_growth.integration_repaired.review
```

The source-bound reviewer rejects changed native bores, stale J29 bounds, reverted rear axes, missing solids, absent `NoError`, false empty rows, misplaced margin witnesses and false qualification claims. A historical review mode retains captured-source integrity while explicitly skipping changed live-source freshness; it cannot establish a new current pass.
