# Permission routing candidate 03 — superseded

Native geometry and schematic parity pass, with 2,237 opens and the two
retained isolated-reference ERC warnings. The independent audit rejects this
candidate: one prior reference case regresses and one new route lacks full
adjacent ground projection. See [reference diagnostics](reference-regressions.json).

The replacement plan reroutes ANA_PG0 around the R95 supply projection and
reuses an existing AUX via for R107. The small digital-source refill change is
under separate investigation. The first isolated fill control was rejected
because KiCad reassigned its test via; a corrected control locks the AUX net.
TBP43 remains selected until a successor passes its full review. Not fab-ready.
