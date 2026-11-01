Actual nine-via U102 candidate with wider local contact

This packet binds the real post-refill P03 candidate PCB `bd4765eb8184a2c5fe336d68e0951ab383e2d959fa05a099e4dcaa14e82de119`, copied under `sources/`. It preserves canonical P03/E28, the rejected six-via trial, and the frozen T01 base. The PCB owner's actual candidate has nine direct 0.70/0.25 mm EP vias on 0.50 mm pitch, six filled AGND spreading zones, additional remote barrels and three moved bottom components: R110, R130 and C109. The copied `current-native.json` binds the actual all-severity PCB DRC report: zero violations and 25 opens. Fresh schematic ERC/parity were not run for that PCB-only diagnostic. This is an electrically incomplete candidate.

The first owner-proposed metal contact was 5.5 × 5 mm. This separate MCAD trial extends its left edge to capture the existing saved copper border without inventing new copper or moving more parts:

| Item | Native PCB coordinates | Housing coordinates / Z |
| --- | --- | --- |
| Metal contact, 7 × 5 mm | (121.75,117.5)–(128.75,122.5) | (189.75,125.5)–(196.75,130.5), top Z5.28 |
| Insulating TIM outline, 9 × 7 mm | (120.75,116.5)–(129.75,123.5) | (188.75,124.5)–(197.75,131.5) |
| Proposed retained-floor window | — | (188.55,124.3)–(197.95,131.7), through the 2.8 mm carrier floor |
| Board datum | Relative (0,0) | (168,108,6.5), with matched assembly plane 6.3–6.7 |

The nominal TIM left edge clears the actual J106 tail reserve by 0.35 mm. That is a CAD dimension, not an approved registration/tolerance margin. All candidate P03 bodies, through-hole tails and mount-head reserves are rebuilt from its own PCB/BOM using the shared height rules. E28 and other inherited electronics, all controls, the actual return and positive-link assemblies, and the retained-case variant are included. The packet contains 506 actual P03/E28 electrical component records plus tails and mount hardware reserves. Unapproved body/mate heights remain requirements rather than measured dimensions.

Five native cases passed: required metal/TIM geometry is 249.060006 mm³ versus independent STEP volume 249.06 mm³; actual component, link and modified-case intersections are empty; the injected 0.008 mm³ interference witness is detected. Each case has its native log and actual STL where nonempty. `LAND.step`, `TIM.step`, their STL counterparts, `checks.scad`, `obstacles.json` and `geometry.json` provide the reviewable geometry. The frozen base has not acquired this fifth land/window.

The numerical solver uses the actual saved AGND filled polygons, matching pads/straight tracks and through-via annuli. Foreign-net clearance voids and physical holes are retained. The model does not replace the contact with an ideal blanket-copper area. In the refined grid, 22.7827 mm² of actual bottom AGND copper lies under the nominal 35 mm² metal land. All six actual layers and nine actual direct EP vias are included; C50's 50 µm wall is a fabrication requirement, not received microsection evidence. Resin receives no solid-copper credit.

The selected IC remains TPS7A1601DGNR. The model adds TI's 14.9 K/W DGN bottom-package metric; the alternate DRB package's 4.7 K/W is inapplicable. The native EP pad is 1.68 × 1.88 mm, while heat is applied over the manufacturer's minimum 1.34 × 1.66 mm package pad. The package metric has no supplied production upper tolerance. The power input remains the conservative, unverified 0.9613069233 W allocation.

| Declared scenario, refined 320² cells per layer | Nominal/reference inputs | Illustrative sensitivity |
| --- | ---: | ---: |
| Copper conductivity | 385 W/mK | 350 W/mK |
| TIM conductivity | Typical 6 W/mK | Unverified 4 W/mK |
| TIM gap | 1.22 mm | 1.50 mm |
| Additional contact resistance | Assumed 0.8 K/W | Assumed 2 K/W |
| Added package metric | Reference 14.9 K/W | Reference 14.9 K/W |
| Total conditional junction-to-base path | 37.17294 K/W | 47.25504 K/W |
| Junction scenario at 60 °C base | 95.7346 °C | 105.4266 °C |
| Junction scenario at 65 °C base | 100.7346 °C | **110.4266 °C before uncertainty** |

The sensitivity is not a manufacturer-guaranteed enclosure. The 160/320 grid differences are 0.11587 K/W nominal and 0.23871 K/W for the sensitivity. Linear KCL residual and the 1 W energy identity are checked, but two meshes do not provide a discretization-error bound. The model omits FR4, parallel air paths, lateral TIM conduction and spreading outside its 12 × 12 mm domain. Radial via/cap conduction, nonuniform package heat flux, solder/mask/contact behavior and material uncertainty are not physically bounded. These temperatures are calculations, not observed temperatures.

At a hypothetical 60 °C upper base temperature, the 110 °C project junction allocation permits 52.0125 K/W before uncertainty, or 49.9320 K/W if a separate 2 °C uncertainty allocation were justified. At 65 °C those figures become 46.8113 and 44.7308 K/W. These are examples of the acceptance equation, not newly approved measurement limits. The real acceptance must use source-bound upper IC heat and base temperature, a bounded aggregate path and positive expanded measurement uncertainty. Those bounds remain null; guardbanded acceptance remains false.

The fifth pad also needs a real pressure/compression stack. The collision TIM top Z6.3 represents the lowest matched board plane; it does not assert a guaranteed compressed thickness for a received pad. Match the fifth sheet thickness and assembled plane to the existing pads/shims, verify board deflection and clamp-force distribution, and measure actual compression/contact. No solder-mask or anodize insulation credit is allowed. Retain the selected electrically insulating TIM, filled/capped flat vias and the quiet-ground isolation policy. Actual dielectric performance, wear, pressure, cap flatness and hot compression remain unqualified.

Remaining physical work includes received C50 plating/fill/annulus/web microsections; manufacturer or lot-tested minimum TIM conductivity and contact behavior; an assembled fixture with all five contacts; source-valid full normal heat at 0–40 °C ambient and worst operating profile; calibrated aggregate junction/base thermal-path measurement with uncertainty; and actual assembled tail/body/registration checks. Measure or justify junction temperature with suitable calibrated electrical/vendor methods. A case thermocouple plus unrelated θJA, or the thermal-shutdown trip, is not a normal-operation junction qualification.

Reproduction:

```sh
python -m hardware.cad.a12.thermal.candidates.u102.stronger.generate
python -m hardware.cad.a12.thermal.candidates.u102.stronger.verify --openscad /path/to/OpenSCAD
python -m hardware.cad.a12.thermal.candidates.u102.stronger.analyze
python3 -S -m unittest hardware.cad.a12.thermal.candidates.u102.stronger.test_candidate
```

CAD generation uses CadQuery; analysis uses NumPy/SciPy. Seven tests pass with `AFX_THERMAL_SOLVERS=1`, including actual saved-copper wall/TIM mutations. Portable tests skip only that solver test. The actual SVG/PNG drawing was visually reviewed. All physical, thermal-path, PCB-release, frozen-base-modification and fabrication flags remain false. Native global-source freshness is bound to its capture checkpoint; a later source promotion requires renewed comparison, not inheritance of this result.
