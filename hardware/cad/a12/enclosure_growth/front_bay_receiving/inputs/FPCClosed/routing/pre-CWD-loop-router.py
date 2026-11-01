"""Deliberate local loops/force paths before any exploratory autorouting.

Run with KiCad Python. Physical noise/current/startup qualification stays false.
"""

import json
from pathlib import Path

import pcbnew

from hardware.qualification.boards.fan_health.composite.native import check, mm, xy

ROOT = Path(__file__).resolve().parent


def main():
    path = ROOT / "fan_power_health.kicad_pcb"
    board = pcbnew.LoadBoard(str(path))
    assert not list(board.GetTracks()), "Preserve routed work; rebuild explicit new scratch before rerun"
    pads = {
        (f.GetReference(), p.GetNumber()): p for f in board.GetFootprints() for p in f.Pads() if p.GetNumber()
    }
    records = []

    def p(ref, n):
        pad = pads[(ref, str(n))]
        return [pcbnew.ToMM(pad.GetPosition().x), pcbnew.ToMM(pad.GetPosition().y)]

    def net(ref, n):
        return pads[(ref, str(n))].GetNetname()

    def route(name, points, width=0.2, layer=pcbnew.F_Cu, role="local"):
        info = board.FindNet(name)
        assert info is not None, name
        ids = []
        for start, end in zip(points, points[1:]):
            if start == end:
                continue
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(xy(*start))
            t.SetEnd(xy(*end))
            t.SetWidth(mm(width))
            t.SetLayer(layer)
            t.SetNet(info)
            t.SetLocked(True)
            board.Add(t)
            ids.append(t.m_Uuid.AsString())
        records.append(
            dict(
                net=name,
                points_mm=points,
                width_mm=width,
                layer=board.GetLayerName(layer),
                role=role,
                uuids=ids,
            )
        )

    def link(a, b, waypoints=(), width=0.2, layer=pcbnew.F_Cu, role="local"):
        assert net(*a) == net(*b), (a, b)
        route(net(*a), [p(*a), *waypoints, p(*b)], width, layer, role)

    def via(name, point, role="local-ground"):
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(xy(*point))
        v.SetWidth(mm(0.65))
        v.SetDrill(mm(0.3))
        v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetNet(board.FindNet(name))
        v.SetLocked(True)
        board.Add(v)
        records.append(
            dict(
                net=name,
                via_mm=point,
                diameter_mm=0.65,
                finished_bore_mm=0.3,
                role=role,
                uuid=v.m_Uuid.AsString(),
            )
        )

    def grounded(a, point, role="local-ground"):
        assert net(*a) == "/GND", a
        route("/GND", [p(*a), point], 0.3, role=role)
        via("/GND", point, role)

    # Crystal: F-only, no vias; leave the metal case except manufacturer lands.
    link(("U1", 2), ("C20", 1), width=0.2, role="XTAL1")
    link(("C20", 1), ("X1", 1), [(51.025, 8.3), (56.5, 8.3), (56.5, 5.5)], role="XTAL1")
    link(("U1", 3), ("C21", 1), [(49.77, 11.1), (48.4, 11.1), (46.825, 9.825)], role="XTAL2")
    link(("C21", 1), ("X1", 2), [(46.825, 8.3), (40.5, 8.3), (40.5, 5.5)], role="XTAL2")
    grounded(("C20", 2), (52.575, 10.25), "clock-ground")
    grounded(("C21", 2), (48.375, 10.25), "clock-ground")
    # ADC-side filters remain literal F paths, separate from slow sensor wiring.
    link(("U1", 12), ("C23", 1), [(49.77, 19.055)], role="ADC_R")
    link(("R23", 2), ("C23", 1), [(50.6625, 22.4375)], role="ADC_R")
    link(("U1", 13), ("C22", 1), [(51.04, 19.0), (53.525, 19.0)], role="ADC_L")
    link(("R21", 2), ("C22", 1), [(55.6625, 22.4375)], role="ADC_L")
    grounded(("C22", 2), (57.875, 20.3), "ADC-ground")
    grounded(("C23", 2), (51.475, 21.7), "ADC-ground")
    # MCU bypass output/reference. Full source-to-MCU drop remains to extract.
    link(("U1", 1), ("C4", 1), [(53.2, 13.415), (53.2, 13.475)], width=0.3, role="MCU-bypass")
    grounded(("C4", 2), (57.6, 13.025), "MCU-ground")
    grounded(("U1", 14), (53.7, 17.475), "MCU-ground")
    # Regulator input/output/delay all same face, with literal EP/GND returns.
    link(("C1", 1), ("U2", 8), width=0.3, role="LDO-input")
    link(("U2", 1), ("C2", 1), width=0.3, role="LDO-output")
    link(("U2", 7), ("C3", 1), [(30.5, 14.325), (29.825, 13.65)], role="LDO-delay")
    link(("C1", 2), ("U2", 9), [(34, 16.3)], width=0.3, role="LDO-direct-ground")
    link(("C2", 2), ("U2", 4), width=0.3, role="LDO-direct-ground")
    link(("U2", 4), ("U2", 9), [(35.1,13.025)], width=0.3, role="LDO-direct-ground")
    link(("C3", 2), ("U2", 9), [(34, 10.8)], width=0.3, role="LDO-direct-ground")
    via("/GND", (34, 16.3), "LDO-ground")
    via("/FAN5V_IN", (29.65, 18.95), "health-input")
    route("/FAN5V_IN", [(29.65, 18.95), p("C1", 1)], 0.3, role="health-input")
    via("/FAN5V_IN", (30.9, 12.3), "LDO-EN")
    route("/FAN5V_IN", [(30.9, 12.3), p("U2", 5)], 0.2, role="LDO-EN")
    route("/FAN5V_IN", [(29.65, 18.95), (30.9, 12.3)], 0.3, pcbnew.B_Cu, "LDO-EN")
    # Watchdog's tiny timing current stays beside the device, without vias.
    link(("U4", 2), ("C7", 1), [(31.8, 21.675), (31.8, 23.825)], role="WD-CWD")
    grounded(("C7", 2), (34.6, 28.075), "WD-timing-ground")
    grounded(("C6", 2), (28.9, 23.975), "WD-bypass-ground")
    link(("U4", 1), ("C6", 1), width=0.3, role="WD-bypass")
    link(("U4", 4), ("U4", 9), [(34,22.975)], width=0.3, role="WD-ground")
    route("/GND", [p("U4", 9),(34.6,22),(34.6,24.2),(34.6,24.1)], 0.3, role="WD-ground")
    via("/GND", (34.6, 24.1), "WD-ground")
    # Fan branch supply/capacitor loops. Wide force trunks are on B; GND In1
    # remains continuous and is not silently cut by these routes.
    for base, ic, y, via_out, via_gnd in [
        (200, "U201", 3.3, (20.8, 5.0), (17.5, 9.1)),
        (300, "U301", 34.7, (18.0, 27.8), (17.9, 29.2)),
    ]:
        ca, cb, co = "C" + str(base + 1), "C" + str(base + 2), "C" + str(base + 3)
        rr = "R" + str(base + 1)
        bridge = (18.2, y)
        vin = (18.2, 1.9 if base == 200 else 36.6)
        link((ca, 1), (cb, 1), width=0.5, role="fan-input-bypass")
        route("/FAN5V_IN", [bridge, vin], 0.5, role="fan-input-force")
        via("/FAN5V_IN", vin, "fan-input-force")
        link((ca, 1), (ic, 1 if base == 200 else 3), width=0.5, role="fan-input-bypass")
        if base == 200:
            link((ic, 1), (ic, 3), [(15.0, 5.55), (15.0, 7.45)], width=0.5, role="fan-EN-input")
            grounded((ca, 2), (12.65, y), "fan-input-ground")
            grounded((cb, 2), (22.475, y - 1.7) if base == 300 else (23.85,y), "fan-input-ground")
            route(net(ic, 6), [p(ic, 6), (20.25, 5.55), via_out], 0.5, role="fan-output-escape")
        else:
            route("/FAN5V_IN", [p(ic,3),(15.7,32.45)],.4,role="fan-EN-input");via("/FAN5V_IN",(15.7,32.45),"fan-EN-input")
            route("/FAN5V_IN", [p(ic,1),(16.1,29.7)],.4,role="fan-EN-input");via("/FAN5V_IN",(16.1,29.7),"fan-EN-input")
            route("/FAN5V_IN", [(15.7,32.45),(15.2,32.45),(15.2,29.7),(16.1,29.7)],.4,pcbnew.B_Cu,"fan-EN-input")
            grounded((ca, 2), (12.65, y), "fan-input-ground")
            grounded((cb, 2), (22.475, y - 1.7) if base == 300 else (23.85,y), "fan-input-ground")
            route(net(ic, 6), [p(ic, 6), (19.1375, 28.9375), via_out], 0.5, role="fan-output-escape")
        via(net(ic, 6), via_out, "fan-output-force")
        route(net(ic, 6), [via_out, p(co, 1)], 1.0, pcbnew.B_Cu, "fan-output-force")
        header = "J202" if base == 200 else "J203"
        route(
            net(ic, 6),
            [p(co, 1), (14.5, 10 if base == 200 else 27.6), (7.5, 10 if base == 200 else 27.6), p(header, 2)],
            1.0,
            role="fan-output-force",
        )
        route("/GND", [p(ic, 2), (17.9, p(ic, 2)[1]), (17.9,via_gnd[1]), via_gnd], 0.3, role="fan-local-reference")
        via("/GND", via_gnd, "fan-local-reference")
        if base == 200:
            link((ic, 5), (rr, 1), [(20.2,6.5)], role="fan-ILIM")
        else:
            link((ic, 5), (rr, 1), [(20.25, 31.5), (20.25, 30.5375)], role="fan-ILIM")
    # Input force port is actual J201, never the rejected P03TEST header.
    route("/FAN5V_IN", [p("J201", 1), (5, 15), (7, 13), (18.2, 1.9)], 1.0, pcbnew.B_Cu, "raw-input-force")
    route(
        "/FAN5V_IN",
        [p("J201", 1), (5, 19), (7, 21), (25, 21), (25, 36.6), (18.2, 36.6)],
        1.0,
        pcbnew.B_Cu,
        "raw-input-force",
    )
    route("/FAN5V_IN", [(25, 21), (27.6, 21), (29.65, 18.95)], 0.5, pcbnew.B_Cu, "health-input-force")
    pcbnew.SaveBoard(str(path), board)
    (ROOT / "generated/local-routes.json").write_text(
        json.dumps(
            dict(
                routes=records,
                all_local_routes_locked=True,
                source_only_operating_DIG_force_branch_required=True,
                local_noise_and_current_qualified=False,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    check("local")


if __name__ == "__main__":
    main()
