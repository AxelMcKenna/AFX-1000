"""Independent pin-contract and static state checks of the actual E28 logic."""

import copy

AND = [(1, 2, 3), (4, 5, 6), (9, 10, 8), (12, 13, 11)]
NOR = [(2, 3, 1), (5, 6, 4), (8, 9, 10), (11, 12, 13)]
AUP = [(1, 2, 7), (5, 6, 3)]


def contract(parts):
    by = {c["ref"]: c for c in parts}

    def pins(ref):
        return {int(p["number"]): p["net"] for p in by[ref]["pins"]}

    for ref in ("U13", "U14", "U15", "U16", "U17", "U32", "U33"):
        assert by[ref]["part"] == "TPS259482LYWP"
        p = pins(ref)
        assert p[4] == "AGND" and p[8] == "AGND" and p[10] is None
        assert p[5] == p[12] and p[6] == p[11] and p[5] != p[6]
    assert pins("U13")[1] == "E28_ANA_ENABLE"
    assert pins("U14")[1] == "E28_ANA_FOLLOW"
    assert pins("U15")[1] == "E28_MASTER_ENABLE"
    assert pins("U16")[1] == "E28_DIG_FOLLOW1"
    assert pins("U17")[1] == "E28_DIG_FOLLOW2"
    assert pins("U33")[1] == "E28_DIG_FOLLOW3"
    assert pins("U32")[1] == "E28_ANA_FOLLOW2"
    assert pins("U34")[1] == "E28_MASTER_ENABLE" and pins("U34")[2] == "DIG_PG2"
    assert pins("U34")[7] == "E28_DIG_FOLLOW3"
    assert pins("U34")[5] == "E28_MASTER_ENABLE" and pins("U34")[6] == "ANA_PG1"
    assert pins("U34")[3] == "E28_ANA_FOLLOW2"
    # Independent manufacturer pin numbers catch the easy02-vs08 pinout error.
    assert pins("U21")[1] == "E28_ARM_BAR" and pins("U21")[4] == "E28_ARMED"
    assert pins("U21")[10] == "E28_FAULT_BAR" and pins("U21")[13] == "E28_FAULT"
    for ref in ("U29", "U30", "U31", "U34"):
        p = pins(ref)
        assert by[ref]["part"] == "SN74AUP2G08DCUR"
        assert p[4] == "AGND" and p[8] == "V2V5_AUX"
    assert pins("U29")[1] == "ALL_RAILS_ALLOW" and pins("U29")[2] == "E28_AUX_VALID"
    assert pins("U29")[7] == "E28_MASTER_ENABLE"
    assert pins("U30")[5] == "E28_MASTER_ENABLE" and pins("U30")[6] == "DIG_PG3"
    assert pins("U30")[3] == "E28_ANA_ENABLE"
    if "U35" in by:
        assert by["U35"]["part"] == "SN74LVC3G17DCUR"
        assert pins("U35") == {
            1: "E28_TIMEOUT_RAW",
            7: "E28_TIMEOUT",
            3: "E28_AUX_RESET_RAW",
            5: "E28_AUX_RESET_N",
            6: "NF_OUTPUT_VALID_RAW",
            2: "NF_VALID_LOGIC",
            4: "AGND",
            8: "V2V5_AUX",
        }
        assert pins("U19")[6] == pins("R135")[1] == "E28_AUX_RESET_RAW"
        assert pins("U20")[6] == pins("R136")[1] == "E28_TIMEOUT_RAW"
        assert pins("U31")[5] == "E28_AUX_RESET_N" and pins("U26")[4] == "E28_TIMEOUT"
        assert pins("U25")[4] == pins("U27")[3] == "POS_OUTPUT_READY"
        assert pins("U25")[5] == "NF_VALID_LOGIC" and pins("U25")[6] == "E28_OUTPUT_READY"
        assert pins("J12") == {1: "NF_OUTPUT_VALID_RAW", 2: "AGND"}
        assert pins("R143") == {1: "NF_OUTPUT_VALID_RAW", 2: "AGND"}
        assert by["R143"]["part"].startswith("15k ")
    else:
        assert pins("U25")[4] == pins("U25")[5] == "AGND" and pins("U25")[6] is None
    assert pins("U27")[12] == "E28_SAFE_STAGE" and pins("U27")[13] == "E28_NOT_FAULT"
    assert pins("U27")[11] == "E28_SAFE_REQUEST"
    assert by["U28"]["part"] == "SN74LVC14APWR"
    assert pins("U28")[1] == "POWER_RUN" and pins("U28")[2] == "E28_NOT_RUN"
    assert pins("U28")[9] == "E28_NOT_RUN" and pins("U28")[8] == "E28_RUN_LOGIC"
    assert pins("U28")[11] == "P03_SOURCES_READY" and pins("U28")[10] == "E28_NOT_SOURCE_READY"
    assert pins("U28")[13] == "E28_NOT_SOURCE_READY" and pins("U28")[12] == "E28_SOURCE_READY_LOGIC"
    assert not any(
        c["ref"] != "U28"
        and c["part"].startswith("SN74LVC")
        and p["kind"] == "input"
        and p["net"] in ("POWER_RUN", "P03_SOURCES_READY")
        for c in parts
        for p in c["pins"]
    )
    assert pins("J6")[2] == "E28_MASTER_ENABLE"
    assert pins("J9") == {
        1: "AGND",
        2: "P03_SOURCES_READY",
        3: "E28_OUTPUT_READY",
        4: "E28_FAULT",
        5: "E28_MASTER_ENABLE",
    }
    return dict(
        staged_channels=7,
        digital_parallel_channels=4,
        analog_parallel_channels=3,
        rcbctrl_low=True,
        steady_reverse_blocking=False,
        output_ready_is_voltage_accuracy_proof=False,
        physical_brownout_or_fault_qualified=False,
    )


