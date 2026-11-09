# Digital startup routing plan

Candidate plan based on verified TBP39. Seven resistors remain on the bottom
side and retain their packages, values and pin nets. Four supply-good pull-ups
and three follower pull-downs are connected locally; the pull-up supply ends,
Schmitt receivers and remaining startup chain are still incomplete.

The plan replans the eight control-ground escapes, adds four PG and three EN
escapes, relocates the U17 star by 0.25 mm, shortens the C47 return and uses one
new local quiet via for R112. The master-enable local tie is shortened and its
upper trace moves 0.5 mm to open resistor placement space. Every existing
connection and star-only quiet-return ownership still requires native proof.

The archived search programs record the exact scratch workflow and retain
`/private/tmp` paths. Their JSON results are the construction inputs; they are
not manufacturing outputs. Earlier search attempts found mechanically clear
but unroutable sites. The accepted search checks pad clearance, drill clearance,
body/courtyard spacing, accepted routes and local quiet-return ownership.

Native fill, DRC, circuit parity, connection-partition comparison, ground-owner
checks, reference preservation and visual inspection remain required.
