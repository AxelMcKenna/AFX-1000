"""Check the IPC-D-356 point identities, nets and coordinates against native CAD."""

import json
import re
from collections import Counter
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.evidence_paths import recorded_path

REPO = Path(__file__).resolve().parents[2]
ROOT = REPO / "hardware/fabrication/staging/rail-monitor-manufacturing-review-02"
CAPTURE = REPO / "hardware/fabrication/staging/rail-monitor-dc-inputs-01/capture.json"
PCB = REPO / "hardware/fabrication/staging/rail-monitor-r83-land-native-01/rail_monitor.kicad_pcb"


def parse(text):
    lines = text.splitlines()
    if "P  UNITS CUST 0" not in [line.rstrip() for line in lines] or lines[-1].rstrip() != "999":
        raise ValueError("Require terminated decimil IPC-D-356A data")
    aliases, records = {}, []
    for line in lines:
        if line.startswith("P  NNAME"):
            alias, name = line[8:13].strip(), line[14:72].strip()
            if alias in aliases:
                raise ValueError("Duplicate IPC net alias")
            aliases[alias] = name
        elif line[:3] in ("317", "327", "367"):
            if len(line) != 80:
                raise ValueError("IPC test record must have 80 columns")
            location = re.search(r"A\d{2}X([+-]\d{6})Y([+-]\d{6})", line)
            if location is None:
                raise ValueError("Missing IPC coordinate")
            records.append(dict(kind=line[:3], signal=line[3:17].strip(), ref=line[20:26].strip(),
                                pin=line[27:31].strip(), x_mm=int(location[1])*0.00254,
                                y_mm=int(location[2])*0.00254))
        elif not line.startswith("P  ") and line.rstrip() != "999":
            raise ValueError("Unsupported IPC record")
    return aliases, records


def check():
    export = json.loads((ROOT / "export-review.json").read_text())
    assert sha(PCB) == export["source_sha256"][str(PCB.relative_to(REPO))]
    capture = json.loads(CAPTURE.read_text())
    assert all(sha(recorded_path(name)) == digest for name, digest in capture["source_sha256"].items())
    board = read_sexpr(PCB.read_text())
    target = next(f for f in children(board, "footprint")
                  if any(p[1:3] == ["Reference", "R83"] for p in children(f, "property")))
    position = list(map(float, first(target, "at")[1:]))
    assert len(position) == 2 or position[2] == 0, "Explicit rotation handling required"
    r83 = {pad[1]: list(map(float, first(pad, "at")[1:3])) for pad in children(target, "pad")}
    expected = []
    for item in capture["objects"]:
        if item["kind"] not in ("PAD", "PCB_VIA"):
            continue
        if item["kind"] == "PCB_VIA":
            ref, pin, kind = "VIA", "", "317"
        else:
            ref, pin = item["ref"], item["pin"]
            kind = "367" if item["npth"] else "317" if any(item["drill_mm"]) else "327"
        x, y = item["position_mm"]
        if ref == "R83":
            x, y = position[0]+r83[pin][0], position[1]+r83[pin][1]
        expected.append(dict(kind=kind, ref=ref, pin=pin, net=item["net"], x_mm=x, y_mm=-y))
    path = ROOT / "test/rail_monitor.d356"
    aliases, records = parse(path.read_text())
    remaining, largest = list(expected), 0.0
    for actual in records:
        signal = actual["signal"]
        matches = [i for i, item in enumerate(remaining)
                   if all(item[k] == actual[k] for k in ("kind", "ref", "pin"))
                   and (aliases[signal] == item["net"] if signal in aliases else signal == (item["net"].upper() or "N/C"))
                   and abs(item["x_mm"]-actual["x_mm"]) <= 0.001270001
                   and abs(item["y_mm"]-actual["y_mm"]) <= 0.001270001]
        if len(matches) != 1:
            raise ValueError("IPC point/net/origin mismatch: "+str(actual))
        item = remaining.pop(matches[0])
        largest = max(largest, abs(item["x_mm"]-actual["x_mm"]), abs(item["y_mm"]-actual["y_mm"]))
    assert not remaining
    return dict(source_sha256={str(p.relative_to(REPO)): sha(p) for p in (path, CAPTURE, PCB, Path(__file__))},
                point_counts=dict(Counter(r["kind"] for r in records)), total_points=len(records), aliases=len(aliases),
                all_point_identifiers_net_names_and_coordinates_match=True,
                units="0.0001 inch (0.00254 mm), degrees; KiCad CUST 0",
                maximum_axis_quantization_error_mm=largest, axis_tolerance_mm=0.001270001,
                exporter_reference="https://raw.githubusercontent.com/KiCad/kicad-source-mirror/10.0.7/pcbnew/exporters/export_d356.cpp",
                physical_bare_board_electrical_test_performed=False, fabrication_approved=False)


if __name__ == "__main__":
    report = check()
    with (ROOT / "test/ipc-inspection.json").open("x") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print(json.dumps({k: report[k] for k in ("point_counts", "total_points", "maximum_axis_quantization_error_mm")}))
