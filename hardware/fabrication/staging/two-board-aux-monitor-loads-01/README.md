# TBP50 monitor output loads and AUX voltage budget

The power monitor's internal reference supplies **0.651616 mA nominally**.
Across the stated resistor, reference-voltage, input-current and negative-rail
screening cases, its output current is **0.602288–0.707209 mA**. This is an
additional AUX-funded output load, separate from the earlier E_U7 reference
analysis and from the monitor's own quiescent current.

[Analysis](analysis.json) binds the current netlist, 11 newly covered resistors
and all 81 AUX IC supply pins across 29 part families.
[Independent verification](verification.json) checks 4,608 reference cases and
896 fast-overvoltage output cases against eliminated-node formulas, KCL and
power conservation. Maximum current disagreement is 5.18e-18 A.

## Power monitor reference

P_U25 (LTC2910HGN#PBF) drives P_R310–P_R315 from its internal reference at
pin 10. P_R310 is 590 Ω and feeds a shared bias node with a 1 kΩ ground
return. Two further branches reach the N19 and N12 source rails through their
sense dividers. Solving these together is necessary; they are not independent
full-reference-voltage loads.

The model uses reference 0.985–1.020 V, independently bounded ±3% resistors,
and ±30 nA receiving input-current allocations at pins 7 and 8. Negative-rail
cases cover 0, nominal −19/−12 V, and −30 V. The −30 V endpoints define a
chosen screening domain, not accepted installed fault-voltage bounds.
The modeled maximum leaves 0.292791 mA to the reference's ±1 mA table-load
condition. Other package pin currents, timer behavior and startup remain
separate; this is not a complete device-current bound.

## Fast-overvoltage comparator

P_U103 (TLV7011DBVR) drives P_R117 feedback and the P_R121/P_R120 gate branch.
P_R115/P_R116 also connect the feedback node to VIN_IC and ground. The five
resistors draw output current from −9.517 µA (the output must sink) to
+36.734 µA across the selected independent voltage/state cases. Negative
output current is not credited against the AUX budget. P_R118/P_R119's AUX
reference divider was already covered and is not added again.

The linear model flags **144 cases outside the comparator input operating
interval**, including low-inlet startup cases and some 30 V inlet cases.
These flags preclude treating the resistor-only result as a clamp-current or
fault-protection guarantee. Actual HIGH/LOW states, input protection, output
swing, MOSFET gate leakage and transient drive remain to be checked. P_U26's
output connects to P_U25 pin 5 without a resistor load; its receiver current
still belongs in the package/pin ledger.

## Source voltage and distribution allowance

The existing TPS7A1601 feedback network is P_R108 = 11.7 kΩ plus P_R130 =
49.9 Ω above P_R109 = 10 kΩ. Its nominal output is **2.594763 V**.
The [source-voltage screen](source-voltage-screen.json) includes overall ±2%
regulator accuracy and signed ±0.1 µA feedback current. Positive feedback
current flows out of the IC and lowers the required output voltage. It does
not add typical line/load-regulation terms a second time.

| Resistor assumption | Calculated source range | Margin above monitor's 2.3 V minimum |
| --- | --- | --- |
| Initial value-label tolerances only | 2.538955–2.650691 V | 238.955 mV |
| Proposed complete ±1% per resistor | 2.514502–2.676730 V | 214.502 mV |
| Blanket ±3% per resistor | 2.461705–2.736310 V | 161.705 mV |

The blanket 3% case exceeds the 2.7 V upper assumption used by the current
screens. A complete 1% feedback-resistor requirement keeps the steady-state
source inside that band and provides a conditional 214.5 mV allowance for
distribution loss before P_U25 reaches 2.3 V. Merely assuming a 2.3 V source
provides no such allowance. The 1% requirement still needs exact MPN,
temperature, aging and assembly acceptance; initial tolerance alone does not
prove it. Load/headroom and temperature conditions of regulator accuracy must
also hold. This calculation does not qualify startup, thermal behavior or the
unrouted supply/return paths.

All 96 source-voltage cases agree with a separate two-node KCL solution.
[Sign verification](source-voltage-verification.json) also rejects 96 cases
with the feedback-current sign reversed.

## Evidence and remaining work

[Primary review](primary-review.json) retains device-table conditions and
download limitations. Two TI PDFs were downloaded and three TI pages visually
inspected, including the existing regulator PDF. The official LTC2910 PDF was
read through the official web source; direct downloads failed and its page was
not visually inspected. The review records its source URL and extracted limits;
no local LTC2910 PDF or visual inspection is claimed.

The full IC inventory records supply pins and every connected pin, with no
unearned complete-current acceptance. Remaining work includes the per-package
and per-pin current limits, driver load/state behavior, the fast-OV fault cases,
source-resistor procurement, routed voltage-drop checks, startup and installed
thermal limits. No copper changed. Fabrication remains unreleased.
