"""CP01 live capture, deliberately separate from nonmutating captured replay."""

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

from hardware.cad.a12.thermal.enlarged_base.verify import mesh

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]
OUT = ROOT / "generated"
EB = ROOT.parent / "enlarged_base"
PS = REPO / "hardware/cad/a12/pot_stack"
EI = REPO / "hardware/cad/a12/enclosure_growth/integration_repaired"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, indent=2) + "\n")


def guard_capture(root=ROOT):
    if (root / "handoff.json").exists():
        raise RuntimeError(
            "Capture refuses sealed destination. Replay captured context into a NEW output directory."
        )
    if (root / "capture.json").exists():
        raise RuntimeError(
            "Capture already exists. Preserve it and make a new sibling; do not recapture over evidence."
        )


def closure(entry):
    found, todo = {}, [entry]
    while todo:
        p = todo.pop().resolve()
        if p in found:
            continue
        assert p.exists(), str(p)
        found[p] = sha(p)
        if p.suffix != ".scad":
            continue
        for a, b in re.findall(r'(?:include|use)\s*<([^>]+)>|import\(\s*"([^\"]+)"', p.read_text()):
            q = Path(a or b)
            todo.append(q if q.is_absolute() else p.parent / q)
    return found


def audit_parent(folder):
    seal = json.loads((folder / "handoff.json").read_text())
    bad = [n for n, h in seal["files_sha256"].items() if not (folder / n).exists() or sha(folder / n) != h]
    assert not bad, bad
    return dict(
        folder=str(folder.relative_to(REPO)),
        handoff_sha256=sha(folder / "handoff.json"),
        files=len(seal["files_sha256"]),
        all_sealed_hashes_current=True,
    )


