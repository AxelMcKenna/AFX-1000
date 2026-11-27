# ADC control routing checkpoint r83

Adds three short front-layer joins: one THRESH_UPPER and two PD_GATED connections. Total opens reduce 190 → 187. All r82 authored objects and native groups are retained; only declared ADC control groups merge. No vias, zones, footprints, or original copper are modified. Existing DAC connectivity and its missing ESS/analog qualification limitations remain explicit.

Planning checks actual In1 reference fields and original source-derived sensitive openings. The selected control nets are explicitly outside the FDA sensitive summing/output nets. No raw ADC force/sense, high-impedance reference divider or pump-loop route is approved through this checkpoint. ADC source documents and their unresolved analog constraints are bound in the manifest.

The native geometry/ERC/parity checks and independent connectivity capture are followed by full new/retained reference, transition identity, local-return, drill and raw-fill fidelity audits. The exact added six-segment inventory and per-route lengths appear in replacement-audit-r83.json. The diagram is a view of captured native geometry, not an independent acceptance test.

Portable verification: `python -m hardware.cad.two_board_sensor_05.signal_dac.verify_portable_r83 --reference --regressions`. Root integration must refresh selected-board mechanical identity before selection. This checkpoint is not fabrication or analog-performance approval.
