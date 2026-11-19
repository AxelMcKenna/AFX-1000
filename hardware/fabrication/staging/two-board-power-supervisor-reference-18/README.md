# Supervisor and reference connections

Six new 0.30 mm traces connect local 3.3 V logic and two precision reference outputs. M_U8's sense input joins its supply pin and the M_U7 manual-reset input. The fan circuit's watchdog SET1 input joins the level translator's 3.3 V supply node. M_C45 connects to the rail-monitor logic gate's supply pin. These local connections still require power distribution to their sources.

P_U4 pin 6 connects directly to P_C31 over 2.71 mm. M_U6 pin 6 connects directly to M_C49 over 3.48 mm. Both REF5025EIDR references use nominal 2.2 µF output capacitors. TI specifies pin 6 as VOUT and recommends 1–100 µF of low-ESR output capacitance for the EI variant. The capacitor ground returns, effective capacitance under bias and reference performance remain open. [TI datasheet, sections 5 and 9.4](https://www.ti.com/lit/ds/symlink/ref50.pdf)

All six traces have full-width ground coverage on the adjacent layer. KiCad 10.0.7 verifies six intended connections and 1,692 opens before and after refill. All 47 refilled zone-layer geometries match the independently refilled parent. DRC reports zero geometry or schematic parity findings. ERC retains the two existing isolated-reference warnings. The paired board placements match the current assembly capture.

[Routes](routes.json) · [Ground coverage](reference-review.json) · [Connectivity](connectivity.json) · [Retained copper](retention.json) · [Refill](refill-comparison.json) · [Placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Previous revision](../two-board-power-buffer-decoupling-17/README.md)
