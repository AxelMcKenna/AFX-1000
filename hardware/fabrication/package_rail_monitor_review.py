"""Freeze the inspected, explicitly unreleased E13 export packet for review."""

import argparse
import json
import zipfile
from pathlib import Path

from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.audit_rail_monitor_r83 import check as check_lands
from hardware.fabrication.inspect_rail_monitor_ipc import check as check_ipc
from hardware.fabrication.inspect_rail_monitor_outputs import DEFAULT, SOURCE, build

ARCHIVE = DEFAULT.parent / "E13-R83-REVIEW-ONLY-20261101.zip"


def validate_inputs():
    report, derived = build(DEFAULT)
    assert report == json.loads((DEFAULT / "manufacturing-inspection.json").read_text())
    assert all((DEFAULT / name).read_text() == text for name, text in derived.items())
    assert check_ipc() == json.loads((DEFAULT / "test/ipc-inspection.json").read_text())
    assert check_lands() == json.loads((SOURCE / "r83-land-review.json").read_text())
    visual = json.loads((DEFAULT / "previews/visual-review.json").read_text())
    assert visual["copper_and_front_mask_paste_images_visually_reviewed"]
    for name, digest in visual["image_sha256"].items():
        assert sha(DEFAULT / "previews" / name) == digest
    for name, digest in visual["source_gerber_sha256"].items():
        assert sha(DEFAULT / "gerbers" / name) == digest
    for name, digest in visual["source_assembly_sha256"].items():
        assert sha(DEFAULT / name) == digest
    extra = json.loads((DEFAULT / "extra-native-review.json").read_text())
    assert extra["source_PCB_sha256"] == sha(SOURCE / "rail_monitor.kicad_pcb")
    assert all(sha(DEFAULT / name) == digest for name, digest in extra["generated_file_sha256"].items())
    assert not report["fabrication_approved"] and not report["complete_BOM_approved"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    validate_inputs()
    manifest_path = DEFAULT / "review-package-manifest.json"
    files = sorted(p for p in DEFAULT.rglob("*") if p.is_file() and p != manifest_path)
    assert all(not p.is_symlink() for p in files)
    manifest = dict(schema="AFX-E13-manufacturing-review-1", status="REVIEW_ONLY_UNRELEASED",
                    files_sha256={str(p.relative_to(DEFAULT)): sha(p) for p in files},
                    package_recipe_sha256=sha(Path(__file__)),
                    source_scope="one unselected E13 R83 candidate; full-unit fabrication work remains",
                    reviewed_design_input_hashes=True, fabricator_DFM_accepted=False,
                    complete_BOM_approved=False, fabrication_approved=False, order_placed=False)
    checksum = ARCHIVE.with_suffix(".zip.sha256")
    if args.check:
        assert json.loads(manifest_path.read_text()) == manifest
    else:
        with manifest_path.open("x") as stream:
            json.dump(manifest, stream, indent=2)
            stream.write("\n")
        with zipfile.ZipFile(ARCHIVE, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for path in [*files, manifest_path]:
                name = "E13-R83-REVIEW-ONLY/" + str(path.relative_to(DEFAULT))
                item = zipfile.ZipInfo(name, date_time=(2026, 11, 1, 0, 0, 0))
                item.compress_type = zipfile.ZIP_DEFLATED
                item.external_attr = 0o100644 << 16
                archive.writestr(item, path.read_bytes())
        with checksum.open("x") as stream:
            stream.write(sha(ARCHIVE)+"  "+ARCHIVE.name+"\n")
    assert checksum.read_text() == sha(ARCHIVE)+"  "+ARCHIVE.name+"\n"
    with zipfile.ZipFile(ARCHIVE) as archive:
        assert archive.testzip() is None
        expected = {"E13-R83-REVIEW-ONLY/"+str(p.relative_to(DEFAULT)): p for p in [*files, manifest_path]}
        assert set(archive.namelist()) == set(expected)
        assert all(archive.read(name) == path.read_bytes() for name, path in expected.items())
    print(json.dumps(dict(archive=str(ARCHIVE), bytes=ARCHIVE.stat().st_size,
                          checked_files=len(files)+1, sha256=sha(ARCHIVE), fabrication_approved=False)))


if __name__ == "__main__":
    main()
