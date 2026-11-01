"""Read-only OS trust checks then fresh native Boolean self-tests.

Run with access to macOS signing services, not inside the restricted sandbox.
This never changes quarantine, signing, Gatekeeper or existing receipts.
"""

import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parent
APP = Path("/private/tmp/afx-openscad-20261027-mounted/OpenSCAD.app")
BINARY = APP / "Contents/MacOS/OpenSCAD"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    out = ROOT / "generated/native"
    out.mkdir(parents=True, exist_ok=False)
    commands = []

    def run(args, label):
        result = subprocess.run([str(a) for a in args], text=True, capture_output=True, timeout=60)
        (out / (label + ".log")).write_text(result.stdout + result.stderr)
        commands.append(dict(label=label, command=[str(a) for a in args], returncode=result.returncode,
                             stdout=result.stdout, stderr=result.stderr))
        return result

    signed = run(["/usr/bin/codesign", "--verify", "--deep", "--strict", "--verbose=2", APP], "codesign")
    assert signed.returncode == 0, commands[-1]
    assessed = run(["/usr/sbin/spctl", "--assess", "--type", "execute", "--verbose=2", APP], "gatekeeper")
    assert assessed.returncode == 0 and "Notarized Developer ID" in assessed.stderr, commands[-1]
    version = run([BINARY, "--version"], "version")
    assert version.returncode == 0 and "2026.10.27" in version.stdout + version.stderr
    checks = {}
    for name, expected_volume in [("solid", 1.5), ("witness", .008), ("empty", None)]:
        path = out / (name + ".stl")
        result = run([BINARY, "--backend", "Manifold", "--export-format", "binstl", "-o", path,
                      ROOT / "fixtures" / (name + ".scad")], name)
        log = result.stdout + result.stderr
        assert "WARNING:" not in log and "ERROR:" not in log, commands[-1]
        if expected_volume is None:
            assert result.returncode == 1 and not path.exists()
            assert "Current top level object is empty." in log
            checks[name] = dict(expected_empty=True, exact_empty_receipt=True)
            continue
        assert result.returncode == 0 and "NoError" in log, commands[-1]
        raw = trimesh.load_mesh(path, process=False)
        # STL stores unindexed triangle vertices. Index identical coordinates
        # exactly; do not move vertices, repair a mesh or discard any face.
        vertices, index = np.unique(raw.vertices, axis=0, return_inverse=True)
        mesh = trimesh.Trimesh(vertices=vertices, faces=index[raw.faces], process=False)
        assert np.array_equal(mesh.vertices[mesh.faces], raw.vertices[raw.faces])
        assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume > 0
        assert bool((mesh.area_faces > 0).all())
        assert abs(mesh.volume - expected_volume) < 1e-6, mesh.volume
        checks[name] = dict(volume_mm3=float(mesh.volume), expected_volume_mm3=expected_volume,
                            closed_oriented=True, degenerate_triangles=0,
                            exact_coordinate_indexing_only=True, discarded_triangles=0)
    report = dict(scope="New native macOS trust/Manifold proof only; old Linux/design evidence unchanged",
                  app_path=str(APP), binary_sha256=sha(BINARY),
                  source_sha256={str(p.relative_to(ROOT)): sha(p) for p in [Path(__file__), *sorted((ROOT / "fixtures").glob("*.scad"))]},
                  actual_commands=commands, checks=checks, macOS_signature_verified=True,
                  macOS_gatekeeper_accepted=True, notarized_developer_id=True,
                  security_or_quarantine_settings_changed=False, old_receipts_modified=False,
                  actual_design_checks_inherited=False, physical_qualified=False, fabrication_released=False)
    (ROOT / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Verified official Mac OpenSCAD: signed/notarized; three native Boolean self-tests pass")


if __name__ == "__main__":
    main()
