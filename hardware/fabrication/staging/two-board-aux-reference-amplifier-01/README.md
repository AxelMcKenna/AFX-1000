# TBP50 reference and amplifier output loads

The current reference output must supply **0.187437–0.204079 mA** in the
conditional zero-leakage resistor model. Four amplifier channels supply
**0.478036 mA nominally**, or a sum of individual maxima of **0.492821 mA**
with independent ±3% resistor factors at nominal negative-rail voltages.
These are output currents, not complete AUX supply-current bounds.

The [analysis](analysis.json) uses TBP50's actual netlist.
[Independent verification](verification.json) checks 632 reference cases,
80 amplifier cases, four nominal amplifier cases and 12 pin-current transfer
coefficients using series-path formulas, Ohm's law, KCL and power conservation.
The largest closed-form current difference is 6.39e-18 A.

## Reference ownership

E_U7 is REF35125QDBVR. VIN and EN are both tied to AUX; its output is
PWR_PROTECT_REF. There are 14 direct resistor branches: six startup reference
dividers, E_R94's bleed, and seven comparator feedback branches. Their complete
paths contain 39 resistors. Twenty-one already appear in the
[direct AUX network analysis](../two-board-aux-resistor-networks-01/README.md):
the seven pullup/feedback paths have both AUX and reference source ports.
Their AUX currents must not be added again when accounting for reference
output current. The remaining 18 resistors are newly covered here.

Each released feedback path injects some AUX current into the reference;
each asserted path draws from it. The reference remains a net source throughout
the model, even after those injections. The result assumes fixed reference
voltage at 1.2375–1.2625 V, AUX at 2.3–2.7 V, zero pin current and ideal
open-collector sinks. It excludes E_J6/N_J1 external loads, comparator input
currents, E_C26 charging and actual reference voltage errors.

## Amplifier ownership

E_U8 and N_U13 are both OPA2333AID, powered by AUX with grounded negative
supplies and noninverting inputs. Their four feedback channels contain 17
resistors, disjoint from the direct AUX and reference resistor inventories.

| Channel | Monitored rail | Input resistance | Nominal output | Nominal output current |
| --- | --- | --- | --- | --- |
| E_U8.1 | N19 source at −19 V | E_R49 + E_R50 = 156.2 kΩ | 1.216389 V | 121.639 µA |
| E_U8.7 | N12 source at −12 V | E_R53 = 100 kΩ | 1.200000 V | 120.000 µA |
| N_U13.1 | Protected N19 at −19 V | N_R23 = 160 kΩ | 1.187500 V | 118.750 µA |
| N_U13.7 | Protected N12 at −12 V | N_R40 = 102 kΩ | 1.176471 V | 117.647 µA |

All four feedback resistors are 10 kΩ nominal. The model enforces an ideal
zero-volt inverting node, solves amplifier output voltage and current together,
and includes the actual sense-resistor branches. Sense branches draw zero DC
current only under the stated zero-leakage assumption. Pin-current transfer
coefficients are recorded so later leakage allocations can be applied without
counting one pin twice. The E-side source sense outputs also feed N-side
comparators and connector pins.

The ±3% screen is a receiving requirement, not accepted lifetime drift or a
new resistor specification. Rail extrema, offset, finite gain, output swing,
input clamps, startup, saturation, transient capacitor current and connector
loads remain unqualified. Nominal negative rails do not bound fault behavior.

## Device evidence and remaining acceptance

[Primary review](primary-review.json) records the inspected TI datasheet tables
and their test conditions. OPA supply current is specified per amplifier, so
the board has four channels to account for. The full-temperature input-bias
entry is typical, not a guaranteed maximum. REF35 enable-pin current also needs
ownership because EN is tied to AUX. These device terms are deliberately
separate from the resistor/output-current results.

Next: isolated-driver input and supply currents, the remaining package and pin
currents, switching and external loads, startup current and installed thermal
limits. No historical aggregate reserve is reduced. TBP50 copper and selected
documentation are unchanged; fabrication remains unreleased.
