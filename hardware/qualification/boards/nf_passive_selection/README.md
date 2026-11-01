# NP01 — NF passive selection proposal

This packet supplies catalog-supported candidates for **196 actual passives: 97 resistors and 99 capacitors**. It does not adopt them into a schematic or PCB. The original **complete ±0.1% resistor assumption is not closed**. Several package and land changes require a new routed board and fresh electrical/MCAD analysis. Every fabrication, physical and electrical qualification flag remains false.

The per-reference review table is [selections.csv](generated/selections.csv); [selections.json](generated/selections.json) also contains body maxima, proposed seating, order-code confidence, original nets and holds. [analysis.json](analyses/analysis.json) records independent calculations and actual pad extraction. [primary-facts.json](primary-facts.json) links the public primary documents; all ten downloaded PDFs have byte hashes in the selection report. The two TDK exact-product pages were reviewed online; their PDF/page bytes could not be captured, and that provenance limitation is explicit.

The inputs are immutable copies of historical NF249 and provisional NF261, plus the physical NF233 parent. The copied261 predates the subsequent TPS3890 pin correction and is used **only to enumerate passive identities and nets**. Historical249 has the RESET/VDD swap only on its new U52/U54; pre-fix261 additionally has U56. The four older floating TPS3890 monitors were correct. [electrical-pin-erratum.json](electrical-pin-erratum.json) preserves the exact scope. No erroneous electrical circuit is adopted and no future261/READY circuit is implicitly represented here.

[passive-input-delta.json](analyses/passive-input-delta.json) enumerates the nine added passives and six changed passive identities/nets between the two captured versions. It explicitly captures the AUX clamp supply and separate module-primary return changes.

## Concrete component choices and limits

| Function / actual references | Candidate | What remains to resolve |
|---|---|---|
| 29 precision gain/reference resistors | TNPU0805 .02% /2ppm for500Ω..20kΩ; .02% /5ppm for100Ω..200kΩ | Catalog restrictions are checked per value. Four low trim parts R26/R30/R34/R50 need TNPU0603 .05% /5ppm, which changes actual lands. |
| 61 ordinary0805 and R97/1206 | TNPW .1% /25ppm | General-mode rating and drift basis used, not the headline high-power/high-temperature mode. Complete0.5/3% still needs actual process/life/temperature closure. |
| R56/R57/R73/R74 floating feed | Retained CRCW2010402RFKEF; alternative **PRG5025P-4020-B-T4** | CRCW's complete3% is unproved. PRG has real catalog support but **long-side terminals**, new lands/orientation, and an unresolved1.5..2W application/test-board rating. It is not a drop-in. |
| R69/R86 current shunts | **WSL2512R3300DEA / WSL2512R1200DEA** | Initial0.5% and component75ppm/K, not element-only20ppm. New recommended lands and intentional Kelvin takeoffs; fault pulse/repetition remain open. |
| C1/C2 watchdog timing | C1206C563J5GACTU / C1206C333J5GACTU | Actual NF233 still has0805 here. The proposed1206 parts must be physically placed/routed and the watchdog rerun. Max projections with a project0.1mm seat are1.45 /1.10mm. |
| C0G timing/ramp/reference capacitors | Exact KEMET1206/1210 candidates listed per reference | Initial5% plus65K×30ppm/K already totals5.195%; a complete6% limit leaves only0.805% for everything else. Catalog F1% variants are proposed options, not adopted replacements. |
| 43 local100nF50V X7R bypasses | C0603C104K5RACTU | Exact CJ thickness max0.95mm +project0.10seat =**1.05mm**. Initial and X7R temperature alone permit a0.765 lower-capacitance factor, before DC bias/aging. No effective-C/PDN pass. |
| Six module/local-VIN X7R filters | TDK C3216X7R1E106K160AB10µF25V and C3216X7R1H105K160AB1µF50V | Both max3.4×1.8×1.8mm,1.9mm proposed projection. The50V option changes the two old25V local-VIN items. A nominal1µF is not a guaranteed1µF effective. Manufacturer land drawing, module input inrush/filter stability and actual effectiveC/ESR remain open. |
| Four2.2µF CF capacitors | Retain **MKS2C042201K00JSSD** | Public WIMA table supplies nominal7.2×7.2×13mm but no body maximum. PCM5±0.5mm at pin exit needs forming/process review. Hot leakage, effective CF10%, solder process and lead trim remain open. |

These codes are supported by published manufacturer series ordering/range tables; where an individual product record was not found, the table explicitly says so. A catalog order code is not factory availability, a quotation, a guaranteed custom option or purchase approval. No substitute is silently selected.

## Error scenarios and actual circuit implications

The TNPU planning scenarios add initial error,65K TCR, a catalog endurance term, solder-heat and steady damp-heat test limits, including their absolute-ohm terms. These are **separate qualification test limits**, not a guaranteed simultaneous installed drift distribution. They help size a defensible receiving requirement; the temperature, board load, service life and process have not been accepted.

At1000h the25 high-value precision candidates sum0.203–0.240%; the four low-value trims sum0.293–0.337%. At8000h all29 sum0.253–0.415%, so **±0.5% is a feasible planning scenario to investigate**, not an approved complete bound. At225000h the low trims exceed0.5%. Uniform0.25% is not justified for all parts; mixed0.25% high-value /0.5% trim is an alternative scenario requiring the complete circuit analysis to be rerun.

