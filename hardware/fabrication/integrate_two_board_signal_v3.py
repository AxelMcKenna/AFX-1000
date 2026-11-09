"""Remove orphan labels belonging exclusively to the two removed power flags."""
import json
import shutil
from pathlib import Path
from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha

SOURCE = STAGING / "two-board-signal-integration-02"
OUT = STAGING / "two-board-signal-integration-03"


def build():
    assert not OUT.exists()
    erc_path = STAGING / "two-board-signal-native-02/erc.json"
    erc = json.loads(erc_path.read_text())
    violations = [v for sheet in erc["sheets"] for v in sheet.get("violations", [])]
    assert len(violations) == 2 and all(v["type"] == "label_dangling" for v in violations)
    ids = {item["uuid"] for v in violations for item in v["items"]}
    assert ids == {"35eb356c-3ebe-5591-93de-0316f409e166", "6c9e5b66-8f12-560d-b954-948881d34d94"}
    shutil.copytree(SOURCE, OUT)
    removed = []
    for name in ["A_codec.kicad_sch", "D_processor.kicad_sch"]:
        path = OUT / name
        tree = read_sexpr(path.read_text())
        for label in children(tree, "global_label"):
            if str(first(label, "uuid")[1]) in ids:
                removed.append(dict(sheet=name, label=label[1], uuid=first(label, "uuid")[1]))
                tree.remove(label)
        path.write_text(sexpr(tree) + "\n")
    assert len(removed) == 2
    record = json.loads((SOURCE / "construction.json").read_text())
    paths = [Path(__file__), erc_path, *[p for p in SOURCE.rglob("*") if p.is_file()]]
    record["source_sha256"] = {str(p.relative_to(REPO)): sha(p) for p in paths}
    record["orphaned_flag_labels_removed"] = removed
    (OUT / "construction.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(removed))


if __name__ == "__main__":
    build()
