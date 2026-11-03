# Unselected six-layer audio local-routing trial

**Not ready for fabrication.** This trial continues `audio-main-six-control-01`;
it does not replace the selected four-layer fabrication/readiness checkpoint.

Native Linux KiCad 10.0.7 confirms **180 open connections**, down from 201 in
the source. The delta consists of 21 surface connections / 22 tracks, all
0.20 mm wide. No vias are added, and existing tracks, footprints, stack settings,
authored keepouts and component poses remain exact.

Six 1.27 mm output-to-inverting-input feedback links are now connected on U103,
U104 and U305. The other links join local passive signal nodes. The longest new
link is 5.648 mm; the two U104 reference-buffer feeds remain deferred because
they could not meet the separate 6 mm construction limit. The feedback links
have a 2.5 mm limit. Converter differential wiring, negative-bias branches,
charge pumps, relay coil currents and long audio trunks are outside this delta.

Native DRC geometry and ERC findings are zero, with no ignored checks. The known
schematic parity warning remains: U201 / ES9292QPRO has no footprint. All 138
earlier local connections, 17 original control pairs, 200 ground pads, 161 rail
pads, inherited global control witnesses and two private timing pairs retain
native connectivity. All 930 native pad shapes match the six-layer source.

`surface-delta-review.json` replays the additive copper, actual pad geometry,
both native filled planes, short-link length/clearance limits and complete
native endpoint witnesses. Its scope is the local delta; it does not certify the
six-layer preparation or electrical performance. Seven mutation tests include
changed existing power copper/pads, narrowed new tracks, undeclared inner-layer
copper, relaxed feedback limits and false island merges.

Circuit roles come from the source's native netlist. TI's
[OPA1656 layout guidance](https://www.ti.com/lit/ds/symlink/opa1656.pdf) (section 8.4)
and [OPA4192 layout guidance](https://www.ti.com/lit/ds/symlink/opa4192.pdf)
(section 11) motivate short amplifier input connections. These routes alone do
not demonstrate stability, noise, distortion or installed performance.

Remaining work includes 180 placed-board connection gaps, the missing codec
land pattern, independent six-layer preparation review, accepted manufacturer
stack/process/materials, electrical/mechanical review and the fabrication release
checks. Production qualification also requires measured hardware results.
