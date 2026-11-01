"""Primary DCU AUP2G08 gate identity; never infer pin mapping from parity."""

from collections import Counter


def signature(part):
    # TI SCES681F p3 Table4-1 and DCU TOP VIEW: 1,2 ->7; 5,6 ->3.
    assert part["part"] == "SN74AUP2G08DCUR"
    pins = {int(p["number"]): p["net"] for p in part["pins"]}
    assert set(pins) == set(range(1, 9))
    assert pins[4] == "AGND" and pins[8] == "V2V5_AUX"
    return ((pins[7], Counter((pins[1], pins[2]))), (pins[3], Counter((pins[5], pins[6]))))


def verify(before, after):
    assert before["ref"] == after["ref"]
    assert signature(before) == signature(after), "Different physical gate, output or supply net"
    return True
