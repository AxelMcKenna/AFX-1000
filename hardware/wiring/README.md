# Standalone power interconnect plan

The [CSV](generated/power-interconnect.csv) and [JSON](generated/power-interconnect.json) map eleven source-side power/control pins between the main supply, E25 disconnect candidate and E23 input/auxiliary PCB. Every pin is checked against both its actual PCB land and exported netlist. The board datums must match A11 CAD. Source and protected net names remain distinct; no implicit 5 V aliases are accepted.

| Harness | Connection | Pins |
| --- | --- | --- |
| PWR-ANALOG | Main supply J2 → disconnect J1 | P19_SRC, AGND, N19_SRC, P12_SRC, N12_SRC, V5_REG_SRC |
| PWR-DIGITAL | Main supply J3 → disconnect J2 | 5V_DIG_SRC, AGND |
| PWR-AUX-RUN | Input/auxiliary J6 → disconnect J5 | V2V5_AUX, AGND, POWER_RUN |

Lengths are straight-line lower bounds between actual header lands. They are not wire cut lengths: bend radii, connector backshells, vent exclusion zones, service loops and protected-load/front-panel fanout remain unfinished. Production connector/keying/current ratings and wire gauges are unselected. Prototype header geometry does not establish production contact resistance.

The existing conditional E17/E21 protected-star model leaves about 2.170 mV on analog 5 V and 2.788 mV on digital 5 V before additional wiring. A trial conductor area of 0.823 mm² (approximately 18 AWG) and assumed 1.8e−8 Ωm resistivity give wire-only drops of about 2.181/11.898 mV using the shortest supply-plus-return paths. **Both trials fail the remaining loss budgets**, even before contacts, temperature or a real routed harness are added. These figures diagnose a distribution constraint; they do not qualify the underlying source model or the full power budget.

The digital path permits only about 1.55 mΩ of additional total resistance under that model. Revise the physical power distribution or regulation design before selecting/releasing a harness. The existing rail targets have not been relaxed. The generated report retains the failures and leaves every assembly-release flag false.

```sh
python3 -m hardware.wiring.power
python3 -m unittest discover -s tests/tooling -p 'test_power_interconnect.py' -v
```

The main supply remains routed and separately verified. E25 is placed only, and full startup, fault protection, electrical/audio/thermal behavior and physical assembly remain unqualified. Nothing here is an instruction to assemble or power an unverified unit.
