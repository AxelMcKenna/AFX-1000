# Standalone RMX hardware

The isolated [A10 housing study](cad/a10/README.md) integrates the enlarged 90 × 44 mm supply PCB with the RMX-style controls inside the unchanged 334 × 157 × 38 mm chassis. Native solids, full button/lever sweeps and the 0.25 mm power-reserve clearance check pass. Part heights and physical fit remain unverified. A09 retains its frozen 84 × 38 mm source; the main working tree's B1/A08 files are untouched.


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
remain open; full-unit supply qualification and the rail-disconnect PCB are unfinished.

The [E24 main-supply candidate](electronics/power_supply/README.md) now has all
157 components placed, including corrected inductor candidates and checked land
dimensions. Its 333 opens describe the frozen placement snapshot. The [current routing candidate](electronics/power_supply/routing/README.md) covers both bucks, both raw generators, all three positive linear rails, the negative reference and DC target paths: 2,600 segments/285 vias, seven fills, zero native DRC/parity issues and zero open connections. All 322 measured paths and 135 tooling tests pass. Actual loss/stability/thermal/EMI and physical testing remain open. A10 provides conditional housing integration.

The [E25 disconnect placement](electronics/rail_disconnect/placement/README.md) and [A11 housing](cad/a11/README.md) add all 164 interlock parts, four floor mounts and capacitor vent clearance. Native nonrouting DRC/parity and all eight A11 collision checks pass; 365 E25 connections remain unrouted. The [source-harness plan](wiring/README.md) verifies eleven pin/net pairs and retains failed trial 5 V wiring-loss screens. Current tooling and CAD integration totals are 150 and 23 tests; the unit remains unqualified.

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
