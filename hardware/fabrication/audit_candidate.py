"""Independent saved-file audit of additive/removal-only CAD candidates."""

import argparse
import hashlib
import json
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr
from hardware.electronics.rail_disconnect.revision28.native_profile import summarize

REPO = Path(__file__).resolve().parents[2]
TAGS = ("footprint", "segment", "via", "zone")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def authored(node):
    if node[0] != "zone":
        return sexpr(node)
    return sexpr([v for v in node if not (isinstance(v, list) and v and v[0] == "filled_polygon")])


def geometry_delta(before, after):
    result = {}
    for tag in TAGS:
        old = {str(first(n, "uuid")[1]): n for n in children(before, tag)}
        new = {str(first(n, "uuid")[1]): n for n in children(after, tag)}
        assert len(old) == len(children(before, tag)) and len(new) == len(children(after, tag))
        result[tag] = dict(added=sorted(new.keys()-old.keys()), removed=sorted(old.keys()-new.keys()),
                           changed=sorted(key for key in old.keys() & new.keys() if authored(old[key]) != authored(new[key])))
    def other(tree):
        return [v for v in tree if not (isinstance(v, list) and v and v[0] in TAGS)]
    result["other_root_geometry_exact"] = sexpr(other(before)) == sexpr(other(after))
    return result


def native_evidence_errors(project, record):
    """Return precise stale/missing evidence failures; never infer a native run."""
    folder = project.parent
    pcb = project.with_suffix(".kicad_pcb")
    errors = []
    expected = record.get("checked_PCB_sha256", record.get("filled_PCB_sha256"))
    for path, digest in ((pcb, expected), (project, record.get("checked_project_sha256"))):
        if not digest or not path.is_file() or sha(path) != digest:
            errors.append("Missing or stale checked file: "+str(path))
    schematic = project.with_suffix(".kicad_sch")
    schematic_digest = record.get("checked_schematic_sha256")
    if not schematic_digest:
        digests = {digest for path, digest in record.get("source_sha256", {}).items()
                   if Path(path).name == schematic.name}
        if len(digests) == 1:
            schematic_digest = digests.pop()
    if not schematic_digest or not schematic.is_file() or sha(schematic) != schematic_digest:
        errors.append("Missing or stale checked schematic")
    for field in ("raw_report_sha256", "captured_project_library_sha256", "captured_library_table_sha256"):
        for name, digest in record.get(field, {}).items():
            path = (folder/name).resolve()
            if not path.is_relative_to(folder.resolve()) or not path.is_file() or sha(path) != digest:
                errors.append("Missing or stale native dependency: "+name)
    for suffix in ("drc", "erc"):
        if not (folder / (suffix+".json")).is_file():
            errors.append("Missing native "+suffix+" report")
    if errors:
        return errors
    drc, erc = [json.loads((folder / (suffix+".json")).read_text()) for suffix in ("drc", "erc")]
    actual = summarize(drc, erc)
    if actual != record["status"]:
        errors.append("Native report summary differs from saved status")
    if not actual["all_native_rule_checks_enabled"]:
        errors.append("Native check coverage is incomplete")
    missing = record.get("uncapped_open_connections", record.get("uncapped_missing_connections"))
    if missing is None or len(drc["unconnected_items"]) != min(499, missing):
        errors.append("Native uncapped connectivity count is inconsistent")
    return errors


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--removal-proof", type=Path)
    args = parser.parse_args()
    assert all(p.resolve().is_relative_to(REPO) for p in (args.before, args.review))
    record = json.loads(args.review.read_text())
    project = next(args.review.parent.glob("*.kicad_pro"))
    assert not native_evidence_errors(project, record)
    pcb = project.with_suffix(".kicad_pcb")
    before, after = [read_sexpr(p.read_text()) for p in (args.before, pcb)]
    delta = geometry_delta(before, after)
    assert delta["other_root_geometry_exact"]
    assert all(not delta[tag]["changed"] for tag in TAGS)
    assert not delta["footprint"]["added"] and not delta["footprint"]["removed"]
    assert not delta["zone"]["added"] and not delta["zone"]["removed"]
    assert not delta["via"]["removed"]
    removed = delta["segment"]["removed"]
    inputs = (args.before, args.review, pcb, project, Path(__file__))
    if removed:
        assert args.removal_proof and args.removal_proof.resolve().is_relative_to(REPO)
        proof = json.loads(args.removal_proof.read_text())
        proven = {row["uuid"] for row in proof["checks"] if row["removed"] and row["actual_track_copper_covered_by_remaining_electrodes"]}
        assert set(removed) == proven and not delta["segment"]["added"] and not delta["via"]["added"]
        inputs += (args.removal_proof,)
    output = args.review.parent / "independent-geometry-audit.json"
    assert not output.exists()
    output.write_text(json.dumps(dict(source_sha256={str(p.resolve()): sha(p) for p in inputs},
        delta=delta, all_original_component_poses_pads_courtyards_models_exact=True,
        all_retained_tracks_vias_and_authored_zones_exact=True,
        original_copper_removals_require_explicit_coverage_proof=True,
        native_status=record["status"], uncapped_open_connections=record.get("uncapped_open_connections", record.get("uncapped_missing_connections")),
        physical_qualified=False, fabrication_released=False), indent=2)+"\n")
    print("Independent geometry audit:", {tag: {k: len(v) for k, v in delta[tag].items()} for tag in TAGS})


if __name__ == "__main__":
    run()
