# U10 — stronger copper path, separate unreleased candidate

**The eight-via/cleared-field candidate improves the actual thermal path without reducing the earlier material, gap, board-thickness or temperature allowances. It is not electrically complete or thermally qualified.** At a 60 °C local base and the retained 0.629222 W loss allocation, the grid320 reference result is **84.80 °C nominal / 95.39 °C sensitivity**, compared with **96.48 / 112.44 °C** in the sealed four-via candidate.

[Drawing](generated/review.svg), [PNG](generated/review.png), [PCB](variant/power_p03.kicad_pcb), [native electrical receipt and exact removal ledger](variant/receipt.json), [actual-copper analysis](generated/analysis.json), [native collisions](generated/verification.json), [sealed packet](handoff.json).

## Actual construction and electrical obligations

This candidate starts from sealed U10 PCB `981c308665f1a90f3e7a3e3954762949c64028da907b724101375046afde3f30`, itself an isolated derivative of the fully routed P03 `42addb43…`. The new filled PCB is `6d563e91ada1e9815c42325987ad0a12d53b5ca57080879d96373d033d4a291a`. Canonical P03 and all files in the sealed `u10/` and `u102/` packets remain unchanged.

U10 remains **LT3090IDD#PBF on F.Cu native (194.2,129.3)**, housing **(262.2,137.3)**. EP11 is live **RAW_N22/IN**, with the DD package's **5.5 K/W reference θJC**; that is not a guaranteed complete-path upper bound. The original source B-side pose, polarity/package evidence and rejected no-move trials remain in [the sealed packet](../u10/README.md).

Eight actual 0.60 mm land / 0.25 mm finished-hole EP vias replace four: X193.8/194.4 × Y128.55/129.05/129.55/130.05. All lands fit the manufacturer's minimum 1.55×2.28 mm EP. Original matching remote barrels remain where not explicitly removed. The native field is refilled with the actual C50 construction: 1.6 mm nominal, outer85/inner70 µm copper, required minimum50 µm barrel wall. Resin fill is not treated as copper. The 0.50 mm row pitch leaves 0.25 mm finished-hole gap; a 0.35 mm predrill at the required minimum wall leaves only **0.15 mm nominal drill web and 0.125 mm preplate annulus**. Wall maxima, drilling/registration bounds, cap flatness and actual factory approval/microsections remain missing.

The draft removes **82 additional original copper objects**, including the four replaced RAW_N22 vias and AGND, 5V_DIG_SRC, RAW_P17, N19_SRC, N12_SRC, NREF_FILTER and N19_SET routing. Every removed object is enumerated with exact original S-expression and UUID. Unlike the earlier candidate, **NREF_FILTER is now among the restoration obligations**. Full native checks give **zero hard DRC/ERC/parity findings, 19 opens and 20 dangling warnings**. These are real electrical defects, not waived warnings. The power-board owner has the exact handoff; restore affected supply, return, reference/SET and decoupling loops in an isolated routing branch, then renew electrical checks, actual thermal extraction and quiet-ground analysis. The thermal screen cannot establish that restoration will fit without reducing the current field.

## Geometry and thermal comparison

The actual land, TIM cut, floor window and all component/connector/board datums stay identical to the sealed U10 candidate: land3.65×3.70 mm at housing X258.1…261.75/Y135.7…139.4, topZ5.28; TIM5.65×5.70 mm; proposed floor window X256.9…262.95/Y134.5…140.6. The LAND remains an addition for a future integral machined base boss, not a loose unsupported post. The complete revised base and clamp/pressure construction are not released.

All actual native footprint and pad inventories are independently compared with the sealed candidate before reusing its captured obstacle geometry. Seven native Manifold cases cover the real land/TIM, both-face component and tail reserves, mount heads, other boards, controls, positive/return links and case. Required geometry and separate land/front-U10/C32-tail witnesses must be nonempty; an empty collision row with an actual STL is rejected. Nominal intersection clearance is not a manufacturing-tolerance proof: the previous ~0.20 mm TIM-to-body/lead gaps still require an approved placement/trim/die-cut/registration budget.

The grid320 actual matching B.Cu under the 13.505 mm² metal land increases from **8.629 to 13.205 mm²**. The model uses actual saved fill/pads/tracks, physical holes, eight direct EP barrels and matching remote barrels. No AGND heat path, fictitious sink, resin copper-core or FR4/air credit is introduced.

| Declared inputs, unchanged | Nominal | Sensitivity |
|---|---:|---:|
| Cu conductivity, W/(m·K) | 385 | 350, unverified |
| TIM conductivity, W/(m·K) | 6, typical | 4, unverified |
| Physical gap, mm | 1.22 | 1.50 |
| Extra interface assumption, K/W | 0.8 | 2.0 |
| PCB thickness, mm | 1.60 | 1.76 project allocation |
| Package reference, K/W | 5.5 | 5.5, not an upper bound |
| Total reference path, K/W | 39.416 | 56.239 |
| Junction at hypothetical60 °C base, °C | 84.802 | 95.387 |

