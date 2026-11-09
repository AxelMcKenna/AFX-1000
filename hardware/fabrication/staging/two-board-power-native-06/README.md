# TBP06: buffered NF enables and integrated UV-fault review

NF GLOBAL_MASTER and AUX_VALID now connect to their actual E28 sources through
the two previously unused E_U42 buffer channels. The circuit retains 1,077 parts
and all placement geometry. **Electrical qualification, complete routing and
fabrication release remain unfinished.**

Open [power_protection.kicad_pro](power_protection.kicad_pro).

| Check | Result |
| --- | --- |
| Electrical parts / schematic pin entries | 1,077 / 3,379 |
| Physical pad instances mapped | 3,440 |
| Retained footprint geometries | 1,092, including 15 mechanical |
| Declared interface pin pairs | 30 base + 15 NF + 4 enable |
| Native geometry / schematic-parity findings | 0 / 0 |
| ERC | 0 errors; 2 retained floating-reference warnings |
| Unrouted connections | **2,679** |
| Settled integrated UV-fault combinations | 64 |

## Implemented enable interfaces

- E_U12.11 ALL_RAILS_ALLOW → E_U42.3/.5 → NF GLOBAL_MASTER.
- E_U31.3 E28_AUX_VALID → E_U42.6/.2 → NF AUX_VALID.

GLOBAL_MASTER remains distinct from E_U29.7 E28_MASTER_ENABLE. Both receiving
47 kΩ pull-downs remain. E_U42 changes from SN74AUP3G17DCUR to pin-compatible
**SN74LVC3G17DCUR**, using the existing DCU0008A manufacturer land. Its original
ANA_PG2 channel, supply, return and decoupling connection remain unchanged. No
new package or footprint is added; no component is moved.

The [independent audit](enable-recovery-audit.json) checks the complete native
before/after pin partition, all component values and footprints, every physical
pad mapping, and the one declared MPN substitution. Its land check matches
the TI DCU0008A example: eight 0.85 × 0.30 mm lands, 0.50 mm pitch, 3.10 mm
column spacing and 0.05 mm corner radius. Supplier mask/paste/process acceptance
and final placement/decoupling remain separate requirements.

## Current-drive screen and its limits

At the declared 2.7 V maximum and −3% resistance, each pull-down draws up to
59.22 µA. Adding a 1 µA HCS-input receiving allowance and 1 µA PCB leakage
reserve, then applying a 1.2 guard, gives **73.47 µA per output**. This fits
the LVC buffer's 100 µA VCC−0.1 V output row; it exceeds the old AUP buffer's
20 µA row. This closes the identified output-current mismatch under those
receiving assumptions.

It does not qualify the entire interface. In particular, the actual E_U31
AUX_VALID fan-out includes two LVC inputs. With their specified leakage limits,
the guarded source load is 15.0 µA through 85°C, but **55.8 µA through 125°C**.
The 20 µA AUP output row cannot support the latter claim; the pre-existing
fan-out already exceeded it before adding the buffer. No whole-unit operating
temperature acceptance is inferred. Full-range Schmitt-threshold/noise margins,
partial-power defaults, input-transition current and loaded delays remain open.
The report binds the reviewed primary electrical tables and land drawing.

## Actual UV fault and retained disable path

The selected 265-part NF source already contains U58 and the retained-ARM
UV-to-fault path. Its current contract is **NF05R265**, not the older 261-part
contract used in some earlier integration notes. Its NF AUX allocations are
11 mA normal and 14 mA fault, within the still-unqualified common 90 mA pool.

The independent native-pin model checks 64 combinations of UV readiness,
source safety, ARM, AUX_VALID, RUN and another fault. A six-phase trace verifies:

1. Recognized UV loss after ARM asserts the combined fault SET.
2. The E28 fault latch asserts and drops ALL_RAILS_ALLOW through E_U28/E_U27/E_U12.
3. The new buffer drops NF GLOBAL_VALID, which clears NF ARM.
4. NF's fault request then clears, but E28 retains the fault.
5. Recovery of UV readiness leaves GLOBAL disabled while RUN and AUX_VALID remain high.
6. RUN low resets the fault and keeps GLOBAL disabled.

Five wiring mutations are rejected: wrong MASTER source, reversed UV polarity,
UV directly clearing ARM, fault feedback bypass and missing SET mask. The earlier
32 fault/reset combinations and both upstream source-sense channels also pass
again on this native export.

**This is settled Boolean evidence only.** Loss of AUX_VALID explicitly resets
the E28 latch; the audit includes that counterexample. Deep AUX corruption,
minimum recognized UV pulse width, loaded fault-capture delay, relay cutoff and
minimum physical GLOBAL-OFF duration are not proven by this trace. The next
recovery work must address those conditions, not duplicate the existing UV
fault path or assume the supervisor's nominal delay proves them.

## Remaining fabrication work

Guarded module-input power and its separate force return, final signal/power
interfaces, loaded reference/sense/clamp and AUX distribution review, temperature
and logic-level acceptance, and physical fault/recovery timing remain open.
The power placement still needs electrical optimization and all routing. The
[signal board](../two-board-signal-routed-native-03/README.md) retains Daisy Seed 3
and has 251 opens and a missing ESS codec footprint. Manufacturing stack/BOM/
process, supports/cooling, complete installed fit, fabrication outputs and the
first-article inspection/bring-up plan remain required.

The two ERC warnings remain the separate ISO7721F floating-reference domains.
No check category was suppressed. [Native results](review.json) and the
[circuit comparison](circuit-audit.json) support the composition checks above,
not a fabrication-readiness claim.
