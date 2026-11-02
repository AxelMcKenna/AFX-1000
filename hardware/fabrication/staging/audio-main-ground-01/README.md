# Historical first audio reference-plane trial

**Unselected.** This trial connects 197 of 200 placed ground pads and has 396
native open connections. Full native checks retain two track-to-via centring
errors at a new C227 ground via, zero ERC findings, and the missing ESS footprint
finding. No rule category is ignored.

The initial `authored-input` omitted the explicit `net_name` required by the
legacy 20240108 board format. The first native capture exposed an unassigned
plane; that input, capture and executed-source snapshots are preserved.
`authored-netted-input` adds the verified AGND label, and the subsequent native
fill/capture confirms the intended eleven through-hole ground contacts before
179 ground escapes are constructed.

The [corrected successor](../audio-main-ground-02/README.md) removes the offending
via, reuses a properly centred existing ground via, completes the last three
ground pads and passes the full native checks. The first trial is not an order
file or a fabrication release.
