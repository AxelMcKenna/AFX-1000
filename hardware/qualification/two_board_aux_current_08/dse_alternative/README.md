# Four DSE errors: package decision

The exact four failures are E_U900 pad pairs 1–2 and 2–3, and P_U902 pad pairs 1–2 and 2–3. Their TPS3703 DSE mixed-mask land pattern uses 0.25 mm mask openings with 0.05 mm copper overlap per side: 0.35 mm copper at 0.50 mm pitch gives 0.15 mm. The earlier vector audit of TI drawing 4220552/B is preserved and hash-bound. The selected project requires 0.20 mm. There is no rule waiver, package reinterpretation or PCB change in this record.

TI lists TPS3703 in DSE only; no pin-compatible larger package was found in the primary ordering table. Shrinking those lands or using all-NSMD geometry is not supported by the documented mixed-mask example and cannot be treated as a verified minimal change.

The concrete alternate is **TPS37042A3OFDDFRQ1**, a dual window supervisor in DDF0008A. Its manufacturer NSMD example uses 0.45 mm copper width at 0.65 mm pitch, meeting the existing nominal 0.20 mm rule exactly. This is a nominal layout result, not fabrication-tolerance qualification. Drawing 4222047/E appears on page 39 of the cached Q1 PDF (and page 36 of the catalog PDF, visually inspected). Maximum package height is 1.1 mm. The exact orderable is active on TI's primary part page; availability is not guaranteed.

It is **not a drop-in electrical replacement**. One dual part could monitor main AUX directly at its 3.3 V ±5% channel and the 5 V preregulator through a 0.24-ratio divider into its 1.2 V ±5% channel. VDD remains held 3.3 V, and the two active-low open-drain outputs join FAST_RESET_N. This requires an eight-pin layout, divider/input-loading analysis and rerouting of both former remote supervisors. Supply maximum is 15 µA versus 2×7 µA for the existing two supervisors. Reset release becomes 10 ms ±30%; startup remains typical-only and repeated-fault/recharge behavior must be reassessed.

The decisive difference is **10 µs maximum detection at 10% overdrive**, versus existing TPS3703's 30 µs maximum at 5% overdrive. Retaining the old conditional 100 mA, 4.7 Ω ±3%, 20 mV loss and 200 µF effective reservoir assumptions, an ideal unloaded divider gives a 4.23225 V overdrive endpoint and only 28.363 µs above the held-LDO 3.6 V input floor. After 10 µs detection and the still-unqualified 1 µs logic allocation, only 17.363 µs remains. Retaining a 50 µs driver allocation needs **430.132 µF effective**, even before actual divider error/loading and additional qualification. The installed 2×220 µF nominal parts cannot be assumed to deliver this. These are sensitivity calculations, not bounds on an unselected implementation.

TPS3702 in DDC would provide a 0.35 mm nominal land gap, but its 19/35 µs timing values are nominal only; reject it as a source-guaranteed shutdown substitute. TPS37's adjustable 17 µs maximum requires 20% overdrive, losing the existing reservoir headroom before its feed drop; it is not a minimal compatible substitution.

Decision: retain the DSE errors as unresolved while routing independent supplies. TPS37042A3OFDDFRQ1 is the concrete redesign candidate if the supervisor/reservoir/divider change is pursued; it is not authorized by this record as a qualified swap. Primary PDFs and calculation inputs are bound in `decision.json`; `verify.py` checks the exact errors and sensitivity arithmetic.

```
.venv/bin/python -m hardware.qualification.two_board_aux_current_08.dse_alternative.verify
```
