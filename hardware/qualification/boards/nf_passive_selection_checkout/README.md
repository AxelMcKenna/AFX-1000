# NP01 checkout-location replay

This successor replays the sealed NP01/P1 models after moving the repository to
another checkout. It canonicalizes only recognized repository path prefixes and
relocates the sealed verifier's file lookups in a private runtime namespace.
Original packet files and seals remain unchanged. External inputs keep their
recorded locations; changed/missing bytes still fail.

The original strict geometry, identity, hash and type comparison remains active.
Its four-ULP allowance still applies only to the identified sums of five unchanged
nonnegative terms. No numerical limit, physical qualification or fabrication
release follows from relocating a path.

```sh
python -m hardware.qualification.boards.nf_passive_selection_checkout.verify
```

An optional `--output NEW_FILE` writes a source-bound report and refuses to
overwrite a file. The verifier checks all 55 NP01 parent files and all 27
NP01-P1 files against their unchanged seals before replay.
