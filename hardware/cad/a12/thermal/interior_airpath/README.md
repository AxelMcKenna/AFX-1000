# AP02 — interior-airpath mechanical prototype

**The nominal 125 mm² base-meter allocation fails the declared 5300 rpm / Cd 0.6 pressure sensitivity.** Its 1.2 m³/h orifice loss is 11.133 Pa, exceeding the approximately 5.04 Pa remaining after the common guards, before base pins, turns, approach and outlet losses. See `generated/pressure-rejection.json`. The geometry below remains useful evidence, but does not establish either branch flow. A larger meter/approach variant must be a separate candidate.

AP02 retains the HT01/FI01 captured 334 × 188.4 × 45.6 mm enclosure, higher-temperature pot receiving study, existing thermal lands/TIM/matched shims, base attachments, feet, controls and accepted wire geometry. Its parent scene uses P03 db83, E28 fed (45 open connections) and E19 3b2a with the old R1. Newer E28/R1/PB/NF/FH electrical or wire candidates are not adopted. All thermal, installed-flow, physical, structural, fabrication and complete-wiring qualification flags remain false.

## Actual parts and evidence

- `generated/AP02-layout.png` and `.svg`: reviewed dimensioned layout, height stack and source-derived pin removals.
- `generated/AP02-BASE.step`: valid single-solid exact-curve BREP, independently round-tripped. Forty-two additional whole pins are removed from FI01's 960, leaving **918**. Base volume 476148.6224 mm³; independent pin/window mass balance agrees. The faceted native part differs by 8.28 ppm, a numerical comparison rather than a fabrication tolerance.
- `generated/current-native/`: **70/70 native checks pass**, including actual parts, floor/base/wall voids, fan/baffle/plate/pin clearances, shared floating mounting axes, matched shim endpoints, case and five actual obstacle families, pressure-boundary geometry and positive controls. Strict production-part/control STL gates require closed oriented nonzero boundaries; Boolean solids require `NoError`. Exact named profile gauges have independent analytic polygon volume/bounds checks.
- `generated/mating-seated/`: **22/22 supplemental native checks pass**, covering actual nominal seal/fastener/contact construction, eight overlap controls using the same seat guards, and three deliberately oversized radial/axial counterexamples.
- `generated/AP02-complete-modeled-component-review.3mf`: all 21 modeled scene families, 824246 triangles, exact per-object coordinate/order round-trip. Group topology caveats are explicit in `assembly-manifest.json`. This is a component review assembly, not a single manufacturable part or a completed loose-wire assembly.

The two floor/base openings have actual faceted net area **2563.1282 mm²**. The west wall's 18 rounded 4 × 36 mm slots have **2557.1437 mm²** total net area. Each seven-slot guard has **868.2002 mm²** actual faceted net area, above the 800 mm² minimum and below the optional 900 mm² preference. These are geometric areas, not aerodynamic free-area guarantees. The actual C3 board shadows 335.2663 mm² of floor projection, leaving 2227.8619 mm² unobstructed vertically; lateral turning through the 17.2 mm floor-to-board gap must be modeled separately.

Two 2 mm pressure-bay walls and tray geometry separate the interior inlets from the old 3724 mm² underside outlet. The base branches use two removable 6.25 × 10 mm meters through 10 × 10 mm wall ports. Opaque, fully filled composite lead-feedthrough receivers prevent an unreported open leak path; wire/resin selection, cure and actual sealing are unresolved requirements. The nominal pressure boundary has geometric coverage, not a measured leak rate.

## Fan and joint receiving requirements

The exact Sunon MF40100V1-1000U-G99 drawing defines the receiving envelope: 40 ± 0.5 mm square, 10–10.5 mm thickness, 32 ± 0.3 mm pitch, and 4.3 ± 0.3 mm holes (minimum 4.0 mm). The manufacturer-linked generic MF4010 STEP supplies nominal frame/end-face geometry only. It is external, hashed in `generated/fan-geometry.json`; no Noctua face geometry is substituted. The actual common top/bottom land is 223.6645 mm². Exact-part hot warp, rotor movement, gasket land tolerances and sealing are unqualified.

