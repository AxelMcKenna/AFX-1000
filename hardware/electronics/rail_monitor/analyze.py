"""E13 threshold corners from exported resistor endpoints and comparator pins."""

import itertools


def pair(pins, ref):
    return (pins[ref]["1"], pins[ref]["2"])


def path_sum(parts, pins, refs, start, end, number):
    # Series lists must really be a single path, with no repeated/stray branch.
    node = start
    remaining = set(refs)
    total = 0
    while remaining:
        choices = [r for r in remaining if node in pair(pins, r)]
        assert len(choices) == 1, (refs, start, end, node)
        ref = choices[0]
        a, b = pair(pins, ref)
        node = b if a == node else a
        remaining.remove(ref)
        total += number(parts[ref].findtext("value"))
    assert node == end, (refs, node, end)
    return total


def screen(parts, pins, mapping, number):
    windows = {w["name"]: w for w in mapping["windows"]}
    amps = {a["window"]: a for a in mapping["amplifiers"]}
    rows = []
    used = set()
    minimum_hysteresis = 1e9
    # Required total errors include initial tolerance, temperature and aging.
    precision_error = 0.001
    feedback_error = 0.05
    reference_error = 0.001
    for row in mapping["comparators"]:
        w = windows[row["window"]]
        name = row["name"]
        sense = name + "_SENSE"
        threshold = name + "_REF"
        srefs = row["sense_parts"]
        trefs = row["threshold_parts"]
        assert pair(pins, row["feedback"]) == (row["output"], row["positive"])
        assert pair(pins, row["pull"]) == ("V3V3_IO", row["output"])
        base = threshold + "_BASE" if row["mode"] == "OV" else threshold
        rt = path_sum(parts, pins, trefs[:-1], "REF_2V5", base, number)
        assert pair(pins, trefs[-1]) == (base, "AGND")
        rb = number(parts[trefs[-1]].findtext("value"))
        rh = number(parts[row["feedback"]].findtext("value"))
        assert rb == 10000 and rh == 20e6 and number(parts[row["pull"]].findtext("value")) == 10000
        used.update(srefs + trefs + [row["feedback"], row["pull"]])
        series = 0
        if row["mode"] == "OV":
            r = row["threshold_series"]
            assert pair(pins, r) == (base, threshold)
            series = number(parts[r].findtext("value"))
            assert series == 10000
            used.add(r)
        if w["kind"] == "positive":
            st = path_sum(parts, pins, srefs[:-1], w["rail"], sense, number)
            assert pair(pins, srefs[-1]) == (sense, "AGND")
            sb = number(parts[srefs[-1]].findtext("value"))
            gain_options = None
        else:
            assert len(srefs) == 1 and pair(pins, srefs[0]) == (w["name"] + "_INV", sense)
            sr = number(parts[srefs[0]].findtext("value"))
            a = amps[w["name"]]
            assert pair(pins, a["input_ref"]) == (w["rail"], w["name"] + "_FB")
            assert pair(pins, a["feedback_ref"]) == (w["name"] + "_INV", w["name"] + "_FB")
            rin = number(parts[a["input_ref"]].findtext("value"))
            rf = number(parts[a["feedback_ref"]].findtext("value"))
            gmin = rf * (1 - precision_error) / (rin * (1 + precision_error))
            gmax = rf * (1 + precision_error) / (rin * (1 - precision_error))
            error = (1 + gmax) * 150e-6 + 5e-9 * rf * (1 + precision_error)
            gain_options = list(itertools.product((gmin, gmax), (-error, error)))
            used.update((a["input_ref"], a["feedback_ref"]))
        trip = []
        recover = []
        hysteresis = []
        corners = 0
        resistor_cases = itertools.product(
            (-1, 1), repeat=(5 if w["kind"] == "positive" else 4) + (1 if series else 0)
        )
        for rs in resistor_cases:
            tr = rt * (1 + rs[0] * precision_error)
            br = rb * (1 + rs[1] * precision_error)
            hr = rh * (1 + rs[2] * feedback_error)
            rr = 1 / (1 / tr + 1 / br)
            rr_with_series = rr + (series * (1 + rs[-1] * precision_error) if series else 0)
            if w["kind"] == "positive":
                ts = st * (1 + rs[3] * precision_error)
                bs = sb * (1 + rs[4] * precision_error)
                resistance = 1 / (1 / ts + 1 / bs)
                signals = [(bs / (ts + bs), 0)]
            else:
                resistance = sr * (1 + rs[3] * precision_error)
                signals = gain_options
            for ref, offset, ip, im, (gain, error) in itertools.product(
                (2.5 * (1 - reference_error), 2.5 * (1 + reference_error)),
                (-0.005, 0.005),
                (-1.2e-9, 1.2e-9),
                (-1.2e-9, 1.2e-9),
                signals,
            ):

                def at(out):
                    if row["mode"] == "UV":
                        m = gain / (1 + resistance / hr)
                        c = (error / resistance + out / hr - ip) / (1 / resistance + 1 / hr)
                        n = ref * br / (tr + br) - im * rr
                        return (n - c - offset) / m
                    positive = (ref * br / (tr + br) / rr_with_series + out / hr - ip) / (
                        1 / rr_with_series + 1 / hr
                    )
                    return (positive - error + im * resistance + offset) / gain

                lo = [at(v) for v in (0, 0.25)]
                hi = [at(v) for v in (3.04, 3.55)]
                trip.extend(hi)
                recover.extend(lo)
                corners += 4
                h = (min(lo) - max(hi)) if row["mode"] == "UV" else (min(hi) - max(lo))
                assert h > 0, (name, h)
                hysteresis.append(h)
        if row["mode"] == "UV":
            assert min(trip) > w["valid"][0], (name, "late UV", min(trip), w["valid"])
            assert max(recover) < w["normal"][0], (name, "normal low rejected", max(recover), w["normal"])
        else:
            assert max(trip) < w["valid"][1], (name, "late OV", max(trip), w["valid"])
            assert min(recover) > w["normal"][1], (name, "normal high rejected", min(recover), w["normal"])
        minimum_hysteresis = min(minimum_hysteresis, min(hysteresis))
        rows.append(
            dict(
                name=name,
                mode=row["mode"],
                rail=w["rail"],
                polarity="magnitude" if w["kind"] == "inverted" else "positive",
                corners=corners,
                trip_with_healthy_output_v=[min(trip), max(trip)],
                recover_with_fault_output_v=[min(recover), max(recover)],
                minimum_hysteresis_v=min(hysteresis),
                normal_generation_magnitude_v=w["normal"],
                accepted_safety_envelope_magnitude_v=w["valid"],
            )
        )
    # Real values from the guarded divider; no negative rail goes to a supervisor.
    assert pair(pins, "R110") == ("V5_REG", "V5_COARSE_SENSE")
    assert pair(pins, "R111") == ("V5_COARSE_SENSE", "AGND")
    top = number(parts["R110"].findtext("value"))
    bottom = number(parts["R111"].findtext("value"))
    lower = 0.405 * 0.9875 * (1 + top * 0.999 / (bottom * 1.001))
    upper = 0.405 * 1.0125 * 1.006 * (1 + top * 1.001 / (bottom * 0.999))
    assert lower > 4.5 and upper < 4.90
    # Each comparator drives one LVC input and one hysteresis resistor. Open-drain
    # leakage has only a typical datasheet value, so1uA is an explicit allocation.
    output_load = 5e-6 + 1e-6 + 3.55 / (20e6 * 0.95)
    high_min = 3.135 - output_load * 10100
    high_max = 3.465 + output_load * 10100
    assert high_min > 3.04 and high_max < 3.55 and high_min > 2.0
    low_current = 3.465 / 9900 + 3.55 / (20e6 * 0.95)
    assert low_current < 0.004
    final_load = 3.465 / (47000 * 0.99) + 3.465 / (330000 * 0.99) + 1e-6
    assert final_load < 100e-6 and 3.135 - 0.2 > 2.5
    return dict(
        revision="E13",
        window_channels=8,
        comparators=16,
        threshold_corners=sum(r["corners"] for r in rows),
        thresholds=rows,
        minimum_rail_referred_hysteresis_v=minimum_hysteresis,
        allocations=dict(
            total_precision_resistor_fraction=0.001,
            total_feedback_resistor_fraction=0.05,
            total_reference_fraction=0.001,
            comparator_offset_at5v_v=0.005,
            comparator_input_bias_a=1.2e-9,
            opamp_offset_at5v_v=150e-6,
            opamp_input_bias_a=5e-9,
            comparator_output_off_leakage_a=1e-6,
            offset5v_and_leakage_allocations_bench_verified=False,
        ),
        coarse_guard=dict(
            v5_uv_lower_screen_v=lower,
            v5_uv_upper_release_screen_v=upper,
            minimum_reset_release_s=0.180,
            maximum_reset_release_s=0.420,
            reference_amplifier_startup_max_allocation_s=0.100,
            startup_allocation_measured=False,
        ),
        logic_dc=dict(
            comparator_high_min_v=high_min,
            comparator_high_max_v=high_max,
            comparator_low_max_v=0.25,
            maximum_comparator_low_sink_a=low_current,
            lvc_vih_min_v=2.0,
            lvc_vil_max_v=0.8,
            maximum_pre_analog_ok_load_a=final_load,
            pre_analog_ok_high_min_v=3.135 - 0.2,
        ),
        all_window_resistors_used=sorted(used),
        response_timing_verified=False,
        power_generation_implemented=False,
        overvoltage_disconnect_implemented=False,
        pcb_routed=False,
        physical_audio_verified=False,
    )
