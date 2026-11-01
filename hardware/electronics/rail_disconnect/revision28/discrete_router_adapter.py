"""Route discrete signals without fictitious DSN plane connectivity.

Actual filled-force guards and protected objects stay present. All native
planes stay in the real PCB. Ground routing is deferred, not exempted from
native checks; no virtual electrical bridge is introduced.
"""

import argparse
import copy
import hashlib
import json
import re
from pathlib import Path

from ...common.sexpr import a, read_sexpr, sexpr
from .select_native_open_nets import span


def main(workspace):
    workspace = Path(workspace).resolve()
    assert workspace.is_relative_to(Path(__file__).resolve().parent / "generated")
    metadata_path = workspace / "export.json"
    meta = json.loads(metadata_path.read_text())
    assert meta.get("force_guard_receipt_sha256"), "Actual force guards are mandatory"
    assert meta.get("native_route_selection_sha256"), "Require current actual native open-net selection"
    dsn = workspace / meta["dsn_filename"]
    before = dsn.read_text()
    assert hashlib.sha256(dsn.read_bytes()).hexdigest() == meta["dsn_sha256"]
    ranges = [
        (span(before, m.end() - len("(plane")), "plane") for m in re.finditer(r"(?m)^[ \t]*\(plane\b", before)
    ]
    ranges += [
        (span(before, m.end() - len("(class")), "class") for m in re.finditer(r"(?m)^[ \t]*\(class\b", before)
    ]
    changes, omitted, ground_classes = [], [], []
    for (start, end), kind in sorted(ranges):
        literal = before[start:end]
        node = read_sexpr(literal)
        if kind == "plane":
            omitted.append(literal)
            changes.append((start, end, ""))
        else:
            members = [n for n in node[2:] if not isinstance(n, list)]
            ground = [n for n in members if str(n).lstrip("/") == "AGND"]
            if not ground:
                continue
            assert len(ground) == 1
            settings = [n for n in node[2:] if isinstance(n, list)]
            name = "afx_deferred_native_ground_" + str(node[1])
            ground_classes.append(name)
            remainder = [n for n in members if n not in ground]
            blocks = [sexpr([a("class"), a(name), *ground, *copy.deepcopy(settings)])]
            if remainder:
                blocks.append(sexpr([a("class"), node[1], *remainder, *copy.deepcopy(settings)]))
            changes.append((start, end, "\n".join(blocks)))
    assert omitted and len(ground_classes) == 1
    # Actual keepouts remain byte-identical and no artificial wiring is added.
    assert before.count('(keepout "force-') > 0
    text = before
    for start, end, replacement in reversed(changes):
        text = text[:start] + replacement + text[end:]
    assert not re.search(r"\(plane\b", text)
    selection = workspace / "native-route-selection.json"
    report = dict(
        original_dsn_sha256=meta["dsn_sha256"],
        original_native_route_selection_sha256=hashlib.sha256(selection.read_bytes()).hexdigest(),
        omitted_router_only_conduction_planes=omitted,
        deferred_ground_classes=ground_classes,
        actual_native_planes_or_finding_exemptions_changed=False,
        actual_force_keepouts_preserved=True,
        artificial_wiring_or_electrical_bridges_added=False,
        manual_ground_closure_and_all_native_findings_still_required=True,
        helper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        physical_qualified=False,
    )
    receipt_path = workspace / "discrete-router-adapter.json"
    receipt_path.write_text(json.dumps(report, indent=2) + "\n")
    (workspace / "export-before-discrete-routing.json").write_text(json.dumps(meta, indent=2) + "\n")
    name = (
        "afx-"
        + hashlib.sha256(
            (meta["design_name"] + hashlib.sha256(receipt_path.read_bytes()).hexdigest()).encode()
        ).hexdigest()[:24]
    )
    output = workspace / (name + ".dsn")
    output.write_text(text)
    meta.update(
        design_name=name,
        dsn_filename=output.name,
        dsn_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
        discrete_router_adapter_sha256=hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
        autorouter_ignore_net_classes=meta["autorouter_ignore_net_classes"] + ground_classes,
    )
    metadata_path.write_text(json.dumps(meta, indent=2) + "\n")
    print("Router-only planes omitted:", len(omitted), "; native ground deferred, all native checks retained")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("workspace")
    args = p.parse_args()
    main(args.workspace)
