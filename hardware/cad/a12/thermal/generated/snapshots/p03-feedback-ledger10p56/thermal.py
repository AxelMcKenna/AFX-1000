"""Implement and inventory actual P03 thermal copper, without a thermal pass.

The declared construction uses plated barrels, not fictitious solid copper fill.
Thermal resistances are lower-bound screening values; silicon, spreading, TIM,
contact and convection remain additional series/network terms.
"""

import copy
import hashlib
import json
import math

from ...common.netlists import netlist
from ...common.sexpr import a, children, first, read_sexpr, sexpr
from ...output_stage.check_placement import transform
from . import models
from .board import BASE
from .route import PowerRouter, coded, named
from .spec import MOUNTS, ROOT, THERMAL_NODES, THERMAL_REGIONS, U13_QUIET_FIELD_NETS

OUT = ROOT / "generated"
NODES = THERMAL_NODES


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rect_zone(net, code, layer, box):
    x0, y0, x1, y1 = [100 + x for x in box]
    return read_sexpr(f'''(zone (net {code}) (net_name "/{net}") (layer "{layer}")
      (hatch edge .5) (connect_pads yes (clearance .16)) (min_thickness .15)
      (fill yes (thermal_gap .2) (thermal_bridge_width .5))
      (polygon (pts (xy {x0} {y0}) (xy {x1} {y0}) (xy {x1} {y1}) (xy {x0} {y1}))))''')


