# Historical baseline source audit

The first broad tooling run is retained in `initial-failing-tooling-tests.log`:
500 tests, 20 failures and three skips. The reported failures concern baseline
power-link, return and thermal records referring to files that have since changed.
They are not fresh native checks of the latest boards.

`manifest.json` binds 15 exact historical source captures, including the three
original test files before this repair. Each copy retains the original receipt
SHA-256. The original receipts and historical CAD outputs are unchanged. The
regression tests now verify those exact bytes while explicitly recording that
the historical inputs do not match the current boards. The live-input checks in
new native validation remain strict.

Two historical source files could not be recovered: the thermal README and
the old P03 generated placement report. Their original hashes remain in the
manifest with `historical_capture_missing` status. The affected thermal packet
is explicitly incomplete and cannot qualify the current board. No replacement
bytes or updated hashes have been invented.

`hardware/cad/a12/historical.py` rejects unknown mismatches, altered captures and
attempts to use a missing historical file as reconstructed input. Mutation tests
exercise those failures. The repaired tests continue checking the original
geometry, numerical and non-release contracts. Passing regression tests does
not restore current applicability, complete the missing capture or release
fabrication. The final adopted assembly still needs fresh validation against its
actual boards, wiring and thermal design.
