# Power-board monitor and control routing

This KiCad candidate adds 23 connections relative to the local bypass revision. The new copper joins rail-window outputs, fan heartbeat and indicator circuitry, negative-rail reset and clamp-indicator signals, and the master-enable header branch. The circuit still has 1,890 open connections.

The 128 traces are 0.20 mm wide. The one new through-via connects two portions of E rail-disconnect P19_OV_OK and has a 0.60 mm land with a 0.30 mm drill. Its nearby existing main-ground via contacts the adjacent connected reference fields. The full trace width is referenced outside the signal via's clearance. The board keeps the existing footprint placements, mounting clearances and manufacturing rules.

KiCad 10.0.7 passes geometry and schematic parity on the saved board and on a full refill. Native connectivity confirms all 23 intended pad-group merges. Existing copper objects and plane boundaries are retained. Two ground fills acquire clearance around the new via. The JSON DRC marker list caps at 499 open markers. The native count is uncapped.

[Routes](routes.json) · [Connectivity](connectivity.json) · [Saved-board DRC](drc.json) · [Ground references and cradle clearances](reference-review.json) · [Retained objects](retention.json) · [Mechanical comparison](placement.json)

The additional wiring has not been bench-tested. Timing, thermal performance, source distribution, mechanical tolerances, and the manufacturing stack remain open.
