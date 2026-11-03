"""Construct and natively review the ADC supervisor bus and PD divider links."""

import argparse
import json
import shutil
import sys
from pathlib import Path

from hardware.electronics.common.sexpr import read_sexpr, sexpr
from hardware.fabrication.audio_main_bypass_repack import add_geometry, add_via
from hardware.fabrication.audio_main_local_routes import relative_hashes, verify_hashes
from hardware.fabrication.audit_candidate import sha

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "staging/audio-main-six-monitor-04"
OUT = ROOT / "staging/audio-main-six-pd-01"
PLAN = ROOT / "audio_main_pd_plan.json"


def snapshot(label):
    path = OUT / ("applied-"+label+".py.txt")
    assert not path.exists()
    shutil.copyfile(Path(__file__), path)
    return path


def build():
    from hardware.fabrication.audit_audio_main_pd import verify_routes

    assert not OUT.exists()
    plan = json.loads(PLAN.read_text())
    verify_hashes(plan["source_sha256"])
    source_proof = json.loads((SOURCE / "comparator-closure-review.json").read_text())
    verify_hashes(source_proof["source_sha256"])
    assert source_proof["uncapped_open_connections"] == 171 and not source_proof["fabrication_released"]
    captured = json.loads((SOURCE / "final-native-inputs.json").read_text())
    board = read_sexpr((SOURCE / "audio_core.kicad_pcb").read_text())
    additions = []
    for row in plan["routes"]:
        for face, points in row["runs"]:
            add_geometry(board, additions, row["net"], face, points, .2, row["purpose"])
        for xy in row["new_vias_mm"]:
            add_via(board, additions, row["net"], xy, row["purpose"])
    # Verify the actual intended copper before writing any candidate project.
    record = dict(routes=plan["routes"], allowed_nets=plan["allowed_nets"], complete_target_nets=plan["complete_target_nets"],
                  added_segments=[r for r in additions if r["kind"] == "segment"],
                  added_vias=[r for r in additions if r["kind"] == "via"], expected_native_opens=165,
                  trace_width_mm=.2, clearance_mm=.2, planning_margin_mm=.01,
                  comparator_centreline_clearance_mm=.71, native_checks_pending=True, fabrication_released=False)
    verify_routes(read_sexpr((SOURCE / "audio_core.kicad_pcb").read_text()), read_sexpr(sexpr(board)), record, captured)
    OUT.mkdir()
    applied = snapshot("PD-construction")
    for path in SOURCE.iterdir():
        if path.suffix in (".kicad_sch", ".kicad_pro", ".kicad_sym", ".kicad_dru") or path.name in ("plan.json", "fp-lib-table", "sym-lib-table"):
            shutil.copyfile(path, OUT / path.name)
    shutil.copytree(SOURCE / "libraries", OUT / "libraries")
    dest = OUT / "distribution-input.kicad_pcb"
    dest.write_text(sexpr(board)+"\n")
    record.update(authored_PCB_sha256=sha(dest), source_sha256=relative_hashes([
        applied, PLAN, SOURCE / "audio_core.kicad_pcb", SOURCE / "final-native-inputs.json", SOURCE / "comparator-closure-review.json",
        ROOT / "audio_main_bypass_repack.py", ROOT / "audio_main_quiet_screen.py", ROOT / "audit_audio_main_pd.py"]))
    (OUT / "distribution-construction.json").write_text(json.dumps(record, indent=2)+"\n")
    print("Constructed six PD control joins; native checks pending; expected opens 165")


def native(action):
    assert sys.platform == "linux", "Mac CAD remains disabled"
    applied = snapshot(action+"-entry")
    if action == "fill":
        from hardware.fabrication import audio_main_power_routes as helper
        helper.OUT = OUT
        helper.fill()
        result = OUT / "native-refill.json"
    elif action == "review":
        from hardware.fabrication.audio_main_native_review import review
        review(OUT, SOURCE / "terminal-connectivity-review.json", SOURCE / "final-native-inputs.json", OUT / "distribution-construction.json", applied)
        result = OUT / "terminal-connectivity-review.json"
    elif action == "retain":
        from hardware.fabrication.review_audio_layer_retention import review
        review(SOURCE, OUT, 102, applied)
        result = OUT / "additional-terminal-review.json"
    else:
        from hardware.fabrication.capture_audio_layer_trial import capture
        result = OUT / "final-native-inputs.json"
        capture(OUT, OUT / "audio_core.kicad_pcb", OUT / "terminal-connectivity-review.json", result.name, applied)
    (OUT / (action+"-entry.json")).write_text(json.dumps(dict(source_sha256=relative_hashes([applied, result]), fabrication_released=False), indent=2)+"\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("build", "fill", "review", "retain", "capture-final"))
    action = parser.parse_args().action
    build() if action == "build" else native(action)
