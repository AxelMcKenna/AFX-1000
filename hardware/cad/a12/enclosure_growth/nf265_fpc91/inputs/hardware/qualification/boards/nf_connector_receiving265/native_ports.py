"""Real KiCad connector-only prototype; never a complete NF265 board."""

import argparse
import hashlib
import json
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parent


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def vec(x, y):
    return pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))


def rectangle_rule(board, layer, bounds):
    a, b, c, d = bounds
    zone = pcbnew.ZONE(board)
    zone.SetLayer(layer)
    zone.SetIsRuleArea(True)
    for method in ["SetDoNotAllowPads", "SetDoNotAllowTracks", "SetDoNotAllowVias", "SetDoNotAllowZoneFills"]:
        getattr(zone, method)(True)
    outline = zone.Outline()
    outline.NewOutline()
    for x, y in [(a, b), (c, b), (c, d), (a, d)]:
        outline.Append(pcbnew.FromMM(x), pcbnew.FromMM(y))
    board.Add(zone)


def run(out):
    if out.exists():
        raise RuntimeError("Fresh connector prototype output required")
    p = ROOT / "ports.json"
    contract = json.loads(p.read_text())
    source = {str(p): sha(p), str(Path(__file__)): sha(Path(__file__))}
    for port in contract["ports"]:
        file = Path(port["footprint_file"])
        if sha(file) != port["footprint_sha256"]:
            raise ValueError("Changed actual candidate footprint")
        source[str(file)] = sha(file)
    out.mkdir()
    board = pcbnew.BOARD()
    board.SetCopperLayerCount(4)
    board.GetDesignSettings().SetBoardThickness(pcbnew.FromMM(1.6))
    nets = {}
    for name in sorted(
        {net for port in contract["ports"] for net in port["physical_pads"].values() if net is not None}
    ):
        net = pcbnew.NETINFO_ITEM(board, name)
        board.Add(net)
        nets[name] = net
    for port in contract["ports"]:
        file = Path(port["footprint_file"])
        fp = pcbnew.FootprintLoad(str(file.parent), file.stem)
        if fp is None:
            raise ValueError("Native footprint load failed")
        # Parent ownership is established before positioning; no unowned Flip
        # or dangling SettingsManager/Project is used in this prototype.
        board.Add(fp)
        fp.SetReference(port["ref"])
        fp.SetValue(port["header"] or "DIRECT_18AWG_FORCE")
        fp.SetFPID(pcbnew.LIB_ID("NC265", file.stem))
        fp.SetPosition(vec(*port["anchor_mm"]))
        fp.SetOrientationDegrees(port["rotation_deg"])
        for pad in fp.Pads():
            name = port["physical_pads"][pad.GetNumber()]
            if name is not None:
                pad.SetNet(nets[name])
    for a, b in [((0, 0), (149, 0)), ((149, 0), (149, 39)), ((149, 39), (0, 39)), ((0, 39), (0, 0))]:
        edge = pcbnew.PCB_SHAPE()
        edge.SetShape(pcbnew.SHAPE_T_SEGMENT)
        edge.SetLayer(pcbnew.Edge_Cuts)
        edge.SetStart(vec(*a))
        edge.SetEnd(vec(*b))
        edge.SetWidth(pcbnew.FromMM(0.05))
        board.Add(edge)
    for layer in [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]:
        for u in [38, 138]:
            for v0, v1 in [[0, 1.65], [37.35, 39]]:
                rectangle_rule(board, layer, [u - 3.6, v0, u + 3.6, v1])
    filename = out / "NC265_connector_prototype.kicad_pcb"
    if not pcbnew.SaveBoard(str(filename), board):
        raise ValueError("Native PCB save failed")
    (out / "fp-lib-table").write_text(
        '(fp_lib_table (lib (name "NC265")(type "KiCad")(uri "'
        + str(ROOT / "ConnectorCandidates.pretty")
        + '")(options "")(descr "NC265 candidate ports")))\n'
    )
    reloaded = pcbnew.LoadBoard(str(filename))
    actual = {}
    for fp in reloaded.GetFootprints():
        actual[fp.GetReference()] = dict(
            pads={
                pad.GetNumber(): dict(
                    net=pad.GetNetname() or None,
                    at_mm=[pcbnew.ToMM(pad.GetPosition().x), pcbnew.ToMM(pad.GetPosition().y)],
                    size_mm=[pcbnew.ToMM(pad.GetSize().x), pcbnew.ToMM(pad.GetSize().y)],
                    drill_mm=pcbnew.ToMM(pad.GetDrillSize().x),
                )
                for pad in fp.Pads()
            }
        )
    for port in contract["ports"]:
        saved = actual[port["ref"]]["pads"]
        if {n: v["net"] for n, v in saved.items()} != port["physical_pads"]:
            raise ValueError("Serialized physical pad/net mismatch")
    if (
        len(actual) != 6
        or sum(len(v["pads"]) for v in actual.values()) != 40
        or len(list(reloaded.Zones())) != 16
    ):
        raise ValueError("Incomplete actual native fixture")
    report = dict(
        revision="NC265-native-port-parser-and-pose",
        KiCad_version=pcbnew.Version(),
        actual=actual,
        pcb_sha256=sha(filename),
        source_sha256=source,
        clip_rule_areas=16,
        normalized_pin_parity_errors=0,
        prototype_scope="SIX CONNECTORS ONLY; no other259 components or full-board routing/qualification",
        physical_qualified=False,
        full_board_fit_certified=False,
        fabrication_released=False,
    )
    (out / "native-ports.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            dict(
                footprints=6,
                pads=40,
                native_saved_pinmap_errors=0,
                clip_all_layer_KOs=16,
                KiCad_version=pcbnew.Version(),
            )
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args().output.resolve())