The new provisional RAW5 UV divider has a further issue: R93=49.9Ω TNPW's analogous planning sum is0.49262% at1000h and **0.56266% at8000h**, exceeding its complete0.5% assumption. [lifetime-scenarios.json](analyses/lifetime-scenarios.json) supplies the concrete **TNPU060349R9AZEN00** alternative (.05%/5ppm),0.38266% at8000h in the same conditional sum. That requires a0603 footprint; keeping0805 with a larger trim-only error and rerunning the actual divider is another explicit option. Neither is adopted. The same report quantifies the retained CRCW402Ω feed sum at3.93731% versus3%; the PRG long-side option improves that conditional1000h sum to0.51996%, with application lands/thermal power still unresolved.

The captured protected-monitor equation was independently replayed using the actual261 resistor values. Reference/offset/input-bias assumptions are retained as unaccepted. No precision endpoint or new safety acceptance threshold is invented:

| Uniform complete resistor scenario | N19 protected UV (V) | N19 protected OV (V) | N12 protected UV (V) | N12 protected OV (V) |
|---|---:|---:|---:|---:|
| ±0.1%, old assumption |18.2590–18.5415|19.4566–19.7442|11.4107–11.5898|12.4085–12.5918|
| ±0.25%, comparison |18.1999–18.6016|19.3971–19.8047|11.3731–11.6280|12.3706–12.6304|
| ±0.5%, comparison |18.1018–18.7023|19.2984–19.9059|11.3108–11.6919|12.3077–12.6950|

Required before adoption: rerun source-UV guards with the actual E28 external sense ratio; protected UV/OV, bias-valid/INTVCC guards and RAW5/AUX supervisor dividers; watchdog min/max times; ramp/CF charge, normal/fault current, FET SOA/reset/charged-load trajectories; total controller/LED/reference loads; bypass PDN, module input inrush and minimum effectiveC/ESR. If resistor pairs are replaced by a ratio network, a real matching/tracking/absolute-error specification and exact package lands must be selected first. A generic ratio-network label supplies no guarantee.

## Lands, process and power

[NP01.pretty](analyses/NP01.pretty) contains **nine new two-pad manufacturer-recommendation candidates**, parsed by real KiCad10.0.7:18 pads, exact pad numbers, centers and dimensions cross-checked. [native-lands.json](analyses/native-lands.json) is the saved parser receipt. This is a library-geometry check, not a board DRC or solderability pass.

Actual NF233 pads were extracted from the saved native PCB, including absolute pad-angle normalization. All167 comparisons for which both a saved parent pad and an explicit manufacturer land recommendation exist differ from that selected recommendation; the other29 have no old native part or await a TDK/WIMA process drawing. A recommendation difference is **not automatically a native DRC failure**. The original land may be a different valid density/process choice, but it cannot be called the checked manufacturer's pattern without review. In particular:

- WSL actual generic2512 gap4.70mm/pad1.225×3.35 differs from recommended4.06mm/pad1.65×3.68. Candidate overall span7.36mm and Kelvin takeoffs must be routed deliberately.
- CRCW2010 actual span5.85mm differs from the recommended6.40mm reflow pattern.
- TNPU/TNPW0805 recommended IPC gap1.00mm differs from actual0.80mm; low trim0603 also changes package and lands.
- KEMET1206/1210 pad centers change±1.475→±1.50mm; the old C1/C2 change is much larger because their actual source is0805.

The conditional85°C ambient DC screens give R4/R11≤69.34mW, R97≤116.15mW and each feed resistor≤446.84mW under the declared5.2V/26.4V and complete3% resistance cases. A20% power provision fits the catalog derated general/DC ratings in those cases. This does not establish actual film temperature, thermal spreading, fault duration or assembled behavior. WSL value derating above0.1Ω is included; their75ppm component TCR and absolute-ohm drift terms are included in separate planning sums. Gate/ramp resistors R6/R7/R13/R14/R70/R87/R72/R89 require measured/bounded pulse voltage, energy, repetition and hot condition. Mean/DC power alone cannot qualify them.

An external coordination message once compared J6 primary contact loss with the804Ω isolated-secondary feed. That comparison was wrong and is explicitly rejected in the analysis. At the provisional174.13mA primary current, two20mΩ interfaces would lose6.965mV **in the primary domain**; source minimum, inrush and hot/life resistance still need proof. This was not a claim in sealed NC01.

## Reproduce without replacing a seal

Portable saved-artifact checks and thirteen analytical/mutation regressions:

```sh
python3 -m hardware.qualification.boards.nf_passive_selection.verify
python3 -m unittest hardware.qualification.boards.nf_passive_selection.test_np01
```

Captured replay uses only the copied historical inputs and refuses any existing output directory:

```sh
python3 -m hardware.qualification.boards.nf_passive_selection.selection --output /private/tmp/np01-new-selections
python3 -m hardware.qualification.boards.nf_passive_selection.audit --selected /private/tmp/np01-new-selections/selections.json --output /private/tmp/np01-new-analyses
```

Optional real KiCad parser rerun needs a Python environment with `pcbnew`; save a **new** output file:

```sh
KICAD_PYTHON hardware/qualification/boards/nf_passive_selection/native_land_check.py --output /private/tmp/np01-new-native-lands.json
```

No test downloads models or runs live parent builders. The tests check complete inventory, checked catalog-range boundaries, drift absolute-ohm terms, independent analytic monitor corners, source pad geometry and physical package changes, correct complete height stacks, the feed-resistor maximum-power corner and derating, false-qualification rejection, and fresh-output replay/overwrite refusal. No board fabrication or prototype measurements were performed.
