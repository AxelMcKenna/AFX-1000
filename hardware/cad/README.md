# Enclosure and control CAD

Editable OpenSCAD models describe the standalone housing, lever mechanism, control layout and component reserves. A07 reads the output, input-hub, processor-carrier, LED-driver and E23 power-input placement records. Its 690 modeled reserves pass box checks; seven printable solids and the lever/board collision checks pass native rendering, including the input board against the rear plate. Physical parts, complete electronics placement, wiring and assembly remain open; see the [validation record](../validation/README.md).

![Standalone assembly preview](../../docs/assets/hardware/assembly.png)

## Files

| Location | Purpose |
| --- | --- |
| `enclosure.scad` | Housing, panel, rear plate, mounts and assembly views |
| `mechanisms.scad` | Lever, touch backer and fit coupon |
| `generate.py` | Control coordinates, apertures and parameter schedule |
| `standalone.py` | Board/component reserves, fixing bounds and rear I/O |
| `input_power.py` | Actual E23 profile/footprints, inlet/switch bounds and rear-panel alignment |
| `render.py` | Mechanical exports, mesh/motion checks and preview generation |
| `button_fixture.scad`, `button_fixture.py`, `button_render.py` | [Button-fit fixture](BUTTON-FIT.md) |
| `generated/*.scad`, `*.svg`, `controls.csv` | Small generated coordinates and review drawings |
| `generated/*validation.json`, `internal-clearance.json` | Verification records |
| `../../build/artifacts/cad/` | Ignored STL, DXF and PNG exports |
| `../../docs/assets/hardware/` | Selected, tracked documentation previews |

The [dated CAD design notes](../../docs/hardware/history/2026-10-23-cad-design.md) retain dimensions, allowances and the earlier placement discussion. Component investigations live in [research](../../research/hardware/components.md). Review ZIPs are listed in the [release catalog](../releases/README.md).

## Regeneration

Run from the repository root with Python 3.11+, KiCad and OpenSCAD installed:

```sh
python3 -m venv build-cad-tools
build-cad-tools/bin/python -m pip install -r hardware/cad/requirements.txt
python3 -m hardware.cad.generate
python3 -m hardware.electronics.output_stage.generate
python3 -m hardware.electronics.output_stage.place --kicad-cli /path/to/kicad-cli
python3 -m hardware.electronics.output_stage.route
python3 -m hardware.electronics.output_stage.check_placement --kicad-cli /path/to/kicad-cli
python3 -m hardware.electronics.control_inputs.generate
build-cad-tools/bin/python -m hardware.electronics.control_inputs.board --kicad-cli /path/to/kicad-cli
python3 -m hardware.electronics.processor_carrier.generate
build-cad-tools/bin/python -m hardware.electronics.processor_carrier.board --kicad-cli /path/to/kicad-cli
python3 -m hardware.electronics.processor_carrier.verify --kicad-cli /path/to/kicad-cli
python3 -m hardware.electronics.control_inputs.verify --kicad-cli /path/to/kicad-cli
python3 -m hardware.electronics.led_driver.generate
python3 -m hardware.electronics.led_driver.place --kicad-cli /path/to/kicad-cli
python3 -m hardware.electronics.led_driver.route
python3 -m hardware.electronics.led_driver.cleanup --kicad-cli /path/to/kicad-cli
python3 -m hardware.electronics.input_protection.generate
python3 -m hardware.electronics.input_protection.place --kicad-cli /path/to/kicad-cli
python3 -m hardware.electronics.input_protection.route
python3 -m hardware.electronics.input_protection.cleanup --kicad-cli /path/to/kicad-cli
python3 -m hardware.electronics.input_protection.check_board --kicad-cli /path/to/kicad-cli
python3 -m hardware.electronics.power_supply.verify --kicad-cli /path/to/kicad-cli
python3 -m hardware.electronics.input_protection.verify --kicad-cli /path/to/kicad-cli
python3 -m hardware.electronics.rail_disconnect.verify --kicad-cli /path/to/kicad-cli
python3 -m hardware.electronics.led_driver.verify --kicad-cli /path/to/kicad-cli
python3 -m hardware.cad.standalone
build-cad-tools/bin/python -m hardware.cad.render --openscad /path/to/openscad
```

Refresh `power_supply`, `input_protection` and `rail_disconnect` verification in
that order before E20 verification when their source fingerprints differ. The
[E20 guide](../electronics/led_driver/README.md) records its unclosed power
allocation and unfinished front-panel emitters/harnesses. The housing includes
four E20 M2 insert bosses and conditional component/tail/harness envelopes;
those bounds do not qualify selected parts or physical assembly.

A07 adds four input-board M2 insert bosses, profile reliefs around the rear web
and output-stage parts, a rectangular jack-body aperture and a lower power-switch
slot. The nominal jack face reaches the rear plate outer plane. The native input
collision check includes the rear plate and the complete allocated actuator sweep.
Plug mating, switch access/feel, exact part tolerances, insert/screw selection and
physical fit remain unqualified. Main rail-generation/disconnect PCBs and complete
analog/control placement still do not fit by inference from the generic power reserve.

Meshes and previews are written to `build/artifacts/cad/`; small verification records remain in `hardware/cad/generated/`. Add `--update-previews` to copy the selected PNGs into the tracked documentation after a successful render. The button renderer supports the same option. Documentation previews represent their last reviewed snapshot.

The rendering checks require the OpenSCAD backends used by the model. Their recorded scope and version are in the generated validation JSON. Mesh closure, clearances and source-level checks remain separate from a physical print or full-unit fit test.
