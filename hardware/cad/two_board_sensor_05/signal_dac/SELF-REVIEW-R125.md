# Antagonistic self-review r125

Scope: one modeled FDA PD_L join; one declared D101 pose; exactly two original supply-stub replacements; all previous routing and mechanical keepouts preserved. This is a self-review.

Fixed findings:

- The initial bounded escape search considered new return-via sites but omitted an existing qualifying ground via. The revised search tests existing returns first, without changing distance, field or clearance requirements.
- Pad clearance did not establish component spacing. Native r117 rejected the D101/C103 courtyard overlap. The next finite pose family was screened against authored courtyards before native execution; circular courtyards use an outward polygon approximation.
- Native r123 passed connectivity and new-route reference checks but removed reference support beneath two original NBIAS_L traces. It remains rejected. The new via location preserves those traces and is subject to the full unchanged retained-reference gate; no original feedback route is altered and no exclusion is widened.
- Host route planning can represent a decimal coordinate with sub-nanometre binary floating-point noise. Exact native endpoint comparison now rounds the declared coordinates to KiCad's 1 nm coordinate grid; this is serialization, not an added physical clearance tolerance.

Acceptance checks cover every original object outside the exact allowlist, all native group memberships, the unchanged mount rule file, transformed pad identities/nets/world coordinates, complete cumulative footprint poses, strict reference/return support, native fill fidelity and drill clearance. Portable source verification uses explicit immutable inputs and rejects contract tampering while tolerating unrelated shared-folder files.

No geometry-only result qualifies analog performance. Fresh cumulative CAD capture and full assembly screening remain mandatory because D101 moved. Missing ESS and remaining board connections are explicitly retained.
