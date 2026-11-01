# NF01 — negative startup architecture comparison

**The strongest next candidate is LTC4252A-1 with its native SS current profile and a separate, higher fault limit. It is not ready for another schematic.** A fixed shunt alone cannot meet the −12 V full-live-load/220 mA comparison window. LT4250 is outside its operating range on −12 V. LM5067's 100 mΩ maximum shunt remains binding. SC02 stays sealed and unchanged; this study creates no circuit, PCB, operating-net or mechanical change.

The 150/220 mA startup ceilings and five-second comparison are provisional planning allocations, **not user-approved hard requirements**. [Machine-readable calculations](comparison.json) preserve those distinctions, exact primary references and null guarantees. All startup, SOA, physical and implementation flags remain false.

## Inputs and manufacturer constraints

The frozen planning source is copied from SC02, preserving its historical source hashes. N19 has 1.8 mF of local bulk including initial +20%, a 19.112 V derived output maximum and 26.419 mA of declared full external load plus native bleed. N12 has 264 µF, 12.071 V and 151.265 mA. A separate **unverified 0.550 mA** output-leakage/influence allowance makes the conservative current screens 26.969/151.815 mA. Full downstream capacitance, hot/aged load behavior and actual simultaneous source capacity remain unverified. The load is present from zero; it is not silently gated until power good. The mathematical charge model clamps output at zero until the controlled current exceeds the load; actual low-voltage compliance/crossrail injection and clamp dissipation need a real circuit model.

