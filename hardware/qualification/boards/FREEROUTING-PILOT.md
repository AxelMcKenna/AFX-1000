# Isolated routing pilot

The routing experiment uses the official Freerouting 2.5.0 Java release with a
Temurin 25 runtime. It operates on copied projects in `/private/tmp`; it has not
promoted a board or approved fabrication. The macOS native executable failed
while serializing supported board objects. Removing real obstacles to work around
that failure is not an accepted routing method; the Java release is the fallback.

`freerouting_bridge.py` runs with KiCad 10.0.7's bundled Python/`pcbnew`. Export
captures the source project, checks its hashes, and locks every existing track
and via. The exporter gives SMD-to-SMD clearance a 50 µm special rule. The bridge
raises that rule to 200 µm for this E28 experiment. It does not reduce any rule.
The DSN filename binds its namespace to the captured project and selected
clearance. Import rejects a session from another namespace, changed component
identities/poses, or missing/changed original copper. Via dimensions are compared
on all six copper layers, together with drill size. Original lock states are
restored after import; new copper remains editable.

The no-routing baseline receipt is
`hardware/validation/board-qualification/generated/freerouting/6abc6ff1ed0c6720105ee13e/summary.json`.
Its frozen source is the already refilled 47-open E28 baseline beginning
`eabfb1731930`, not a claim about the changing canonical board. It descends from
checkpoint `4d9e8cc876fb`; those file hashes must not be interchanged. All 23,286 original tracks/vias and all
component poses survived the native DSN/SES roundtrip unchanged. A session from a
different namespace was rejected. After native KiCad refill and schematic-parity
checking, the copied board retained zero hard DRC findings, zero parity findings,
zero ERC findings, 47 unconnected items and 70 DRC warnings. The archive contains
the source, imported project, original locked board, DSN, SES, commands and reports.
`import.json` hashes the pre-refill board; `summary.json` separately identifies
the post-refill board. Both export-time and import-time bridge versions are saved.

Freerouting's interpretation is not equivalent to native KiCad connectivity or
filled copper. In particular, overlapping unfilled plane outlines and fixed
existing geometry produce hundreds of Freerouting conflict reports even for the
unchanged baseline with zero native hard DRC findings. Those reports are not
evidence that the physical source board has hundreds of shorts. Its unrouted
counts also cannot replace KiCad's unconnected-item count.

The all-locked routing trial was intentionally stopped after seven passes because
the confirmed signal cages require movement of existing objects. Its router scores
oscillated; no routed candidate was accepted. This was a change of routing
strategy, not a restart after an observation timeout. A separate
selective-routing trial permits movement of 18,042 nonforce legacy signal objects
while retaining 5,244 protected objects. Its explicit contract is E28's
`generated/freerouting-47-lock-contract.json`, bound to the original
`4d9e8cc876fb` checkpoint. The bridge's `--lock-contract` option verifies the source
hash and exact UUID partition and rejects loss of protected copper on import.
Independent full-footprint and zone checks from that contract are still required;
the bridge's part-pose comparison alone does not establish them. Force paths,
thermal vias, local converter loops, sensitive return paths and deliberate
component escapes need their own preservation rules.

Even with fanout, autorouting and optimization disabled, the selective trial's
SES normalizes movable tracks: the import contains 23,121 objects instead of
23,286. The strict unchanged-roundtrip check correctly rejects it. The protected
5,244 objects and component poses survive, but native KiCad reports 51 opens
instead of 47 after refill, with zero parity errors and 71 warnings. That
selective baseline is rejected. The actual two-pass routing experiment must
recover those connections and advance the original source before any promotion
can be considered; tool completion by itself is insufficient.

That first selective two-pass experiment finished and was rejected. It has 42
native opens, zero ERC/parity findings, 100 hard DRC findings (79 undersized tracks,
21 board-edge clearances) and 63 warnings. Native footprint/pad/zone/outline/setup
contracts and the 5,244 protected objects survived, but native polygon subtraction
found 194.1862 mm² of removed force copper. Its source, SES, candidate, native
reports and rejected receipt are retained in
`generated/freerouting/rejected-routed-5266a065b40f35668fa70a45/` under board validation.
It has not replaced the canonical 46-open source.

