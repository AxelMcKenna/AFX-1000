"""Actual U19 TPS3890 to U31 AUP2G08 static and strict rising-edge screen.

The historical2G17 identification was wrong and is preserved as rejected
evidence. AUP VIH/II ranges apply here. Enforce its200ns/V recommended row
despite conflicting Schmitt text; no input-edge waiver is inferred.
"""

import math

from ...common.sexpr import children, first

PART = "10k 0.1% 25ppm Panasonic ERA6AEB103V"
MPN = "ERA6AEB103V"
FOOTPRINT = "RMX_E28:Resistor_SMD_Panasonic_ERA6A_2012"
MODEL_URL = "https://industrial.panasonic.com/ww/products/pt/high-precision-chip-resistors/models/ERA6AEB103V"


def screen(resistance_ohm=10000, node_cap_requirement_f=10e-12):
    assert resistance_ohm > 0 and node_cap_requirement_f >= 0
    aux_low, aux_high, frac = 2.5, 2.7, 0.02
    receiver, off, board = 0.5e-6, 0.25e-6, 2e-6
    leak = receiver + off + board
    rmin, rmax = resistance_ohm * (1 - frac), resistance_ohm * (1 + frac)
    high = aux_low - leak * rmax
    vih, vil, vol, rate = 1.6, 0.7, 0.25, 200e-9
    return dict(
        actual_receiver="U31 SN74AUP2G08DCUR pin5",
        resistance_ohm=resistance_ohm,
        total_resistance_fraction_requirement=frac,
        receiver_aux_requirement_v=[aux_low, aux_high],
        receiver_input_leak_a=receiver,
        supervisor_off_leak_row_a=off,
        board_leakage_requirement_a=board,
        HIGH_min_v=high,
        VIH_requirement_v=vih,
        static_high_margin_v=high - vih,
        RESET_LOW_sink_allocation_a=aux_high / rmin + leak,
        TPS3890_LOW_row_current_a=0.0004,
        TPS3890_LOW_row_VDD_min_v=1.5,
        TPS3890_LOW_row_VOL_v=vol,
        AUP_VIL_v=vil,
        LOW_reference_offset_ceiling_v=vil - vol,
        LOW_pullup_source_current_max_a=aux_high / rmin,
        LOW_pullup_power_max_w=aux_high**2 / rmin,
        LOW_current_delta_vs100k_same_corner_a=aux_high / rmin - aux_high / (100000 * (1 - frac)),
        strict_input_transition_row_s_per_v=rate,
        allowable_total_node_C_f=rate * (high - vih) / rmax if high > vih else None,
        node_capacitance_requirement_f=node_cap_requirement_f,
        RC_rise_slope_at_VIH_s_per_v=rmax * node_cap_requirement_f / (high - vih) if high > vih else None,
        RC_VIL_to_VIH_time_s=rmax * node_cap_requirement_f * math.log((high - vil) / (high - vih))
        if high > vih
        else None,
        AUP_Ci_1p5pF_is_typical_not_a_maximum=True,
        actual_node_C_trace_via_Coff_probe_and_received_slew_accepted=False,
        TPS_reset_leak_row_transfer_from5v5_accepted=False,
        manufacturer_conflicting_Schmitt_no_rate_wording_does_not_waive200ns_row=True,
        native_CT_C60_unchanged=True,
        output_cap_delay_RESET_propagation_transient_and_partial_power_qualified=False,
        complete_AUX_load_and_PDN_qualified=False,
        physical_and_fabrication_qualified=False,
    )


def validate_footprint(fp):
    """Independent rectangular land contract from Panasonic2012 a/b/c table."""
    assert str(fp[1]).split(":")[-1] == FOOTPRINT.split(":")[-1]
    pads = children(fp, "pad")
    assert len(pads) == 2 and {str(p[1]) for p in pads} == {"1", "2"}
    side = str(first(fp, "layer")[1])[0]
    for p in pads:
        assert p[2:4] == ["smd", "rect"]
        assert list(map(float, first(p, "at")[1:3])) == [-1.15 if str(p[1]) == "1" else 1.15, 0]
        assert list(map(float, first(p, "size")[1:])) == [1.1, 1.25]
        assert set(map(str, first(p, "layers")[1:])) == {side + ".Cu", side + ".Mask", side + ".Paste"}
        assert not children(p, "roundrect_rratio")
    assert 1.0 <= 2 * 1.15 - 1.1 <= 1.4  # a=1.2
    assert 3.2 <= 2 * 1.15 + 1.1 <= 3.8  # b=3.4
    assert 0.9 <= 1.25 <= 1.4  # c=1.25
    court = [q for q in children(fp, "fp_rect") if first(q, "layer")[1] == side + ".CrtYd"]
    assert len(court) == 1
    pts = [list(map(float, first(court[0], tag)[1:])) for tag in ("start", "end")]
    assert sorted(p[0] for p in pts) == [-1.95, 1.95]
    assert sorted(p[1] for p in pts) == [-0.925, 0.925]
    return True
