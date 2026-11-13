# Shared supply/reset branch cutover

`native-04` explicitly isolates eight existing pads from their old shared groups and assigns the nets already declared by the held-rail schematic:

- E_U31.6 becomes fast RESET, not held supply.
- E_U31.8, E_C76.1, E_U29.8 and E_C74.1 become held supply.
- P_U102.5/.8 and P_C102.1 become preregulated 5 V.

The complete obsolete branches require removal of 26 tracks and five vias. Ten tracks directly touch the changed pads; remaining old-net tails are traced and pruned back to retained junctions. The initial cuts left dangling tails and two new clearance conflicts. Three rejected stage reports and their exact plans are preserved compactly in `rejected-tail-evidence.json`; rejected complete PCBs remain local only. One geometrically overlapping In2 stub was explicitly removed after native DRC identified its dangling endpoint; geometric overlap alone was insufficient to infer a valid junction.

Two 0.25 mm B.Cu tracks reconnect E_U29.8 to C74.1 with a 1.683 mm total local route, fully referenced by the existing main In6 fill. U31/C76 and U102 input/enable surface-route screens found no accepted path within the stated bounded search. The remaining LDO input, RESET and wider held distribution are not complete.

Native verification permits only the eight declared pad isolations and the U29/C74 reconnection. All unrelated original groups, pads, copper and all 47 complete filled zones are unchanged. The 55 formerly anonymous pads retain their exact unique physical identities. Candidate opens rise 1957 → 1964 as obsolete shared connections are separated; the accepted PCB remains unchanged.

The final candidate has exactly the same four unwaived DSE clearance errors as its baseline, no added errors or warnings. All 3,476 netted schematic pin assignments now match PCB net names, with the exact union of board pin keys checked for the eight changes. This is logical pin assignment alignment, not complete physical connectivity or manufacturing qualification.

`verify.py` and four regression tests check the source hashes, exact pin deltas, missing pin rejection, RESET-versus-held identity, retained zones/rules and native evidence. `plan.py` reconstructs cut selection from source copper and declares pruning evidence. `routes.py` binds the local route to that cut plan.

The inherited electrical receiving conditions remain unresolved: ≥200 µF effective reservoir, ≤100 mA total drain, ≤20 mV distribution drop and ≤1 µs logic-delay allocation. The corresponding 81.00348 µs modeled hold interval and 50.00348 µs driver-turnoff allocation remain conditional. This cutover establishes neither actual current/timing bounds nor effective bypass capacitance, thermal behavior, startup safety or complete rail integrity.
