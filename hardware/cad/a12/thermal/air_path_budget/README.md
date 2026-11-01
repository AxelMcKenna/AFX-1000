# AP01 — internal air and pressure requirements

The enlarged base alone does not establish control or internal-air temperatures. AP01 derives necessary air volume from the captured 89-row, **35.43155 W provisional source-power ledger**, then checks the pressure remaining for an actual air path. It introduces no enclosure cuts, fan substitution or cooling acceptance.

At **40°C inlet, 101325 Pa and 1.2× heat**, the necessary bulk-air volumes are:

| Interior-air ceiling | All heat through interior | Hypothetical 5.85885 W to base, remainder through interior, including base branch |
|---|---:|---:|
| 48°C | 16.974 m³/h | 15.290 m³/h |
| 50°C | 13.579 m³/h | 12.456 m³/h |
| 58°C | 7.544 m³/h | 7.419 m³/h |
| 60°C | 6.789 m³/h | 6.789 m³/h |

The existing PTV09 control has a 50°C operating limit. A 48°C bulk-air target leaves only a hypothetical 2°C local rise. The 58°C scenario instead accompanies a proposed 70°C-rated control and 60°C project body target; that control change and its local temperature still need qualification. Neither air target proves component temperature.

The four-land heat case is deliberately hypothetical. Its five source rows include converter inductor/diode losses, so the entire 5.85885 W cannot simply be credited to IC thermal pads. The base-branch air outlet target is 60°C against a proposed 65°C base goal. That is an energy requirement, not proof of convection or a package/PCB/TIM heat path. The source ledger also predates NF02's new negative-startup controls and is not a final hot whole-unit heat bound.

The **0.132 A fan allocation partitions the existing 0.416 A digital reserve**. At the ledger voltage it represents 0.66829 W, leaving 1.43783 W unassigned; no second fan heat load is added. All fan motor heat is retained in the interior energy requirement. No exterior motor-heat export is credited. New control and tach power must use the remaining reserve or cause an explicit source-inventory revision.

## Concrete air-path target and failed baseline

An initial design target is **9.2 m³/h total: 8.0 through the interior and 1.2 through the base path**, with at least **2200 mm² net inlet and 2200 mm² net exhaust** for the interior. The flow split covers both heat-allocation cases at 58°C/101325 Pa; it does not cover the 80000 Pa sensitivity. It is a sizing target, not achieved flow.

The actual existing guard has **37 nonoverlapping 48-sided holes**, net opening **511.151 mm² per fan**. Mounting holes outside the fan opening are excluded. With two Noctua 5V fans, the catalogue curve scaled to 90% in flow and pressure and corrected for ideal density gives 5.347 Pa at the target flow. Under discharge-coefficient sensitivities 0.6, 0.75 and 0.9, the existing guards plus the two 2200 mm² interior ports consume more pressure than that, before channels, baffles or pin losses. This baseline does not support the target under any of those sensitivities.

A proposed 800 mm² guard reduces restriction but still leaves an uncertain, small pressure budget. A more open protective guard, higher-pressure fan or revised air network needs evaluation. A large open under-base outlet would bypass the interior; the next CAD design must provide a controlled flow split and prevent recirculation. Selecting a larger free-air CFM number alone does not establish installed cooling.

The fan curve is transcribed from page 6 of the [manufacturer's 5V specification](https://cdn.noctua.at/media/e4b04217/Noctua%20NF-A4x10%205V%20Specification.pdf?download=true), SHA-256 `989f5ccc244424262921a60d8cf2dbe62972d4913196d8bacf4d20834aacbc6c`, visually inspected. The 90% pointwise scaling and ideal density correction are engineering sensitivities; the document does not guarantee a full installed lower curve. Discharge coefficients are also sensitivities, not measured bounds. No actual heat-transfer coefficient is inferred from CFM.

## Reproduce

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python -m hardware.cad.a12.thermal.air_path_budget.analyze
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python -m unittest hardware.cad.a12.thermal.air_path_budget.test_budget -v
```

Twelve checks cover independent enthalpy recovery, altitude sensitivity, heat conservation, reserve allocation, old-control failure, both heat splits, actual guard geometry, flow/area pressure scaling, unsupported curve extrapolation and invalid inputs. They do not qualify hardware. Every installed-cooling, component-temperature and fabrication flag remains false.
