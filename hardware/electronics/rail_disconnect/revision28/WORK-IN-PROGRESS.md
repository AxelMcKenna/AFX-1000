# E28 development checkpoints — not a fabrication release

The canonical PCB and every historical sealed packet remain unchanged. Work
below is isolated in named `generated/` candidates. No electrical, startup,
thermal, mechanical, fabrication or physical qualification is granted.

## Coherent routing checkpoint

`generated/c83-pg2-reconnected-work/rail_disconnect.kicad_pcb`

SHA-256: `1d245eb9cd4375dd4c2873a5903d321c6efecef3ce9602ed2fdcc696e812a3c4`

- Fresh KiCad10.0.7: **25 reported and independently uncapped opens, 168
  warnings, zero hard DRC errors, zero ERC violations, zero parity findings**.
- Both raw ignored-check lists are empty. All five formerly stock-ignored DRC
  categories and all four stock-ignored ERC categories are enabled.
- Input versus refilled track/via geometry, all six via diameters and net
  identities match. Raw reports and exact native components are retained in
  that candidate's `generated/`; see `snapshot-summary.json`.
- Analog output-health buffered, analog source-health raw, digital
  output-health raw, analog FOLLOW2 and digital PG2 raw paths are newly
  connected relative to the verified30-open checkpoint. Check exact native
  components before claiming a later source has no new net debt.
- Four actual U24 receiving escapes and explicit ordinary-control repairs were
  added. Unused ordinary islands were removed only from source-bound native
  components containing no actual package pad. Two separated control-ground
  islands were explicitly reattached with0.5mm tracks; this is real geometry,
  not a ground/noise qualification.
- A failed29-open attempt with four clearance errors is preserved separately
  in `u24-oc-joint-reconnect-work`. The successful successor removes only a
  newly generated50µm POS_OUTPUT_READY endpoint overshoot and its backtrack.
- Later explicit bypass repairs move C82+0.1mm X, C83+0.5mm X and rotate C84
  to local(62.8,52.4,270). C83 replaces one dedicated AUX barrel and its local
  supply/return geometry. Its initial native clearance/mask failures are
  preserved; a separate return-diagonal repair clears them. Actual AUX/GND
  continuity is checked, but supply/impedance/mechanical passes are not inherited.

Board datum remains `[8,108.5,5]`mm; outline156×54.5mm. J4 source positive is
world(161,120.5), ground(161,129.5). The old fed/EI02 ground(161,126.5) harness
proof does not apply. No direct-J8 return attachment or NF-module topology is
adopted here.

## Active repairs and rejected trials

`middle-input-local-escapes-work` added actual U38.6 and U39.6 receiving barrels
at local(67.075,50.625) and(112.05,50.875), with14 declared ordinary fragments
withdrawn. Its intermediate native result is36 opens/178 warnings and zero
hard/ERC/parity findings, all checks enabled. Its debts were restored in later
successors; that intermediate must not replace the coherent source.
`pg-receiving-pad-escapes-work` is a further active PG-pad repair; restoration
and fresh native checks are required before adopting it.

U40.6 and U41.6 failed an optimistic fixed-pad/via-only0.025mm-grid screen
within5mm; all tracks had been omitted for that necessary-condition screen.
This is bounded evidence, not a global impossibility theorem. Their common
0.55mm bypass-pad gap cannot pass a0.2mm trace with0.2mm clearance on both
sides. U38/U39 have possible under-body escapes, so the gap alone does not
prove those pins trapped. C83's explicit supply repair resolves U40.6; the
separate joint C84/ANA receiving proposal is still under development.

The whole-U39 relocation trial is rejected:49 opens, only seven of eight
buffer pins escaped, and an unproved approximately16mm bypass-return loop.
Its actual raw evidence remains in `schmitt-u39-joint-ordered-escapes-work`.

## Finite-copper diagnostics have an exact, older source

Completed0.1/0.05mm-grid diagnostics belong only to
`coherent-follow2-c84-corrected-work/generated/filled-coherent-follow2-c84-corrected.kicad_pcb`
(SHA-256`d6cdd23869171e4ed050892f4fe395cd568ef835319602c0995185c4ad36c36e`;
editable26-open PCB`fd4b1055fa75be07aead5be006062739e5b3a1d5cdc7cd6ac7b2dad9fb752efa`).
At0.05mm: analog copper plus unequal-chip penalty2.939440mΩ;
digital2.485971mΩ; PCB-only J4.2→J8.1 return1.834737mΩ. The open-circuit
analog-terminal transfer is−0.932662…−0.915219mΩ. Negative PCB path totals
are42.175479mΩ(N12) and207.171374mΩ(N19), excluding MOSFET/contact loss.
The0.1mm analog estimate2.978986mΩ versus0.05mm2.939440mΩ has39.55µΩ
spread; the remaining60.56µΩ below3mΩ is not a certified margin.

These are diagnostic estimates, **not upper bounds**. The model assumes70µm
on every copper layer,85°C copper and25µm barrel wall, with actual native pad
polygons and distributed barrel sectors. Material/process/contact bounds are
unaccepted. Both real bars plus the P03 regulator/reference multiport return
network, dynamic loads and assembled measurements remain required. Do not
carry these values onto the25-open or later routing sources.

## Reproduction and remaining release holds

Run the explicit candidate through `native_candidate_snapshot.py` using the
KiCad-bundled Python and the recorded KiCad10.0.7 environment. It checks a
scratch copy, exports all raw findings, independently counts uncapped native
airwires, verifies track/via identity and exports actual pad polygons.
`native_closed` also requires zero warnings and empty ignored lists for both
ERC and DRC; no current candidate meets it.

All67 E28 regression tests pass, including transient net-ID and native
track-versus-pad net-clause regression cases. Live code passes Ruff excluding `generated/`;
frozen evidence recipes retain their original bytes. Exact27 pre-format
producer/helper copies and old/current hashes are indexed in
`generated/repair-executed-recipes/continuation-20261029/index.json`. Historical
byte replay is not claimed without isolated re-execution.

Still unresolved: all opens/warnings, complete actual part/land-pattern and
assembly approval (including retained quad-logic lands), finished stackup and
filled/capped process acceptance, AUX partition/partial power, loaded signal
edges, fail-off/source/OV/UV sequencing, bipolar and first-master full-bulk
inrush/SOA, hot gate bias, complete finite distribution/PDN, assembled thermal
and fault measurements. Native via metadata is not proof of filled/capped
manufacture. Protected bulk stays protected; no upstream-bulk relocation or
late-closure inrush exemption has been adopted.
