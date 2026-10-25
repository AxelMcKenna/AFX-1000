# E12 ADC-driver characterization PCB

This is a separate 110 × 78 × 1.6 mm, six-layer characterization candidate for the unchanged 79-part E12 circuit. Native KiCad 10.0.7 checks report **0 DRC violations, 0 schematic-parity issues and 0 open connections** with 1,060 segments and 120 conventional 0.6/0.3 mm through vias. Four M2 clearance holes have all-layer copper/via keepouts. It is **not integrated into A11 or demonstrated to fit the enclosure**.

In1.Cu and In4.Cu carry only AGND. Native-refilled evidence contains one connected filled polygon per reference plane. Independent checks follow actual ground copper from all 45 AGND lands to contacts inside both fills; the largest nearest-contact distance is under 2.5 mm. These are construction checks. They do not qualify ground impedance, charge-pump coupling, return-current distribution or audio noise.

Twenty-four local FDA/output/buffer-feedback paths are checked on actual F.Cu. Four output force/sense stars are checked across actual copper layers: removing each J2 plated terminal must separate its force path from its FDA and common-mode feedback paths. **The taps are at J2, not the ES9292 pins.** Each subsequent harness conductor is shared. Final hardware requires ADC-driver/codec co-location and board consolidation, or a revised force/sense interface. This independent characterization board does not close the complete converter loop.

The assigned VSSOP8 library lands have 0.65 mm pitch and 0.50 mm width, leaving 0.15 mm between adjacent pads. The declared minimum applies only to pad pairs within U1/U2/U5/U6; other copper clearance remains 0.25 mm. This is an unqualified fabrication prerequisite. Footprint inputs are hashed and native library/parity checks run in isolation. No component land pattern is replaced to hide the spacing requirement.

Analog stability across actual converter loading/harnesses, reference settling, pump ripple, parasitic capacitance around the 1 pF feedback capacitors, 100 MΩ servo leakage/cleanliness/guarding, thermal behavior and production stackup remain unverified. No physical board or bench result is asserted. Build readiness remains false.

`generated/filled.kicad_pcb` is the exact native-refilled evidence board. The editable board retains its zone definitions and checked copper; `reviewed-copper.json` reproduces that copper without running the exploratory router. The route search requires NumPy; all essential source, copper, ground and regression checks run with standard Python.

```sh
python3 -m hardware.electronics.adc_driver.pcb.generate --kicad-cli /path/to/kicad-cli --reviewed
python3 -m hardware.electronics.adc_driver.pcb.check --kicad-cli /path/to/kicad-cli
python3 -m unittest discover -s tests/tooling -p test_adc_driver_pcb.py -v
```

`--route` is the reproducible exploratory search alternative. Every regeneration requires a fresh native check. The saved native report records exact source/evidence hashes and the independent construction checks; it does not certify analog performance or fabrication.