Measured 2.0–2.5 mm matched shims must pair with measured 10.5–10.0 mm frames to maintain the 12.5 mm receiving stack. The nominal STEP is 10.4 mm, requiring a 2.1 mm matched shim. Eight M3 × 20 receiving screws use the retained shared-floating-axis contracts, minimum fan bores 4.0 mm, explicit washers/seals and nut stack. No fixed-axis approximation is promoted. M2 meter hardware and all direct seal bearing faces are explicit receiving requirements; exact selected fastener bearing flats, torque, preload, thread engagement under production tolerances, strength and service life remain unapproved.

The HT800 0.79 mm sheet has a documented 0.688–1.171 mm supplied thickness interval. A 0.5 mm compressed gap spans approximately 27.3–57.3% compression; the source's 25% CFD row does not bound this complete interval. Custom profile conversion, registration, contact force, compression set, leak rate and mounting loads require actual qualification. Stock ±1.6 mm slitting does not approve the nominal 0.6 mm frame-side sealing land.

## Preserved failures and numerical seat contracts

`history/` captures exact historical source bytes; each reconstruction map binds its raw receipt/logs/meshes. It preserves initial primitive-gate/void-boundary findings, the original tray float32 sliver, the repaired tray, six Docker socket failures in which no CAD ran, and early interface trials. No failed execution is counted as a geometry pass.

`generated/raw-port-boundary-audit.json` and `raw-port-boundary-recheck.json` classify all 2430 residual triangles on the authored inlet facets (maximum 15.2553 nm). The named void-interior check alone uses a 20 nm XY erosion/end-plane exclusion; actual openings are unchanged. Deliberate material/void controls remain.

`generated/raw-mating-surface-audit.json` classifies all 18980 triangles of the eight rejected exact-seat comparisons, with no non-seat triangles. `generated/raw-mating-bolt-domain-audit.json` additionally bounds their bolt-axis domains. `mating_guards.scad` and `generated/mating-seat-contract.json` limit the supplemental test-only 20 nm exclusions to named seating planes, gasket footprints, R3.1 boss/facet and R2.2 filled-feedthrough interfaces. M3 plane exclusions are local to R3.71 around eight axes; M2 exclusions to R2.73 around four axes. Actual parts, dimensions and pressure apertures are unchanged. Eight 20 µm overlap controls and radial/axial witnesses survive the same guards. These are nominal correlated seat tests, not tolerance or factory approval.

`HT01-review-erratum.json` records that AP02 explicitly adds the same actual antirotation lug to the complete pot hardware group; the sealed HT01 sources remain unchanged.

## Read-only verification and captured replay

From the repository root:

```sh
python3 -S -m hardware.cad.a12.thermal.interior_airpath.audit
python3 -S -m unittest hardware.cad.a12.thermal.interior_airpath.test_review
```

`stage.py` is a **new live capture entry point**, not a captured replay. It refuses an existing candidate and must never be run to regenerate this sealed packet. `base_brep.py`, `drawing.py`, `assembly.py` and `seated_stage.py` likewise refuse existing outputs.

For a justified independent native replay, use `verify.py` with the reviewed Linux runner and a **new output folder outside this sealed packet**. It reads the captured private model and refuses stale captured bytes/existing destinations. The captured context retains repository absolute paths; this is a same-workspace captured replay, not a portable relocated-source rebuild. The main 70-case replay does not substitute for the separate 22-case seat proof or the saved-artifact audit.

```sh
python3 -S -m hardware.cad.a12.thermal.interior_airpath.verify \
  --openscad /Users/axelmckrnna/dev/rmx-publish/hardware/cad/a12/enclosure_growth/r1_local/linux_runner/openscad.py \
  --outdir /Users/axelmckrnna/dev/rmx-publish/hardware/cad/a12/thermal/ap02-independent-review
```

Actual installed fan curves, branch flow, leak balance, internal package-to-air heat paths, motor power/fault behavior, loose wiring, touch tuning, EMI, guard protection, structural loads and temperatures require their own evidence. The latest parent heat provision is 37.28570586 W before its 1.2 planning factor; AP02 provides no thermal inheritance from idealized all-heat-to-base models.
