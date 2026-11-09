# SERIAL_1 receiving-area review

The receiving-area trials did not produce a complete candidate. The latest
native-checked comparison remains the [source-preparation checkpoint](../digital-serial1-source-preparation-native-01/README.md):
31 opens, zero native geometry/parity/ERC findings, and all previous pad groups
preserved. It prepares the source escape but does not close SERIAL_1. The
selected four-layer DC04 remains unchanged at 143 opens.

## Evidence and limits

Moving R3015 by 0.25 mm to (75.25, 21) permits both DATA branches in the local
screen. Fresh receiving escapes were sampled at 0.025 mm spacing. The discrete
packing search found 292 spatially distinct local arrangements; 32 were
independently replayed, spanning ten SERIAL_1 exit bins. Local compatibility
does not establish complete net restoration.

The combined searches retain all five obligations: SERIAL_1, CLOCK, LED48,
LED50, and CONTROL30. The table counts attempted packs; a last attempt may be
cut short by the route budget. It does not count every pack as fully explored.

| Terminal search or diagnostic | Attempted packs |
| --- | ---: |
| [digital-serial1-data-placement-first-02](../digital-serial1-data-placement-first-02/diagnosis.json) | — |
| [digital-serial1-combined-restoration-02](../digital-serial1-combined-restoration-02/construction.json) | 3 |
| [digital-serial1-shifted-target-escape-01](../digital-serial1-shifted-target-escape-01/diagnosis.json) | — |
| [digital-serial1-shifted-target-pack-01](../digital-serial1-shifted-target-pack-01/diagnosis.json) | — |
| [digital-serial1-combined-restoration-03](../digital-serial1-combined-restoration-03/construction.json) | 19 |
| [digital-serial1-receiving-topology-01](../digital-serial1-receiving-topology-01/diagnosis.json) | — |
| [digital-serial1-combined-restoration-04](../digital-serial1-combined-restoration-04/construction.json) | 10 |
| [digital-serial1-combined-restoration-05](../digital-serial1-combined-restoration-05/construction.json) | 17 |

Independent topology replay of the first two resampled packs found an actual
loss of free-space connectivity after routing SERIAL_1 or LED48. Removing the
opposing global route restored access; removing only the global CLOCK route
did not. The local CLOCK escape remained in that diagnostic. This is evidence
about those specific proposals, not proof that the board is unroutable.

The alternate-departure search restricted the LED48 starting-via graph edge
to test other layer paths. This removes a planner option only; it does not
remove actual copper or relax rules. A separate bounded search targeted the
17 local packs with CLOCK's via farther left (x < 72.9 mm), which the earlier 32-pack
sample had missed. Neither search emitted a complete candidate.

The first resampled SERIAL_1 proposal was approximately 338 mm long. Its
electrical suitability was not established, and no such route was adopted.
No conclusion about global infeasibility follows from these bounded searches.

## Verification and unit status

[All 42 focused tests pass](focused-tests.log), including four tests for
independent trial reservations. Captured copper and its spatial indexes are
shared read-only; proposed tracks, vias and cache dictionaries are separate
between trials. [Recursive source verification](source-audit.json) records
the exact source bindings and discloses the two unchanged historical NF test
hash mismatches. All 213 current unit-source bindings match.

The source-preparation checkpoint lengthens MCU_PERMIT by about 24.7 mm and
adds one via; that trade-off remains electrically unqualified. Audio still
has 208 opens and the approved ESS footprint hold; NF has 138 opens and two
isolated-ground ERC warnings. Stack/process, receiving, installed-unit and
first-article electrical, thermal and EMC qualification remain unfinished.

The next layout work must preserve a complete LED48 path while opening a
separate SERIAL_1 receiving corridor, then restore every cut net and pass
native and independent copper checks. Repeating only the previously sampled
exit positions is insufficient. No board was released or ordered, and no
commit or external message was made. The full-unit goal remains active.
