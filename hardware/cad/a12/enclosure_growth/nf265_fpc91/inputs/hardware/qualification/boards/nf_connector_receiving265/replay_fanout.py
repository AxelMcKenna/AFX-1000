"""Fresh continuous406-pair replay using the actual preserved NC01 functions."""

import argparse
import copy
import hashlib
import importlib
import json
import shutil
import sys
from pathlib import Path

from hardware.qualification.boards.nf_connector_receiving import local_fanout

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run(out):
    if out.exists():
        raise RuntimeError("Fresh proof output required")
    modules = [
        local_fanout,
        importlib.import_module("hardware.qualification.boards.nf_connector_receiving.study"),
        importlib.import_module("hardware.cad.a12.enclosure_growth.front_bay_receiving.escape_certificate"),
        importlib.import_module("hardware.cad.a12.enclosure_growth.front_bay_receiving.capture"),
        importlib.import_module("hardware.electronics.common.sexpr"),
    ]
    sources = [Path(m.__file__).resolve() for m in modules] + [
        Path(__file__),
        ROOT / "inputs/references/NC01-local-fanout.json",
        ROOT / "ports-v2.json",
    ]
    bindings = {str(p): sha(p) for p in sources}
    out.mkdir()
    copies = {}
    for p in sources:
        to = out / "captured-source" / p.relative_to(REPO)
        to.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, to)
        if sha(to) != bindings[str(p)]:
            raise ValueError("Proof source copy changed")
        copies[str(to)] = sha(to)
    source = json.loads((ROOT / "inputs/references/NC01-local-fanout.json").read_text())
    routes = [r for r in source["routes"] if r["circuit"] != 4]
    required = source["required_centerline_separation_mm"]
    certificates = {}
    for i, a in enumerate(routes):
        for b in routes[i + 1 :]:
            certificates[str(a["circuit"]) + "-" + str(b["circuit"])] = local_fanout.certify(a, b, required)
    a = copy.deepcopy(next(r for r in routes if r["circuit"] == 1))
    b = next(r for r in routes if r["circuit"] == 2)
    a["straight_mm"] = 0
    rejected = local_fanout.certify(a, b, required)
    if (
        len(certificates) != 406
        or not all(c["certified"] for c in certificates.values())
        or rejected["certified"]
    ):
        raise ValueError("Continuous proof/control failure")
    changed = [str(p) for p in sources if sha(p) != bindings[str(p)]]
    report = dict(
        revision="NC265-fresh-continuous-pair-replay",
        runtime=sys.version,
        source_sha256=bindings,
        captured_source_sha256=copies,
        actual_pair_count=406,
        required_distance_mm=required,
        certificates=certificates,
        unstaggered_samecolumn_negative_control=rejected,
        changed_inputs=changed,
        all406_replayed_continuously=True,
        sampled_minimum_used=False,
        rigid_isometry_to_actual_port_pose_does_NOT_change_distances=True,
        actual_mate_entry_host_destinations_and_wholeunit_fit_qualified=False,
        physical_qualified=False,
    )
    (out / "proof.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            dict(pairs=406, continuous=True, unstaggered_rejected=not rejected["certified"], changed=changed)
        )
    )
    raise SystemExit(bool(changed))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args().output.resolve())
