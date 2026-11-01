# NF02 — negative startup protection, equations before native implementation

NF02 finds a conditional design region using **LTC4261IGN#PBF's separate output-ramp function**, an independently armed **TPS3431 startup deadline/fault latch**, and the retained upstream reverse-blocking banks. It keeps all protected bulk downstream and retains the26/151mA external live-load allocations. It is a new, private **pre-native** study. There is no new schematic/PCB, no measured startup/fault waveform, and no released design.

`generated/analysis.json` contains the actual calculations, native node inventory, error intervals and source fingerprints. `architecture.json` specifies series-path orientation, proposed pin roles, arming/FAULT logic, physical interfaces and partial-power conditions. `PRIMARY-FACTS.md` separates primary table conditions from receiving requirements. Do not turn `closed_algebraic_receiving_region` into a physical or full-temperature pass.

## Results

| Conditional quantity | N19 | N12 |
|---|---:|---:|
| Actual P03 source magnitude enclosure |18.88866–19.11165V|11.92949–12.07069V|
| Retained final target magnitude |18.81–19.19V|11.88–12.12V|
| Full-live protected current, including E28 bleed and new1mA leakage requirement |27.419mA|152.265mA|
| New complete-network capacitance requirement, **unverified** |2.8mF|400µF|
| RAMP nominal CR / CF / RF |1.2µF /4.7µF /27Ω|0.9µF /3.3µF /39Ω|
| Normal protected-current peak diagnostic |99.367mA|165.992mA|
| Full-ramp/filter/gate/ready diagnostic |2.73035s|1.56745s|
| CWD nominal / resulting watchdog interval |56nF /3.58014–5.28101s|33nF /2.13017–3.13676s|
| Proposed shunt / native45–55mV limit interval |.330Ω /.12987–.17544A|.120Ω /.35714–.48246A|
| Proposed steady stage drop |10.926mV|25.646mV|
| Existing remaining DC-drop allocation after10mV dynamic +5mV return/harness |63.658mV|34.486mV|
| Actual-ledger cold switch peak diagnostic |.71584A|.73140A|
| Normal cap+live-load linear-pass energy diagnostic |.99494J|.83256J|
| Full-watchdog rectangular fault energy **before unknown transients** |17.7068J|18.2672J|

The algebra retains20% ratio margin for the stated normal ramp/current, cold0.9A-only source screen, minimum deadline, capacitance receiving allocation, filter time constant, floating bias feed and DC drop. The transfer from the manufacturer's single SS test point to the entire ramp is **not** guaranteed; the additional20% trajectory excursion is a diagnostic sensitivity. The original150/220mA ceilings and5s startup preference are planning values, not hard user limits. This design uses a higher **fault** limit while keeping normal charging lower; the source is not promised to sustain that fault limit.

The old initial-only1.8mF/264µF capacitor upper estimates are insufficient as complete worst-case inventories. Actual Panasonic endurance permits a restored20°C comparison2.25mF/330µF before other network capacitors. The2.8mF/400µF receiving requirements leave20% over those known subtotals but do not prove hot capacitance, all external capacitance or lifetime behavior. Hot leakage, ESR, stability and load-step limits remain open. Nothing modifies NF01, SC02 or the original bulk.

## Source power and bias

The guarded-positive12V floating bias must switch **normally OFF** whenever the actual after-bank negative rail or AUX is invalid. Permanent resistor feed is rejected because it can keep the controller alive with the negative input missing. Proposed two-resistor feeds1612Ω(N19) and906Ω(N12) supply9.694–13.853mA and9.788–16.637mA under the stated voltage/resistance conditions. Controller plus external receiving load is7.787mA. Normal feed is inside5–25mA; initial VIN-zero feed remains below50mA with20% margin.

Every bias milliampere is counted in both the positive input and the negative-source return. The model also includes actual E28 bleeds, new leakage/absolute-monitor allowances, a VEE10k bleed,6mA new isolated-control primary load on DIG and.10mA on AUX. Those physical interfaces are **not installed**. Exact translator/latch/monitor parts, hot bias-switch behavior and optional sink-driver supply current remain unselected or unbounded.

