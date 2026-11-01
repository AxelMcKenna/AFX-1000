"""Source-bound native solid/collision receipt, with explicit unresolved holds."""

import argparse
import json
import subprocess

from hardware.cad.a12.thermal.verify import binary_stl

from .collisions import native_packet
from .generate import OUT, REPO, ROOT, geometry, load, sha


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--openscad", required=True)
    args = parser.parse_args()
    d = load()
    saved = json.loads((OUT / "geometry.json").read_text())
    d["assembled_board_bottom_z_mm"] = saved["effective_measured_plane_inputs"]
    d["assembled_terminal_top_override_z_mm"] = saved.get("effective_terminal_top_override_z_mm", {})
    packet = json.loads((OUT / "native-envelopes.json").read_text())
    assert packet == native_packet(d), "Native board changed; regenerate collision envelopes"
    assert saved["design_sha256"] == sha(ROOT / "design.json")
    assert saved["bars"] == geometry(d), "Measured plane/configuration mismatch; regenerate actual geometry"
    results = {}
    failures = []
    for name in (
        "bars",
        "component_collision",
        "retention_board_collision",
        "bar_retention_collision",
        "bar_bar_collision",
        "fastener_bar_collision",
        "fastener_board_collision",
        "positive_control",
    ):
        target = OUT / ("native-" + name + ".stl")
        target.unlink(missing_ok=True)
        cmd = [
            args.openscad,
            "--hardwarnings",
            "--backend",
            "Manifold",
            "--export-format",
            "binstl",
            "-D",
            f'part="{name}"',
            "-o",
            str(target),
            str(OUT / "collisions.scad"),
        ]
        run = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        log = run.stdout + run.stderr
        (OUT / ("native-" + name + ".log")).write_text(log)
        assert "WARNING" not in log and "ERROR" not in log, log
        if run.returncode == 1 and "Current top level object is empty." in log:
            results[name] = dict(result="empty intersection", returncode=1)
            target.unlink(missing_ok=True)
        else:
            assert run.returncode == 0 and "NoError" in log and target.exists(), log
            mesh = binary_stl(target)
            results[name] = dict(result="valid native manifold", returncode=0, **mesh)
            if name not in ("bars", "positive_control") and mesh["volume_mm3"] > 1e-6:
                failures.append(name)
    assert results["positive_control"].get("volume_mm3", 0) > 0.9, (
        "Deliberately colliding control was not detected"
    )
    assert results["bars"].get("volume_mm3", 0) > 1000
    cad = json.loads((OUT / "cad-verification.json").read_text())
    cad_volume = sum(cad[f"AFX-A12-R01-{n}-BAR"]["volume_mm3"] for n in d["paths"])
    relative = abs(results["bars"]["volume_mm3"] - cad_volume) / cad_volume
    assert relative < 0.0005, ("Independent native/OCC volume mismatch", relative)
    component_failures = []
    if "component_collision" in failures:
        for index, body in enumerate(packet["bodies"]):
            target = OUT / ("native-single-" + body[0] + ".stl")
            target.unlink(missing_ok=True)
            cmd = [
                args.openscad,
                "--hardwarnings",
                "--backend",
                "Manifold",
                "--export-format",
                "binstl",
                "-D",
                'part="single_component_collision"',
                "-D",
                f"component_index={index}",
                "-o",
                str(target),
                str(OUT / "collisions.scad"),
            ]
            run = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            log = run.stdout + run.stderr
            (OUT / ("native-single-" + body[0] + ".log")).write_text(log)
            assert "WARNING" not in log and "ERROR" not in log, log
            if run.returncode == 0:
                assert target.exists() and "NoError" in log
                volume = binary_stl(target)["volume_mm3"]
                if volume > 1e-6:
                    component_failures.append(dict(ref=body[0], volume_mm3=volume, height_scope=body[7]))
            else:
                assert run.returncode == 1 and "Current top level object is empty." in log, log
                target.unlink(missing_ok=True)
    assert packet == native_packet(d), "Native source changed during checks; reject and rerun"
    version = subprocess.run([args.openscad, "--version"], capture_output=True, text=True, check=True)
    sources = {
        str(p.relative_to(REPO)): sha(p)
        for p in sorted(ROOT.iterdir())
        if p.is_file() and p.suffix in (".json", ".py", ".md", ".csv")
    }
    sources.update(packet["source_sha256"])
    for dependency in (
        "hardware/cad/a12/thermal/verify.py",
        "hardware/electronics/common/sexpr.py",
        "hardware/electronics/output_stage/check_placement.py",
    ):
        sources[dependency] = sha(REPO / dependency)
    test = REPO / "tests/tooling/test_return_hardware.py"
    sources[str(test.relative_to(REPO))] = sha(test)
    report = dict(
        revision=d["revision"],
        native_engine=(version.stdout + version.stderr).strip(),
        native_checks=results,
        native_collision_failures=failures,
        actual_component_collision_findings=component_failures,
        native_port_contract_matches=packet["all_four_native_ports_match"],
        independent_native_occ_bar_volume_relative_difference=relative,
        source_sha256=sources,
        evidence_sha256={
            str(p.relative_to(REPO)): sha(p)
            for p in sorted(OUT.iterdir())
            if p.is_file() and p.name not in ("verification.json", "verify-log.txt")
        },
        all_component_and_mate_heights_approved=False,
        source_terminal_drawing_approved=False,
        contact_resistance_measured=False,
        pcb_return_access_resistance_measured=False,
        plating_and_conductivity_certificate_received=False,
        peek_thread_torque_lifetime_validated=False,
        physical_tests_performed=0,
        physical_fit_verified=False,
        electrical_joint_qualified=False,
        mechanical_stability_qualified=False,
        fabrication_released=False,
        build_ready=False,
    )
    (OUT / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if not k.endswith("_sha256")}, indent=2))


if __name__ == "__main__":
    main()
