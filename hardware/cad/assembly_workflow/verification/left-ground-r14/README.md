# Full assembly screen of r14 left ground candidate

The source-bound candidate replaces the r13 combined exits only for this screen.
It does not change the active assembly selection. Run with:

```sh
.venv/bin/python -m hardware.cad.assembly_workflow.verification.left-ground-r14.screen check
```

Sensor and cooling checks pass. The controls check fails with a closed intersection
of 20.748299 mm³ at X147.300–172.700, Y19.155–36.345, Z30.241–32.195 mm.
This is a geometric failure, not a runtime failure. No contact waiver is applied.
The harness owner is localizing and correcting the conflict. This candidate is
not accepted, and the active r13 source-exit geometry remains unchanged.

All operands passed the workflow's positive geometry validation; contact-rich
link geometry used original SCAD for intersections. Native check results, meshes,
logs and exact source identities are preserved under `native-evidence`.
The source registries and frozen local evidence remain in their original paths.

Supports, service slack, the scene/selector branch and physical terminal receiving
qualification remain incomplete. This is not a fabrication release.

## Corrected r4 selection

The later r4 reroute clears the BPM display without changing terminal adjacency. All three current-assembly checks pass; `native-r4/`, `results-r4.json` and `review-r4.json` preserve the evidence. The active receiving geometry now selects this left chain and the unchanged right exit. The earlier failed r3 evidence above remains historical. Supports, service slack and the complete right branch remain open.
