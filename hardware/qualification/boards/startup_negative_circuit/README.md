# Negative rail startup development

No revision here is a qualified or fabrication-ready board. The latest circuit
work is [NF05R UV recovery](uv_recovery/), a sealed265-part successor implementing an
independent AUX undervoltage path into the retained-ARM fault logic and separate
resistive paths for both clamp LEDs. Its13 independent tests pass; root verified
all90 sealed files before and after that run. Loaded cutoff time, hot optical
behavior and shared E28 fault-latch timing remain unqualified. The new
[NF06P physical layout](physical_layout/README.md) represents that circuit:
265 electrical components and two mounting holes on six layers. Its current
receiving-repair routing candidate has zero native geometry/parity findings
and **204 missing connections**. Routing, whole-unit fit, PDN and physical
qualification remain incomplete. Older physical studies represent older circuits.

| Record | What it establishes | Remaining boundary |
| --- | --- | --- |
| [NF03C](compact/README.md) | Sealed231-part circuit;15 checks; original four TPS3890 monitors correctly wired | Original current, package and timing assumptions require later corrections |
| [NF03P placement](placement/README.md) | Actual231-part placement and exploratory routing | No accepted routed NF board; old rear-envelope assumption superseded by FR01 receiving limits |
| [NF04R READY](ready_integration/README.md) |233-part final-output-valid interface | Loaded HIGH margin, external ARM/START and physical PCB adoption unresolved |
| [NF05S249](standalone_sequence/) | Hardware standalone sequence checkpoint | Rejected pin maps on its two new START timers; original four monitors were correct |
| [NF05H261](absolute_aux_gate/README.md) | Corrected seven supervisor maps, independent RAW5-powered AUX cutoff and split module-primary return | Automatic UV recovery and floating LED MID charge paths require the NF05R successor; no PCB |
| [NP01 passive review](../nf_passive_selection/README.md) |196 catalog candidates and actual historical land comparisons | Complete±0.1% assumptions fail; selected parts, drift, power and new lands need explicit adoption |

The NF05H native circuit has zero ERC errors, two unchanged isolated-secondary
ground warnings and exact declared pin/value parity. Its12 tests pass in the
independent Python3.12 run. NP01's independent run exposed two exact binary
floating-point comparisons that fail across interpreters; the sealed inputs and
failure log are retained in the
[independent review](../../../cad/a12/qualification_reviews/nf05h_np01/initial-python312-regression.json).
The separate [NP01-P1 portable verifier](../nf_passive_selection_portable/README.md)
passes23 tests under both Python3.9 and3.12. Only five-term computed totals with
identical summands allow up to four ULP of rounding difference against an exact
rational reference. Inputs, geometry, hashes and qualification flags remain
exact. The two old strict failures and original seal are preserved.

The 149×39mm NF06P allocation now includes revised passive lands, a selected
control connector, separate primary supply return, force pigtail ports, strain
supports and all-layer mount keepouts. Their final routed/assembled integration
still requires validation. No older routing,
whole-unit MCAD, PDN or airflow result is automatically inherited. Startup,
partial power, loaded cutoff, fault current/energy/SOA, module warmup, shared
returns, installed temperatures and physical tests remain open.
