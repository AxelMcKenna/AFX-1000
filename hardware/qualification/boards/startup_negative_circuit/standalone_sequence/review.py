"""Review actual exported native pin maps, not just the builder's intention."""

from pathlib import Path

from hardware.electronics.common.netlists import netlist

ROOT = Path(__file__).resolve().parent


def validate(pins):
    required = {
        "U35": {
            "4": "GLOBAL_VALID",
            "5": "GLOBAL_VALID",
            "6": "N19_WD_ENABLE",
            "12": "GLOBAL_VALID",
            "13": "N19_WD_ARMED",
        },
        "U38": {"12": "N12_STAGE_ENABLED", "13": "GLOBAL_VALID", "11": "N12_WD_ENABLE"},
        "U39": {"4": "N12_STAGE_ENABLED", "5": "N12_WD_ARMED"},
        "U48": {"11": "GLOBAL_VALID", "10": "NOT_GLOBAL_VALID"},
        "U50": {
            "1": "N19_ARM_Q",
            "2": "NOT_GLOBAL_VALID",
            "3": "N19_ARM_QBAR",
            "4": "N19_ARM_QBAR",
            "5": "N19_ARM_SET",
            "6": "N19_ARM_Q",
            "8": "NOT_GLOBAL_VALID",
            "9": "N12_ARM_QBAR",
            "10": "N12_ARM_Q",
            "11": "N12_ARM_SET",
            "12": "N12_ARM_Q",
            "13": "N12_ARM_QBAR",
        },
        "U51": {
            "1": "GLOBAL_VALID",
            "2": "N19_PERMIT_D",
            "3": "N19_ARM_SET",
            "4": "GLOBAL_VALID",
            "5": "N19_OUTPUT_QUALIFIED",
            "6": "N12_STAGE_ENABLED",
            "9": "N12_STAGE_ENABLED",
            "10": "N12_PERMIT_D",
            "8": "N12_ARM_SET",
        },
        "U28": {"2": "N19_ARM_Q", "4": "N19_ARM_CONDITIONED"},
        "U30": {"2": "N12_ARM_Q", "4": "N12_ARM_CONDITIONED"},
        "U52": {"1": "N19_ARM_CONDITIONED", "4": "N19_START_DELAY_N", "5": "N19_START_CT"},
        "U53": {"2": "N19_START_DELAY_N", "4": "N19_START"},
        "U54": {"1": "N12_ARM_CONDITIONED", "4": "N12_START_DELAY_N", "5": "N12_START_CT"},
        "U55": {"2": "N12_START_DELAY_N", "4": "N12_START"},
        "J1": {
            "18": "N19_ARM_CONDITIONED",
            "19": "N19_START",
            "24": "N12_ARM_CONDITIONED",
            "25": "N12_START",
            "30": "NF_OUTPUT_VALID",
        },
    }
    errors = []
    for ref, row in required.items():
        for pin, expected in row.items():
            if pins.get(ref, {}).get(pin) != expected:
                errors.append((ref, pin, expected, pins.get(ref, {}).get(pin)))
    return errors


def main():
    parts, pins = netlist(ROOT / "generated/netlist.xml")
    assert len(parts) == 249
    assert not validate(pins), validate(pins)
    return parts, pins


if __name__ == "__main__":
    main()
    print("249 actual native components and standalone cone checked")
