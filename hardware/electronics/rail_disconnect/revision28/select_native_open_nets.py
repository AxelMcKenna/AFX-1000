"""FR-only routing classes selected from actual fresh native airwires.

Native-complete nets remain present as copper/obstacles under the existing lock contract. All native nets,
DRC severities, constraints, package geometry and force fills are still checked.
Only router work selection changes; no PCB rule or native finding is exempted.
"""

import argparse
import copy
import hashlib
import json
import re
from pathlib import Path

from ...common.sexpr import a, read_sexpr, sexpr


def span(text, start):
    depth = 0
    quoted = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return start, index + 1
    raise ValueError("Unclosed DSN class")


def main(workspace, receipt_path, drc_path):
    workspace = Path(workspace).resolve()
    receipt_path = Path(receipt_path)
    drc_path = Path(drc_path)
    metadata_path = workspace / "export.json"
    metadata = json.loads(metadata_path.read_text())
    receipt = json.loads(receipt_path.read_text())
    raw = json.loads(drc_path.read_text())
    assert receipt["pcb_sha256"] == metadata["source_pcb_sha256"]
    assert receipt["drc_sha256"] == hashlib.sha256(drc_path.read_bytes()).hexdigest()
    assert not any(v["severity"] == "error" for v in raw["violations"])
    needed = set()
    for finding in raw["unconnected_items"]:
        names = {
            m.lstrip("/") for i in finding["items"] for m in re.findall(r"\[([^\]]+)\]", i["description"])
        }
        assert len(names) == 1, "Require unambiguous actual native airwire net"
        needed.update(names)
    dsn = workspace / metadata["dsn_filename"]
    before = dsn.read_text()
    assert hashlib.sha256(dsn.read_bytes()).hexdigest() == metadata["dsn_sha256"]
    assert "(class_class" not in before, "Cross-class rules need a separate complete translation"
    ranges = [
        span(before, m.start() + len(m.group()) - len("(class"))
        for m in re.finditer(r"(?m)^    \(class\b", before)
    ]
    assert ranges
    changes = []
    active = set()
    completed = set()
    ignored = []
    for start, end in ranges:
        node = read_sexpr(before[start:end])
        assert node[0] == "class"
        members = [n for n in node[2:] if not isinstance(n, list)]
        settings = [n for n in node[2:] if isinstance(n, list)]
        opens = [n for n in members if str(n).lstrip("/") in needed]
        done = [n for n in members if str(n).lstrip("/") not in needed]
        active.update(str(n).lstrip("/") for n in opens)
        completed.update(str(n).lstrip("/") for n in done)
        replacements = []
        for prefix, nets in (("afx_native_open_", opens), ("afx_native_complete_", done)):
            if not nets:
                continue
            name = prefix + str(node[1])
            new = [a("class"), a(name), *nets, *copy.deepcopy(settings)]
            replacements.append(sexpr(new))
            if prefix == "afx_native_complete_":
                ignored.append(name)
        changes.append(
            dict(
                start=start,
                end=end,
                original=before[start:end],
                replacement="\n    ".join(replacements),
                unchanged_class_settings_sha256=hashlib.sha256(sexpr(settings).encode()).hexdigest(),
            )
        )
    assert needed <= active and active.isdisjoint(completed)
    text = before
    for row in reversed(changes):
        text = text[: row["start"]] + row["replacement"] + text[row["end"] :]
    selector = dict(
        source_pcb_sha256=receipt["pcb_sha256"],
        raw_native_drc_sha256=receipt["drc_sha256"],
        original_dsn_sha256=metadata["dsn_sha256"],
        active_native_open_nets=sorted(active),
        excluded_only_from_router_work_native_complete_nets=sorted(completed),
        ignore_net_classes=ignored,
        changed_classes=changes,
        selector_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        native_findings_or_constraints_exempted=False,
        physical_qualified=False,
    )
    digest = hashlib.sha256(json.dumps(selector, sort_keys=True).encode()).hexdigest()
    name = "afx-" + hashlib.sha256((metadata["design_name"] + digest).encode()).hexdigest()[:24]
    selected = workspace / (name + ".dsn")
    assert not selected.exists()
    selected.write_text(text)
    (workspace / "export-before-native-selection.json").write_text(json.dumps(metadata, indent=2) + "\n")
    selection_path = workspace / "native-route-selection.json"
    selection_path.write_text(json.dumps(selector, indent=2) + "\n")
    metadata.update(
        design_name=name,
        dsn_filename=selected.name,
        dsn_sha256=hashlib.sha256(selected.read_bytes()).hexdigest(),
        native_route_selection_sha256=hashlib.sha256(selection_path.read_bytes()).hexdigest(),
        autorouter_ignore_net_classes=ignored,
    )
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
    print(
        "Actual native-open nets",
        len(active),
        "; native-complete nets excluded from router work",
        len(completed),
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("workspace")
    p.add_argument("receipt_path")
    p.add_argument("drc_path")
    args = p.parse_args()
    main(args.workspace, args.receipt_path, args.drc_path)
