"""Add the actual private H9 post/head evidence; preserve earlier conceptual snapshot."""

import json
import shutil

from .capture import INPUTS, REPO, ROOT, sha


def main():
    prior = ROOT / "capture.json"
    if (INPUTS / "H9-support-verification.json").exists():
        raise ValueError("H9 capture already exists")
    shutil.copy2(prior, ROOT / "capture-before-H9.json")
    shutil.copy2(INPUTS / "electronics.json", INPUTS / "electronics-before-H9.json")
    folder = REPO / "hardware/cad/a12/harness/generated/receiver-ear-support"
    a = json.loads((folder / "analysis.json").read_text())
    v = json.loads((folder / "verification.json").read_text())
    if not v["local_post_and_head_fit_clear"] or v["changed_inputs"]:
        raise ValueError("Rejected H9 actual fit evidence")
    r = json.loads(prior.read_text())
    for group in ["source_sha256", "evidence_inputs_sha256", "evidence_sha256"]:
        for n, h in v.get(group, {}).items():
            if sha(REPO / n) != h:
                raise ValueError("Stale H9 proof:" + n)
            dst = INPUTS / "context" / n
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO / n, dst)
            r["original_source_sha256"][n] = h
    for name in ["analysis", "verification"]:
        src = folder / (name + ".json")
        shutil.copy2(src, INPUTS / ("H9-support-" + name + ".json"))
        r["original_source_sha256"][str(src.relative_to(REPO))] = sha(src)
    data = json.loads((INPUTS / "electronics.json").read_text())
    data["native"]["cylinders"] = [c for c in data["native"]["cylinders"] if c[0] != "provisional_H9_head"]
    data["native"]["cylinders"] += [
        [
            "actual_H9_post_requirement",
            182,
            97.2,
            2.7,
            7.2,
            3.8,
            "Actual private post outer envelope, blind insert bore conservatively filled",
        ],
        [
            "actual_H9_head_requirement",
            182,
            97.2,
            8.1,
            5.6,
            2.31,
            "Unselected exact M2x4-class fastener requirement; physical access not qualified",
        ],
    ]
    data["H9_provisional_not_actual_source"] = False
    data["H9_supported_E19_pcb_sha256"] = a["candidate_pcb_sha256"]
    data["H9_vertical_tool_access_clear"] = False
    data["H9_strain_relief_implemented"] = False
    (INPUTS / "electronics.json").write_text(json.dumps(data, indent=2) + "\n")
    r["H9_actual_source_added"] = True
    r["H9_vertical_tool_access_clear"] = False
    r["captured_inputs_sha256"] = {
        str(p.relative_to(INPUTS)): sha(p) for p in INPUTS.rglob("*") if p.is_file()
    }
    prior.write_text(json.dumps(r, indent=2) + "\n")
    print("Actual H9 source captured; service access remains failed")


if __name__ == "__main__":
    main()