The next export adds actual filled force copper as DSN keepouts. The optional
`--force-filled-board` path requires matching complete native board contracts and
identical original routed copper, and checks that all force objects are locked.
`freerouting_force.py` unions each force net/layer's native filled polygons,
preserves their real hole windows, converts nm to µm with inverted Y, and checks
emitted outline-minus-hole areas against the native union. The initial packet
contains 24 keepouts and 488 windows covering 4194.2795 mm² across the layers.
AGND pours remain withdrawable. These are routing-only obstacles; no new keepout
is written into the operating PCB. Place them after layer declarations in DSN:
the first placement before declarations failed parsing and was retained as a
failed scratch attempt, then corrected.

The unexpanded outlines also triggered Freerouting division/projection warnings
on near-touching contours at its coarser coordinate resolution. That parser
attempt was intentionally stopped and is not an accepted obstacle representation.
The third scratch export expands routing-only obstacles by 1 µm using native
rounded offsets with 10 nm maximum approximation error. Independent native
subtraction verifies zero uncovered source copper on every net/layer. Emitted
outline/window areas are then checked against the expanded native shapes. This
conservative representation has 21 keepouts and 491 windows, and its no-routing
parser/import check completes without those decomposition warnings while
preserving all 5,244 protected objects. The actual PCB copper is unchanged.
The guarded two-pass routing result remains subject to the full native and
conductor checks; the obstacle expansion itself grants no acceptance.

The guarded trial also explicitly disables automatic/optional neckdown, requests
500 µm board-edge and 200 µm hole clearance, and enables strict new-route DRC.
The relevant native width minimum remains 200 µm. Existing Freerouting conflict
counts include fixed power items overlapping routing-only force obstacles; only
native checks and independent filled-copper comparison can establish acceptance.

The guarded two-pass result is now terminal and rejected: serial native checks
find zero hard DRC, ERC or parity findings, 70 warnings and 48 opens versus the
47-open original. Full native contracts and protected objects survive, but
0.0510352 mm² of force material is removed above native clipping controls. The
strict settings eliminated the first trial's 100 hard width/edge errors; they
did not establish useful native routing progress. The initial native check
overlapped the import process and was discarded. The accepted execution record
for this rejected candidate explicitly starts after import completion and binds
the settled input/output PCB hashes.

A further append-only diagnostic retained all 23,286 original objects and added
934 router-derived objects. Independent comparison confirms every original
object survives. Nevertheless **all per-net open counts remain unchanged**, 47
opens before and after; the additions also create 165 overlapping-hole warnings
from redundant rounded via geometry. This diagnostic is rejected without further
conductor qualification. It explains why the router's internal 533-to-281 count
cannot be used as evidence that native airwires closed. More blind routing passes
on this representation are not justified; endpoint/placement repair is needed.
The helper, native reports, rejected candidate projects and comparison receipts
are archived under `rejected-guarded-routed-82e3bf9a7f8043156b025ec9/` and
`rejected-append-guarded/` in the same board-validation routing evidence directory.

Every routed candidate still needs native refill, full DRC/ERC/parity and
connectivity checks, followed by actual filled-copper force/return-network
comparison. A route that closes an airwire by cutting a supply plane can fail
the voltage-drop allocation while passing native clearance checks. Mechanical
source binding and relevant thermal checks must then be renewed. None of the
bridge receipts proves those gates or physical board behavior.

Tool sources: [Freerouting 2.5.0 release](https://github.com/freerouting/freerouting/releases/tag/v2.5.0)
and [official command-line documentation](https://github.com/freerouting/freerouting/blob/v2.5.0/docs/command_line_arguments.md).
Downloaded tool binaries remain outside the repository; hashes are in the receipt.