class StaticLogic:
    """Actual native component pin maps, preserving feedback between settles.

    Only Boolean steady states are modeled. No propagation, analog thresholds,
    startup rail waveform, SOA, brownout glitch or elapsed-time pass is implied.
    """

    def __init__(self, parts):
        self.parts = copy.deepcopy(parts)
        self.values = {"AGND": 0, "V2V5_AUX": 1}
        self.gates = []
        for part in parts:
            pins = {int(p["number"]): p["net"] for p in part["pins"]}
            name = part["part"]
            if name.startswith(("SN74LVC08A", "SN74LVC32A", "SN74LVC02A", "SN74AUP2G08")):
                mapping = (
                    NOR if name.startswith("SN74LVC02A") else AUP if name.startswith("SN74AUP2G08") else AND
                )
                function = (
                    "nor"
                    if name.startswith("SN74LVC02A")
                    else "or"
                    if name.startswith("SN74LVC32A")
                    else "and"
                )
                self.gates.extend((function, pins[a], pins[b], pins[y]) for a, b, y in mapping if pins[y])
            elif name.startswith("SN74LVC3G17"):
                self.gates.extend(("buf", pins[a], None, pins[y]) for a, y in ((1, 7), (3, 5), (6, 2)))
            elif name.startswith(("SN74LVC04A", "SN74LVC14A")):
                self.gates.extend(
                    ("not", pins[a], None, pins[y])
                    for a, y in ((1, 2), (3, 4), (5, 6), (9, 8), (11, 10), (13, 12))
                    if pins[y]
                )
        for _, a, b, y in self.gates:
            for net in (a, b, y):
                if net is not None:
                    self.values.setdefault(net, 0)

    def settle(self, **inputs):
        self.values.update(inputs)
        for _ in range(200):
            before = self.values.copy()
            for function, a, b, y in self.gates:
                av = bool(self.values.get(a, 0))
                bv = bool(self.values.get(b, 0))
                self.values[y] = int(
                    av
                    if function == "buf"
                    else not av
                    if function == "not"
                    else not (av or bv)
                    if function == "nor"
                    else (av or bv)
                    if function == "or"
                    else (av and bv)
                )
            if before == self.values:
                return self.values.copy()
        raise AssertionError("Native combinational/feedback logic did not settle")


def safe_inputs(parts=None):
    result = dict(
        POWER_RUN=0,
        E28_AUX_RESET_N=0,
        P03_SOURCES_READY=0,
        P19_OV_OK=1,
        N19_OV_OK=1,
        P12_OV_OK=1,
        N12_OV_OK=1,
        V5_REG_OV_OK=1,
        **{"5V_DIG_OV_OK": 1},
        REF_LOW_OK=1,
        REF_HIGH_OK=1,
        ANA_SOURCE_OK=0,
        DIG_SOURCE_OK=0,
        ANA_OUTPUT_OK=0,
        DIG_OUTPUT_OK=0,
        DIG_PG0=0,
        DIG_PG1=0,
        DIG_PG2=0,
        DIG_PG3=0,
        ANA_PG0=0,
        ANA_PG1=0,
        ANA_PG2=0,
        E28_TIMEOUT=0,
    )
    if parts is not None and any(c["ref"] == "U35" for c in parts):
        result["E28_AUX_RESET_RAW"] = result.pop("E28_AUX_RESET_N")
        result["E28_TIMEOUT_RAW"] = result.pop("E28_TIMEOUT")
        result["NF_OUTPUT_VALID_RAW"] = 0
    return result
