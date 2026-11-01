"""Exact five-hole exception trial; original timing locks remain unchanged.

Run with KiCad Python. Requires native direct attachment plus independent
intersection with every same-net filled zone on every actual copper layer.
Actual native track/zone/second-pad mutations are emitted for rejection tests.
No native finding is suppressed and no candidate is promoted by this tool.
"""

import argparse
import copy
import hashlib
import json
import math
import shutil
import uuid
from pathlib import Path

import pcbnew

from ...common.sexpr import a, children, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent
SOURCE_HASH = "8fca7a59b585654c60ee332b82fe97c7ac51d42928306aa8ef724dc7b4ae022f"
ALLOW = {
    "27277f86-6b0e-5559-8539-6dd20370fbbd": ("R98", "1", "/E28_ANA_0_DVDT", 135.2875, 110.25),
    "993b2921-3c15-506d-8ad4-f1989b8d12d6": ("C39", "1", "/E28_ANA_0_DVDT_CAP", 145, 108),
    "c0f4f77c-4d0f-563d-84aa-6ab6c6a15de3": ("R98", "2", "/E28_ANA_0_DVDT_CAP", 137.1125, 110.25),
    "9702189c-a0e7-5388-b24e-83b613dfe55e": ("R97", "1", "/E28_ANA_0_ILM", 136.5, 105.9125),
    "14d9a182-040a-51c1-94a3-8d07b4ec5a12": ("R101", "1", "/E28_ANA_1_ILM", 137.3875, 112.7),
}
LAYERS = ("F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu")


def measure(board, identity):
    board.BuildConnectivity()
    connection = board.GetConnectivity()
    via = next(i for i in board.GetTracks() if i.m_Uuid.AsString() == identity)
    assert via.GetClass() == "PCB_VIA" and board.GetCopperLayerCount() == 6
    pads = list(connection.GetConnectedPads(via))
    tracks = list(connection.GetConnectedTracks(via))
    neighbors = [i for i in connection.GetConnectedItems(via) if i.m_Uuid.AsString() != identity]
    attached, zone_contacts, checked_layers = [], [], []
    for name in LAYERS:
        layer = board.GetLayerID(name)
        assert via.IsOnLayer(layer)
        checked_layers.append(name)
        if connection.IsConnectedOnLayer(via, layer):
            attached.append(name)
        land = pcbnew.SHAPE_POLY_SET()
        # Conservative outer native shape: even a marginal contact rejects.
        via.TransformShapeToPolygon(land, layer, 0, pcbnew.FromMM(0.001), pcbnew.ERROR_OUTSIDE)
        for zone in board.Zones():
            if zone.GetIsRuleArea() or zone.GetNetCode() != via.GetNetCode() or not zone.IsOnLayer(layer):
                continue
            intersection = pcbnew.SHAPE_POLY_SET()
            intersection.BooleanIntersection(land, zone.GetFilledPolysList(layer))
            if intersection.Area() > 0:
                zone_contacts.append(
                    dict(
                        zone_uuid=zone.m_Uuid.AsString(),
                        layer=name,
                        contact_area_mm2=intersection.Area() / 1e12,
                    )
                )
    return dict(
        uuid=identity,
        net=via.GetNetname(),
        position_native_mm=[via.GetPosition().x / 1e6, via.GetPosition().y / 1e6],
        attached_tracks=len(tracks),
        same_net_zone_contacts=zone_contacts,
        pad_contacts=[
            dict(
                ref=p.GetParentFootprint().GetReference(),
                pin=p.GetNumber(),
                smd=p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD,
                layers=[name for name in LAYERS if p.IsOnLayer(board.GetLayerID(name))],
            )
            for p in pads
        ],
        attached_copper_layers=attached,
        actual_filled_layers_checked=checked_layers,
        direct_neighbor_classes=sorted(i.GetClass() for i in neighbors),
    )


def require_unused(row):
    assert row["uuid"] in ALLOW, "Not in exact five-hole exception"
    assert row["attached_tracks"] == 0, "Operative track connection"
    assert not row["same_net_zone_contacts"], "Operative filled-zone connection"
    assert len(row["pad_contacts"]) == 1, "Must touch exactly one physical pad"
    pad = row["pad_contacts"][0]
    assert pad["smd"] and len(row["attached_copper_layers"]) == 1
    assert row["attached_copper_layers"][0] in pad["layers"]
    assert row["direct_neighbor_classes"] == ["PAD"], "Second pad or operative barrel path"
    assert row["actual_filled_layers_checked"] == list(LAYERS)
    ref, pin, net, x, y = ALLOW[row["uuid"]]
    assert (pad["ref"], pad["pin"], row["net"]) == (ref, pin, net)
    assert math.dist(row["position_native_mm"], (x, y)) < 1e-8