The input model removes the previous independent raw50/200mA power allocation, inserts the actual all-four-rail ledger and new negative-stage currents, and retains only the unselected positive-controller3mA/sign reserve. It does not add the old negative3mA twice. With the retained plug11.4V/feed.36Ω/efficiency75–85% scenarios:

| State | Total inlet current | Guarded voltage |
|---|---:|---:|
| All loads steady |2.77360A|10.40150V|
| Only N19 charging, other rail loads remain ON |3.00600A|10.31784V|
| Only N12 charging, other rail loads remain ON |2.80163A|10.39141V|

Both charging cases retain20% current headroom against the existing4A input profile. These are constant-power diagnostic points, not adapter/transient guarantees. No concurrent bipolar charging is credited. Initial bias/after-bank capacitor charging is outside these armed-ramp points: its finite source impedance, peak current, energy, bank closure and rail-valid settling still need proof. The new maximum6.6µF after-bank capacitor alone stores about1.21mJ at19.112V; small stored energy is not a peak-current bound.

## What remains to close before implementing this architecture

1. **Primary-row applicability:** full-trajectory ramp/gate current and floating regulator voltage across the proposed feed range; temperature-defined effective CR/CF/CWD and all capacitor network maxima. The full SS/TMR and gate-charge transfer must replace the receiving timing reserves.
2. **A real independent shutdown circuit:** hard fault latch, actual absolute output/source windows, no chatter-petting, reset/rearm policy, loaded ISO/ON/B2B gate turnoff and propagation. Watchdog ENOUT release170–230ms is handled **before RUN**, followed by one accepted WDI falling edge. It is not hidden inside the20ms post-RUN reserve. A slow controller restart may cause a bounded fault; it cannot pause that deadline.
3. **Partial-power proof:** actual UV→bias switch deactivation, whole-path hot off-leakage, minimum effective VEE capacitor, reverse charged-load paths, every pin clamp and source-collapse slew. The simplified DC+20µs injection scenario is.23607V and has20% margin to.3V, but omits unbounded cross-rail/pin/capacitor injection and is not a complete pin-limit proof. No switch output may be exposed to a negative node merely because its positive supply is valid.
4. **Actual source/fault response:** normal cold diagnostics meet the0.9A25°C-only screen, but current-limit fault diagnostics exceed it on both rails. Source capacitance, raw collapse/recovery, loaded cutoff and initial peak/inductive energy are unknown. Therefore guaranteed fault energy is **null**;17.71/18.27J rectangular values cannot be used as guaranteed SOA inputs.
5. **Hot linear SOA and heat paths:** CSD19536KTT has a real DC SOA trace; no diagram at unspecified/higher case temperature proves this board. Its10V RDS row does not cover10V gate minus shunt drop.20mΩ hot,20mΩ bank/copper and package/case thermal bounds remain receiving requirements. New chip/bias/resistor/pass losses require actual placement, isolation, local and whole-system thermal analysis. No old P03/base result is inherited.
6. **Implementation:** real component suffixes/ratings, GN28 pin map, state logic, decoupling/loop layout, protection interfaces, native ERC/DRC/parity/connectivity, sense Kelvin routes, and all current/return/quiet-ground coupling. Optional independent sink driver is not yet an accepted solution. There is no single-fault-tolerance claim.

## Reproduce

Fresh native netlists were exported from the immutable db83 combined P03 schematic and current unchanged E28 schematic using KiCad10.0.7 **`--format kicadxml`**; capture logs and all15 bracket-checked originals are copied. An initial export with KiCad's default S-expression format was rejected by the XML parser and retained under `generated/history/netlist-default-sexpr/`; no result uses it. These exports establish node identity, not new-circuit ERC/PCB validation.

From the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python -m hardware.qualification.boards.startup_negative_protection.analyze
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python -m unittest hardware.qualification.boards.startup_negative_protection.test_nf02 -v
```

All15 tests exercise adverse capacitance, early watchdog, RF/CF, bias starvation, collapse timing/leakage/capacitance, shunt/drop budgets, native polarity, invalid parameters, real source-power recomposition and unsupported acceptance flags. They also verify original/copy/primary hashes. They are analytical checks, not synthetic physical qualification.
