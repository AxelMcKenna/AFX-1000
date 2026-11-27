# Signal-board output routing candidate

Open signal_main.kicad_pro in KiCad 10. This candidate adds four 0.20 mm front-copper segments totaling 38.81 mm on /A_OUTPUT/S_AC_L. It closes one left-channel output connection relative to native-routes-02. The cumulative routing and reference audit covers the original nineteen joins and this addition.

Native KiCad reports 142 opens, zero geometry findings and zero ERC findings. The schematic parity check identifies the outstanding A_U201 ES9292QPRO footprint. The connected reference-plane check passes for the added copper, and all saved zone fills and prior physical connectivity are preserved. See [routing acceptance](../routes-03-review.json) and [native DRC](drc.json).

The board is a development candidate. Analog performance and the codec footprint remain unqualified.

## Clearance between A_D101 and A_C105

On the saved board, the SOT-23 diode A_D101 is centered at (75.8, 65.2) mm and the 0805 capacitor A_C105 at (78.5, 66.5) mm. Both footprints have a native rotation of 90°. The nominal B.Fab outlines put the diode body length and capacitor width along board X. The assembly model leaves 0.02 mm between its conservative envelopes for this pair. [Assembly-model dimensions](../../assembly_workflow/pcb_updates/r125/nearest-envelopes.json)

Using the Nexperia SOT23 package drawing and the KEMET part-specific sheet linked from the schematic, the maximum diode body length is 3.00 mm and maximum capacitor width is 1.45 mm. At the nominal centers and angles the minimum X separation between these maximum-size rectangular bodies is 2.70 − 3.00/2 − 1.45/2 = **0.475 mm**. The separate nominal B.Fab result is 0.625 mm. [SOT23 drawing, page 2](https://www.nxp.com/docs/en/package-information/SOT23.pdf) · [KEMET C0805C220J5GACTU dimensions, page 1](https://search.kemet.com/component-documentation/download/specsheet/C0805C220J5GACTU)

Rotation and translation consume this clearance. As a sensitivity example, ±1° body rotation about each nominal center gives a conservative 0.444 mm X gap using the maximum orthogonal dimensions of 1.40 mm for the diode body and 2.20 mm for the capacitor. Subtract both components’ inward X placement errors from that result. The calculation assumes centered package bodies and covers body overlap only. Assembly acceptance still requires the assembler’s placement and post-reflow tolerances, terminal and solder clearance, and required process margin.
