# AUX package and placement readiness

This isolated library selects manufacturer land patterns for the six package types that were missing or generic in the preregulator/held-rail schematic candidates. It does **not** edit either schematic candidate or the accepted PCB. It is not a fabrication release or a claim of housing fit.

| References | Selected library footprint | Maximum package envelope, mm | Land basis |
|---|---|---|---|
| P_U900 | AUX_READY:TI_DQC0010A | 2.1 × 3.1 × 0.8 | TI DQC0010A 4218281/A, PDF pp31–32; 0.5 × 0.25 pads, 0.5 pitch, row centers ±0.95; EP 0.84 × 2.4 |
| E_U900, P_U902 | AUX_READY:TI_DSE0006A | 1.55 × 1.55 × 0.8 | TI DSE0006A 4220552/B, pp37–39; asymmetric pin 1 and mixed mask definition |
| P_L900 | AUX_READY:Coilcraft_XAL4040 | 4.3 × 4.3 × 4.1 | Coilcraft 806-4 p4; 0.98 × 3.4 pads, **2.37 center spacing**, not inner gap |
| P_R902 | AUX_READY:Vishay_CRCW2512 | 6.5 × 3.3 × 0.7 | Vishay 20035 p11, reflow; 1.45 × 3.50 pads at ±3.10 |
| P_C902, P_C905 | AUX_READY:KEMET_D_7343_LevelB | 7.6 × 4.6 × 3.1 | KEMET T2076 p28 density B; 2.37 × 2.43 pads at ±3.12; courtyard 9.12 × 5.10 |
| P_U901 | AUX_READY:TI_DBV0005A | 3.0 × 3.55 × 1.45 including leads and longitudinal mold-flash allowance | TI DBV0005A 4214839/K pp56–58; 1.1 × 0.6 pads, rows ±1.30, 0.95 pitch |

`footprints.json` binds these dimensions to source PDF hashes. All cited drawing pages were visually inspected. KEMET's manufacturer-authored 2019 family sheet is cached from a distributor-document mirror; its source URL and publisher are in `primary/source.json`. The exact-part sheet already cached under `held_rail/primary` supplies the selected part's body dimensions. The nominal density B land is selected instead of the minimum density C land, whose manufacturer text explicitly calls for additional process qualification.

The DSE drawing dimensions describe the exposed areas. Pads 1–3 are solder-mask-defined: the implementation enlarges copper 0.05 mm per edge and shrinks its mask/paste opening accordingly. Pin 1's exposed area extends inward 0.1 mm, moving its center from −0.60 to −0.55. Pads 4–6 are non-mask-defined. **The left-side copper gap is 0.15 mm, below TBP72's general 0.20 mm clearance rule.** This is a real unresolved process/rule conflict. Do not silently waive that rule or promote these footprints. The 0.125 mm stencil example is a source geometry, not an approved assembly process.

P_U900's EP needs soldering and an engineered thermal connection. TI shows three optional 0.2 mm via sites at (0, −0.95), (0,0), (0,+0.95); none is embedded in this footprint. Via diameter, fill/tenting, stencil voiding, copper area and actual thermal resistance require the board/fabricator review. P_U901's footprint follows the specific TI land instead of the previously assigned generic SOT-23-5's 1.325 mm pad length. Already assigned ceramic and TNPW footprints remain unchanged; their DC-bias/effective-capacitance qualification is still outstanding, and this checkpoint does not imply a fresh manufacturer land-pattern approval of those inherited library entries.

## Placement screen

`screen.py` consumes the **frozen TBP72** native PCB and capture, verifies that their PCB hashes agree, and searches the power-board area at 0.5 mm increments. It uses actual native surface copper (including filled surface zones), transformed footprint courtyard bounding boxes, through holes and all rule areas. It adds a conservative 0.25 mm obstacle buffer and 0.5 mm outline inset. All existing footprints have courtyards. This is a sufficient-empty-rectangle test, not a proof that rejected locations cannot be used with a detailed layout.

`placement-screen.json` contains exact coordinates, rotations, counts and source hashes; `placement-screen.svg` shows first choices on B.Cu. Green and blue rectangles are **alternative independent reservations**, and must not be combined when they overlap. The bulk pair reservation is 9.12 × 10.7 mm, including two 5.10 mm courtyards separated by 0.5 mm. The regulator-chain reservation is an engineering allowance of 22 × 12 mm, not an authored component layout. A 24 × 20 mm combined reservation has no passing site under this screen.

The nearest cap-pair screen candidate is B.Cu at (168,122.5); each cap could be centered at (168,119.70) and (168,125.30), with nominal anode on the left in board coordinates after choosing the mirrored footprint orientation. The pair still needs local input bypass, short common return, resistor-to-cap wiring and the held LDO next to its output bypass. Closest regulator-block alternatives are B.Cu around (149,170.5) rotated 90 degrees and (113.5,169.5). Those are tens of millimeters from P_U102 at **(190.5,130), F.Cu**, so short input switching loops, return continuity and remote sensing cannot be assumed. Ranking uses the actual parsed P_U102 location.

Do not treat a remotely located cap reservation as satisfying the hold-up model: series distribution resistance, the return path, the effective capacitance at operating conditions, reset trace loading and actual gate-driver loads remain acceptance conditions. Buck input capacitor, buck/inductor/output capacitor and return must form a compact local cell; the 5 V monitor and held LDO must sense the corresponding local nodes. E_U900 should remain local to the main-AUX detection/reset function, rather than being moved merely to fit a power block. The 4.1 mm inductor and 3.1 mm bulk-cap heights require a new assembly/housing clearance check on B.Cu; no such clearance is established here. Existing copper is preserved by the screen, but no supply routes, reference-plane paths, thermal spreading, EMI distances or connector accessibility are qualified.

## Verification and next integration step

Six footprint files loaded through pinned Linux KiCad (`native/native-footprints.json`), with no PCB written. `verify.py` checks native hashes, exact pin sets and primary-source hashes; it independently measures the 0.15 mm DSE gap and retains the explicit conflict. Three regression tests cover that reporting and rejection of stale footprints/extra native pads. The isolated schematic/native ERC from `held_rail` is unchanged.

Before assigning these footprints in a fresh schematic/PCB candidate: resolve the DSE fabrication rule, construct a compact placed power cell, rerun native DRC/reference checks, and check component heights against the current housing assembly. If preserving all accepted placement prevents a practical power cell, propose a narrowly scoped placement revision with the original source snapshot retained. Electrical current, discharge, capacitor, startup and thermal qualification limitations remain as documented in `held_rail/README.md`.

Self-review corrected the regulator reference position from a prior assumed y=133.4 to the actual y=130, corrected the CRCW source page to 11, included DBV mold-flash allowance, expanded circular courtyard bounds to their full diameters, and detected the DSE clearance conflict. These are screening artifacts, not an independent review or a completed physical design.
