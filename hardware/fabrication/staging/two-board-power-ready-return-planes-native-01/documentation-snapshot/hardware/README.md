# AFX-1000 standalone hardware

Browse the [current designs](fabrication/active/README.md),
[retained experiments](fabrication/experiments/README.md), or
[complete workspace catalog](fabrication/workspace-catalog.json).

The current design uses **two main custom PCBs with a retained Daisy Seed 3 module**. It consolidates the earlier eight-board main assembly. Panel boards and bought-in modules remain additional.

**The design is not ready for fabrication.** The integrated KiCad projects contain partial routing; complete installed housing fit and manufacturing requirements remain unfinished. See the [current layouts](../README.md#current-pcb-layouts) and [recorded fabrication status](fabrication/staging/two-board-fabrication-status-50/status.json).

| Main PCB | Functions | Overall size | Current project |
| --- | --- | --- | --- |
| Signal main | Audio, converter interface, Daisy Seed 3 in a 40-pin socket, controls and LED drivers | 268 × 63 mm | [KiCad project](fabrication/staging/two-board-signal-routed-native-03/signal_main.kicad_pro) · [Review](fabrication/staging/two-board-signal-routed-native-03/README.md) |
| Power/protection | Supply conversion, inlet and rail protection, monitoring, negative-rail startup and fan health | 320 × 181.1 mm, C-shaped | [KiCad project](fabrication/staging/two-board-power-startup-remaining-native-03/power_protection.kicad_pro) · [Review](fabrication/staging/two-board-power-startup-remaining-native-03/README.md) |

The signal board has **251 open connections** and an unplaced ESS codec. The power board has **2,172 open connections** and 1,086 electrical components. The latest pass closes **27 connections**, completing local bypass and both ground returns for all eleven U18–U28 startup ICs. Five capacitors move; one main In6 ground outline extends, four main-ground zones refill and the other 43 fills remain unchanged. All **1,555 retained reference checks**, 18 new paths and nine previous startup repairs pass. All eleven supply-plane fields and seven quiet-ground networks are preserved. Native geometry/ERC errors are zero; signal retains its missing-codec parity finding and power retains two isolated-reference warnings. The [startup connectivity survey](fabrication/staging/two-board-startup-connectivity-survey-06/README.md) records **58 missing joins across 32 nets**. The [cell survey](fabrication/staging/two-board-startup-cell-survey-04/README.md) confirms that **none of these eleven startup ICs reaches the auxiliary source yet**. The [AUX inventory](fabrication/staging/two-board-aux-distribution-survey-02/README.md) records 73 of 81 IC supply pins still unconnected to the regulator, with current/startup/thermal limits unresolved. Startup, protected outputs, distribution and electrical qualification remain unfinished.

The [A12 housing work](cad/a12/README.md) includes the larger enclosure proposal. Supports, cooling, connector mates, cable bends, tolerances and revised return-bar/harness arrangements still need complete assembly review. Both main boards use provisional eight-layer templates; the final manufacturing stack remains unaccepted.

Before fabrication, complete routing and current-return paths, obtain the approved ESS package/land/stencil inputs, verify critical power and control circuits, finalize inter-board interfaces and exact parts, and review the manufacturing outputs and installed fit. The [fabrication inventory](fabrication/README.md) records the detailed engineering history and remaining work. No hardware has been ordered or assembled.

## Firmware

The [F06 standalone firmware candidate](firmware/full_engine/README.md) builds the shared C++ audio engine for Daisy hardware with 152 parameters, bounded SDRAM storage and control-fault recovery. Host checks and ARM builds are recorded; processor timing, converter operation and complete hardware behavior remain unmeasured. The earlier [runtime snapshot](runtime/README.md) is retained separately.

## Earlier designs

The [earlier development handoff](DEVELOPMENT.md), [A11 housing study](cad/a11/README.md), [electronics source designs](electronics/README.md), [B1 budget prototype](budget/README.md) and [A0 enclosure reference](cad/a0-reference/README.md) document predecessor variants. Their layouts, fit checks and fabrication files apply to their own revisions. Use the two projects above for the current main-board design.

## Start here

| Area | Sources and current instructions |
| --- | --- |
| Current main boards and fabrication work | [Latest status](fabrication/staging/two-board-fabrication-status-50/status.json), [fabrication inventory](fabrication/README.md) |
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
