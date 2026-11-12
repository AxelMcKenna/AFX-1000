# AFX-1000 standalone hardware

Browse the [current designs](fabrication/active/README.md),
[retained experiments](fabrication/experiments/README.md), or
[complete workspace catalog](fabrication/workspace-catalog.json).

The current design uses **two main custom PCBs with a retained Daisy Seed 3 module**. It consolidates the earlier eight-board main assembly. Panel boards and bought-in modules remain additional.

**The design is not ready for fabrication.** The integrated KiCad projects contain partial routing; complete installed housing fit and manufacturing requirements remain unfinished. See the [current layouts](../README.md#current-pcb-layouts) and [latest working-candidate evidence](fabrication/staging/two-board-power-aux-local-distribution-native-03/final-review.json).

| Main PCB | Functions | Overall size | Current project |
| --- | --- | --- | --- |
| Signal main | Audio, converter interface, Daisy Seed 3 in a 40-pin socket, controls and LED drivers | 268 × 63 mm | [KiCad project](cad/two_board_sensor_05/signal_dac/native-r50/signal_main.kicad_pro) · [Review](cad/two_board_sensor_05/signal_dac/README.md) |
| Power/protection | Supply conversion, inlet and rail protection, monitoring, negative-rail startup and fan health | 320 × 181.1 mm, C-shaped | [KiCad project](fabrication/staging/two-board-power-aux-local-distribution-native-03/power_protection.kicad_pro) · [Review](fabrication/staging/two-board-power-aux-local-distribution-native-03/README.md) |

The current signal DAC-r50 candidate has **194 open connections** after 36 additional joins, with one verified resistor translation and an unplaced ESS codec. The latest power checkpoint, **TBP73**, has **1,936 opens** and 1,086 electrical components. Native power geometry/parity/ERC errors are zero, with two retained warnings. Two added tracks join N_U35:14 to N_U15:3 while preserving all original copper and 47 plane fills. The [current AUX inventory](fabrication/staging/two-board-aux-distribution-survey-07/inventory.json) records 78 capacitor grounds connected, but 72 of 81 IC supply pins still lack regulator connections. Current/startup/thermal limits and complete signal-board qualification remain unresolved.

Start with the [print-first kit](cad/two_board_print_02/TBH01-r6-print-first-kit.zip) and [print order](cad/two_board_print_02/README.md): test the four core coupons, then print the tray before the lid. The minimum case uses three one-piece parts or twelve split pieces.

The [TBH01 r6 print package](cad/two_board_print_01/README.md) supplies checked housing STLs for an **unpowered fit prototype**. It includes actual board supports, a removable lid and bolted split parts. The largest split part is 175 × 192.4 × 43.6 mm before brim. For the lever, use the [TBH03-r5 add-on](cad/two_board_print_03/TBH03-lever-retention-r5.zip) and [assembly instructions](cad/two_board_print_03/README.md): its removable bearing cap and replacement bracket supersede the original r6 lever bracket. All fourteen delivered meshes and nineteen clearance/retention checks pass independent review. Selector/display/LED/sensor carriers, lever spring and magnet retention, harness integration and operating cooling remain unfinished. Its TBP61 placement snapshot is preserved by the TBP62–67 copper changes. Both main boards use provisional eight-layer templates; the final manufacturing stack remains unaccepted.

Before fabrication, complete routing and current-return paths, obtain the approved ESS package/land/stencil inputs, verify critical power and control circuits, finalize inter-board interfaces and exact parts, and review the manufacturing outputs and installed fit. The [fabrication inventory](fabrication/README.md) records the detailed engineering history and remaining work. No hardware has been ordered or assembled.

## Firmware

The [F06 standalone firmware candidate](firmware/full_engine/README.md) builds the shared C++ audio engine for Daisy hardware with 152 parameters, bounded SDRAM storage and control-fault recovery. Host checks and ARM builds are recorded; processor timing, converter operation and complete hardware behavior remain unmeasured. The earlier [runtime snapshot](runtime/README.md) is retained separately.

## Earlier designs

The [earlier development handoff](DEVELOPMENT.md), [A11 housing study](cad/a11/README.md), [electronics source designs](electronics/README.md), [B1 budget prototype](budget/README.md) and [A0 enclosure reference](cad/a0-reference/README.md) document predecessor variants. Their layouts, fit checks and fabrication files apply to their own revisions. Use the two projects above for the current main-board design.

## Start here

| Area | Sources and current instructions |
| --- | --- |
| Current main boards and fabrication work | [Latest verified working candidate](fabrication/staging/two-board-power-aux-local-distribution-native-03/final-review.json), [fabrication inventory](fabrication/README.md) |
| Firmware and pin assignments | [Firmware guide](firmware/README.md), [external converter profile](firmware/EXTERNAL-CONVERTER.md) |
| Electronics and board contracts | [Electronics index](electronics/README.md) |
| Enclosure, mechanisms and CAD generation | [CAD guide](cad/README.md), [button-fit fixture](cad/BUTTON-FIT.md) |
| Component investigations | [Research shortlist](../research/hardware/components.md) |
| Verification records and open gates | [Validation index](validation/README.md) |
| Archived review bundles | [Release artifact catalog](releases/README.md) |
| Earlier architectural discussion | [Design history](../docs/hardware/history/2026-10-23-system-design.md) |

## Folder ownership

- `fabrication/`: current integrated board candidates, routing audits and fabrication preparation records.
- `firmware/`: embedded adapters, board configuration, pin maps and ARM build tooling.
- `electronics/<board>/`: editable KiCad designs, generators, independent contracts, BOMs and verification scripts. `electronics/common/` provides shared EDA utilities.
- `cad/`: editable OpenSCAD models and geometry generators. Small generated coordinate files and verification records remain beside their inputs.
- `validation/`: small verification records. Historical records retain the paths and hashes of their original source snapshot.
- `releases/`: manifests and recovery instructions for review bundles.

Large review archives and generated meshes/renders live under the ignored `build/artifacts/` directory. Selected documentation images live in `docs/assets/hardware/`. See the [artifact policy](../docs/artifacts.md).

## Build and check

Build the shared engine and host tests using the [repository instructions](../README.md#build). The firmware guide documents the pinned SDK, ARM toolchain and both profiles. Run board tools as Python modules from the repository root; each board guide lists its regeneration and native KiCad checks.

Keep current instructions in these guides, investigations in `research/`, and dated design narratives in `docs/hardware/history/`. Passing generated or host checks does not establish physical hardware performance.
