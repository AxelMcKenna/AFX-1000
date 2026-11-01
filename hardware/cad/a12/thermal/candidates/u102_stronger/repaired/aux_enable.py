"""Inventory the actual U102 EN escape used by the same-face AUX cell.

This offset filled/capped .55/.20 barrel is an explicit custom-process condition.
Native clearance is not drill-registration, solder-joint or physical approval.
"""

from ...common.sexpr import children, first

SITE = (24.925, 20.325)


def inventory(tree):
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    rows = []
    for via in children(tree, "via"):
        xy = tuple(float(v) - 100 for v in first(via, "at")[1:3])
        if all(abs(a - b) < 1e-8 for a, b in zip(xy, SITE)):
            net = str(first(via, "net")[-1])
            rows.append(
                dict(
                    at_mm=xy,
                    net=names.get(str(first(via, "net")[1]), net).lstrip("/"),
                    land_mm=float(first(via, "size")[1]),
                    finished_bore_mm=float(first(via, "drill")[1]),
                )
            )
    assert len(rows) == 1 and rows[0]["net"] == "POWER_RUN"
    assert abs(rows[0]["land_mm"] - 0.55) < 1e-8 and abs(rows[0]["finished_bore_mm"] - 0.20) < 1e-8
    return dict(
        actual_EN_escape=rows[0],
        filled_capped_flat_required=True,
        preplate_annulus_at_min50um_wall_mm=0.125,
        drill_registration_max_wall_and_assembler_approved=False,
        physical_qualified=False,
    )
