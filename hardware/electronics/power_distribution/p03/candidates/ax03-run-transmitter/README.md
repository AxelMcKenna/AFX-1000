# P03 AX03 RUN transmitter candidate

The preferred 264-part paired project has zero native DRC errors, warnings,
opens, ERC and parity findings with every rule category enabled. It is not
physically qualified or released for fabrication.

Use [CURRENT_LAYOUT.json](CURRENT_LAYOUT.json) or the
[checked project](generated/native-closed-transmitter/power_p03.kicad_pro).
The root PCB is an incomplete staging parent.

The [integration review](../../../../../qualification/boards/aux_low_power_run/P03_INTEGRATION_REVIEW.md)
documents exact source conservation, actual local bypass paths, five new
via-in-SMD process requirements, the four-wire logical E28 map and outstanding
qualification. The
[actual PCB plot](generated/native-closed-transmitter/closed-top.svg),
[native results](generated/native-closed-transmitter/review.json) and
[handoff](generated/native-closed-transmitter/handoff.json) retain the evidence.

The eight-part source cell buffers only J106.3. Original R113, internal RUN/PG
and switch topology remain intact. The original 160 × 45 mm outline, mounting
positions, stackup and all 1,254 strict-source vias remain exact. The strict
source's two P19_SRC neck limitations and all manufacturing/physical holds carry
forward. Canonical and preserved source projects are unchanged.
