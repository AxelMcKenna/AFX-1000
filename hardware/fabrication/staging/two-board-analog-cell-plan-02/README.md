# Analog control routing candidate 02 — superseded

This candidate proposed twelve component moves, 42 paths, 96 tracks and
nineteen vias. Native component poses and the zone-independent geometry
screen passed. It was not selected as a board revision.

The subsequent reference check found two conflicts: retained PG1 track
`27fecc93-8d30-5a92-a16b-7ed1f3fdaacc` interrupts 0.274093 mm² of U14's required
In6 quiet reference, and the proposed PG1 restoration interrupts 0.140223 mm²
of U32's required In6 quiet reference. See
[quiet-reference-conflicts.json](quiet-reference-conflicts.json).

[Plan 03](../two-board-analog-cell-plan-03/README.md) replaces that retained
PG1 branch and reroutes both PG1 connections around the required quiet regions.
It reuses these native component poses. The `fanout-search-original.py` archive
records the exploratory search and its scratch paths; `routing-search.py`
reproduces this candidate from repository inputs. No fabrication release.
