# Print-first kit for the verified r6 housing

**Start with `TBH01-r6-print-first-kit.zip`.** This is a smaller, staged handoff for printing the housing fit prototype. It preserves the r6 housing geometry and adds five small, source-derived interface coupons. The complete 67-design r6 package remains available separately; it is not necessary to print all 67 designs to check the boards in the case.

This kit is for an **unpowered mechanical fit prototype**. It does not finish the selector, display/LED or angle-sensor carriers, harness or operating cooling. See `reference/r6-assembly.md` for full assembly details and limitations.

## Minimum print list

Choose one column, and print the quantities in `parts.csv`. Do not mix the one-piece and split shell/lid sets.

| Purpose | One-piece printer | Split version |
| --- | --- | --- |
| First: tray and board mounting | `shell` ×1 | `shell_left` ×1, `shell_right` ×1, `floor_join_plate` ×3 |
| Then: close the case | `lid` ×1, `rear_plate` ×1 | `lid_left/right` ×1 each, `rear_left/right` ×1 each, `lid_join_bar` ×2, `rear_join_bar` ×1 |
| Total minimum complete case | **3 printed pieces** | **12 printed pieces** |

The mounting posts are already part of the shell: no separate PCB standoffs are printed. The guide, touch backer, keys, optics, knobs and lever parts are optional for this first bare-case/board fit check. They are needed later for their respective control assemblies and are supplied in the full r6 package.

If the available print time is tight, prioritize the tray stage. It permits checking the current board outlines, 24 support locations, underside clearance and Trill passages before the lid finishes. A split tray needs its three joining plates and screws before mounting the boards. Printing only one half is a local dimensional check, not an assembled-tray test.

## Print order and fit tests

1. Print the **core coupons** first: `corner_shell_coupon`, `corner_lid_coupon`, `coupon` and `rear_coupon`. The included `00-core-fit-tests.3mf` arranges these four objects in **110 × 54 mm**, before brim/skirt. It carries millimetre geometry only, with no printer profile or G-code. You can instead import the four STLs. Use the same material, nozzle and dimensional compensation intended for the case.
2. Slide an actual M2 nut diagonally into the corner coupon from the open interior side. Fit its matching lid using M2×8 and a 0.4 mm washer. The nut must slide into position, stay below its retaining roof when tightening, and allow the lid registration lip to seat. Hand-tighten only. The corner coupon copies the actual r6 front-left interface; its added bottom is only a test-piece base.
3. Check M2 nut/through-hole fit and actual rear connectors in the other coupons. The nut coupon columns are AF4.0/4.1/4.2/4.3; matching bores Ø2.2/2.3/2.4/2.5. The housing uses AF4.2 pockets and Ø2.4 bores. Rear coupon openings are Ø8.2 RCA, Ø9.8 TS, 10.4×14.2 DC, 7.2×5.5 power switch and 12×8 USB. The audio apertures are generic allocations: test your exact jack hardware.
4. Slice the selected **tray stage**, inspect the complete toolpath and read the slicer's time/material estimate. Start it only after the coupon fit is acceptable. Then slice the lid/rear parts while the tray prints. No machine-independent completion-time promise is possible.
5. Assemble the tray with its nuts and feet, then check both boards unpowered. For the split version, the floor laps register the two halves and the three underside plates hold them together. Close the case only after checking that no hardware presses on either board.

The optional **control coupons** are also included, but need not delay the tray print:

- `pot_panel_coupon` reproduces the current **Ø9.5 hole in a 2 mm panel**. Test the actual threaded pot, washer and nut. `shaft_coupon` and `knob_16x13` check the shaft/socket interface; they do not establish the correct shaft projection for every knob.
- `button_panel_coupon` and `button_guide_coupon` reproduce the current Quantize opening, screw pattern and D-shaped guide. Use the included `button_quantize`, `holder_1` and one `retaining_clip`. Three clips are listed so there are spares for the small-feature test. The guide sits directly beneath the panel; the holder sits beneath the guide. Use two M2×8 countersunk screws in checked/tapped Ø1.6 holder pilots. A complete button test additionally needs the selected tactile switch, return spring and silicone contact described in the full instructions. Do not replace the compliant contact with a rigid spacer.

## Bed size and orientation

All files use **millimetres at 100% scale**. Never scale the housing to fit the bed. Center XY in the slicer; retain the supplied Z orientation.

| Part or group | Actual maximum footprint | With a 5 mm brim on every side |
| --- | --- | --- |
| One-piece shell/lid | 338 × 192.4 mm | 348 × 202.4 mm |
| Largest split piece: left shell | 175 × 192.4 mm | 185 × 202.4 mm |
| Split lid halves | 168.9 × 192.4 mm each | 178.9 × 202.4 mm each |
| Rear halves | At most 156.9 × 40.6 mm each | 166.9 × 50.6 mm each |

