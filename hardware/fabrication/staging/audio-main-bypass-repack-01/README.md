# AC04 — bypass-supervisor inputs and unused-space survey

**Input capture and preliminary study only. No revised PCB has been emitted.**
The selected board remains the
[208-open ANALOG_OK revision](../audio-main-controls-06/README.md).

The immutable native capture contains 3,737 native objects and 44 native
control islands from that board. It freezes actual pads, tracks, vias,
authored exclusions and stored reference fill for subsequent planning.

The [space survey](supervisor-space-survey.json) tests moving U605 and C606
together into unused space on the existing 150 × 63 mm board. Proposed
supervisor centres at **(100, 4), (105, 4), (110, 4) and (112, 5) mm** pass
the preliminary receiving, foreign-copper and relocated-ground-via screens.
The (95, 4) mm option is rejected because moved support copper conflicts
with retained copper. The proposed drill-edge-to-SMD gap is approximately
0.170 mm on both faces. These positions do not require a larger housing.

The screen includes the rigidly moved private ground/supply couplers and
every actual SMD land. The relocated ground via is checked as a new hole;
the unchanged-centre exemption is not used. Its intentional moved AGND
spurs are excluded from that obstacle test because they connect at the
hole; all other-net copper and solder lands remain screened. Native DRC
must still check the eventual complete candidate.

The survey assumes four declared old source-entry objects would be
replaced. **Replacement power/sense connections, control routes, native
refill/DRC/ERC/connectivity, full receiving and installed qualification are
unfinished.** No surveyed position is an approved or selected relocation.
The study does not establish heights, mating, harness paths, noise/timing,
fault behaviour or manufacturing acceptance. No supplier message, upload
or order was made, and native Mac CAD remains disabled.

The subsequent distant-supervisor routing draft in this directory is an
unselected experiment. It cannot close all five repaired/new controls within
its original construction targets. Its input captures, applied sources and
partial proposals are retained because the nearer-root comparison explicitly
rechecks three of its routes against new native geometry. No final native-clean
board is claimed here. See the [cleaned near-root comparison](../audio-main-bypass-repack-04/README.md).
