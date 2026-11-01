# macOS signing-service recheck and native Manifold proof

The earlier restricted signing commands reported invalid signatures or an
internal code-signing error. Repeating the check with access to macOS's signing
services validates the **unchanged official OpenSCAD2026.10.27 app**. Gatekeeper
accepts it as a notarized Developer ID application. Those earlier restricted
results do not establish damaged application bytes.

`verification.json` captures fresh actual trust commands and three native
Manifold Boolean cases: a1.5 mm³ solid, a0.008 mm³ witness and an exact empty
intersection. The two solids require `NoError`, positive volume, closed oriented
boundaries and no degenerate faces; the empty case requires return1, the exact
empty-object message and no STL. Binary identity, source hashes and raw logs are
retained. This does not replay or inherit any design collision result.

The initial verification's unindexed-STL boundary failure is preserved under
`history/`. STL repeats vertex coordinates per triangle. The new check indexes
only exactly identical coordinates and verifies every original triangle is
preserved; there is no positional tolerance, geometry repair or face removal.

`installation.json` records installation of the same verified binary at
`/Users/axelmckrnna/Applications/OpenSCAD-2026.10.27.app`, beside the existing app.
Its copied signature, Gatekeeper assessment and version are checked again.
No quarantine, signing policy, security setting or file association is changed.

The pinned Linux2026.10.26 runner remains the source of existing sealed design
checks. Historical packets, including UA01's reference to the earlier failed
macOS check, remain byte-for-byte unchanged; this later recheck is the erratum.
Future Mac design checks need fresh source-bound outputs. All physical and
fabrication-release flags remain false.
