# Two-board power/protection circuit composition

The six power/protection circuits now share one native KiCad schematic and
the 320 × 181.1 mm placement candidate. **This is not a completed power circuit
or a fabrication release.** NF control, fault, clamp and auxiliary paths still
need design work, and the board has no routed copper.

Open [power_protection.kicad_pro](power_protection.kicad_pro). The project includes
six source sheets, their own symbol libraries, the mapped PCB, footprint
libraries and retained placement rules.

| Check | Result |
| --- | --- |
| Electrical components | 1,077, all retained |
| Source schematic pin entries | 3,379, exact declared connectivity partition |
| Explicit interface pin pairs | 30 |
| Shared interface nets / source-net merges | 24 / 29 |
| Physical pads mapped to the schematic | 3,440 |
| Complete footprint geometries retained | 1,092, including 15 mechanical |
| Native placement / schematic parity findings | 0 / 0 |
| ERC | 0 errors; 2 retained isolated-reference warnings |
| Native open connections | **2,663** |

The open count is the original unrouted placement's 2,634 plus 29 new source-net
merges. None of these new schematic connections is represented by routed copper.

## Actual connections and checks

The composition implements the previously reconciled inlet/switch, source and
protected-rail monitoring interfaces. Negative source rails enter NF before
E28. NF control raw5 comes through the fan board's current-limited U401 output.
Fan health remains in the E28 RUN path. The separate NF module-input return is
not joined to AGND. The [join map](interface-joins.json) names each source net
and its new common net explicitly.

The [native circuit audit](circuit-audit.json) compares every source component,
value, assigned footprint and pin partition. Mutation checks reject negative-stage
and raw5-limiter bypasses, fan-RUN bypass, an isolated-return short, a protected/raw
5 V short, the wrong GLOBAL_MASTER source and swapped negative-force pins.

Thirteen nonphysical external-power flags became redundant after the real
drivers were connected inside the project. Only those flags and their own direct
labels were removed. No electrical component, source driver or protection stage
was deleted, and no ERC/DRC category was ignored.

The [native review](review.json) and independent [placement delta](placement-delta.json)
show unchanged component values, land geometry, poses, outline, mounts and setup,
apart from declared net/instance-path mapping and mechanical `board_only` flags.
The independent check rejects a shifted part, altered land size or component
substitution. It does not qualify the packed power layout's feedback, decoupling,
Kelvin, timing, switching-loop or thermal relationships.

The two ERC warnings concern ISO7721F GND1 pins N_U19.4 and N_U24.4. Their actual
references are the respective negative source rails, distinct from their host
side's AGND. This preserves the original floating domains. The warnings are
recorded, not suppressed or treated as proof of a qualified interface.

## Next circuit changes

The [NF interface design review](nf-interface-design-review.json) inventories
the real source and destination pins. Two unused E_U42 buffer channels exist,
but the existing NF 47 kΩ pull-down alone can demand 59.22 µA under the declared
2.7 V / −3% resistance bounds. The manufacturer's continuous-range VCC−0.1 V
output guarantee is specified at 20 µA. That guarantee cannot be applied to the
existing load; the spare-channel option has not been implemented or accepted.
The reviewed primary electrical tables are bound in the report. A stronger
buffer or a deliberately checked receiver-load redesign remains necessary.

NF GLOBAL_MASTER must originate from E_U12.11 ALL_RAILS_ALLOW, through the
qualified interface, rather than E_U29.7 E28_MASTER_ENABLE. NF auxiliary power,
AUX_VALID, reference and OV feedback, protected-rail sense and bank clamps must
also be integrated. Inserting the NF combined fault requires splitting the
existing E28 native fault-request net; connecting two outputs together is not
an acceptable substitute. Guarded module power and its separate force return,
minimum physical GLOBAL-OFF interval and fault-latched AUX-UV recovery remain
open design requirements.

The [signal checkpoint](../two-board-signal-routed-native-03/README.md) retains
Daisy Seed 3 and has 251 opens. Both boards still need a complete cross-board
interface, critical placement/routing, the ESS codec land, manufacturing stack
and process, revised supports/cooling and a full installed-fit check. Clean
composition/parity results do not establish those remaining requirements.