| Controller | Actual primary constraints | Result here |
|---|---|---|
| [LM5067 Rev D](https://www.ti.com/lit/ds/symlink/lm5067.pdf), §7.3/§9.2.2.2 | At least 2 mA into VCC recommended; RS ≤100 mΩ. Current-limit table 44…56 mV. | Largest legal shunt still gives at least 440 mA current limit. To cap its upper current at 150/220 mA would need at least 373/255 mΩ before tolerances, violating the explicit rule. SC02's separate Miller ramp has already exposed supply/injection/turnoff failures. |
| [LT4250L/H 4250lhfa](https://www.analog.com/media/en/technical-documentation/data-sheets/4250lhfa.pdf), p3/p5/p8–9 | Supply 18…80 V; 40…60 mV limit; 500 µs circuit-breaker timing only typical. Native drain-feedback ramp requires anti-injection capacitor. | −12 V local supply rejected. N19 is within range at the declared 18.9 V minimum allocation, but the native ramp still creates substantial gate-charge and hard-off obligations. |
| [LTC4252A 425212fe](https://www.analog.com/media/en/technical-documentation/data-sheets/425212fe.pdf), p3–4/p14/p19 | Rising VIN UVLO max 10 V; VCB 45…55 mV; VACL/VCB 1.05…1.38. Native SS and gate anti-injection. Timing/SS dynamic coefficients mostly typical only. | Best architectural direction. −12 V headroom is plausible but low-VIN current/gate-drive conditions need confirmation. Fixed-ACL N12 window fails; native SS can separate normal startup from higher fault current. |

For the two ADI parts, no numeric hard maximum shunt was found in the reviewed datasheets. That is **not unlimited approval**. LTC4252A p19 Eq8 explicitly derives RS from minimum circuit-breaker threshold and load; LT4250 p9 gives an inrush formula using RS. The comparison therefore explores larger values using those instructions, without importing or waiving LM5067's separate 100 mΩ restriction. Exact resistor MPN, lifetime/TCR/Kelvin/pulse bounds and manufacturer confirmation remain selection work. The ±4% shunt interval below is a sensitivity allocation, not a selected part guarantee.

## Why fixed current limiting fails on N12

LTC4252A's guaranteed table threshold/ratio enclosure gives VACL = **47.25…75.9 mV**. The p19 application text separately says 54…66 mV. Both are recorded; this study does not silently replace the table product with the narrower prose range.

To keep N12's settled 151.815 mA below the lowest CB threshold requires **RS,max <45 mV/151.815 mA =296.41 mΩ**. To cap its highest ACL current at 220 mA requires **RS,min ≥75.9 mV/220 mA =345 mΩ**. There is no overlap even with a perfect resistor. With ±4%, the nominal bounds become ≥359.38 mΩ and <285.01 mΩ. Even the narrower 66 mV prose upper value needs 300 mΩ before tolerances and still fails the steady-load CB inequality.

The smallest compatible fixed-ACL ceiling would exceed **277.40 mA** with the ±4% scenario, before controller/divider/PG overhead or useful CB margin. A 274 mΩ example leaves ~6.10 mA steady CB margin, but its ACL upper screen is **288.55 mA**. Revising the current budget would require a real P03 hot-source/transient/thermal study; this is not an adopted increase.

N19 has a nonempty fixed-shunt interval. A 560 mΩ example gives ACL ~81.13…141.18 mA and CB minimum ~77.27 mA. With the full constant load, charging the local bulk at minimum ACL takes **~0.635 s**, not the capacitor-only time. It deposits ~0.492 J in the FET, including ~0.164 J from the live load.

The shared LTC4252A TIMER makes fixed-ACL startup expensive in delay. In that N19 example, integrating the **typical** 230 µA plus 8×drain-current acceleration over an ideal linear VDS ramp needs ~42.24 µF simply to avoid a typical timeout; that same capacitance gives **~29.13 s typical initial delay** through the 5.8 µA initial-charge source. These are sensitivity results, not capacitor selections. The p20 example's 1.5 multiplier is design guidance, not guaranteed timing corners. The five-second comparison disfavors this approach but is not being promoted to a hard project rejection criterion.

## Promising separation: native SS with a higher fault threshold

Use the **LTC4252A-1 native SS pin**, a shunt around **180 mΩ**, proper native compensation, and independently validated source/fault protection. This avoids SC02's added drain-Miller capacitor and its giant gate-source anti-injection capacitor. The ±4% shunt comparison gives minimum CB **240.38 mA**, above both normal-start ceilings; eventual ACL can reach **439.24 mA**, and the fast-comparator threshold can reach **1.736 A** before any unbounded dynamic overshoot. Normal startup and fault current are deliberately separate budgets.

The manufacturer's nominal SS model is VSS(t)≈1.4·(1−exp(−t/(50 kΩ·CSS))) and VACL(t)≈VSS(t)/20−10 mV. Integrating **current above the complete constant load**, instead of treating all SS current as capacitor charge, gives:

| Typical coefficients only | N19 | N12 |
|---|---:|---:|
| Minimum CSS from the ideal profile at the provisional current ceiling | 20.07 µF | 3.681 µF |
| Output charging begins after reaching full live current | 0.239 s | 0.140 s |
| Output charged, current at 150/220 mA ceiling | 0.755 s | 0.227 s |
| Including typical 330 nF initial TIMER delay | 0.982 s | 0.455 s |
| Startup into a short: time before typical CB activation | 1.953 s | 0.358 s |
| Pass energy into that short **before CB starts timing** | 6.13 J | 0.710 J |

These CSS values are **not selected parts**. The table's SS source current, RSS, scale factor and offset have no guaranteed min/max bounds; the real response is not a tolerance-bounded exponential. Nevertheless, this is an actual manufacturer architecture with plausible nominal timing and full load, rather than another known-failing mirrored gate-ramp schematic.

The short-circuit rows expose the cost of slow native SS. Current below CB does not start the fault timer; extra SS duration can overrun SOA before TIMER helps. The datasheet expressly warns about this. A suitable CSD19536KTT might cover the bounded current if its case temperature and actual waveform are controlled, or an independent guaranteed startup watchdog/hard-off might be needed. Neither is established. Do not disable or clamp SS below CB indefinitely without an independently safe continuous-fault path.

## Local bias, input steps and hard-off

**N12 supply:** a 499 Ω ±1% feed and an assumed 2 mA load at 11.9 V leave VIN−VEE≈10.892 V, ~0.892 V above the LTC4252A's 10 V maximum rising UVLO threshold. At the *catalogue 25 °C* 24.4 V TVS clamp and 11.5 V low zener, that resistor would conduct ~26.11 mA, below the documented 30 mA continuous input-current allowance subject to die heat. This gives a more coherent headroom/transient screen than an arbitrary tiny feed resistor. It does **not** establish actual low-voltage operation: the 2 mA maximum supply-current test is at VIN=VZ−0.3 V, and the 10 V minimum gate-drive test is at IIN=2 mA. A high-zener unit remains unregulated on a 12 V local feed. Actual supply current and gate drive over the proposed 10.9…12.1 V VIN interval need vendor bounds. No positive-rail phantom feed or extra AUX supply is introduced.

For N19, a 2 kΩ ±1% comparison gives at least ~2.18 mA at 18.9 V with the 14.5 V high zener, and ~3.84 mA at the normal 19.112 V/11.5 V low-zener corner. A 38.9 V catalogue TVS clamp would give ~13.84 mA. Those input currents, dividers, PG drive and isolation loads must be added to P03's source ledger; controller overhead is not included in the capacitor/live-load currents above. The catalogue clamps are only specified pulse points, not the system's actual temperature/source/inductance envelope.

LTC4252A's native gate circuit is explicitly designed to suppress initial CGD feedthrough before usable VIN. Its compensation still needs to be selected from the actual MOSFET CISS and verified on the board; a ≥10 nF starting recommendation is not proof for every CSD/input-step combination. Input feed/VIN protection, fast-current overshoot, source inductance, clamp/snubber energy and brownout must be bounded. The small compensation capacitor avoids the added multi-second gate-charge problem, but the 17/190 mA sink and ~0.4 µs UV/OV delays are **typical**, not guaranteed hard-off limits.

The [CSD19536KTT Rev C](https://www.ti.com/lit/ds/symlink/csd19536ktt.pdf) remains a candidate only. Its 100 V VDS and ±20 V VGS ratings do not establish clamped input steps or hot SOA. The normal/fault ACL upper screen below 0.44 A is promising against the previously conservative 50 V/DC/case100 °C 1 A graph reference; the 1.736 A fast threshold, unknown peak/duration, pre-CB energy and actual case-to-base path remain unresolved. Gate-drive conditions must support the chosen RDS specification. No MOSFET pass follows from these calculations.

The [TLP170GM Rev3.0.A](https://toshiba.semicon-storage.com/info/TLP170GM_datasheet_en_20230522.pdf?did=69102&prodName=TLP170GM) can remain a **UV-divider control candidate**, not a load-current switch. Its 1 ms maximum turnoff is a 25 °C test at IF=2 mA, VDD=20 V and RL=200 Ω; that does not establish a hot fast-fault isolation time in this divider. Recompute divider values for LTC4252A's actual UV/OV thresholds. Keep HOST3V3 and the unresolved SC01/SC02 enable-level interface explicit; no 2.5 V status-to-3 V enable compatibility is assumed.

Put any new limiter after the retained B2B bank with **all protected bulk downstream**, or independently prove the bank ON before allowing an upstream ramp. Either choice still needs actual charged-load and partial-power analysis. A single N-FET's SENSE→drain body diode permits a charged negative output to energize the after-bank input node; opening an upstream B2B bank does not instantly discharge downstream bulk. LTC4252A UV resets TIMER/SS and starts a new insertion cycle on release; OV does not reset TIMER or latched PWRGD after startup. PWRGD is a latched switch-completion indication, not independent absolute output validity. These states, host-reset races, source collapse, opposite-polarity injection and real discharge time remain requirements, not assumed successes.

## Decision before another schematic

Proceed only with a bounded native-SS architecture study after obtaining:

1. ADI's low-VIN operating-current/gate-drive bounds for a −12 V local feed, plus maximum shunt/use constraints for these low-current examples.
2. Guaranteed or otherwise approved production bounds for SS current/RSS/gain/offset, timer currents/thresholds/acceleration, and gate sink/delay. Resolve the p3 ratio versus p19 absolute-ACL text. A typical simulation or the 1.5 timing multiplier cannot supply those guarantees.
3. A complete live-load/capacitance contract and actual P03 simultaneous startup/fault current, hot capacity, rail sag and input-step envelope. If fixed-ACL N12 is retained, independently approve the larger current budget first.
4. A source-bound CSD fault waveform/SOA/thermal path including the pre-CB interval, actual hard-off bank behavior, clamps and charged-load/reset states. Add an independent watchdog only as an explicitly designed protection, not an assumed one.

No additional native draft is justified by this comparison alone. Five seconds remains a comparison target. The current result is **a plausible native-SS direction with concrete specification holds**, not a fully validated negative startup circuit.

Reproduce with `python3 -m hardware.qualification.boards.startup_negative_feasibility.compare`, then `python3 -m hardware.qualification.boards.startup_negative_feasibility.seal` and `python3 -S -m unittest hardware.qualification.boards.startup_negative_feasibility.test_comparison`. Primary observations are identified by document revision/page in `comparison.json`; direct ADI PDF downloads timed out, so no invented local PDF hash or redistributed model is supplied.
