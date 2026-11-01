"""Actual E19 5V trace-centreline network diagnostic, not a resistance bound.

Ideal zero-resistance pad/via contacts and full centreline segment lengths are
explicit approximations. No spreading, finite barrels, return plane, extracted
parasitics or accepted copper/process limits are inferred. Use this to expose
missing board distribution in the retained lumped harness model.
"""

import argparse
import json
import math
from pathlib import Path

from hardware.electronics.common.circuits import LU
from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.electronics.output_stage.check_placement import transform

from ..generate import REPO, sha

LAYERS = ("F.Cu", "In1.Cu", "In2.Cu", "B.Cu")


class Union:
    def __init__(self):
        self.parent = {}

    def root(self, key):
        self.parent.setdefault(key, key)
        while self.parent[key] != key:
            self.parent[key] = self.parent[self.parent[key]]
            key = self.parent[key]
        return key

    def join(self, a, b):
        self.parent[self.root(a)] = self.root(b)


def node(layer, xy):
    return (layer, round(xy[0], 6), round(xy[1], 6))


def run(workspace):
    out = workspace / "generated"
    proof = json.loads((out / "independent-review.json").read_text())
    hashes = dict(proof["source_sha256"])
    assert all(sha(REPO / n) == h for n, h in hashes.items())
    pcb = out / "filled.kicad_pcb"
    tree = read_sexpr(pcb.read_text())

    def netname(n):
        return str(first(n, "net")[-1]).lstrip("/") if children(n, "net") else ""

    # No positive plane is silently omitted from this track-only diagnostic.
    assert not any(netname(z) == "5V_DIG" for z in children(tree, "zone"))
    assert not any(netname(z) == "5V_DIG" for z in children(tree, "arc"))
    tracks, pad_nodes = [], {}
    union = Union()
    for t in children(tree, "segment"):
        if netname(t) != "5V_DIG":
            continue
        layer = str(first(t, "layer")[1])
        assert layer in LAYERS
        a, b = [tuple(map(float, first(t, key)[1:3])) for key in ["start", "end"]]
        na, nb = node(layer, a), node(layer, b)
        union.root(na)
        union.root(nb)
        tracks.append(
            dict(
                a=na,
                b=nb,
                length_mm=math.dist(a, b),
                width_mm=float(first(t, "width")[1]),
                uuid=str(first(t, "uuid")[1]),
            )
        )
    for via in children(tree, "via"):
        if netname(via) != "5V_DIG":
            continue
        assert first(via, "layers")[1:] == ["F.Cu", "B.Cu"]
        xy = tuple(map(float, first(via, "at")[1:3]))
        for layer in LAYERS:
            union.join(node("F.Cu", xy), node(layer, xy))
    for fp in children(tree, "footprint"):
        ref = next(p[2] for p in children(fp, "property") if p[1] == "Reference")
        for p in children(fp, "pad"):
            if netname(p) != "5V_DIG":
                continue
            xy = transform(fp, first(p, "at")[1:3])
            layers = (
                list(LAYERS)
                if "*.Cu" in first(p, "layers")[1:]
                else [l for l in LAYERS if l in first(p, "layers")[1:]]
            )
            nodes = [node(layer, xy) for layer in layers]
            for n in nodes:
                union.join(nodes[0], n)
            # Every routed 5V pad-centred contact must have a literal native
            # segment/via endpoint at its centre. Otherwise this simplified
            # model rejects, rather than inventing a connection through air.
            assert any(n in (t["a"], t["b"]) for n in nodes for t in tracks), (ref, p[1])
            pad_nodes[ref + "." + str(p[1])] = nodes[0]
    assert set(pad_nodes) == {"J1.1", "J11.2", "R1.1"}
    roots = sorted({union.root(n) for n in union.parent})
    idx = {n: i for i, n in enumerate(roots)}
    source = idx[union.root(pad_nodes["J1.1"])]
    free = [i for i in range(len(roots)) if i != source]
    local = {i: j for j, i in enumerate(free)}
    targets = {name: idx[union.root(pad_nodes[name])] for name in ["R1.1", "J11.2"]}
    loads = {"R1.1": 1.0, "J11.2": 0.380 + 4 * 0.096}
    cases = []
    for thickness in [0.035, 0.070]:
        for temperature in [20, 100]:
            rho = 1.724e-5 * (1 + 0.00393 * (temperature - 20))  # ohm mm; scenario material
            matrix = [[0.0] * len(free) for _ in free]
            for t in tracks:
                a, b = [idx[union.root(t[k])] for k in ["a", "b"]]
                if a == b:
                    continue
                g = t["width_mm"] * thickness / (rho * t["length_mm"])
                for x in [a, b]:
                    if x != source:
                        matrix[local[x]][local[x]] += g
                if source not in (a, b):
                    matrix[local[a]][local[b]] -= g
                    matrix[local[b]][local[a]] -= g
            lu = LU(matrix)
            columns = {}
            for name, target in targets.items():
                rhs = [0.0] * len(free)
                rhs[local[target]] = 1
                x = lu.solve(rhs)
                assert (
                    max(
                        abs(sum(matrix[i][j] * x[j] for j in range(len(free))) - rhs[i])
                        for i in range(len(free))
                    )
                    < 1e-9
                )
                columns[name] = {n: x[local[t]].real for n, t in targets.items()}
            drops = {name: sum(loads[n] * columns[n][name] for n in targets) for name in targets}
            assert math.isclose(columns["R1.1"]["J11.2"], columns["J11.2"]["R1.1"], rel_tol=1e-10)
            cases.append(
                dict(
                    copper_thickness_scenario_mm=thickness,
                    temperature_scenario_c=temperature,
                    transfer_resistance_ohm=columns,
                    simultaneous_positive_only_drop_v=drops,
                )
            )
    for p in [
        Path(__file__),
        pcb,
        out / "independent-review.json",
        REPO / "hardware/electronics/common/circuits.py",
    ]:
        hashes[str(p.relative_to(REPO))] = sha(p)
    assert all(sha(REPO / n) == h for n, h in hashes.items())
    report = dict(
        scope=__doc__,
        source_sha256=hashes,
        loads_a=loads,
        candidate_pcb_sha256=proof["candidate_pcb_sha256"],
        actual_track_count=len(tracks),
        track_total_length_mm=sum(t["length_mm"] for t in tracks),
        native_tracks=tracks,
        cases=cases,
        no_selected_E19_copper_stackup=True,
        ideal_pad_and_via_contacts=True,
        rigorous_upper_or_lower_bound=False,
        board_return_and_positive_coupled=False,
        complete_endpoint_analysis=False,
        current_path_resistance_qualified=False,
        physical_qualified=False,
        fabrication_released=False,
    )
    (out / "power-path-diagnostic.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(loads_a=loads, cases=cases), indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path)
    run(parser.parse_args().workspace.resolve())
