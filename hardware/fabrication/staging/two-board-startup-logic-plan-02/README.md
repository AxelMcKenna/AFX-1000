# Revised startup logic interconnect plan

Supersedes plan-01 after native candidate-01 exposed two disconnected U17
quiet-return branches (C47 and R112) and six lost prior ground projections.
That candidate is rejected despite zero geometry and schematic-parity findings.

The corrected plan reserves FOLLOW1 routing before the PG0 route, and brings
FOLLOW1, PG0 and PG2 from existing bottom copper to new vias outside the quiet
fields and enclosed inner supply fields. Those three interconnects then use
In2/In3 instead of cutting across the In6 quiet/reference fields. Existing
surface copper, component values and pin nets are preserved. Three additional
vias are planned. All prior connection and reference checks still must pass.

The same four footprint moves and local bypass geometry are retained. U29
ALL_RAILS_ALLOW remains reserved but unrouted; its unused escape is not emitted.
This is a construction plan, not a fabrication release or complete startup chain.
