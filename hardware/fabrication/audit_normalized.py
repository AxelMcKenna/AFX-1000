"""Compare legacy/current PCB geometry after read-only Linux format loading.

Some old sources omit UUIDs and use numeric net codes. Native loading assigns
identities and resolves nets. Ignore those generated identities and refill
polygons; retain every authored geometric/assembly/process attribute.
"""

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

from hardware.electronics.common.sexpr import read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(node):
    if not isinstance(node, list):
        return node
    if node and node[0] in ("uuid", "tstamp", "filled_polygon"):
        return None
    values = [value for item in node if (value := canonical(item)) is not None]
    # Point order defines polygon/curve geometry. Other tagged children are
    # named attributes or independent objects whose saved order has no effect.
    if values and values[0] not in ("pts",):
        atoms = [v for v in values if not isinstance(v, list)]
        nested = sorted((v for v in values if isinstance(v, list)), key=sexpr)
        return atoms+nested
    return values


def run():
    assert sys.platform == "linux", "Mac CAD remains disabled"
    import pcbnew

    parser = argparse.ArgumentParser()
    parser.add_argument("roles", nargs="+")
    args = parser.parse_args()
    scope = json.loads((ROOT/"scope.json").read_text())
    rows = {row["role"]: row for row in scope["roles"]}
    for role in args.roles:
        row = rows[role]
        before = (REPO/row["previous_source"]).with_suffix(".kicad_pcb")
        after = (REPO/row["source"]).with_suffix(".kicad_pcb")
        assert before.is_relative_to(REPO) and after.is_relative_to(ROOT/"staging")
        output = ROOT/"staging"/("normalized-audit-"+role)
        output.mkdir(exist_ok=False)
        hashes = {str(p): sha(p) for p in (before, after, Path(__file__))}
        normalized = []
        for label, path in (("before",before),("after",after)):
            board = pcbnew.LoadBoard(str(path))
            destination = output/(label+".kicad_pcb")
            assert pcbnew.SaveBoard(str(destination),board)
            normalized.append(destination)
        left, right = [canonical(read_sexpr(p.read_text())) for p in normalized]
        old, new = Counter(sexpr(v) for v in left[1:]), Counter(sexpr(v) for v in right[1:])
        differences = dict(removed=list((old-new).elements()),added=list((new-old).elements()))
        exact = left[0] == right[0] and not any(differences.values())
        assert all(sha(Path(p)) == digest for p,digest in hashes.items())
        report = dict(source_sha256=hashes,normalized_sha256={p.name:sha(p) for p in normalized},
            native_version=pcbnew.GetBuildVersion(),authored_geometry_and_attributes_equivalent=exact,
            ignored_only_UUID_tstamp_and_derived_filled_polygon=True,differences=differences,
            Mac_CAD_launches=0,physical_qualified=False,fabrication_released=False)
        (output/"review.json").write_text(json.dumps(report,indent=2)+"\n")
        print(role,"normalized geometry equivalent",exact,flush=True)


if __name__ == "__main__":
    run()
