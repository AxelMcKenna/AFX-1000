# ADC monitor/control routing checkpoint r89

Adds ten ADC monitor/control joins relative to r83, reducing native opens 187 → 177. THRESH_LOWER, THRESH_UPPER and BIAS_SHIFT_L become connected; BIAS_SHIFT_R retains one join. All r83 authored objects and native groups remain intact. No existing copper is removed and no footprint moves. The added inventory contains 18 route pieces, eight signal vias, two ground vias and nine physical In4/In6 ground corridors.

Signals use front/back and In3 copper. In3 has adjacent physical In4 reference; back routes have In6. Every new and retained transition requires exact UUID/net/position/native group, direct main-ground field contact and a continuous ≤2.5 mm local return on In1/In4/In6. Neither field tolerance nor source-derived low-capacitance policy changes.

Failed r85 could not verify one threshold return. A physical-ground-via repair in r87 proved that return but exposed three new-route reference gaps; all original retained routes still passed. r89 instead joins the back-side threshold route to its other same-net via, eliminating the redundant transition and its failed bridge entirely. A small BIAS_SHIFT_R detour removes the remaining local uncovered sliver. Failed source captures/reviews remain in the provenance closure; no failed candidate is selected.

The source for the implemented monitor is E12-R2: revision2/README.md, integration.json and components.json are explicitly bound. Older E12 documents in history describe the pre-repair design. R2 implements monitors and revised divider/servo values; real threshold accuracy, dynamic shutdown, partial-power behavior and coupled-loop stability remain unqualified. This routing does not touch FDA summing/output, raw converter force/sense, reference-divider or pump-current nets.

Exact native additions, all retained native groups and per-route lengths/nearest foreign-copper context appear in replacement-audit-r89.json. Native geometry/ERC/parity, independent connectivity, full new/retained reference, transition identity, local returns, raw fill fidelity and drill checks are mandatory. Geometry does not establish analog performance.

Portable verification: `python -m hardware.cad.two_board_sensor_05.signal_dac.verify_portable_r89 --reference --regressions`. Root integration must refresh selected-board mechanical identity. Missing ESS, 177 other connections, physical/analog qualification and fabrication release remain unresolved.
