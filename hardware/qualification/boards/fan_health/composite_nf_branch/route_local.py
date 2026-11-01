"""Explicit new-stage local loops, leaving every parent copper object unchanged."""

import hashlib
import json
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parent


def main():
    assert not (ROOT / "handoff.json").exists()
    path = ROOT / "fan_power_health.kicad_pcb"
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    b = pcbnew.LoadBoard(str(path))
    nets = {n.GetNetname(): n for n in b.GetNetsByNetcode().values()}
    fp = {f.GetReference(): f for f in b.GetFootprints()}
    pads = {(r, p.GetNumber()): p for r, f in fp.items() for p in f.Pads() if p.GetNumber()}

    def p(ref, num):
        q = pads[(ref, str(num))].GetPosition()
        return (pcbnew.ToMM(q.x), pcbnew.ToMM(q.y))

    def xy(q):
        return pcbnew.VECTOR2I(pcbnew.FromMM(q[0]), pcbnew.FromMM(q[1]))

    records = []

    def line(net, layer, points, width=0.3):
        for a, z in zip(points, points[1:]):
            if a == z:
                continue
            t = pcbnew.PCB_TRACK(b)
            t.SetLayer(layer)
            t.SetStart(xy(a))
            t.SetEnd(xy(z))
            t.SetWidth(pcbnew.FromMM(width))
            t.SetNet(nets["/" + net])
            b.Add(t)
            records.append(
                dict(
                    kind="track",
                    uuid=t.m_Uuid.AsString(),
                    net=net,
                    layer=b.GetLayerName(layer),
                    a=a,
                    b=z,
                    width_mm=width,
                )
            )

    def via(net, where):
        v = pcbnew.PCB_VIA(b)
        v.SetPosition(xy(where))
        v.SetWidth(pcbnew.FromMM(0.65))
        v.SetDrill(pcbnew.FromMM(0.3))
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetNet(nets["/" + net])
        v.SetFrontTentingMode(pcbnew.TENTING_MODE_TENTED)
        v.SetBackTentingMode(pcbnew.TENTING_MODE_TENTED)
        b.Add(v)
        records.append(
            dict(kind="via", uuid=v.m_Uuid.AsString(), net=net, xy=where, land_mm=0.65, drill_mm=0.3)
        )

    F, B = pcbnew.F_Cu, pcbnew.B_Cu
    for net, pos in [
        ("FAN5V_IN", (13.8, 15.4)),
        ("FAN5V_IN", (11.1, 16.6)),
        ("GND", (12.5, 14.2)),
        ("GND", (12.5, 17.6)),
        ("GND", (13.4, 22.2)),
        ("NF_RAW5", (13.7, 19.8)),
    ]:
        via(net, pos)
    # Two real IN capacitors, a direct EN tie and separate ground stitches.
    line("FAN5V_IN", B, [(5, 15), (9.5, 15), (10.275, 15.775), p("C401", 1), p("C402", 1)], 0.5)
    line("FAN5V_IN", B, [p("C402", 1), (13.8, 15.4)])
    line("FAN5V_IN", F, [(13.8, 15.4), p("U401", 1)], 0.5)
    line("FAN5V_IN", F, [p("U401", 3), (11.1, 16.6)])
    line("FAN5V_IN", B, [(11.1, 16.6), p("C401", 1)])
    line("GND", B, [p("C401", 2), (12.5, 14.2), p("C402", 2)])
    line("GND", F, [p("U401", 2), (12.5, 17.6)])
    line("GND", B, [p("C403", 2), (12.5, 17.6), p("C404", 2)])
    # Literal short ILIM/GND paths; no external drive on ILIM.
    line("NF_RAW5_ILIM", F, [p("U401", 5), (12.5, 20), (11.5875, 20.9125), p("R401", 1)], 0.2)
    line("GND", F, [p("R401", 2), (13.4, 22.2)])
    # Actual OUT caps and a declared0.3mm neck before0.5mm force fanout.
    line("NF_RAW5", F, [p("U401", 6), (13.7, 19.8)], 0.3)
    line("NF_RAW5", B, [(13.7, 19.8), p("C404", 1), p("C403", 1)], 0.3)
    line("NF_RAW5", F, [p("U401", 6), (13.45, 18.35), (10.5, 18.35)], 0.3)
    line("NF_RAW5", F, [(10.5, 18.35), (10.5, 21.9), (9.6, 22.8), (5, 22.8), p("J401", 1)], 0.5)
    pcbnew.SaveBoard(str(path), b)
    report = dict(
        parent_input_pcb_sha256=before,
        output_pcb_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        added_literal_objects=records,
        new_part_actual_pad_xy={
            r: {n: p(r, n) for rr, n in pads if rr == r}
            for r in ["U401", "R401", "C401", "C402", "C403", "C404", "J401"]
        },
        old_objects_removed_or_modified=[],
        native_DRC_required=True,
        physical_qualified=False,
    )
    (ROOT / "generated/local-route.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Added", len(records), "literal objects; native checks required")


if __name__ == "__main__":
    main()