Sensitivity energy shares are ~10.18 K/W barrel, 6.19 sheet and 28.58 TIM, plus EP peak-above-mean1.45, package reference5.5, axial land2.34 and assumed interface2. They are network energy shares, not independently proven series bounds. Two meshes change the sensitivity path by0.58 K/W; this is not a discretization-error enclosure.

At **65 °C base plus an illustrative2 °C positive expanded uncertainty allocation**, the reference sensitivity result is **102.39 °C**, leaving7.61 °C to the110 °C project allocation. The actual acceptance requirement is **total path upper≤68.34 K/W** at the retained loss allocation, or a correspondingly renewed bound if actual loss/base/uncertainty differs. Current source parameters do not establish that upper bound. If every other modeled term were independently bounded, the derived remaining package-plus-interface allocation would be19.60 K/W; this is a requirement, not a guaranteed package/contact value. All actual base, power, whole-path and uncertainty bounds remain null.

The selected physical TIM remains the original Henkel TGP6000ULM sheet2195667, nominal1.524 mm. The1.50 mm-gap sensitivity is conditional on a received pad that actually spans it under an approved compression condition; the nominal thickness tolerance does not guarantee this for every received sheet. An unmatched pad is a rejected assembly, not a fictitious conductive bridge. A thinner TGP7000ULM0.020 inch sheet was investigated using its [official TDS](https://datasheets.tdx.henkel.com/BERGQUIST-GAP-PAD-TGP-7000ULM-en_GL.pdf), copied and hashed under `sources/`. It is **not selected here**: a0.508 mm pad cannot span a0.4064 mm nominal gap plus the unchanged0.28 mm variation. No thermal bridge is credited without an actual matched-height construction. Its typical7 W/(m·K), 40-mil dielectric test and modulus do not qualify a20-mil assembled insulator.

## Independent frozen U102 audit

[Audit report](generated/u102-angle-audit.json) and [native reader evidence](sources/u102-native-pad-orientation.json) preserve the original `bd4765eb…` nine-via U102 board. Native KiCad10.0.7 confirms that saved PCB pad angles are already absolute. The frozen model double-adds footprint angle for rotated C101.2, C109.2, D101.2, J106.2 and R104.2. A separately copied model corrects only that operation; all frozen sources stay untouched.

The correction changes the grid320 connected-path temperatures by about **+0.000005 °C**: corrected nominal95.734606 °C and original sensitivity105.426607 °C. A separately declared **1.76 mm PCB sensitivity**, previously omitted from that U102 scenario, gives **106.226716 °C** at60 °C base. At65 °C base plus2 °C uncertainty that exceeds110 °C. This remains a hold. The owner has requirements for absolute-angle extraction, fresh merged-board source binding, actual holes/foreign-net voids and received stack/barrels. No historical U102 result is promoted to a physical pass.

## Remaining acceptance and reproduction

Restore every actual electrical open, rerun source-bound electrical/return/thermal checks, obtain approved C50 construction and received microsections, validate actual TIM pressure/compression/wetting/flatness/isolation/durability, then measure whole junction-to-base resistance with a validated junction-temperature method and positive uncertainty. Whole P03 heat/base/ambient performance and simultaneous load conditions remain open. A PCB surface reading, JEDEC θJA or thermal shutdown is not junction qualification. Instrument live RAW_N22 with suitable isolation; the floating-chassis policy remains unchanged.

All fabrication, physical-fit and thermal-qualification flags are false. No canonical net/port, frozen thermal kit or sealed historical source was changed. Portable contract/source/artifact tests require no native tools; numerical replay is optional with `AFX_THERMAL_SOLVERS=1`.

```sh
python3 -m hardware.cad.a12.thermal.candidates.u10_stronger.synthesize --kicad-cli /path/to/kicad-cli
python3 -m hardware.cad.a12.thermal.candidates.u10_stronger.generate
python3 -m hardware.cad.a12.thermal.candidates.u10_stronger.verify --openscad /path/to/OpenSCAD
/path/to/numerical-python -m hardware.cad.a12.thermal.candidates.u10_stronger.analyze
/path/to/numerical-python -m hardware.cad.a12.thermal.candidates.u10_stronger.audit_u102
/path/to/numerical-python -m hardware.cad.a12.thermal.candidates.u10_stronger.draw
python3 -m hardware.cad.a12.thermal.candidates.u10_stronger.handoff
python3 -S -m unittest hardware.cad.a12.thermal.candidates.u10_stronger.test_candidate
```
