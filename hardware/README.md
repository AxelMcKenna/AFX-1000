# Standalone RMX hardware

The hardware project combines the shared C++ audio engine with a processor module, stereo converters, analog stages, controls and an independent bypass path. The firmware targets **48 kHz / 128 frames**. Processor timing, physical fit, electrical performance and complete assembly still require measurement.

The E20 LED/display driver is routed and included in the A06 housing model.
Its [E21 load reconciliation](electronics/led_driver/generated/power-reconciliation.json)
uses revised power/current/ramp and parallel-switch allocations. Their conditional
screens pass; all-rail startup, gate timing, large-capacitor loop stability,
thermal limits, remaining boards, front-panel wiring and physical testing must
be finished before the unit is build-ready.

The [E23 DC input/protection PCB](electronics/input_protection/README.md) is routed
and incorporated into the A07 housing model, including dedicated mounts and
rear inlet/switch apertures. Electrical/thermal and physical assembly qualification
remain open; the main supply and rail-disconnect PCBs are still unfinished.

The [E24 main-supply candidate](electronics/power_supply/README.md) now has all
157 components placed, including corrected inductor candidates and checked land
dimensions. Its 333 open connections, thermal/EMI layout and housing integration
remain unfinished. The [current routing candidate](electronics/power_supply/routing/README.md)
routes both bucks, including bulk power, separate load sense and IC-ground
returns, soft-start and enables: 219 segments/53 vias, one filled ground region,
zero native DRC/parity issues and 273 open connections. Fifty-three path checks
and 36 tooling tests pass. Raw generators and linear/precision stages, actual
voltage drop, loop/thermal/EMI, housing and physical qualification remain open.

## Start here

| Area | Sources and current instructions |
| --- | --- |
| Firmware and pin assignments | [Firmware guide](firmware/README.md), [external converter profile](firmware/EXTERNAL-CONVERTER.md) |
| Electronics and board contracts | [Electronics index](electronics/README.md) |
| Enclosure, mechanisms and CAD generation | [CAD guide](cad/README.md), [button-fit fixture](cad/BUTTON-FIT.md) |
| Component investigations | [Research shortlist](../research/hardware/components.md) |
| Verification records and open gates | [Validation index](validation/README.md) |
| Archived review bundles | [Release artifact catalog](releases/README.md) |
| Earlier architectural discussion | [Design history](../docs/hardware/history/2026-10-23-system-design.md) |

## Folder ownership

- `firmware/`: embedded adapters, board configuration, pin maps and ARM build tooling.
- `electronics/<board>/`: editable KiCad designs, generators, independent contracts, BOMs and verification scripts. `electronics/common/` provides shared EDA utilities.
- `cad/`: editable OpenSCAD models and geometry generators. Small generated coordinate files and verification records remain beside their inputs.
- `validation/`: small verification records. Historical records retain the paths and hashes of their original source snapshot.
- `releases/`: manifests and recovery instructions for review bundles.

Large review archives and generated meshes/renders live under the ignored `build/artifacts/` directory. Selected documentation images live in `docs/assets/hardware/`. See the [artifact policy](../docs/artifacts.md).

## Build and check

Build the shared engine and host tests using the [repository instructions](../README.md#build). The firmware guide documents the pinned SDK, ARM toolchain and both profiles. Run board tools as Python modules from the repository root; each board guide lists its regeneration and native KiCad checks.

Keep current instructions in these guides, investigations in `research/`, and dated design narratives in `docs/hardware/history/`. Passing generated or host checks does not establish physical hardware performance.
