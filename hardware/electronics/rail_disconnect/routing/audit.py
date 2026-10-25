"""Classify remaining native endpoint masks; no claim of routing impossibility."""

import json
import re
from collections import Counter, deque
from pathlib import Path

from ...common.reports import sha
from ...common.sexpr import read_sexpr
from . import router as aid

ROOT = Path(__file__).resolve().parent


def main():
    out = ROOT / "generated"
    native = json.loads((out / "drc.json").read_text())
    assert not native["violations"] and not native["schematic_parity"]
    aid.STEP = 0.125
    r = aid.Router(read_sexpr((ROOT / "rail_disconnect.kicad_pcb").read_text()))
    r.load_existing_copper()
    groups = {}
    seen_pads = set()
    counts = Counter()
    blocked_pads = []
    no_local_via_escape = []
    for item in native["unconnected_items"]:
        for endpoint in item["items"]:
            text = endpoint["description"]
            net = re.search(r"\[/(.*?)\]", text).group(1)
            counts[net] += 0.5
            if not re.search(r"\b[Pp]ad ", text):
                continue
            ref = re.search(r" of (\w+)(?: on |$)", text).group(1)
            xy = (endpoint["pos"]["x"] - 100, endpoint["pos"]["y"] - 100)
            pad = min(
                (p for p in r.by_ref[ref] if p["net"] == net),
                key=lambda p: (p["xy"][0] - xy[0]) ** 2 + (p["xy"][1] - xy[1]) ** 2,
            )
            key = (ref, pad["pin"], tuple(pad["xy"]))
            if key in seen_pads:
                continue
            seen_pads.add(key)
            if net not in groups:
                groups[net] = []
            groups[net].append((text, pad))
    for net, items in groups.items():
        width = (
            1.0
            if net in ("5V_DIG", "5V_DIG_SRC")
            else 0.5
            if net
            in (
                "P19",
                "P19_SRC",
                "N19",
                "N19_SRC",
                "P12",
                "P12_SRC",
                "N12",
                "N12_SRC",
                "V5_REG",
                "V5_REG_SRC",
                "AGND",
            )
            else 0.25
        )
        block, via = r.masks(net, width)
        for text, p in items:
            x, y = (round(v / aid.STEP) for v in p["xy"])
            face_blocked = all(block[z, x, y] for z in p["layers"])
            if not face_blocked and len(p["layers"]) == 1:
                layer = p["layers"][0]
                queue = deque([(x, y)])
                visited = {(x, y)}
                reachable_vias = 0
                while queue:
                    u, v = queue.popleft()
                    if not via[u, v]:
                        reachable_vias += 1
                    for du, dv in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        other = (u + du, v + dv)
                        if (
                            0 <= other[0] < r.nx
                            and 0 <= other[1] < r.ny
                            and abs(other[0] - x) <= 32
                            and abs(other[1] - y) <= 32
                            and other not in visited
                            and not block[layer, other[0], other[1]]
                        ):
                            visited.add(other)
                            queue.append(other)
                if reachable_vias == 0:
                    no_local_via_escape.append(
                        dict(
                            endpoint=text,
                            net=net,
                            point_relative_mm=p["xy"],
                            requested_route_width_mm=width,
                            bounded_search_radius_mm=4,
                            accessible_surface_grid_nodes=len(visited),
                        )
                    )
            if face_blocked:
                blocked_pads.append(
                    dict(
                        endpoint=text,
                        net=net,
                        point_relative_mm=p["xy"],
                        requested_route_width_mm=width,
                        nearest_grid_point_blocked=True,
                    )
                )
    report = dict(
        scope="Diagnostics for the actual remaining native connections; blocked mask samples do not prove geometric impossibility.",
        pcb_sha256=sha(ROOT / "rail_disconnect.kicad_pcb"),
        native_drc_sha256=sha(out / "drc.json"),
        native_open_connections=len(native["unconnected_items"]),
        grid_mm=aid.STEP,
        native_opens_by_net=dict(sorted(counts.items())),
        pad_endpoints_blocked_at_requested_trace_width=blocked_pads,
        pad_endpoints_without_surface_access_to_a_conventional_via_within_4mm=no_local_via_escape,
        required_followup=[
            "Reserve conventional via escapes before routing global traces; current resistor courtyards were packed independently of escape channels.",
            "Revise placement in a new board/CAD variant if via escapes require moved bottom resistors or wider channel corridors; preserve the original E25/A11 certificates.",
            "Use a narrow local pin neck only where independently justified, followed by wider high-current copper; do not make all ground or rail copper thin to force connectivity.",
            "Rework source/protected rail and return distribution using a reviewed stackup and loss model. Existing0.5/1mm exploratory trunks do not qualify current sharing, copper loss or heat.",
        ],
        geometric_impossibility_proven=False,
        pcb_routed=False,
        build_ready=False,
    )
    (out / "escape-audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        len(native["unconnected_items"]),
        "native opens;",
        len(blocked_pads),
        "pad endpoint samples blocked at requested trace widths;",
        len(no_local_via_escape),
        "without a local conventional-via escape within4mm",
    )


if __name__ == "__main__":
    main()
