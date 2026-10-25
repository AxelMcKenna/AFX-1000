# A10 housing and controls with the enlarged standalone supply

Open `assembly.scad` in OpenSCAD. A10 retains the RMX-style 334 × 157 × 38 mm enclosure, 29 guided buttons, ten knobs, selectors, optics and release lever. It integrates the current 90 × 44 × 1.6 mm higher-headroom power PCB, extending the A09 board reserve by 6 mm to the right and front. It remains separate from the B1 budget design and the main working tree's A08 edits.

The power-board datum is (201,105,6.5) mm. Its four unchanged mount centres are (205,109), (275,109), (205,139) and (275,139), with Ø2.2 through bores for M2 hardware. The board ends at X=291 and Y=149. The extra space accommodates positive-rail compensation, bypass, divider and minimum-load components; the outside chassis and control layout do not grow. The current integration also includes C49/C54 compensation and C61 bypass relocation around U6, plus R34 rotation and R37/R42 isolation-resistor relocation beside the target amplifiers. Native meshes, sweeps and collisions have been rerun for these component positions.

`integration.py` reads all 157 component courtyards on both faces, the outline, holes and actual through-hole lead positions from the current PCB. Height, trimmed-lead, header/harness and fixing-head dimensions remain **conditional assembly allocations**, not selected-part guarantees. The smallest allocated floor clearance remains 0.35 mm. Actual fasteners, underside retention and feet remain to be selected.

Native checks cover all printed solids, the full button travel and release-lever sweep, fixed/optical/chassis collisions, 0.25 mm expansion of the power component/lead/head reserves and one millimetre of air below the retained thermal-copper areas. These are geometric checks. Copper loss, loop stability, thermal/EMI performance, component dimensions and physical print/assembly fit remain unverified. Other standalone boards and wiring still require integration.

## Rebuild

From the repository root with the [uv environment](../../../README.md#python-tooling), and OpenSCAD with Manifold and CGAL:

```sh
uv run --locked python hardware/cad/a10/build.py --openscad /path/to/openscad
uv run --locked python -m unittest discover -s tests -p a10_integration_tests.py -v
uv run --locked python -m hardware.cad.a10.verify
```

`--geometry-only` performs native mesh/collision checks and creates the 3MF without graphics previews. `--preview-only` creates review images without qualifying new solids. Outputs are under `build/artifacts/cad/a10/`. Use `parts.csv` and [PRINTING.md](PRINTING.md) for quantities and prototype assembly; the 3MF is an inventory, not a machine profile. This model does not overwrite A08 or A09. A09 keeps its frozen 84 × 38 mm source snapshot.

The [electrical routing record](../../electronics/power_supply/routing/README.md) describes current power-board scope. Its PCB remains explicitly incomplete. A10 is a prototype mechanical inventory, not a complete-unit fabrication or assembly release.

The latest main supply has zero native DRC/parity/open items and 322 independent path checks. This continuation changes copper only. All component poses, lead/thermal reserves, mounts and printed geometry were compared exactly with the last native CAD build before refreshing integration hashes. The print pack includes the UNQUALIFIED power PCB; complete-unit electrical and physical qualification remain open.
