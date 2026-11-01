"""Apply only the independently reviewed U11 receiving delta to the routed source."""

import hashlib
import json
import shutil
from pathlib import Path

from ...common.sexpr import a, children, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/schmitt-u37-short-reconnect-work"
BASE = ROOT / "generated/schmitt-u37-backbone-clear-work"
PROPOSAL = ROOT / "generated/schmitt-u11-receiving-proposal"
WORK = ROOT / "generated/schmitt-u11-coherent-merge-work"
STRICT_KEYS = (
    "missing_courtyard",
    "track_not_centered_on_via",
    "tuning_profile_track_geometries",
    "footprint_filters_mismatch",
    "footprint_type_mismatch",
)


def ident(n):
    return str(first(n, "uuid")[1])


def objects(t):
    return {ident(n): n for k in ("segment", "via") for n in children(t, k)}


def main():
    assert not WORK.exists()
    blob = (SOURCE / "rail_disconnect.kicad_pcb").read_bytes()
    t = read_sexpr(blob.decode())
    bp = BASE / "rail_disconnect.kicad_pcb"
    base = read_sexpr(bp.read_text())
    receipt = json.loads((PROPOSAL / "candidate0-receipt.json").read_text())
    assert hashlib.sha256(bp.read_bytes()).hexdigest() == receipt["source_pcb_sha256"]
    handoff = PROPOSAL / "handoff.json"
    assert (
        hashlib.sha256(handoff.read_bytes()).hexdigest()
        == "e9d471f51e5be8b214c1474dac989bc94b8f755daa050a282918ab3bc605bbd5"
    )
    for p, h in json.loads(handoff.read_text())["files_sha256"].items():
        assert hashlib.sha256((PROPOSAL / p).read_bytes()).hexdigest() == h, p
    candidate = read_sexpr((PROPOSAL / "candidate0/rail_disconnect.kicad_pcb").read_text())
    old, new, current = objects(base), objects(candidate), objects(t)
    removed = [read_sexpr(s) for s in receipt["removed_control_segments"]]
    removedids = {ident(n) for n in removed}
    assert set(old) - set(new) == removedids
    assert len(removedids) == 30
    for n in removed:
        uid = ident(n)
        assert uid in current and sexpr(current[uid]) == sexpr(old[uid]) == sexpr(n), uid
        t.remove(current[uid])
    added = [new[u] for u in sorted(set(new) - set(old))]
    assert len(added) == 11 and sum(n[0] == "via" for n in added) == 1
    oldnames = {str(n[1]): str(n[2]) for n in children(candidate, "net")}
    codes = {str(n[2]): str(n[1]) for n in children(t, "net")}
    literals = []
    for n in added:
        assert ident(n) not in current
        value = str(first(n, "net")[1])
        net = oldnames.get(value, value)
        assert net.lstrip("/") == "N12_OV_OK_SCHMITT"
        first(n, "net")[1] = a(codes[net])
        t.append(n)
        literals.append(sexpr(n))
    WORK.mkdir()
    (WORK / "generated").mkdir()
    for p in SOURCE.iterdir():
        if p.is_file() and (
            p.suffix in (".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_sym")
            or p.name in ("components.json", "fp-lib-table", "sym-lib-table")
        ):
            shutil.copy2(p, WORK / p.name)
        elif p.suffix == ".pretty":
            shutil.copytree(p, WORK / p.name)
    (WORK / "rail_disconnect.kicad_pcb").write_text(sexpr(t) + "\n")
    project = WORK / "rail_disconnect.kicad_pro"
    before = project.read_bytes()
    pro = json.loads(before)
    pro["board"]["design_settings"].setdefault("rule_severities", {}).update(
        {k: "error" for k in STRICT_KEYS}
    )
    project.write_text(json.dumps(pro, indent=2) + "\n")
    report = dict(
        source_pcb_sha256=hashlib.sha256(blob).hexdigest(),
        receiving_base_pcb_sha256=hashlib.sha256(bp.read_bytes()).hexdigest(),
        independent_handoff_sha256=hashlib.sha256(handoff.read_bytes()).hexdigest(),
        recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        exact_removed_ordinary_control_objects=receipt["removed_control_segments"],
        added_receiving_objects=literals,
        all_current_footprints_ports_values_and_other_Cu_unchanged=True,
        default_ignored_checks_now_explicit_errors=list(STRICT_KEYS),
        no_clearance_width_via_or_dimensional_rule_relaxed=True,
        source_default_project_sha256=hashlib.sha256(before).hexdigest(),
        strict_project_sha256=hashlib.sha256(project.read_bytes()).hexdigest(),
        known_baseline_strict_centering_findings=46,
        full_source_new_native_connectivity_and_fill_PDN_required=True,
        physical_qualified=False,
    )
    (WORK / "generated/coherent-receiving-delta.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        "Merged exact11added/30removed receiving objects; all5defaultignored checks enabled; fresh checks required"
    )


if __name__ == "__main__":
    main()
