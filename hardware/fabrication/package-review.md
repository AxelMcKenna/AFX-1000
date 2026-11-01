# TI package corrections

This review corrects package assumptions before fabrication. Native ERC/DRC
does not establish that an assigned generic footprint matches the purchased
device. The drawing dimensions and source-document hashes are recorded in
[package-contract.json](package-contract.json).

## TPS3431SDRBR, DRB0008A

The previous generic VSON land uses a 1.65 × 2.4 mm exposed pad and terminal
lands different from the selected device's example. The revised own land uses
TI's 1.5 × 1.75 mm central exposed copper, 0.6 × 0.31 mm terminal lands at
0.65 mm pitch, and 2.8 mm between terminal-row centres.
[TI drawing 4218875/A](https://www.ti.com/lit/ds/symlink/tps3431.pdf)
was inspected visually on PDF pages 28–30, including the stencil drawing.

The library uses the central 1.34 × 1.55 mm paste aperture. It deliberately
omits the example's copper/paste fingers and its optional thermal vias. It does
**not** claim to reproduce the complete TI example. Stencil, mask, thermal
and assembly acceptance remain open. Existing board drills are retained;
a conservative rectangle screen found no drill intersection with the new
central paste aperture on NF U3/U9 or fan-protection U4. This does not qualify
all paste apertures or the complete assembly process.

Those three watchdogs have corrected routed-board candidates. Independent
saved-file audits confirm unchanged circuit values, pin nets, component
positions, existing tracks/vias and authored zones. Native findings remain
177 opens/two ERC warnings for NF, and zero findings/opens for fan protection.

## SN74LVC1G74DCTR, DCT0008A

The E11 bypass's original generic SOT-23-8 land has different terminal-row
spacing from DCT. The new own land uses 1.1 × 0.4 mm terminal pads, 0.65 mm
pitch and 3.8 mm between row centres, following
[TI drawing 4220784/D](https://www.ti.com/lit/ds/symlink/sn74lvc1g74.pdf),
visually reviewed on PDF pages 19–20. Its courtyard includes the drawing's
maximum body, permitted flash and 0.25 mm assembly allowance. These lands
are used by the new E11 candidate; its circuit values and numbered pin nets
remain unchanged. Parts and stencil/assembly acceptance remain open.

## Current evidence

- [NF package-only audit](staging/nf-watchdog-land-native-01/package-correction-review.json)
- [Fan-protection package-only audit](staging/fan-watchdog-land-native-01/package-correction-review.json)
- [E11 circuit/layout handoff](staging/bypass-closed-native-03/handoff.json)
- [E11 native top view](staging/bypass-closed-native-03/plots/top/top.svg)

All original source projects remain preserved. These corrections and native
checks are development evidence, not a physical qualification or fabrication
release.
