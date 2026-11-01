"""Bind the cleaned project to its exact removals and retained layout envelope."""

import argparse
import ast
import copy
import hashlib
import json
from collections import Counter
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr

REPO = Path(__file__).resolve().parents[4]
WORK = REPO / "hardware/electronics/rail_disconnect/revision28/generated/low-power-run-work"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def objects(tree, kinds):
    return {str(first(n, "uuid")[1]): n for kind in kinds for n in children(tree, kind)}


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rounds", required=True, type=int)
    parser.add_argument("--publish", action="store_true", help="Update the preferred-project pointer after all audits pass")
    args = parser.parse_args()
    assert 1 <= args.rounds <= 12
    generated = WORK / "generated"
    parent = generated / "native-closed-control-layout"
    final = generated / f"native-signal-stub-cleanup-{args.rounds:02d}"
    report = json.loads((final / "review.json").read_text())
    drc = json.loads((final / "drc.json").read_text())
    assert report["uncapped_missing_connections"] == 0
    assert not [v for v in drc["violations"] if v["severity"] == "error"]
    assert report["status"]["all_native_rule_checks_enabled"]
    assert not drc["schematic_parity"] and report["status"]["counts"]["erc"] == 0
    audit_paths = [parent / "rail_disconnect.kicad_pcb", final / "rail_disconnect.kicad_pcb",
                   final / "rail_disconnect.kicad_pro", final / "rail_disconnect.kicad_sch",
                   final / "review.json", final / "drc.json", final / "erc.json", Path(__file__)]
    removed, silk = set(), set()
    rounds = []
    for number in range(1, args.rounds + 1):
        folder = generated / f"signal-stub-cleanup-{number:02d}"
        path = folder / "cleanup.json"
        audit_paths.append(path)
        review = json.loads(path.read_text())
        recipe = folder / "applied-recipe.py.txt"
        assert sha(recipe) == review["recipe_sha256"]
        audit_paths.append(recipe)
        assert review["source_unchanged"] and review["uncapped_opens_before_save"] == 0
        assert review["power_ground_aux_objects_protected"]
        assert all(sha(Path(p)) == h for p, h in review["source_sha256"].items())
        assert sha(folder / "rail_disconnect.kicad_pcb") == review["output_pcb_sha256"]
        identifiers = {r["uuid"] for r in review["attempts"] if r["removed"]}
        restored = set(review.get("restored_internal_force_uuids", []))
        assert restored <= removed
        removed -= restored
        assert not identifiers & removed
        removed |= identifiers
        silk |= {r["uuid"] for r in review["silk_changes"]}
        rounds.append(dict(round=number, removed=len(identifiers), restored_internal_force=len(restored)))
    before, after = [read_sexpr((p / "rail_disconnect.kicad_pcb").read_text()) for p in (parent, final)]
    old, new = [objects(t, ("segment", "via")) for t in (before, after)]
    assert set(old) - set(new) == removed and not set(new) - set(old)
    assert all(sexpr(new[u]) == sexpr(old[u]) for u in new)
    layout = REPO / "hardware/electronics/rail_disconnect/revision26/layout.py"
    power = next(ast.literal_eval(n.value) for n in ast.parse(layout.read_text()).body
                 if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "POWER_NETS" for t in n.targets))
    internal_force = {p["net"] for c in json.loads((WORK / "components.json").read_text())
                      for p in c["pins"] if p["net"] and p["net"].endswith("_COMMON")}
    assert len(internal_force) == 4
    for identifier in removed:
        item = old[identifier]
        assert str(first(item, "net")[1]).lstrip("/") not in power | internal_force | {"AGND", "V2V5_AUX"}
        if item[0] == "segment":
            assert float(first(item, "width")[1]) <= .4
        else:
            assert float(first(item, "drill")[1]) >= .3
    old_fp, new_fp = [objects(t, ("footprint",)) for t in (before, after)]
    assert set(old_fp) == set(new_fp) and len(silk) == 3
    changed_fp = []
    for identifier in old_fp:
        left, right = [copy.deepcopy(m[identifier]) for m in (old_fp, new_fp)]
        if sexpr(left) == sexpr(right):
            continue
        ref = next(p[2] for p in children(left, "property") if p[1] == "Reference")
        assert ref == "J12"
        changed_fp.append(ref)
        for tree in (left, right):
            tree[:] = [n for n in tree if not (isinstance(n, list) and n and n[0] == "fp_line"
                        and str(first(n, "uuid")[1]) in silk)]
        assert sexpr(left) == sexpr(right)
    assert changed_fp == ["J12"]

    def rest(tree):
        return Counter(sexpr(n) for n in tree if not (isinstance(n, list) and n
                       and n[0] in ("segment", "via", "footprint", "zone")))

    assert rest(before) == rest(after), "Stackup, outline, rules or other board objects changed"
    zone_inputs = []
    for tree in (before, after):
        zone_inputs.append(Counter(sexpr([n for n in z if not
            (isinstance(n, list) and n and n[0] == "filled_polygon")]) for z in children(tree, "zone")))
    assert zone_inputs[0] == zone_inputs[1]
    receiving = generated / "closed-layout-receiving/manifest.json"
    manifest = json.loads(receiving.read_text())
    assert all(sha(Path(p)) == h for p, h in manifest["input_sha256"].items())
    audit_paths.append(receiving)
    for case in ("control-wing-positive", "control-wing-receiving"):
        path = REPO / "hardware/cad/a12/controlled_restart/results" / case / "result.json"
        assert json.loads(path.read_text())["clear"]
        audit_paths.append(path)
    warnings = Counter(v["type"] for v in drc["violations"])
    warning_inventory = []
    for finding in drc["violations"]:
        assert finding["severity"] == "warning" and finding["type"] in ("track_dangling", "via_dangling")
        identifier = finding["items"][0]["uuid"]
        item = new[identifier]
        net = str(first(item, "net")[1]).lstrip("/")
        if net in power | internal_force:
            reason = "preserved force copper; requires current/thermal review"
        elif net in ("AGND", "V2V5_AUX"):
            reason = "preserved return/AUX copper; requires PDN/thermal review"
        elif item[0] == "segment" and float(first(item, "width")[1]) > .4:
            reason = "preserved wide control copper; requires functional review"
        elif item[0] == "via" and float(first(item, "drill")[1]) < .3:
            reason = "preserved smaller process via; requires explicit disposition"
        else:
            raise AssertionError(("Eligible unused signal copper remains", identifier, net))
        warning_inventory.append(dict(uuid=identifier, net=net, type=finding["type"],
                                      reason_retained=reason, resolved=False))
    output = dict(source_sha256={str(p): sha(p) for p in audit_paths}, rounds=rounds,
        removed_track_count=sum(old[u][0] == "segment" for u in removed),
        removed_via_count=sum(old[u][0] == "via" for u in removed),
        every_retained_track_and_via_exact=True, power_ground_AUX_objects_exact=True,
        all_four_internal_MOSFET_force_nets_exact=True,
        footprint_poses_pads_bodies_courtyards_exact=True, clipped_J12_silk_strokes=3,
        stackup_outline_keepouts_zone_settings_exact=True,
        captured_wing_envelope_unchanged=True, captured_clearance_result_still_applicable=True,
        whole_unit_mechanical_qualified=False, uncapped_open_connections=0, hard_DRC_errors=0,
        ERC_findings=0, schematic_parity_findings=0, all_native_rule_checks_enabled=True,
        warnings=dict(warnings), warning_count=sum(warnings.values()),
        remaining_warning_inventory=warning_inventory,
        previous_PDN_thermal_fault_evidence_inherited=False,
        physical_qualified=False, fabrication_released=False)
    destination = final / "cleanup-review.json"
    assert not destination.exists()
    destination.write_text(json.dumps(output, indent=2) + "\n")
    if args.publish:
        assert review["cascade_converged"] and review["signal_via_layer_test_matches_source_DRC"]
        svg = final / "closed-top.svg"
        assert svg.is_file() and report["connector_library_audit"]["project_local_copy"]
        pointer = WORK / "CURRENT_LAYOUT.json"
        history = WORK / "CURRENT_LAYOUT.before-signal-cleanup.json"
        previous = json.loads(pointer.read_text())
        assert previous["project"] == "generated/native-closed-control-layout/rail_disconnect.kicad_pro"
        assert not history.exists() and not (final / "handoff.json").exists()
        old_handoff = json.loads((parent / "handoff.json").read_text())
        handoff = dict(output, preferred_project=str(final / "rail_disconnect.kicad_pro"),
            source_sha256={**output["source_sha256"], str(destination): sha(destination), str(svg): sha(svg)},
            electrical_parts=271, mechanical_footprints=4,
            manufacturing_process_audit=report["manufacturing_process_audit"],
            smaller_via=old_handoff["smaller_via"],
            fabrication_release_gates=[f"Resolve or justify the {output['warning_count']} remaining native warnings",
                                       *old_handoff["fabrication_release_gates"][1:]])
        (final / "handoff.json").write_text(json.dumps(handoff, indent=2) + "\n")
        history.write_bytes(pointer.read_bytes())
        preferred = dict(previous, project=f"generated/{final.name}/rail_disconnect.kicad_pro",
            handoff=f"generated/{final.name}/handoff.json", warning_count=output["warning_count"],
            previous_project=previous["project"], cleanup_review=f"generated/{final.name}/cleanup-review.json")
        temporary = pointer.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(preferred, indent=2) + "\n")
        temporary.replace(pointer)
    print("Exact-object cleanup audit passed:", len(removed), "removed;", output["warning_count"], "warnings remain")


if __name__ == "__main__":
    run()
