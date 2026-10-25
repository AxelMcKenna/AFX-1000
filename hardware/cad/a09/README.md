# A09 housing with the actual standalone power PCB

Open `assembly.scad` in OpenSCAD. A09 retains A08's RMX-style panel, 29 guided buttons, ten shaft-mount knobs, selectors, optics and release lever. It integrates the actual 84 × 38 × 1.6 mm in-progress higher-headroom supply PCB instead of the old 78 mm generic reserve. This variant remains separate from the B1 budget design.

The supply board moves from X=207 to X=201 mm, at Y=105 and Z=6.5 mm. Its four mount centres are (205,109), (275,109), (205,139) and (275,139). The right edge remains X=285. At the original position, the allocated test-header top was only 0.09 mm below the Scene Resonance pot body. The new position clears that control without reducing its component reserve. The four power mounts now have Ø2.2 through bores for M2 fixings; actual fastener length, bottom retention and feet remain to be selected.

`integration.py` reads both-side courtyards, through-hole lead positions, four mounting holes and the board outline directly from the current KiCad PCB. All 157 components appear individually. The old generic power-component block is removed. Header/harness, trimmed lead/solder, fixing-head and underside thermal-air allowances are explicit. All body heights are **maximum assembly allocations requiring part selection or measurement**, not catalogue guarantees. The smallest allocated floor clearance is 0.35 mm beneath a bottom 1210 capacitor.

Native checks retain the full button stroke and 0–35° lever sweep. Additional checks expand all power component/lead/head reserves by 0.25 mm against the housing, controls, other boards and electronics reserves, and check one millimetre of unobstructed air under the existing thermal-copper regions. These establish geometric clearance for these allocations only; they do not establish cooling, electrical readiness or physical fit.

A09 is isolated under `build/workspaces/high-headroom-standalone`; the active main working tree's A08 files are untouched. `source.json` records the inherited A08 source hashes. `reference-components.scad` freezes the other A08 electronics reserves. Future PCB placement or height changes require regeneration and renewed native checks.

## Rebuild

From the isolated repository root, use the Python dependencies in `requirements.txt` and a native OpenSCAD build with Manifold and CGAL:

```sh
python3 hardware/cad/a09/build.py --openscad /path/to/openscad
python3 -m unittest discover -s tests -p a09_integration_tests.py -v
python3 -m hardware.cad.a09.verify
```

Outputs go to `build/artifacts/cad/a09/`. The 3MF is a quantity-correct inventory, not a printer profile. Use `parts.csv` and [PRINTING.md](PRINTING.md) for the prototype mechanical inventory. No print-pack path from A07 or A08 is overwritten. The supplied PCB is an in-progress placement/routing source, not a fabrication file.

Additional standalone circuit boards still need routing and housing integration; the frozen A08 reserves do not represent all higher-headroom circuits. Physical printing, selected-part dimensions, wiring and cable bends, board fastening/feet, control feel, optics, thermal/EMI tests and completion of the electrical system remain open. No complete-unit build readiness is claimed.

A09 now retains its checked 84 × 38 mm supply snapshot in `reference-power.kicad_pcb` and `reference-power-components.json`. The active larger-board integration is [A10](../a10/README.md); rebuilding A09 uses these frozen inputs. The original review archives are unchanged.
