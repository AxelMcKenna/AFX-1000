# TC01 — current Trill Craft C3 mounting candidate

A separate insulating saddle can carry the current C3 board at **Z30.6 mm**, 7.6 mm above its old nominal datum, while E19 stays low. It attaches at the four existing touch-backer corner interfaces and supports the two real board mounting holes from below. The central touch aperture remains open. This is a reviewable local geometry candidate; exact material, hardware, tolerances, backer strength, wiring and touch performance remain unqualified.

The official [RevC datasheet](https://github.com/BelaPlatform/Trill/blob/537ebd6bb9c1de736aa0fc65c66fc1115b7875ef/trill_datasheet.pdf), version1.3 dated2025-02-03, states that RevA was52 mm long and RevC is53.8 mm long. Its page26 gives21.8 mm width,1.6 mm thickness and two M3-compatible mounting holes37 mm apart, **electrically unconnected to ground**. The [official C3 native PCB](https://github.com/BelaPlatform/Trill/blob/537ebd6bb9c1de736aa0fc65c66fc1115b7875ef/hardware/craft/REV_C3_KiCad/trill-craft.kicad_pcb) independently yields53.848 ×21.844 mm nominal outline bounds. The existing52 ×21 mm project reserve therefore undersizes current C3 by1.848 ×0.844 mm. This candidate uses the larger conservative rectangular outline and both actual Ø3.2 mm holes, rather than drawing guessed supports.

| Interface | Nominal candidate |
| --- | --- |
| Board datum / top | [82,123.5,30.6] / Z32.2 mm |
| H2 / H1 hole centres | [93.0871,134.4352] / [130.0871,134.422] mm |
| Actual native hole separation | Approximately37 mm; retain the exact small Y offset in the report |
| Saddle floor / board seats | Z24.6..26.2 /30.6 mm |
| Existing backer corner interfaces | X73/143 ×Y123/145 mm, source Ø1.6 mm pilots |
| Upper saddle mating plane | **Z42.2 mm**, actual raised backer underside |
| Mount seats / saddle bores | Ø5.4 / Ø3.4 mm |
| Upper corner supports | Ø5.8 mm, Z26.2..42.2, Ø2.2 mm interface reserve |
| M3 screw envelope requirement | Ø6.4 ×3.2 mm head plus nominal3 mm shank; exact hardware and engagement remain unselected |

The frame is beneath a declared3 mm solder-tail allocation. Thirteen actual terminal groups define separate conservative above-face component reserves, each using the existing6.4 mm project projection allocation. Thirty-six actual circular connection pads receive separate tail reserves. Neither this projection nor the tail dimensions are measured or guaranteed manufacturer assembly bounds. No unselected right-angle header body is silently assumed: direct soldered I²C/electrode leads are the candidate interface, with their complete wire and strain geometry still required.

**PM01 erratum:** the previous sealed panel audit's touch-backer absolute Z fields omitted the module's enclosing `panel_z−34` translation. Its +7.6 mm shift and module classification were correct, but absolute baseZ should be34.6→42.2 mm, not32.6→40.2. [PM01-erratum.json](PM01-erratum.json) binds the affected sealed report; the original seal remains unchanged. The native contact control rejected the short-post40.2 mm trial, retained under `history/`. A prior undefined-variable attempt is also retained as rejected evidence. The final local run has no warnings and includes the actual imported backer at the explicit43.6 mm panel datum.

The existing E19 J9 connection maps AGND/V3V3_IO/SCL/SDA to Craft J1 pins3/4/6/5. Reset/event are pins1/2 and need an explicit integration policy. Current high-end `hardware/firmware/BoardIO.h` already uses Trill's0x30 identification/DIFF protocol. The MPR121 code in `firmware/daisy/main.cpp` belongs to the separate B1/5V profile and is **not** evidence of a high-end protocol failure. Current C3 command, timing and physical tuning remain unmeasured.

The manufacturer warns that [electrode cables themselves become sensing surfaces](https://learn.bela.io/tutorials/trill-sensors/working-with-trill-craft/). Moving controller and touch assembly together preserves their nominal relative geometry; it does not establish immunity, capacitance limits, sensitivity, grounding, baseline behaviour, ESD or performance. Actual eight-channel foil wiring, unused-channel grounding, whole-bus pull-ups, I²C rise time and complete loose harness routing must be proved.

[Dimensioned drawing](generated/dimensioned.svg), [PNG preview](generated/dimensioned.png), [STEP saddle](generated/saddle.step), [native STL](generated/saddle.stl) and [native evidence](generated/verification.json) are provided. The saddle is one valid STEP solid; analytic versus native64-sided STL volume differs by0.0641%. All13 narrowly scoped native cases pass: required solids; saddle versus conservative board, actual terminal-derived component and tail allocations, and raised backer; head envelopes versus component/backer allocations; central-aperture clearance; two0.008 mm³ positive controls; and intentional backer contact. Complete enlarged-case, other-board, positive/return-link and harness collision renewal belongs to subsequent system integration.

Vendor PCB/datasheet/README bytes remain external under `/private/tmp/afx-trill-vendor`, hash-bound in `report.json`, at official commit537ebd6bb9c1de736aa0fc65c66fc1115b7875ef. The current official hardware/datasheet license is CC BY-SA4.0; this folder does not redistribute the vendor PCB, STEP, logos or datasheet. The independent mechanical fact extraction, rectangular reserve and new saddle do not modify manufacturer electronics or existing project artifacts.

```sh
python3 -S -m unittest hardware.cad.a12.trill_mount_candidate.test_review
python3 -S -m hardware.cad.a12.trill_mount_candidate.review
```

The10 portable checks reject old outlines, grounded-hole assumptions, short posts, swapped pins, missing required solids, forged empty geometry and false qualification claims. Local fit is conditional on the declared geometry. All physical, electrical, fabrication and material qualification flags remain false.
