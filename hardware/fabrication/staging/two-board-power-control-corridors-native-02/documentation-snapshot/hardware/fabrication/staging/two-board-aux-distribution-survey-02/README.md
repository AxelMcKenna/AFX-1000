# AUX source and load inventory

The [native inventory](inventory.json) reconciles the current
[power candidate](../two-board-power-startup-remaining-native-03/power_protection.kicad_pro)
with the historical AUX load review. It records **81 IC supply pins: eight
connected to the regulator output and 73 unconnected**. Eleven of the 87 AUX
capacitors reach the source, and 20 have main-ground returns. Distribution is
unfinished; local bypass completion does not establish powered circuits.

The 230 AUX terminals include 81 IC supply pins, 13 tied IC inputs, 87
capacitor terminals, 45 resistor terminals, two connector terminals, one
diode terminal and the regulator output. Resistor terminals are not independent
full-rail loads; their circuit states and shared paths must be resolved.

Direct capacitance totals **28.5 µF nominal**. Relative to the
[historical load review](../two-board-aux-load-review-01/README.md), P_C114 adds
100 nF and E_U42's datasheet metadata now correctly identifies its retained
LVC part. The earlier load and thermal limitations are still unresolved.
At an assumed 2.7 V endpoint, nominal capacitor charge divided by 1 ms is
76.95 mA; divided by 10 ms it is 7.695 mA. These comparisons exclude actual
ramp behavior, capacitance derating and simultaneous circuit load.

Next, reconcile startup/run/fault loads and transitions, resolve effective
capacitance and regulator startup behavior, and establish applicable current
and installed thermal limits. Then complete source and return routing and
verify loaded startup, fault, noise and thermal behavior. The inventory does
not qualify the LDO, the distribution, or the complete unit for fabrication.
