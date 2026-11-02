# E13 resistor selection proposal

The [candidate table](candidates.csv) covers all 114 resistors in the selected
E13 board: 79 precision, 16 feedback and 19 ordinary resistors. Every value,
footprint identifier and resistor pin net is checked against the source component
inventory. [The report](candidates.json) binds the exact PCB and inventory hashes.
Candidate ordering codes are derived
from manufacturer syntax; they are not confirmed catalog listings, stock checks
or an approved procurement BOM. No circuit or PCB was modified.

For 78 precision resistors, [Vishay PLT, document 60030,
11-May-2026](https://www.vishay.com/docs/60030/plt.pdf), pages 1–2, supports the
required range, initial tolerance and TCR. Its restriction excludes R83's 127 Ω
value. Packaging TS is used in the proposal; quantity and availability need
confirmation. The conditional -55..125 °C resistor-body screen consumes about 0.09003%
from initial tolerance, temperature, the specified 2,000-hour load test and
one-year shelf test combined. Less than 0.01% remains for process and other drift.
The environmental table's typical values cannot close that reserve. These test
conditions do not establish a product mission lifetime or combined-stress limit.

R83's candidate is **Bourns CRT0805-PT-1270ELF**: the
[manufacturer CRT sheet](https://www.bourns.com/docs/product-datasheets/crt.pdf),
01C, pages 1–2, includes 127 Ω at 0.01% and 2 ppm/°C. Its 0.05% solder-heat
and 0.05% load-life limits make the unscreened bound about 0.13006% over the same body
temperature screen, exceeding the existing 0.1% requirement. A proposed
post-reflow 25 °C acceptance bound of 0.02%, **including measurement uncertainty**,
would reduce that partial bound to about 0.09003%. This requires a feasible Kelvin
measurement with isolation or validated de-embedding; measuring the populated
board's parallel network is insufficient. Humidity, lifetime and other stresses
still need closure. Its recommended 1.00 mm pad gap differs from the actual
0.80 mm gap (1.025 × 1.4 mm pads). Neither the alternate lands nor the measurement
process has been accepted. The manufacturer's table and land figure were
visually inspected; no footprint substitution is implied.

A [separate R83 land candidate](../../staging/rail-monitor-r83-land-native-01/README.md)
now implements the recommended copper geometry and passes fresh native checks
with zero findings or opens. Its independent audit confirms the exact original
circuit and unchanged routes. This table continues to describe the selected
parent board; the new candidate still needs exact-part, process, installed-error,
mechanical and PDN acceptance before selection.

For the 20 MΩ feedback positions, **Ohmite HVC0805V2005FET** is a proposed code
from the [HVC sheet, revision 6/20-3](https://www.ohmite.com/assets/images/res-hvc.pdf?r=false).
It still needs confirmation that this exact resistance/tolerance/TCR combination
is supplied. The feedback screen allocates at most 4% intrinsic resistance error
and at least 2 GΩ parallel insulation resistance. With a 20 MΩ nominal part,
the worst passive-shunt result is 19.0174 MΩ, above the existing 19 MΩ lower
limit. A 1 GΩ shunt fails. This is a proposed installed leakage limit, not a
measurement. Leakage to other-voltage nets and comparator input current require
their own node-current analysis. Voltage coefficient at the actual low operating
voltage, process cleanliness, combined drift, lands and temperature remain open.

The 19 ordinary positions have proposed **CRCW080510K0FKEA** (17),
**CRCW0805100KFKEA** (1) and **CRCW0805330KFKEA** (1). The
[Vishay D/CRCW e3 sheet, 20035, 14-Apr-2026](https://www.vishay.com/docs/20035/dcrcwe3.pdf),
pages 1–3, supports their values, 1% initial tolerance and 100 ppm/K TCR.
Initial tolerance, the same temperature screen and the standard-mode 1,000-hour
drift limit already combine to 3.0301%. Timing and logic calculations must
enclose that drift plus the remaining process/environment terms; a source
value marked 1% alone is insufficient. The additional DC calculation shows that
a proposed 5% total bound retains the original comparator HIGH interval, sink
current and final-output load limits. It conditionally allows 5% for the E09
47 kΩ receiving pull-down too; it does not qualify that external part or the
timer mode. No extended-power drift assumption is used. Footprint, process and
lifetime acceptance remain required. All drift calculations retain cross terms.

To close this selection: confirm the exact ordering combinations; establish the
product temperature and service-life envelope; close the precision drift reserves;
approve R83 lands and a practical measurement method; demonstrate feedback
insulation and leakage; then update the production BOM and repeat native checks
if any footprint changes. The current electrical allocations remain unchanged.

Reproduce without native CAD:

```sh
python -m hardware.fabrication.rail_monitor_resistors \
  --output hardware/fabrication/parts/rail-monitor-resistors-01 --check
```

Omit `--check` only with a new output directory. No Mac CAD app, supplier message,
order, or fabrication release is involved.
