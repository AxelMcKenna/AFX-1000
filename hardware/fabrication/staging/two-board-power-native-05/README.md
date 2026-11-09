# TBP05: upstream negative-source sensing

The power/protection schematic now includes the NF auxiliary, sensing, clamp
and reset-masked fault interfaces. Two source-sense feeds are corrected to
remove a startup deadlock. **The complete circuit and PCB routing remain
unfinished; this is not a fabrication release.**

Open [power_protection.kicad_pro](power_protection.kicad_pro). It contains the
six-section schematic, native netlist, mapped power PCB and local libraries.

| Check | Result |
| --- | --- |
| Retained electrical components / schematic pins | 1,077 / 3,379 |
| Mapped physical pad instances | 3,440 |
| Retained complete footprint geometries | 1,092, including 15 mechanical |
| Interface pin pairs | 30 base + 15 NF |
| Native geometry / schematic-parity findings | 0 / 0 |
| ERC | 0 errors; 2 retained floating-reference warnings |
| Unrouted connections | **2,677** |
| Fault/reset combinations checked | 32, settled Boolean behavior only |

## Corrected startup dependency

Inserting NF ahead of E28 changed the E28 input into a switched downstream node.
The original E28 negative-source sensing resistors consequently measured NF's
output. NF requires source UV-good before releasing its permit flip-flop's
asynchronous clear. With the output discharged, that arrangement held the
switch off while waiting for the same switch's output to rise.

Only **E_R49.1** and **E_R53.1** move electrically: they now sense the respective
P03 negative sources upstream of NF. The E28 force inputs, NF drain monitors,
bank clamps and protected-output UV/OV monitors retain their distinct downstream
connections. No resistor value, footprint, placement or force path was changed.

The [source-sense audit](source-sense-audit.json) checks the actual native
resistor/op-amp/comparator paths and traces forced-low UV status through the AND
gates to each permit flip-flop's clear pin. It checks the complete before/after
pin partition, allowing only those two terminal changes. Four mutations reject
either sense returned downstream and a protected-output monitor moved upstream.
The nominal DC comparison illustrates the dependency; tolerance, loading,
partial-power and transient behavior still need qualification.

## Retained NF fault integration

The fifteen [NF interface pairs](NF-interface-joins.json) connect AUX, reference,
OV status/sense, protected outputs, actual bank gate/common clamp endpoints and
the split native/combined fault request. E_U25.8 and E_U21.8 are separate nets:
the NF fault result drives latch SET without shorting the two original outputs.
One now-redundant nonphysical AUX power flag was removed.

The existing N_U34 inverters and formerly unused N_U46 fourth OR gate implement
`SET = (native_fault OR N19_fault OR N12_fault) AND NOT(RESET)`.
The [TBP04 fault audit](../two-board-power-native-04/fault-mask-audit.json) checks
32 combinations and five faulty variants. All 32 combinations pass again using
TBP05's actual exported netlist. This proves settled logic only, not asynchronous
glitch freedom, reset pulse width or AUX undervoltage recovery.

The [native review](review.json), [circuit comparison](circuit-audit.json) and
independent source-sense audit retain all parts, values, assigned footprints,
placements, mounts and board setup. All 3,440 actual pads match the schematic.
The two ERC warnings remain N_U19.4 and N_U24.4: their negative-domain references
must remain separate from their host-side AGND. No check categories are ignored.

## Remaining fabrication work

- Qualified GLOBAL_MASTER buffering from E_U12.11 ALL_RAILS_ALLOW and AUX_VALID receiving.
- Loaded reference/sense/clamp/logic and auxiliary distribution review.
- Guarded module-input power, its separate force return and inrush/short behavior.
- Fault-latched AUX undervoltage recovery and a verified minimum actual GLOBAL-OFF interval.
- Final signal/power interfaces, critical power placement and complete routing.
- ESS codec package/land/stencil inputs, manufacturing stack/BOM/process and fabrication outputs.
- Revised supports/cooling, full installed fit and first-article inspection/bring-up plan.

The [signal board](../two-board-signal-routed-native-03/README.md) retains Daisy
Seed 3 and remains at 251 opens with one missing codec footprint. The large
power-board placement has no copper and has not been optimized for switching
loops, feedback, decoupling, Kelvin sensing or heat flow. Clean native composition
checks do not establish those requirements.
