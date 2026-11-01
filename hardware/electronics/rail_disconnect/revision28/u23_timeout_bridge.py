"""Shift one unlocked TIMEOUT bridge 0.3 mm, then join the real UV-fault pads."""

import copy
import hashlib
import json
import math
import shutil
import uuid
from pathlib import Path

from ...common.sexpr import a, children, first, read_sexpr, sexpr
from .repair import Router
from .u23_band_route_2d import path_between

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/u23-band-reconnect1-work"
WORK = ROOT / "generated/u23-timeout-bridge-work"
TRACKS = {"4e40f3f5-e64f-5a07-9f57-cfa731de890f", "1f8f0c12-a3aa-51c6-85c0-edbd7e372e7a"}
UNUSED_NEW_UV_VIA = "9d3c392d-05fe-510d-8d3a-ef2bc4eddae5"


def main():
    assert not WORK.exists()
    path = SOURCE / "rail_disconnect.kicad_pcb"
    before = path.read_bytes()
    source_sha = hashlib.sha256(before).hexdigest()
    tree = read_sexpr(before.decode())
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    net_ids = {v: k for k, v in names.items()}
    locked = {
        r["uuid"]
        for r in json.loads((ROOT / "generated/leaf-prune-source-lock-contract.json").read_text())[
            "locked_copper"
        ]
    }
    probe = json.loads((SOURCE / "generated/timeout-via-shift-probe.json").read_text())
    assert probe["source_pcb_sha256"] == source_sha
    assert any(math.dist(p["xy"], (135, 32.7)) < 1e-8 for p in probe["candidates"])
    changes = []
    for node in children(tree, "via") + children(tree, "segment"):
        uid = str(first(node, "uuid")[1])
        is_bridge = (
            node[0] == "via"
            and names[str(first(node, "net")[1])] == "E28_TIMEOUT"
            and math.dist(tuple(float(x) for x in first(node, "at")[1:3]), (235.3, 132.7)) < 1e-7
        )
        if uid not in TRACKS and not is_bridge:
            continue
        assert uid not in locked and names[str(first(node, "net")[1])] == "E28_TIMEOUT"
        old = copy.deepcopy(node)
        if is_bridge:
            first(node, "at")[1] = a("235")
        else:
            touched = 0
            for endpoint in ("start", "end"):
                p = first(node, endpoint)
                if math.dist(tuple(float(v) for v in p[1:3]), (235.3, 132.7)) < 1e-7:
                    p[1] = a("235")
                    touched += 1
            assert touched == 1
        changes.append(dict(before=sexpr(old), after=sexpr(node)))
    assert len(changes) == 3
    router = Router(tree)
    source = next(p for p in router.by_ref["U26"] if p["pin"] == "3")
    assert source["net"] == "E28_OUT_UV_FAULT" and source["layers"] == (5,)
    target = (129.5, 46.85)
    attempts = []
    for margin in (3, 5):
        try:
            points, visited = path_between(
                router, source["xy"], target, 5, margin=margin, step=0.025, net=source["net"]
            )
            attempts.append(dict(margin=margin, points_mm=points, visited_cells=visited))
            break
        except AssertionError as error:
            attempts.append(dict(margin=margin, failed=str(error)))
    assert "points_mm" in attempts[-1], attempts
    added = []
    for index, (one, two) in enumerate(zip(points, points[1:])):
        if math.dist(one, two) < 1e-8:
            continue
        uid = uuid.uuid5(uuid.NAMESPACE_URL, f"rmx:E28:U23UVbridge:{source_sha}:{index}:{one}:{two}")
        node = read_sexpr(
            f'(segment (start {one[0] + 100:.6f} {one[1] + 100:.6f}) (end {two[0] + 100:.6f} {two[1] + 100:.6f}) (width .2) (layer "B.Cu") (net {net_ids[source["net"]]}) (uuid {uid}))'
        )
        tree.append(node)
        added.append(sexpr(node))
    # The newly added UV route meets its existing B.Cu fanout stem exactly.
    # Its unused through barrel is unnecessary: the two real .2mm tracks
    # remain a continuous surface junction, with no new drill or fake part.
    removed = [n for n in children(tree, "via") if str(first(n, "uuid")[1]) == UNUSED_NEW_UV_VIA]
    assert len(removed) == 1 and names[str(first(removed[0], "net")[1])] == source["net"]
    assert math.dist(tuple(float(v) - 100 for v in first(removed[0], "at")[1:3]), target) < 1e-8
    meeting = [
        n
        for n in children(tree, "segment")
        if str(first(n, "net")[1]) == net_ids[source["net"]]
        and first(n, "layer")[1] == "B.Cu"
        and any(
            math.dist(tuple(float(v) - 100 for v in first(n, end)[1:3]), target) < 1e-7
            for end in ("start", "end")
        )
    ]
    assert len(meeting) >= 2
    tree.remove(removed[0])
    WORK.mkdir()
    (WORK / "generated").mkdir()
    for p in SOURCE.iterdir():
        if p.is_file() and (
            p.suffix in (".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_sym")
            or p.name in ("components.json", "fp-lib-table", "sym-lib-table")
        ):
            shutil.copy2(p, WORK / p.name)
        elif p.suffix == ".pretty":
            shutil.copytree(p, WORK / p.name)
    (WORK / path.name).write_text(sexpr(tree) + "\n")
    result = dict(
        source_pcb_sha256=source_sha,
        recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        source_probe_sha256=hashlib.sha256(
            (SOURCE / "generated/timeout-via-shift-probe.json").read_bytes()
        ).hexdigest(),
        exact_unlocked_bridge_changes=changes,
        actual_UV_surface_route=attempts,
        added_segments=added,
        removed_unneeded_new_B_only_barrel=sexpr(removed[0]),
        actual_meeting_B_tracks=len(meeting),
        all_other_copper_poses_rules_and_package_contracts_unchanged=True,
        new_native_PDN_MCAD_required=True,
        physical_qualified=False,
    )
    (WORK / "generated/timeout-bridge-route.json").write_text(json.dumps(result, indent=2) + "\n")
    assert path.read_bytes() == before
    print("Specific TIMEOUT bridge shifted; actual UV-fault B.Cu join written", flush=True)


if __name__ == "__main__":
    main()
