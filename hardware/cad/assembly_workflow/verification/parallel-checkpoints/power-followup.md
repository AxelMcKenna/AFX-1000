# Isolated power follow-up

Root reproduced the local-bypass verifier and ten regression tests, the reference-text correction verifier and five regressions, and the DSE alternative source/calculation verifier. Logs are retained here. Selected power remains TBP73; no candidate is promoted.

The original local-bypass candidate mistakenly used global coordinates in a footprint-local reference-text field. The reference-fix candidate changes only C907 reference position to local (3,-2.4), producing native global (184.5,129) with complete text bounds inside the board. Native parity is zero; the original four DSE clearance errors remain unwaived. Original failed placement evidence is preserved.

TPS37042A3OFDDFRQ1 is a concrete wider-pitch alternative, but it requires a divider and reservoir redesign. The conditional ideal-divider calculation requires at least 430.13 microfarads effective reservoir capacitance for the examined 50 microsecond driver interval; actual accuracy, loading and logic delay still need qualification. No component substitution or clearance-rule change is authorized by this analysis.

Full mechanical promotion must account for 19 added components and the E_C13 move, plus explicit validation of serialized footprint/property differences. Local bypass capacitance under bias, remote feed impedance, IN/EN routes, analog/thermal behavior and physical fit remain open.
