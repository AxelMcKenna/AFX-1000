# TBP50 direct AUX resistor networks

The current netlist contains 45 resistors connected directly to AUX. Following
their complete resistor paths gives 44 disjoint networks containing 77 resistors.
The sum of each network's conditional maximum AUX draw is **15.474894 mA**.
This is a steady-state resistor calculation, not a complete rail-current bound
or fabrication release.

[Analysis](analysis.json) records all 1,044 corner solutions, actual resistor
ownership, node voltages, branch currents and source currents.
[Independent verification](verification.json) checks complete coverage,
series/parallel closed forms, Ohm's law, KCL and power conservation. The maximum
closed-form difference is 2.88e-18 A. It also checks 107 nominal leakage-current
transfer coefficients using a separate bordered-matrix formulation.

The calculation uses AUX at 2.3–2.7 V, a fixed reference at 1.2375–1.2625 V,
independent resistor factors of 0.97–1.03, zero pin currents, open capacitors
and ideal open-collector/MOSFET sinks. These resistor bounds are receiving
requirements; actual lifetime and temperature bounds are not accepted.
Network maxima need not correspond to one simultaneous functional state.

The model includes the shared E_R88/E_R92 feedback network, reference feedback
paths, POWER_READY dividers, and the physical RUN switch. RUN OFF disconnects
the AUX resistor branch; RUN ON includes the released or clamped RUN node.
PG and Q103 can clamp the same node, but their individual sink currents are
not separated. Coupled pullups are solved together rather than counted twice.

These 77 resistors are disjoint from the previous output-pulldown inventory.
The [output-load reconciliation](../two-board-aux-current-reconciliation-01/README.md)
adds a conditional 1.557097 mA for 22 AUX-powered logic-output resistors.
Their arithmetic sum is 17.031991 mA under the stated assumptions. No historical
aggregate current reserve is reduced, and reference-source currents are kept
separate rather than used as an unqualified credit.

Still required: package and input currents, reference/OPA and isolated-driver
loads, external connector and clamp behavior, switching loads, effective
capacitance and startup ramp, and installed thermal limits. The selected TBP50
copper is unchanged. Fabrication remains unreleased.
