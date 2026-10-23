# Standalone RMX hardware

The hardware project combines the shared C++ audio engine with a processor module, stereo converters, analog stages, controls and an independent bypass path. The firmware targets **48 kHz / 128 frames**. Processor timing, physical fit, electrical performance and complete assembly still require measurement.

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
