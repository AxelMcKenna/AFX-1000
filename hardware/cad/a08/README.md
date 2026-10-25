# A08 housing and complete printable controls

Open `assembly.scad` in OpenSCAD. A08 is the next revision of the A07 housing study in the overview. It is a separate mechanical prototype from the B1 budget hardware and A0 reference enclosure.

The model includes the 334 × 157 × 38 mm chassis, removable front/rear panels, all 29 guided button caps (including the ten Scene FX sectors), ten shaft-mount knobs, both selector caps, the shared guide plate, individual switch holders, clips, release mechanism, touch backer and all modeled optical inserts. The same geometry drives the assembly, individual STL exports and quantity-correct 3MF print inventory. Springs, switches and electronics are references or purchased parts, not printed solids.

![A08 mechanical overview](../../../docs/assets/hardware/cad-overview.png)

The housing is 2 mm taller than A07 to retain the original Z=27.2 mm switch seating while accommodating the B01-derived stems, clips and guides. Holder mounting patterns avoid the processor USB plug reserve and bank indicator apertures. Four rear fixings have captive M3 nut pockets; the right fixings moved to X=318 to clear the input board. The lever stem/grip is extended by 2 mm. The unrouted BPM reference board is narrowed to 26 mm while retaining the digit locations. `source.json` identifies the preserved A07 snapshot and every reference change; no routed PCB is changed by these models.

The native build checks every STL for a single connected, closed, consistently wound, positive-volume mesh. It checks all 29 key and holder instances for separation, sweeps the full 1.2 mm key travel and 0–35° lever movement, and checks the fixed parts against retained electronics reserves. These checks are geometric evidence. Physical print fit, spring/contact force, friction, fastener retention, optics, wiring and live electronics remain untested. The frozen board/component reserves describe their A07 snapshot, not a qualification of a complete electronics build.

## Files

| File | Purpose |
| --- | --- |
| `assembly.scad` | Assembly, printable part selectors, exploded view and clearance checks |
| `controls.scad` | Caps, guides, holders, knobs, selectors and optical inserts |
| `housing.scad`, `mechanisms.scad` | Chassis, panels and release mechanism |
| `generated/controls.csv` | Control positions and labels inherited from the A07 layout |
| `generate.py` | Shared cap/holder schedule and fastener locations |
| `generated/*.scad` | Layout, frozen electronics reserves and nominal button-stack dimensions |
| `build.py`, `review.py` | Native exports, mesh/motion checks, 3MF, ZIP and image composition |
| [PRINTING.md](PRINTING.md) | Printer handoff, quantities, assembly sequence and purchased hardware |

## Rebuild

Use the root [uv environment](../../../README.md#python-tooling), plus an OpenSCAD build with the Manifold and CGAL backends. The original renders used OpenSCAD 2026.10.15. Run from the repository root:

```sh
uv run --locked python hardware/cad/a08/build.py --openscad /path/to/openscad --update-previews
```

Outputs are ignored under `build/artifacts/cad/a08/`: all STL files, `parts.csv`, `validation.json`, the 3MF inventory, native review images and `RMX-A08-print-pack.zip`. `--update-previews` updates the selected README image only after a successful complete build. `--reuse-exports` reuses existing STL meshes only if their recorded geometry fingerprint matches the current sources; clearance checks still run. `--preview-only` is a visual review mode and does not qualify a print pack.

The previously supplied `build/artifacts/cad/RMX-A07-prototype-print-pack.zip` is refreshed as a compatibility download with the new A08 ZIP contents after a successful build. The inner folder, manifest and README identify A08.

Dimensions used for the interfaces are recorded from the [Omron B3F drawing](https://omronfs.omron.com/en_US/ecb/products/pdf/en-b3f.pdf), [Bourns PTV09 shaft drawing](https://www.bourns.com/docs/product-datasheets/PTV09.pdf) and [C&K JS selector drawing](https://www.ckswitches.com/media/1422/js.pdf). Printed clearances, carriers, spring design and cap geometry are project design choices requiring fit measurements.