def capture():
    guard_capture()
    parents = dict(EB01=audit_parent(EB), PS01=audit_parent(PS))
    psproof = json.loads((PS / "generated/verification.json").read_text())
    assert (
        len(psproof["cases"]) == 32 and psproof["conditional_checks_clear"] and not psproof["changed_inputs"]
    )
    for group in ["source_sha256", "artifact_sha256"]:
        assert all(sha(REPO / n) == h for n, h in psproof[group].items())
    checked = {}
    for n, row in psproof["cases"].items():
        log = (PS / "generated" / (n + ".log")).read_text()
        target = PS / "generated" / (n + ".stl")
        assert "WARNING" not in log and "ERROR" not in log
        if row["expected_empty"]:
            assert (
                row["returncode"] == 1 and "Current top level object is empty." in log and not target.exists()
            )
            checked[n] = dict(empty=True)
        else:
            assert row["returncode"] == 0 and "NoError" in log
            actual = mesh(target)
            assert all(actual[k] == v for k, v in row["statistics"].items())
            if n.startswith("knob_"):
                assert actual["closed_oriented_boundary"] and not actual["degenerate_triangles_excluded"]
            checked[n] = dict(empty=False, actual_mesh=actual)
    transitive = {}
    # Close every declared SCAD source too, including review modules not reached
    # by this entrypoint. Their includes must remain resolvable in a full copy.
    roots = [PS / "generated/checks.scad"] + [
        REPO / n for n in psproof["source_sha256"] if n.endswith(".scad")
    ]
    for entry in roots:
        transitive.update(closure(entry))
    missing = [
        str(p.relative_to(REPO))
        for p in transitive
        if str(p.relative_to(REPO)) not in psproof["source_sha256"]
        and str(p.relative_to(REPO)) not in psproof["artifact_sha256"]
    ]
    known = REPO / "hardware/cad/a12/enclosure_growth/integration/generated/trill-derived.scad"
    old = json.loads((known.parent.parent / "handoff.json").read_text())
    assert old["files_sha256"]["generated/trill-derived.scad"] == sha(known)
    OUT.mkdir(exist_ok=True)
    context = ROOT / "context"
    original_context = EB / "context"
    shutil.copytree(original_context, context)
    for p in context.rglob("*.scad"):
        p.write_text(p.read_text().replace(str(original_context), str(context)))
    # Every actual PS01 transitive source must be copied and rebound. Most are
    # already in EB01's independently closed context; verify original identity.
    original_eb = json.loads((EB / "capture.json").read_text())["original_sha256"]
    transitive_map = {}
    for p, h in transitive.items():
        n = p.relative_to(REPO)
        transitive_map[str(n)] = h
        if str(n) in original_eb:
            assert original_eb[str(n)] == h, str(n)
        else:
            q = context / n
            q.parent.mkdir(parents=True, exist_ok=True)
            if p.suffix == ".scad":
                q.write_text(p.read_text().replace(str(REPO), str(context)))
            else:
                shutil.copyfile(p, q)
    psanalysis = json.loads((PS / "generated/analysis.json").read_text())
    derived = (PS / "generated/context-derived.scad").read_text()
    ui = context / (EI / "generated/checks.scad").relative_to(REPO)
    s = ui.read_text()
    oldpots = next(x for x in s.splitlines() if x.startswith("ui_inherited_envelopes="))
    oldrows = json.loads(oldpots.split("=", 1)[1].rstrip(";"))
    assert len([r for r in oldrows if r[0].endswith("_pot")]) == 10
    for prefix in ["ui_inherited_envelopes=", "module ui_mechanics()"]:
        oldline = next(x for x in s.splitlines() if x.startswith(prefix))
        newline = next(x for x in derived.splitlines() if x.startswith(prefix))
        assert s.count(oldline) == 1
        s = s.replace(oldline, newline)
    oldline = next(x for x in s.splitlines() if x.startswith("module ui_components("))
    newline = oldline.replace("include_trill=true)", "include_trill=true,include_pots=true)")
    newline = newline[:-1] + "if(include_pots)ps_body();}"
    assert newline != oldline
    s = s.replace(oldline, newline)
    oldline = next(x for x in s.splitlines() if x.startswith("module ui_electronics("))
    newline = oldline.replace("exclude_own=false)", "exclude_own=false,include_pots=true)").replace(
        "ui_components();", "ui_components(true,include_pots);"
    )
    assert newline != oldline
    s = s.replace(oldline, newline)
    oldline = next(x for x in s.splitlines() if x.startswith("module ei_other_electronics()"))
    s = s.replace(oldline, oldline[:-1] + "ps_body();}")
    ui.write_text(s)
    # Bound EB01 erratum: its old10mm full-thread gauge was not5.8mm screw overlap.
    ebcode = (EB / "geometry.scad").read_text()
    assert ebcode.count("-16.2])cylinder(d=3.02,h=10.00002") == 1
    ebcode = ebcode.replace("-16.2])cylinder(d=3.02,h=10.00002", "-12])cylinder(d=3.02,h=5.80002")
    ebcode = ebcode.replace(
        "EB_POSITIVE_STL", str(context / "hardware/cad/a12/positive_links/generated/positive-links.stl")
    )
    ps = (PS / "generated/checks.scad").read_text()
    ps = "\n".join(ps.splitlines()[1:]) + "\n"
    # New bodies belong to ui_components now. Only their own body/shoulder
    # contact is excluded in those receiving contracts; retain other bodies.
    ps = ps.replace(
        'if(ps_case=="body_other_electronics_collision")intersection(){ps_body(.25);ui_electronics();}',
        'if(ps_case=="body_other_electronics_collision")intersection(){ps_body(.25);ui_electronics(false,false);}',
    )
    needle = "union(){ui_electronics();ui_power_only();ps_other_controls();pf_wires(.25);ui_all_joints(.25);}"
    assert ps.count(needle) == 1
    ps = ps.replace(
        needle,
        "union(){ui_electronics(false,false);cp_other_pot_bodies(p);ui_power_only();ps_other_controls();pf_wires(.25);ui_all_joints(.25);}",
    )
    parts = (EB / "generated/parts.scad").read_text()
    (OUT / "parts.scad").write_text(parts)
    (OUT / "context-derived.scad").write_text(
        "include <"
        + str(ui)
        + ">\ninclude <parts.scad>\n"
        + ebcode
        + ps
        + "\n"
        + (ROOT / "geometry.scad").read_text()
    )
    write(
        OUT / "config.json",
        dict(
            json.loads((EB / "generated/scene.json").read_text()), openings=psanalysis["candidate_openings"]
        ),
    )
    cases = {}
    ebproof = json.loads((EB / "generated/verification.json").read_text())
    exact_eb = {
        "front_material_positive_control",
        "new_bolt_material_positive_control",
        "foot_screw_positive_control",
        "interface_positive_control",
    }
    for n, row in ebproof["cases"].items():
        role = {
            "production-part": "part",
            "retained-review-only-group": "review",
            "empty-collision": "empty",
            "positive-control": "control",
        }[row["role"]]
        cases["eb_" + n] = dict(
            selector="eb_case", value=n, role=role, expected_volume=0.008 if n in exact_eb else None
        )
    eiproof = json.loads((EI / "generated/verification.json").read_text())
    for n, row in eiproof["cases"].items():
        if n == "whole_geometry":
            continue  # Complete review uses components, never a fused fake part.
        role = {"solid": "review", "empty": "empty", "control": "control"}[row["role"]]
        cases["ei_" + n] = dict(
            selector="ui_case", value=n, role=role, expected_volume=0.008 if role == "control" else None
        )
    for n, row in psproof["cases"].items():
        role = (
            "empty"
            if row["expected_empty"]
            else "part"
            if n.startswith("knob_") or n == "panel_geometry"
            else "review"
            if n in ["stack", "body_geometry"]
            else "control"
        )
        cases["ps_" + n] = dict(
            selector="ps_case",
            value=n,
            role=role,
            expected_volume=0.008 if n.endswith("positive_control") else None,
        )
    cases.update(
        {
            "cp_pot_hardware_review": dict(
                selector="cp_case", value="pot_hardware_review", role="review", expected_volume=None
            ),
            "cp_body_base_all_collision": dict(
                selector="cp_case", value="body_base_all_collision", role="empty", expected_volume=None
            ),
            "cp_receivers_base_all_collision": dict(
                selector="cp_case", value="receivers_base_all_collision", role="empty", expected_volume=None
            ),
            "cp_body_interface_positive_control": dict(
                selector="cp_case",
                value="body_interface_positive_control",
                role="control",
                expected_volume=0.008,
            ),
        }
    )
    assert len(cases) == 122
    write(OUT / "cases.json", cases)
    for parent, files in [
        (
            EB,
            [
                "handoff.json",
                "capture.json",
                "design.json",
                "interface-stack-review.json",
                "geometry-delta.json",
                "generated/analysis.json",
                "generated/verification.json",
                "geometry.scad",
                "verify.py",
                "stage.py",
            ],
        ),
        (
            PS,
            [
                "handoff.json",
                "build.py",
                "generated/analysis.json",
                "generated/verification.json",
                "generated/checks.scad",
                "generated/context-derived.scad",
                "README.md",
            ],
        ),
    ]:
        for n in files:
            target = ROOT / "parent_evidence" / parent.name / n
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(parent / n, target)
    # Capture the raw PS proof itself; its old incomplete transitive map stays intact.
    for n in psproof["artifact_sha256"]:
        p = REPO / n
        t = ROOT / "parent_evidence" / "PS01-raw" / p.name
        t.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, t)
    write(
        ROOT / "parent-audit.json",
        dict(
            parents=parents,
            PS01_actual_case_reintegrations=checked,
            PS01_original_transitive_map_complete=False,
            PS01_missing_transitive_entries=missing,
            PS01_full_literal_closure_sha256=transitive_map,
            historical_trill_source=dict(
                sha256=sha(known),
                parent_handoff=sha(known.parent.parent / "handoff.json"),
                entry="generated/trill-derived.scad",
            ),
            repaired_components_extra_declared_dependency=dict(
                path="hardware/cad/a12/generated/repaired-components.scad",
                sha256=sha(REPO / "hardware/cad/a12/generated/repaired-components.scad"),
                historical_EB01_file_present=False,
                active_EB01_entrypoint_loaded_it=False,
            ),
            all_transitive_sources_in_private_context=True,
        ),
    )
    write(
        ROOT / "EB01-erratum.json",
        dict(
            parent_handoff_sha256=parents["EB01"]["handoff_sha256"],
            original_geometry_sha256=sha(EB / "geometry.scad"),
            originals_modified=False,
            foot_thread_gauge=dict(
                old_interval=[-16.2, -6.19998],
                actual_nominal_screw_overlap=[-12, -6.2],
                new_receiving_abstraction=[-12, -6.19998],
                source_manufacturing_pilot_unchanged=True,
            ),
            replay=dict(
                old_EB_stage_is_live_recapture_not_captured_replay=True,
                do_not_run_stage_inside_sealed_EB01=True,
                new_capture_guard=True,
                new_replay_requires_fresh_outdir=True,
            ),
            external_shape_or_neighbor_change=False,
            old42native_result_invalidated=False,
            physical_qualified=False,
        ),
    )
    copied = {str(p.relative_to(ROOT)): sha(p) for p in context.rglob("*") if p.is_file()}
    write(
        ROOT / "capture.json",
        dict(
            parents=parents,
            derived_context_sha256=copied,
            transformations=[
                "Rebind captured EB01 literal closure to new private context",
                "Remove ten oldpotrows; insert exact PS01body envelopes as owned UIcomponents",
                "Exact PS01knobs/base49.2/grubaxis3; ten9.5panelbores supplied as explicit command config",
                "Receiving ownbody contracts exclude only ownshoulder overlap; otherbodies kept",
                "Restrict footthread abstraction to actual5.8nominal engagement per EB01erratum",
            ],
            live_recapture_operation=True,
            captured_replay_overwrites_sources=False,
        ),
    )
    print(
        json.dumps(
            dict(context_files=len(copied), PS_cases_audited=32, missing_PS_original_entries=len(missing))
        )
    )


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__).parse_args()
    capture()
