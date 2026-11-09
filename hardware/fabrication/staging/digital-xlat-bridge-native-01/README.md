# LED latch input routing comparison: 37 opens

This eight-layer development comparison connects LED_XLAT and reduces the prior
38-open checkpoint to 37 opens. It is not the selected DC04 production design.
The unit is not ready for fabrication.

The added branch is 134.523696 mm with eight conventional 0.60/0.30 mm vias and
54 new 0.20 mm tracks. Total LED_XLAT copper is 136.357755 mm. The board now has
2,886 tracks and 487 vias. All prior copper, component poses, outline, mounts and
zone definitions remain exact. No buffer-channel reassignment was adopted.

The search now connects legal off-grid via locations to nearby grid nodes using
individually checked surface leads. This avoids missing small legal via regions
without relaxing copper or drill rules. The initial 90 mm search target rejected
the 134.524 mm branch; a separately recorded comparison explicitly allowed up to
140 mm. Neither target is an electrical acceptance limit. Timing, capacitive
loading, ringing, return-path transitions and installed latch behaviour remain
unqualified. Shortening this path remains desirable.

Native checks report zero geometry, schematic-parity and ERC findings, with all
rule categories enabled. All 201 power/ground pads, 39 local connections,
33 thermal branches and all 32 front switch/selector inputs remain connected.
The independent delta review preserves every prior pad group and unchanged net
record. All four physical plane unions remain connected. SD carrier spread stays
5.999239 mm with one via per signal. The minimum non-exempt drill-to-SMD gap is
0.154984 mm; 21 mask-covered heat-spreader vias retain their process hold.
Conditional assembly receiving passes for 138 parts and five mounts. Actual
installed fit and electrical/thermal/EMC/ESD performance remain unqualified.

All eight copper plots and two 1200 dpi details were inspected. The focused
routing and regression suite passes 77 tests, including blocked-via,
disconnected-layer and actual off-grid-via cases.

Evidence: [native review](review.json), [connectivity](stage-connectivity-review.json),
[exact additive delta](additive-route-review.json), [physical checks](corridor-audit.json),
[full checkpoint replay](xlat-bridge-review.json), [visual review](visual-review.json),
[construction](../digital-xlat-bridge-comparison-01/construction.json),
[search outcomes](routing-search-review.json), and [native project](digital_core.kicad_pro).

Remaining digital opens are 33 LED output nets plus LED_BLANK, BYPASS_SENSE,
SERIAL_0 and SERIAL_1. Audio routing, negative protection routing, approved ESS
package/interface data, the physical stack/process, installed assembly,
qualification and a current first-article package remain unfinished.
