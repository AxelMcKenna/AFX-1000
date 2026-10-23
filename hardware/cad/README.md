# Enclosure and control CAD

Editable OpenSCAD models describe the housing, lever mechanism, control layout and component reserves. Models read the placement records referenced by their geometry generators. Physical fit, complete electronics placement, wiring and assembly remain open; see the [validation record](../validation/README.md).

![Standalone assembly preview](../../docs/assets/hardware/assembly.png)

## Files

| Location | Purpose |
| --- | --- |
| `enclosure.scad`, `mechanisms.scad` | Editable housing, panel and mechanism geometry |
| `generate.py`, `standalone.py` | Control coordinates and component/board reserves |
| `render.py` | Mesh, motion and placement checks and render exports |
| `button_fixture.scad`, `button_fixture.py`, `button_render.py` | [Button-fit fixture](BUTTON-FIT.md) |
| `generated/` | Small generated coordinates, review drawings and verification records |
| `../../build/artifacts/cad/` | Ignored STL, DXF and PNG exports |
| `../../docs/assets/hardware/` | Reviewed documentation previews |

The [dated CAD notes](../../docs/hardware/history/2026-10-23-cad-design.md) retain earlier dimensions and placement discussions. See the [component research](../../research/hardware/components.md), [release catalog](../releases/README.md), and [artifact policy](../../docs/artifacts.md).

## Regeneration

Run from the repository root after generating and verifying the board placement records required by the model:

```sh
python3 -m venv build-cad-tools
build-cad-tools/bin/python -m pip install -r hardware/cad/requirements.txt
python3 -m hardware.cad.generate
python3 -m hardware.cad.standalone
build-cad-tools/bin/python -m hardware.cad.render --openscad /path/to/openscad
```

Meshes and previews are written to `build/artifacts/cad/`; small verification records remain in `hardware/cad/generated/`. Add `--update-previews` to copy selected PNGs into tracked documentation after successful checks. The button renderer supports the same option. Review previews represent their last checked snapshot; exported geometry does not establish physical fit.
