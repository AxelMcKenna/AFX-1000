# AUX output-load reconciliation against TBP50

This review assigns direct output-to-ground resistor loads to their actual
source supply and updates the shared POWER_READY released-state calculation.
It uses the selected TBP50 netlist. It does not establish a complete rail
current bound or change the PCB.

- [Pin-level load ledger and calculations](output-loads.json)
- [Independent verification](verification.json)
- [Six directly inspected manufacturer PDF pages](primary-review.json)

## Direct output loads

| Conditional DC item | Result |
| --- | ---: |
| AUX logic-output pulldowns identified | 22 resistors |
| Sum with all outputs at 2.7 V and resistance at 97% of nominal | 1.557097 mA |
| NF-side subset supplied by AUX | 12 resistors, 0.619391 mA |
| U42 NF output subset, R15 and R16 | 2 resistors, 0.118447 mA |
| N_R61 and N_R78 | RAW5 loads, excluded from AUX output sum |
| E_R94 | Reference-output load, separate from logic-output sum |

The subsets overlap: do not add their totals to the 22-resistor sum.
The calculation uses simultaneous HIGH outputs as a conservative resistor
screen, not a proved functional state. It excludes input leakage, package
current, switching/capacitor current, external loads, other resistor networks,
isolated-driver power and analog/reference output loading. Most E-side
resistors lack accepted total-drift bounds; the 3% allowance is an engineering
requirement. NF values explicitly state a 3% total receiving requirement,
which still needs component/process acceptance. Actual loaded AUX voltage
remains unqualified. These are logical circuit loads; the 73 unconnected IC
supply pins are not represented as physically powered hardware.

The two dual-supply translators cannot be budgeted by package membership alone.
N_U16 drives B outputs from RAW5 through pin 8, while N_U27 drives B outputs
from AUX through pin 8. Both have DIR tied to VCCA. Their output resistor
loads therefore belong to different supplies. This follows the current
netlist and the [TI DCU port definitions, pages 1-2](https://www.ti.com/lit/ds/symlink/sn74lvc2t45.pdf).

U42's two NF outputs each drive a 47 kΩ pulldown and one HCS08 input. Its
third output drives E_U26. The historical nine-pulldown NF term has no complete
per-resistor ownership proof for today's circuit. The current twelve NF-side
AUX output branches are recorded explicitly, including R68/R85 on the AUX
side of N_U27. No amount is deducted from the old NF reserve or the old E28
external-output reserve; a full term-by-term replacement is still required.

## POWER_READY released load

R110 supplies the two 10 kΩ/22 kΩ enable-divider branches. At nominal
resistance, 2.7 V AUX and zero injected currents, AUX supplies **158.824 µA**.
The previous 2 µA released-state allowance misses this real resistive load.
Across 512 combinations of the existing 2.3-2.7 V scenario, initial 1%
resistor tolerances, 0-25 µA allocated EN sourcing per converter and
±10.15 µA allocated READY-node current, the AUX contribution is
**92.049-169.981 µA**.

These current allocations are assumptions from the existing enable review,
not guaranteed device envelopes. J103/J22 external loads are assumed absent;
component drift and actual supply offsets remain unresolved. Independent
verification checks every matrix result against an eliminated-node closed
form and checks current conservation. When READY is asserted, the old budget
already includes its full pullup load; do not add that branch twice.

## Datasheet and startup limits

The [LVC3G17 table](https://www.ti.com/lit/ds/symlink/sn74lvc3g17.pdf)
places its 10 µA no-load row under specified input conditions and its
500 µA delta-current row at 3-5.5 V with one non-rail input. It does not supply
a guaranteed 2.3-2.7 V transition-current envelope. The
[HCS08 input-leakage maximum](https://www.ti.com/lit/ds/symlink/sn74hcs08.pdf)
is specified at 6 V with rail-valued inputs. Neither table is extrapolated
into a complete AUX-band guarantee here.

P_C110 is connected to the regulator's DELAY pin. That capacitor sets
power-good timing after the output threshold; it is not an externally
programmed output ramp. The regulator has separate internal soft start.
See [TPS7A16 sections 7.3.2 and 7.3.4](https://www.ti.com/lit/ds/symlink/tps7a16.pdf).
The 28.5 µF nominal charge screens therefore cannot substitute the nominal
PG delay for actual ramp time. The PDFs and inspected renders are hash-bound
in the reports. The load report's pending visual flag refers to its earlier
stage; primary-review.json records the completed six-page inspection.

## Next required work

Rebuild the complete E/P/N state ledger using explicit branch ownership:
45 direct AUX resistor terminals still need full network/state accounting,
along with feedback/reference/OPA paths, all package and input currents,
connector/clamp behavior and switching loads. Establish effective capacitor
bounds, output startup behavior and installed thermal performance before
accepting the LDO and completing distribution. Historical aggregate reserves
and current/thermal acceptance remain unresolved. TBP50 remains selected at
2,172 power opens and 251 signal opens. This is not a fabrication release.