def implement():
    pcb = ROOT / "power_p03.kicad_pcb"
    tree = coded(read_sexpr(pcb.read_text()))
    # Quiet SET/feedback-plane exclusions are carried over deliberately, rather
    # than losing them when rebuilding the supply board around new sources.
    old = read_sexpr(BASE.read_text())
    quiet = []
    for zone in children(old, "zone"):
        if not children(zone, "keepout"):
            continue
        if first(first(zone, "keepout"), "tracks")[1] != "allowed":
            continue
        item = copy.deepcopy(zone)
        for poly in children(item, "polygon"):
            for xy in children(first(poly, "pts"), "xy"):
                xy[1] = a(float(xy[1]) + 65)
        quiet.append(item)
    already = any(
        children(z, "name") and first(z, "name")[1] == "P03_THERMAL" for z in children(tree, "zone")
    )
    tree[:] = [
        z
        for z in tree
        if not (
            isinstance(z, list)
            and z
            and z[0] == "zone"
            and (
                (children(z, "name") and first(z, "name")[1] == "P03_THERMAL")
                or (children(z, "keepout") and first(first(z, "keepout"), "tracks")[1] == "allowed")
            )
        )
    ]
    tree.extend(quiet)
    names = {int(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    # The limiting converter needs an actual spreading field. Retained signal
    # copper under that field is removed and must be rerouted on this revision.
    box = THERMAL_REGIONS["U13"]
    removed = 0
    for obj in list(tree):
        if not isinstance(obj, list) or not obj or obj[0] not in {"via", "segment"}:
            continue
        if names[int(first(obj, "net")[1])] == "AGND":
            continue
        if names[int(first(obj, "net")[1])] in U13_QUIET_FIELD_NETS and (
            obj[0] == "via" or first(obj, "layer")[1] in {"F.Cu", "In2.Cu"}
        ):
            continue
        points = (
            [first(obj, "at")[1:3]] if obj[0] == "via" else [first(obj, "start")[1:3], first(obj, "end")[1:3]]
        )
        xs = [float(p[0]) - 100 for p in points]
        ys = [float(p[1]) - 100 for p in points]
        if (
            not already
            and min(xs) < box[2] + 0.5
            and max(xs) > box[0] - 0.5
            and min(ys) < box[3] + 0.5
            and max(ys) > box[1] - 0.5
        ):
            tree.remove(obj)
            removed += 1
    # Through-via access beneath these top EPs needs a genuine clear barrel
    # path on every layer. Existing non-ground inner traces are rerouted.
    fp_index = {
        next(p[2] for p in children(fp, "property") if p[1] == "Reference"): fp
        for fp in children(tree, "footprint")
    }
    for ref, padnum in (("U1", "11"), ("U13", "11"), ("U101", "25"), ("U102", "9"), ("U22", "11")):
        fp = fp_index[ref]
        ep = next(p for p in children(fp, "pad") if p[1] == padnum and children(p, "size"))
        cx, cy = transform(fp, first(ep, "at")[1:3])
        sx, sy = map(float, first(ep, "size")[1:3])
        area = [cx - sx / 2 - 0.3, cy - sy / 2 - 0.3, cx + sx / 2 + 0.3, cy + sy / 2 + 0.3]
        for obj in list(tree):
            if not isinstance(obj, list) or not obj or obj[0] not in {"via", "segment"}:
                continue
            if names[int(first(obj, "net")[1])] == "AGND":
                continue
            points = (
                [first(obj, "at")[1:3]]
                if obj[0] == "via"
                else [first(obj, "start")[1:3], first(obj, "end")[1:3]]
            )
            xs = [float(p[0]) for p in points]
            ys = [float(p[1]) for p in points]
            if min(xs) <= area[2] and max(xs) >= area[0] and min(ys) <= area[3] and max(ys) >= area[1]:
                tree.remove(obj)
    # Power-node backside spreaders must not contain ground stitching. Earlier
    # routed/free-net vias may otherwise be adopted by a broad AGND plane during
    # refill. Remove incompatible old barrels, then create deliberately assigned
    # free thermal vias; real ground returns must be rerouted outside each patch.
    for via in list(children(tree, "via")):
        xy = [float(v) - 100 for v in first(via, "at")[1:3]]
        net = names[int(first(via, "net")[1])]
        for ref, box in THERMAL_REGIONS.items():
            if NODES[ref] == "AGND":
                continue
            if box[0] <= xy[0] <= box[2] and box[1] <= xy[1] <= box[3] and net != NODES[ref]:
                tree.remove(via)
                break
    for via in children(tree, "via"):
        if not children(via, "free"):
            via.append([a("free"), a("yes")])
    # Deliberate dense direct-EP array, replacing the old sparse pattern.
    u13 = fp_index["U13"]
    ep = next(p for p in children(u13, "pad") if p[1] == "11")
    ep_x, ep_y = transform(u13, first(ep, "at")[1:3])
    ep_x -= 100
    ep_y -= 100
    for via in list(children(tree, "via")):
        x, y = [float(v) - 100 for v in first(via, "at")[1:3]]
        if names[int(first(via, "net")[1])] == "AGND" and abs(x - ep_x) <= 0.85 and abs(y - ep_y) <= 1.2:
            tree.remove(via)
    # Dedicated inner/back thermal spreading field: remove obsolete remote
    # signal transit after moving its actual components. Switching/decoupling
    # paths on the front remain, while the six-layer thermal extraction reads
    # the actual remaining pad/clearance voids rather than an ideal solid sheet.
    box = THERMAL_REGIONS["U13"]
    for obj in list(tree):
        if not isinstance(obj, list) or not obj or obj[0] not in {"via", "segment"}:
            continue
        if names[int(first(obj, "net")[1])] == "AGND":
            continue
        if obj[0] == "segment" and first(obj, "layer")[1] == "F.Cu":
            continue
        points = (
            [first(obj, "at")[1:3]] if obj[0] == "via" else [first(obj, "start")[1:3], first(obj, "end")[1:3]]
        )
        xs = [float(p[0]) - 100 for p in points]
        ys = [float(p[1]) - 100 for p in points]
        if (
            min(xs) <= box[2] + 0.5
            and max(xs) >= box[0] - 0.5
            and min(ys) <= box[3] + 0.5
            and max(ys) >= box[1] - 0.5
        ):
            tree.remove(obj)
    # Rebuild the expanded field on a routable1.25mm pitch. A0.8mm pitch
    # of0.6mm lands creates a via fence with no0.16+2x0.16mm signal lane.
    for via in list(children(tree, "via")):
        x, y = [float(v) - 100 for v in first(via, "at")[1:3]]
        box = THERMAL_REGIONS["U13"]
        if names[int(first(via, "net")[1])] == "AGND" and box[0] <= x <= box[2] and box[1] <= y <= box[3]:
            tree.remove(via)
    router = PowerRouter(tree)
    for dx in (-0.5, 0, 0.5):
        for dy in (-0.75, -0.25, 0.25, 0.75):
            xy = (ep_x + dx, ep_y + dy)
            if not router.safe_via("AGND", xy, diameter=0.7, clearance=0.16):
                raise ValueError(f"U13 direct-EP via is physically blocked at {xy}")
            router.via("AGND", xy, diameter=0.7)
    fp_by_ref = {
        next(p[2] for p in children(fp, "property") if p[1] == "Reference"): fp
        for fp in children(tree, "footprint")
    }
    added = {}
    # Via fields under large EPs/tabs, plus free same-node spreading fields.
    # Every proposed via is screened against actual opposite-side pads/copper.
    for ref, net in NODES.items():
        fp = fp_by_ref[ref]
        padnum = "3" if ref == "U8" else "25" if ref == "U101" else "9" if ref in {"U7", "U102"} else "11"
        pads = [p for p in children(fp, "pad") if p[1] == padnum and children(p, "size")]
        if pads:
            pad = max(pads, key=lambda p: float(first(p, "size")[1]) * float(first(p, "size")[2]))
            cx, cy = transform(fp, first(pad, "at")[1:3])
            cx -= 100
            cy -= 100
        else:
            cx, cy = [float(v) - 100 for v in first(fp, "at")[1:3]]
        box = THERMAL_REGIONS[ref]
        # 0.8 mm pitch leaves realistic native routing clearance; small EPs use
        # 0.6 mm pitch inside their actual body, no invented exposed pad.
        proposed = []
        if ref not in {"U20", "U23"}:
            sx, sy = map(float, first(pad, "size")[1:3])
            nx = max(1, int((sx - 0.5) / 0.6) + 1)
            ny = max(1, int((sy - 0.5) / 0.6) + 1)
            proposed.extend(
                (cx + (i - (nx - 1) / 2) * 0.6, cy + (j - (ny - 1) / 2) * 0.6)
                for i in range(nx)
                for j in range(ny)
            )
        pitch = 1.25 if ref == "U13" else 0.8
        proposed.extend(
            (box[0] + 0.8 + i * pitch, box[1] + 0.8 + j * pitch)
            for i in range(int((box[2] - box[0] - 1.6) / pitch) + 1)
            for j in range(int((box[3] - box[1] - 1.6) / pitch) + 1)
        )
        count = 0
        for xy in proposed:
            # Preserve genuine top-side signal escape corridors; a dense
            # through-via fence around fine-pitch pins is electrically unroutable.
            if ref in {"U1", "U13", "U11", "U22", "U102"} and abs(xy[1] - cy) < 1.6 and abs(xy[0] - cx) > 0.9:
                continue
            if ref in {"U20", "U23", "U101"} and (abs(xy[1] - cy) < 2.0 or abs(xy[0] - cx) < 2.0):
                continue
            if ref == "U8" and xy[0] < 103.5:
                continue
            if router.safe_via(net, xy):
                router.via(net, xy)
                count += 1
        added[ref] = count
        for layer in (
            ("F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu")
            if ref in {"U1", "U13"}
            else ("F.Cu", "B.Cu")
        ):
            # Front spreading around small ICs must not fill their signal pins;
            # native clearances isolate them, and switches keep tiny local lands.
            z = rect_zone(net, router.nets[net], layer, box)
            z.append([a("name"), "P03_THERMAL"])
            z.append([a("priority"), a(3)])
            tree.append(z)
    pcb.write_text(sexpr(named(tree)) + "\n")
    print(
        f"P03 thermal fields added {added}; quiet exclusions {len(quiet)}; physical thermal qualification false"
    )
    inventory()


def inventory():
    from .bipolar import ledger
    from .construction import write_contract

    write_contract()
    pcb = ROOT / "power_p03.kicad_pcb"
    tree = coded(read_sexpr(pcb.read_text()))
    nets = {int(n[1]): str(n[2]).lstrip("/") for n in children(tree, "net")}
    poses = json.loads((OUT / "placement.json").read_text())["poses"]
    rows = []
    parts, _ = netlist(OUT / "netlist.xml")
    raw = models.raw_sources(parts)
    low = raw["pairs"][1]
    local = ledger(parts)
    high_negative = raw["pairs"][0]["negative_magnitude_envelope_v"][1]
    # Retained servo output lower bounds are independently derived in E14;
    # unchanged P03 target loops use those conservative lower bounds here.
    p12_min, n12_min = 11.95043855734266, 11.929486009890113
    losses = {
        "U1": 0.762667,
        "U13": sum((low["positive_envelope_v"][1], low["negative_magnitude_envelope_v"][1]))
        * 0.20
        * (1 / 0.75 - 1),
        "U7": 0.122448,
        "U8": (low["positive_envelope_v"][1] - p12_min) * (0.15 + 0.030),
        "U10": (high_negative - local["rails"]["N19"]["source_magnitude_v"][0])
        * local["rails"]["N19"]["source_output_current_required_a"]
        + high_negative * 0.0225,
        "U11": (low["negative_magnitude_envelope_v"][1] - n12_min)
        * local["rails"]["N12"]["source_output_current_required_a"]
        + low["negative_magnitude_envelope_v"][1] * 0.0225,
        "U20": 2.170157,
        "U23": 0.28,
        "U22": 0.283618,
        "U101": 0.848,
        "U102": models.auxiliary_current(parts)["ldo_loss_allocation_w"],
        "Q101": 4**2 * 0.040,
    }

    for ref, loss in losses.items():
        node = NODES.get(ref, "VIN_IC" if ref == "Q101" else "RAW_N22" if ref == "U10" else "AGND")
        box = THERMAL_REGIONS.get(ref)
        vias = []
        for via in children(tree, "via"):
            xy = [float(v) - 100 for v in first(via, "at")[1:3]]
            if nets[int(first(via, "net")[1])] != node:
                continue
            if box and box[0] <= xy[0] <= box[2] and box[1] <= xy[1] <= box[3]:
                vias.append(
                    dict(
                        at_mm=xy,
                        diameter_mm=float(first(via, "size")[1]),
                        finished_hole_mm=float(first(via, "drill")[1]),
                    )
                )
        # Barrel wall min50um is a construction requirement awaiting vendor
        # acceptance. Copper conductivity400 is optimistic, not guaranteed hot.
        g = sum(
            400
            * math.pi
            * ((v["finished_hole_mm"] * 0.001 / 2 + 50e-6) ** 2 - (v["finished_hole_mm"] * 0.001 / 2) ** 2)
            / 0.0016
            for v in vias
        )
        rows.append(
            dict(
                ref=ref,
                pose_mm=poses[ref],
                thermal_node=node,
                conservative_loss_allocation_w=loss,
                loss_allocation_reflects_actual_negative14v=True,
                operating_current_bound_a=0.20
                if ref == "U13"
                else 0.18
                if ref == "U8"
                else local["rails"]["N12"]["source_output_current_required_a"]
                if ref == "U11"
                else local["rails"]["N19"]["source_output_current_required_a"]
                if ref == "U10"
                else 0.09
                if ref == "U102"
                else 4
                if ref in {"U101", "Q101"}
                else None,
                bottom_tim_clear_patch_mm=box,
                same_node_vias_in_patch=vias,
                plated_barrel_only_optimistic_theta_c_per_w=1 / g if g else None,
                connected_filled_spreader_area_extracted=False,
                manufacturer_characterized_temperature_window_c=[-40, 85]
                if ref in {"U1", "U13"}
                else [-40, 125],
                manufacturer_electrical_table_temperature_basis="TA; 0..70 guaranteed, -40..85 characterized"
                if ref in {"U1", "U13"}
                else "TJ",
                engineering_junction_design_ceiling_c=85 if ref in {"U1", "U13"} else 110,
                independent_junction_thermal_proof=False,
            )
        )
    report = dict(
        revision="P03",
        board_datum_housing_mm=[168, 108, 6.5],
        board_thickness_mm=1.6,
        main_and_local_mounts_mm=MOUNTS,
        thermal_regions=rows,
        total_conservative_loss_allocation_w=sum(losses.values()),
        all_losses_simultaneously_attainable=False,
        aux_current_and_heat=models.auxiliary_current(parts),
        u13_quiet_foreign_field_nets=sorted(U13_QUIET_FIELD_NETS),
        u13_quiet_field_inner_layer="In2.Cu; actual voids/foreign barrels receive no AGND conduction credit",
        bipolar_ldo_current_scope="Includes native source bleeds/presence and3mA new-controller reserve; external151/26mA loads and LT3090 IQ envelope remain unverified allocations",
        errata=[
            "Prior U1020.7W did not enclose90mA through the LDO; now use the explicit90mA output-current allocation and100uA LDO-ground reserve",
            "Prior U10.214184W used a smaller ground-current screen inconsistent with the bipolar22.5mA conservative IQ allocation; now both negative LDOs use that same envelope and native bleed/control ledger",
        ],
        efficiency_allocations_are_measured=False,
        retained_target_loop_bound_source="hardware/electronics/power_supply/generated/electrical-screens.json",
        copper_barrel_minimum_um_requirement=50,
        barrel_plating_accepted=False,
        via_fill="Resin-filled and copper-capped; not solid copper-filled",
        thermal_qualified=False,
        physical_tests_performed=0,
        build_ready=False,
        source_sha256={
            str(p): digest(p) for p in (pcb, ROOT / "spec.py", ROOT / "board.py", ROOT / "thermal.py")
        },
    )
    (OUT / "heatmap.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    implement()