def generate(workspace):
    source = ROOT / "generated/p9-pruned-leaf-reviewed-work"
    path = source / "rail_disconnect.kicad_pcb"
    before = path.read_bytes()
    assert hashlib.sha256(before).hexdigest() == SOURCE_HASH
    receipt = json.loads((source / "generated/native-pruned-leaf1.json").read_text())
    assert receipt["pcb_sha256"] == SOURCE_HASH
    filled = source / "generated/filled-pruned-leaf1.kicad_pcb"
    board = pcbnew.LoadBoard(str(filled))
    rows = [measure(board, uid) for uid in ALLOW]
    for row in rows:
        require_unused(row)
    contract_path = ROOT / "generated/leaf-prune-source-lock-contract.json"
    contract = json.loads(contract_path.read_text())
    locked = {r["uuid"]: r for r in contract["locked_copper"]}
    assert set(ALLOW) <= set(locked)
    tree = read_sexpr(before.decode())
    copper = {
        str(first(n, "uuid")[1]): n for n in tree if isinstance(n, list) and n and n[0] in ("via", "segment")
    }
    assert all(
        hashlib.sha256(sexpr(copper[uid]).encode()).hexdigest() == row["native_object_sha256"]
        for uid, row in locked.items()
    )
    removed = [copper[uid] for uid in ALLOW]
    assert all(n[0] == "via" for n in removed)
    candidate = [n for n in tree if n not in removed]
    workspace = Path(workspace).resolve()
    assert workspace.is_relative_to(ROOT / "generated") and not workspace.exists()
    workspace.mkdir()
    (workspace / "generated/mutations").mkdir(parents=True)
    for p in source.iterdir():
        if p.is_file() and (
            p.suffix in (".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_sym")
            or p.name in ("components.json", "fp-lib-table", "sym-lib-table")
        ):
            shutil.copy2(p, workspace / p.name)
        elif p.suffix == ".pretty":
            shutil.copytree(p, workspace / p.name)
    (workspace / path.name).write_text(sexpr(candidate) + "\n")
    uid = next(iter(ALLOW))
    _, _, net, x, y = ALLOW[uid]
    code = first(copper[uid], "net")[1]
    mutants = {}
    track = copy.deepcopy(tree)
    track.append(
        read_sexpr(
            f'(segment (start {x} {y}) (end {x + 0.05:.6f} {y}) (width .2) (layer "B.Cu") (net {code}) (uuid {uuid.uuid5(uuid.NAMESPACE_URL, "E28:negative:leaf-track")}))'
        )
    )
    mutants["track"] = track
    zone = copy.deepcopy(tree)
    z = copy.deepcopy(children(zone, "zone")[0])
    z[:] = [
        n
        for n in z
        if not (isinstance(n, list) and n and n[0] in ("polygon", "filled_polygon", "fill_segments", "uuid"))
    ]
    first(z, "net")[1] = code
    first(z, "net_name")[1] = net
    first(z, "layer")[1] = "F.Cu"
    first(z, "priority")[1] = a("99999")
    first(z, "min_thickness")[1] = a(".2")
    z.append(
        read_sexpr(
            f"(polygon (pts (xy {x - 0.4:.6f} {y - 0.4:.6f}) (xy {x + 0.4:.6f} {y - 0.4:.6f}) (xy {x + 0.4:.6f} {y + 0.4:.6f}) (xy {x - 0.4:.6f} {y + 0.4:.6f})))"
        )
    )
    z.append([a("uuid"), str(uuid.uuid5(uuid.NAMESPACE_URL, "E28:negative:leaf-zone"))])
    zone.append(z)
    mutants["zone"] = zone
    two = copy.deepcopy(tree)
    fp = next(
        f
        for f in children(two, "footprint")
        if next(p[2] for p in children(f, "property") if p[1] == "Reference") == "R98"
    )
    pad = copy.deepcopy(next(p for p in children(fp, "pad") if p[1] == "1"))
    pad[1] = "NEGATIVE_CONTROL_ONLY"
    fp.append(pad)
    mutants["two-pad"] = two
    for label, mutant in mutants.items():
        (workspace / f"generated/mutations/{label}.kicad_pcb").write_text(sexpr(mutant) + "\n")
    report = dict(
        source_pcb_sha256=SOURCE_HASH,
        filled_pcb_sha256=hashlib.sha256(filled.read_bytes()).hexdigest(),
        original_lock_contract_sha256=hashlib.sha256(contract_path.read_bytes()).hexdigest(),
        source_recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        source_bound_exact_allowlist=ALLOW,
        independent_native_rows=rows,
        removed_actual_objects=[sexpr(n) for n in removed],
        all_other_original_locked_copper_preserved=True,
        original_global_lock_contract_unmodified=True,
        all_timing_pads_values_poses_and_operative_routes_preserved=True,
        candidate_pcb_sha256=hashlib.sha256((workspace / path.name).read_bytes()).hexdigest(),
        actual_native_negative_controls_pending=True,
        fresh_native_fill_force_and_return_checks_required=True,
        physical_qualified=False,
        production_release=False,
    )
    (workspace / "generated/timing-leaf-exception.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Exact five nonoperative holes removed; original locks retained outside this exception")


def check_mutations(workspace):
    workspace = Path(workspace)
    rows = []
    for label in ("track", "zone", "two-pad"):
        filled = workspace / f"generated/filled-negative-{label}.kicad_pcb"
        row = measure(pcbnew.LoadBoard(str(filled)), next(iter(ALLOW)))
        rejected = False
        try:
            require_unused(row)
        except AssertionError as e:
            rejected = True
            reason = str(e)
        assert rejected, (label, "Native mutation was not rejected")
        rows.append(
            dict(
                label=label,
                filled_pcb_sha256=hashlib.sha256(filled.read_bytes()).hexdigest(),
                actual_native_measurement=row,
                rejected=True,
                reason=reason,
                negative_control_only_never_candidate=True,
            )
        )
    (workspace / "generated/native-negative-controls.json").write_text(
        json.dumps(
            dict(
                rows=rows,
                all_three_actual_native_mutations_rejected=True,
                reviewer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            ),
            indent=2,
        )
        + "\n"
    )
    print("Rejected actual native track, filled-zone and second-pad mutations")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("workspace", type=Path)
    p.add_argument("--check-mutations", action="store_true")
    args = p.parse_args()
    (check_mutations if args.check_mutations else generate)(args.workspace)
