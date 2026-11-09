# SERIAL_1 restoration and resistor-placement review

The latest verified eight-layer digital comparison still has **31 open
connections**. This investigation produced no complete board candidate and
made no change to the selected designs. The unit remains unreleased.
The [31-open native checkpoint](../digital-bypass-ground-signal-native-02/README.md)
and [previous investigation](../digital-serial1-repair-review-01/README.md)
remain the baseline evidence.

## Findings

With MCU_PERMIT, CLOCK_5V and LED_48 reserved, three contiguous DATA_5V_SRC
back-layer tracks form a conditional obstruction to SERIAL_1. Removing them
permits a screened 338.507 mm serial proposal, but disconnects R3015. The
[cut-set receipt](../digital-serial1-data-cutset-01/diagnosis.json) identifies
the exact objects. This proposal is incomplete and electrically unqualified.

The [full restoration preflight](../digital-serial1-data-restoration-01/construction.json)
finds possible regions for the MCU trunk, LED_50 and CONTROL_30, but not
DATA_5V_SRC or LED_37. Checks use complete retained copper components,
including sampled track interiors, rather than only old segment endpoints.

The [reserved-route comparison](../digital-serial1-fixed-route-conflicts-01/diagnosis.json)
isolates two separate conflicts in this geometry:

- DATA_5V_SRC has access before the global SERIAL_1 route and loses it after
  that route is added. Omitting CLOCK_5V, LED_48 or MCU_PERMIT alone does not
  restore access while the serial proposal is present.
- LED_37 remains blocked before the global serial route; omitting the
  proposed MCU_PERMIT routes restores its potential access.

The [DATA-first trial](../digital-serial1-data-first-repair-01/diagnosis.json)
reconnects DATA, but then SERIAL_1 has no region path. A 0.1 mm local grid over
x=72–78, y=18–24 mm supplies no legal, directly reachable new DATA via escape.
This is a bounded result, not proof that a different layout is impossible.

## Resistor placement results

Native Linux KiCad captured both faces at 0, 90, 180 and 270 degrees, preserving
pad identities and nets. The screen checks component courtyards, opposite-face
through-hole shadows, board edges, mount reservations, pad-to-copper gaps and
drill-to-SMD gaps. New planned tracks and vias participate in these checks.

| Search | Poses screened | Mechanical passes | Pad-clear poses | Connectivity result |
| --- | ---: | ---: | ---: | --- |
| R3015 back, translation only | 2,205 | 382 | 44 | First 36 route attempts fail |
| R3015 back, four rotations | 8,820 | 1,598 | 175 | None of all 175 reaches DATA source |
| R3015 back, denser northern grid | 16,900 | 2,730 | 102 | None reaches DATA source |
| R3015 front, four rotations | 23,652 | 60 | 0 | No pad-clear placement |
| R1003 back, four rotations | 18,980 | 1,072 | 364 | None of all 364 reaches MCU_PERMIT |
| R1003 front, four rotations | 18,980 | 0 | 0 | No mechanical placement |

Rows overlap spatially and are not counts of unique possible layouts. The
full connectivity screen omits the moved resistor's pads, so it supplies a
necessary condition; a positive result would still need both new pads added,
actual routing, independent geometry checks and native verification.

R1003 searches retain the original LED_37 via and restore the MCU main trunk
with a screened 9.206 mm route before testing resistor placement. None supplies
a complete pull-down connection. R3015 and R1003 trials use separate proposed
geometries; no joint two-resistor solution is claimed.

Relevant receipts: [R3015 region access](../digital-serial1-resistor-access-01/diagnosis.json),
[northern R3015 grid](../digital-serial1-data-resistor-repack-03/diagnosis.json),
[front R3015 grid](../digital-serial1-data-resistor-repack-04/diagnosis.json),
[all back-side R1003 poses](../digital-serial1-permit-resistor-repack-02/diagnosis.json),
[front R1003 grid](../digital-serial1-permit-resistor-repack-03/diagnosis.json).

## Whole-unit status

| Area | Verified state | Outstanding work |
| --- | --- | --- |
| Selected four-layer DC04 | 143 opens; zero native geometry, parity and ERC findings | Complete routing and qualification |
| Eight-layer digital comparison | 31 opens; zero native geometry, parity and ERC findings | 29 LED outputs and two serial links; stack/process selection and qualification |
| Audio layout | 208 opens; codec footprint missing | Approved ESS land/interface inputs, routing and receiving |
| Negative-startup protection | 138 opens; two isolated-domain ERC warnings retained | Routing and qualification without merging isolated grounds |
| Native-closed support boards | Routing checks closed in their saved evidence | Installed power, fault, thermal, harness and manufacturing acceptance |
| Assembly | No complete released unit package | Coherent board selection, mechanical receiving, final outputs and first-article plan |

The [unit readiness record](../../current-readiness.json) still selects the
four-layer digital board. The 31-open eight-layer comparison has not silently
replaced it. Native closure on a support board does not qualify the assembled
unit. The existing exposed-pad via treatments and location-specific fabrication
holds remain unresolved.

## Verification and next implementation step

The [focused test log](focused-tests.log) covers 46 passing tests, including
eight new destination-face placement tests. Tests cover native pad identity,
rotation, face-specific courtyards and copper, through-hole shadows, planned
tracks/vias and drill spacing, alongside routing and connectivity regressions.
Native KiCad was used only to capture rotation templates; template work boards
are intermediate files and are not checked PCB candidates.

All started searches have terminated. Fifteen new search/restoration receipts
and two native template receipts are preserved. The [bound review](review.json)
and [recursive source audit](source-audit.json) bind the evidence and unchanged
unit sources. All 213 current unit-source hashes match. Recursive historical
inspection identifies two stale test-file hashes in the older NF 129-test
receipt. The current versions pass [10 supplemental tests](nf-current-tests.log);
this does not rerun or replace the original 129-test record. The audit explicitly
records both mismatches rather than claiming a completely matching history.
No native rules were relaxed, and no source board, release,
order or commit was made.

The next implementation should reopen the local escape choices for
SERIAL_1/DATA_5V_SRC and MCU_PERMIT/LED_37 together. More resistor-only searches
under the same fixed routes do not address the demonstrated conflicts.
Every removed connection must be restored before emitting a candidate; native
checks, independent pad-group replay, physical audits and signal review remain
required before adopting any improvement.
