# EI01 — rejected enlarged-unit integration trial

**The combined trial fails three declared packaging interfaces.** Of42 native cases,39 pass. The failures are retained with actual meshes and owner-specific isolation, rather than reported as a complete fit. Twelve independent evidence/mutation checks pass. No canonical board, frozen control/thermal kit, PM01/TC01 seal or accepted baseline wire curve was changed.

| Retained failure | Native evidence |
| --- | --- |
| TC01 saddle crosses E28 C8 capacitor envelope |175.305827800 mm³. The saddle point[72,134,25] lies inside C8's actual source-derived envelope. Removing only C8 from the diagnostic obstacle union leaves an empty intersection. |
| E19 J29 mating/header reserve crosses power-return retention |43.811394734 mm³. Isolating only J29 reproduces the entire remaining power overlap; omitting only J29 leaves empty intersection. |
| Four rear TS jack requirement boxes extend below cassette opening |63.839988766 mm³ in the combined trial. The TS-only guarded diagnostic reproduces all volumetric rear overlap. Even without the additional ±0.2 mm Z provision, the nominal boxes intersect by21.279827344 mm³. |

The rear TS boxes are existing **unqualified interface allocations**, not selected supplier body models. Their nominal lower surface is13.2−19/2=3.7 mm, below the retained opening's3.8 mm lower edge. Fixed rear-port motion and PCB motion need separate assembly/tolerance treatment. The nominal diagnostic shows that this conflict is not solely the added0.2 mm sweep. Selecting actual body geometry/pose or changing the cassette requires a separate source-bound design. RCA boxes also share the rear cassette's Y0 contact plane; these coplanar facets do not represent additional volumetric interference.

[findings.json](findings.json) contains the source geometry, exact volumes and qualification limits. [generated/whole_geometry.stl](generated/whole_geometry.stl) is the complete declared scene reference, including the failed interfaces. The [native report](generated/verification.json), commands, logs, collision STLs and diagnostic witnesses remain auditable. The native CLI correctly exits1 for this failed geometry trial; the independent evidence reviewer returns0 only when the saved failure evidence is internally consistent.

The scene uses334 ×188.4 ×45.6 mm shell,9 existing/new lid boss/hole positions and34 exact PM01 floor-mount rows. It applies panel-relative +7.6 mm transforms once, keeps the low E19/E18/E20 stack, raises the actual lever/sensor group, and consumes TC01's53.848 ×21.844 mm C3 reserve and separate backer-Z erratum. The backer underside is42.2 mm. It includes both PCB faces and tails, explicit native selected-part height requirements, the real positive/return hardware, retained metal base and the unchanged accepted input-wire pair.

Actual sources are P03 db83a26f… and E28 fed47258…; the latter's45 electrical opens remain a separate unresolved scope. Receiver e4156603… is the READY79-part/88-footprint spaced fanout, electrically native-closed, with J14Y84.5/J15Y92.5, H9[182,92.2], ear topY82 and eastX194.5. Every receiver seal's42 inputs is copied unchanged under `receiver-evidence/`. Ninety-two model/proof sources are copied unchanged under `sources/`.

The full input pair retains its exact selected continuous-curve geometry, hard9.6393 mm minimum radius, independent0.65 mm wire positions,0.25 mm clearance,0.005 mm geometry reserve and7 mm receiver stubs with3.1 mm bare ends. Its actual new receiver PCB is re-derived from source. Cases explicitly check the three actual service boxes (native Fcourtyard+0.5 mm, Z8.1/H11.31), all six3.4 mm square tail requirements, mutual0.25 mm service clearance, H9 post/head/tool, and each minimum2.1 mm receiving bore with1.4 mm core and0.3 mm relative centering. Only J13 has a complete routed wire pair; J14/J15 stubs do not qualify their missing outgoing branches.

PCB material includes every actual drilled pad:40 P03 bores,45 E28 bores and142 E19 bores, with native coordinates/types/angles retained. Initial mount-only material falsely treated some intended locating bores as solid PCB. That rejected trial is preserved in `history/`. The second trial and all subsequent owner diagnostics retain the three actual remaining failures. TC01 modules are renamed only in an exact derived private file so its generic `aperture()`/`hardware()` cannot shadow the unrelated A11/ROOT modules.

Required solid outputs and seven0.008 mm³ positive controls must have actual nonempty meshes, native Boolean `NoError`, source hashes and mesh metadata agreement. Empty collision output is accepted only as the documented rc1/no-file result. The evidence checker rejects fabricated empty rows that retain a real collision mesh, missing solids, changed bores, missing manifold status, wrong source ports and false release flags.

Nominal PCB/standoff seating planes and intended Trill seat/head-bearing planes use20 nm Boolean-only guards. Component envelopes retain the declared extra0.2 mm Z provision; these are project assumptions, not measured tolerance bounds. The retained thermal base remains334 ×157 mm, so enlarged front-base/structural and cooling design is not closed. Exact mates, fasteners, PCB/case tolerances, loose wiring, touch performance, currents, heat rejection and all physical qualification remain open. This scene is the stated subset of unit geometry, not proof that every necessary production subassembly exists or is qualified.

```sh
python3 -S -m unittest hardware.cad.a12.enclosure_growth.integration.test_review
python3 -S -m hardware.cad.a12.enclosure_growth.integration.review
```

The archived-source reviewer also supports `--historical`; this deliberately skips live-source freshness while retaining captured-source/artifact integrity. A historical replay is never a claim that changed live sources were checked.
