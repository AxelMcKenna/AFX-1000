# Main PCB fastener and copper-contact audit

The selected assembly still uses generic heads at 22 main-board mounts. This study proposes full screw/washer/nut stacks while preserving the sensor-owned D_H2/D_H5 mounts and original shallow nut pockets. No replacement hardware is selected.

Sources visually checked from retained supplier PDFs:

- [Accu SSCF-M2-10-A2](https://www.accu.co.uk/api/product-datasheet?id=3794): fully threaded M2×10; head Ø3.62–3.8, height1.86–2.0, pitch0.4, hex1.5 mm.
- [Accu SSCF-M2-12-A2](https://www.accu.co.uk/api/product-datasheet?id=3795): same stated head/thread dimensions, nominal12 mm length.
- [Accu HRDW-M2-A4-BL](https://www.accu.co.uk/api/product-datasheet?id=404939): DIN433 washer OD4.2–4.5, ID2.2–2.34, thickness0.25–0.35 mm. Its coating is not credited as insulation.

The proposed receiving bearing area is radius2.4 mm: maximum washer radius2.25 plus project acceptance limit0.15 mm for washer-center registration. The polygon circumscribes that circle. Registration is a receiving/assembly requirement, not a supplier guarantee. All 22 mount poses are matched to the exact selected native PCB footprint ownership; reference prefixes do not determine board membership.

## Confirmed copper under the bearing area

At signal mount D_H4=(188,80), two LINK_SDA tracks and one LED_39 via lie inside even the original nominal Ø4.5 mm head/washer area:

| Copper object UUID | Radial copper-edge distance | Gap to nominal radius2.25 |
|---|---:|---:|
| ddc4f060-acad-5cdf-b2c5-eacdce6eecf9 | 2.023482 mm | −0.226518 mm |
| f9f46967-df4b-52ce-b081-6c81851d0ff4 | 2.037756 mm | −0.212244 mm |
| ecea17e2-69ed-5621-9e63-7ff6ca085a4f | 2.205993 mm | −0.044007 mm |

These distances use exact segment centerlines/widths and via center/diameter, not only conservative pad bounding circles. They violate the proposed no-copper-under-conductive-bearing requirement. No claim is made that an assembled short has already occurred; solder mask or black coating has not been qualified as a load-bearing insulation barrier. The earlier 94 mechanical clearance checks do not model copper/hardware electrical contact and therefore do not cover this condition.

The other eight screened signal mounts and all 13 power mounts have no conservative contact hit for the specified receiving footprint. This is an outer-copper contact screen, not a proof of fastener strength, full mechanical fit or physical insulation. Pads are conservatively circumscribed; filled-zone hole bridges are reconstructed with winding checks; unsupported geometry fails rather than being ignored.

`contact-keepouts.json` supplies all22 F.Cu receiving regions and exact board/source hashes. Signal routing must explicitly repair the three declared objects, preserve all other copper and connectivity, and verify returns/reference and native rules. Native rule-area keepouts should enforce the constraint on later routing. The source-bound `copper-screen.json` retains the original finding; it must not be rewritten to imply the selected r98 board passed.

## Conditional full-stack geometry

`parts.scad` models all22 full nominal screw/washer/nut stacks, preserving D_H2/D_H5 and the original nut-pocket roof. Signal mounts use10 mm screws; power mounts use12 mm screws with the sourced0.3 mm washer. H_NEW5 here is the bare-board mount; the separately unselected touch cradle requires its own14 mm screw/tab stack.

The declared receiving budget leaves at least0.51 mm (signal) and1.30 mm (power) of full thread beyond the nut after a0.4 mm incomplete-tip allocation. Minimum table gaps are4.11 and3.20 mm **if measured loaded local floor clearance is at least6 mm**. Nut flat alignment±0.5°, nut centering0.05 mm, screw centering0.1 mm and washer-to-screw centering0.05 mm are project acceptance requirements. The length ranges9.71–10.29 and11.65–12.35 mm are receiving limits informed by the retained Unbrako js15 table, not separately stated Accu length guarantees.

Ten native receiving-envelope checks pass against74 external roles; an additional check passes against the subsequently selected S04 wire. Own-contact checks retain all22 washer/PCB seat planes and all22 nut/pocket-roof planes, without calling those contacts empty intersections. Eleven host tests cover stack failures and NPTH discrimination. The source PCB's12 signal and23 power NPTH pads are proved wholly contained by their drill apertures; enlarged or offset annuli are not silently excluded. Use `npth_guard.audit()` before applying the frozen `copper_screen.audit()` to a different board.

Underhead fillet/washer mating, actual screw length/tip condition, washer registration, nut bearing, printed strength, torque, feet compression and tooling remain unqualified. In particular, the simplified nominal shank is not a supplier guarantee that an unmodeled underhead transition will seat in the washer. Hardware is **not selected** while copper repair and final integration remain open.