A nominal 200 mm bed does **not** fit a split shell with that brim in the supplied orientation. Account for purge lines, clips, exclusion zones and the actual usable area. A bed larger than the table values is useful for placement margin. Printer build volume and material have not yet been supplied.

The shell prints floor-down, with the cavity open upward. The lid prints visible-face-down, registration lip upward. Rear plates print outer-face-down, with the switch-body relief upward. Joining plates/bars use their supplied flat orientation; inspect bridges over nut pockets. The coupon panel, guide and pot plate print flat. The lid-corner coupon prints visible-face-down; its mating shell coupon prints on its added base.

## Slicer starting point

For the housing, a provisional starting point is 0.4 mm nozzle, 0.2 mm layers, four perimeters, five top/bottom layers and 25–30% infill. Use the manufacturer's material/printer profile for temperatures. A brim may help the large flat parts. Verify small bores, captive-nut bridges and the 1.4 mm guide in the layer preview; don't fill working pockets with support. The small clips and holder lips may need a finer layer height or local support, depending on the printer.

PETG is a reasonable mechanical-prototype candidate; PLA can serve an unpowered dimensional trial. This is not an operating-temperature or strength qualification. Official background: [PETG](https://help.prusa3d.com/article/petg_2059), [brims](https://help.prusa3d.com/article/skirt-and-brim_133969), [layers/perimeters](https://help.prusa3d.com/article/layers-and-perimeters_1748). These settings are untested starting assumptions, not ready-made G-code.

## Minimum hardware to have ready

| Joint | Hardware |
| --- | --- |
| Lid | 7 × M2×8, 0.4 mm washers, M2 nuts |
| Rear plate | 4 × M3×12, 0.5 mm washers, M3 nuts |
| Main PCB mounts | 24 × M2×10, 0.5 mm washers, M2 nuts; head/washer OD≤4.5 and combined height≤2.5 above PCB |
| Trill, if fitted | 2 × M2×25, 0.5 mm washers, M2 nuts; same head limits |
| Split tray only | 6 × M3×8 countersunk and M3 nuts |
| Split lid only | 4 × M2×6, 0.4 mm washers and M2 nuts |
| Split rear only | 2 × M2×6, 0.4 mm washers and M2 nuts |
| Feet | At least four adhesive elastomer feet, **≥6 mm high**, clear of nut access and underside join plates |

Nut assumptions are M2 AF4.0×1.6 and M3 AF5.5×2.4. Check your stock. The split floor screws reach Z−5.2; 6 mm feet leave 0.8 mm nominal table clearance. PCB screws intentionally use M2×10; M2×8 barely engages the power-board floor nuts. Full positioning and installation order are in the preserved r6 assembly instructions.

## What is and is not finished

The r6 shell, supports, lid, rear panel, split joints and modeled control/lever clearances have verified print files. This kit adds verified small tests for the actual corner nut/lid interface and current control apertures. It does not change either PCB or their mounting coordinates. `latest-physical-compatibility.json` independently confirms that the TBP63 power-board outline, thickness and all 1,101 physical footprint records match the TBP61 geometry used by r6. Later copper-only checkpoints do not themselves change these interfaces; any future placement change needs renewed checks.

The source audit still finds no finalized mounting pattern/carrier for the PCB-mount settings/release switches, BPM/panel LEDs, or angle-sensor board. Their reserved envelopes are not attachments. Purchased lever retention/spring details, full harness and operating thermal assembly are also unfinished. Those unknown interfaces cannot be completed reliably by inventing holes in unspecified hardware.

You can print and assemble the **fit prototype** now, subject to printer and coupon fit. A functional powered enclosure is not released. The remaining information essential to the actual print job is the printer's usable build volume, nozzle, filament/material, and the slicer's measured print time.

## Evidence and sources

`manifest.json` records every delivered file. `verification.json` binds the new coupon geometry to the preserved r6 sources. The new native checks exercise corner nut insertion, axial retention, lid seating and button motion through the test panel/guide. The independent mesh report checks exact delivery facets without repairing them.

The editable source tree preserves its relative includes. `source/hardware/cad/two_board_print_02/coupons.scad` selects a coupon by its filename stem via `-D part=...`. Existing case/control meshes are copied byte-for-byte from the independently checked r6 delivery. The r6 ZIP SHA256 remains `7f3c53a54b73f08c3b2342c9bcb806b327a6ca1779ff3d3dea3c82932126791d`.
