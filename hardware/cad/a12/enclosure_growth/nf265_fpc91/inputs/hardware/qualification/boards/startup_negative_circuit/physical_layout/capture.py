"""Capture the exact NF05R circuit and actual-land placement proposals.

No parent or electrical component value is changed. This prepares a NEW physical
layout study; NP01 recommendations do not become manufacturing acceptance.
"""

import copy
import hashlib
import json
import shutil
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent / "uv_recovery"
NP = ROOT.parents[1] / "nf_passive_selection"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verified(root):
    handoff = json.loads((root / "handoff.json").read_text())
    for name, digest in handoff["files_sha256"].items():
        assert sha(root / name) == digest, (root, name)
    return len(handoff["files_sha256"])


def box(tree):
    points = []
    for tag in ["fp_line", "fp_rect"]:
        for n in children(tree, tag):
            if first(n, "layer")[1] == "F.CrtYd":
                points.extend([list(map(float, first(n, k)[1:3])) for k in ["start", "end"]])
    assert points, tree[1]
    return [min(p[0] for p in points), min(p[1] for p in points),
            max(p[0] for p in points), max(p[1] for p in points)]


def main():
    assert not (ROOT / "sources/manifest.json").exists(), "Captured inputs are immutable"
    counts = {str(p): verified(p) for p in [PARENT, NP]}
    source = ROOT / "sources"
    source.mkdir(exist_ok=False)
    library = ROOT / "NF06P.pretty"
    library.mkdir(exist_ok=False)
    manifest = {}

    def capture(path, name):
        dest = source / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest)
        manifest[name] = dict(original=str(path), sha256=sha(path))

    for name in ["handoff.json", "components.json", "generated/netlist.xml", "generated/footprint-area.json"]:
        capture(PARENT / name, "NF05R/" + name)
    for name in ["handoff.json", "generated/selections.json", "analyses/native-lands.json"]:
        capture(NP / name, "NP01/" + name)
    parts = json.loads((source / "NF05R/components.json").read_text())
    selections = {r["ref"]: r for r in json.loads((source / "NP01/generated/selections.json").read_text())["rows"]}
    area = {r["ref"]: r for r in json.loads((source / "NF05R/generated/footprint-area.json").read_text())["rows"]}
    # New passive functions use the same physical package family, never the
    # historical nominal value or MPN from these geometry exemplars.
    for new, exemplar in [("R98", "R5"), ("R99", "R12"), ("C100", "C3")]:
        selections[new] = copy.deepcopy(selections[exemplar])
        selections[new]["geometry_exemplar_ref"] = exemplar
    current = {c["ref"]: c for c in parts}
    for new in ["R98", "R99", "C100"]:
        assert current[new]["footprint"] == selections[new]["old_footprint"], (new, "Geometry exemplar package mismatch")
    rows = []
    for c in parts:
        ref = c["ref"]
        original = Path(area[ref]["library_file"])
        assert sha(original) == area[ref]["library_sha256"]
        alias = c["footprint"].replace(":", "__")
        selected = selections.get(ref)
        replacement = NP / "analyses/NP01.pretty" / ((selected or {}).get("land", "UNSELECTED") + ".kicad_mod")
        if replacement.is_file():
            capture(replacement, "NP01/lands/" + replacement.name) if not (source / "NP01/lands" / replacement.name).exists() else None
            tree = read_sexpr(replacement.read_text())
            alias = "PROPOSED_" + selected["land"]
            # Manufacturer pad geometry stays exact. This explicit receiving
            # courtyard encloses pads plus catalog maximum plan dimensions.
            points = []
            for pad in children(tree, "pad"):
                x, y = map(float, first(pad, "at")[1:3])
                w, h = map(float, first(pad, "size")[1:3])
                points.extend([(x - w / 2, y - h / 2), (x + w / 2, y + h / 2)])
            body = selected["body_max_mm"]
            points.extend([(-body[0] / 2, -body[1] / 2), (body[0] / 2, body[1] / 2)])
            xx, yy = max(abs(p[0]) for p in points), max(abs(p[1]) for p in points)
            tree.extend(read_sexpr(f'''(extra
                (fp_rect (start {-xx-.25} {-yy-.25}) (end {xx+.25} {yy+.25})
                (stroke (width .05) (type default)) (fill none) (layer "F.CrtYd"))
                (fp_rect (start {-body[0]/2} {-body[1]/2}) (end {body[0]/2} {body[1]/2})
                (stroke (width .05) (type default)) (fill none) (layer "F.Fab")))''')[1:])
            land_kind = "Exact NP01 manufacturer-recommendation pads; receiving courtyard; unaccepted process"
        else:
            tree = read_sexpr(original.read_text())
            capture(original, "parent-lands/" + alias + ".kicad_mod") if not (source / "parent-lands" / (alias + ".kicad_mod")).exists() else None
            land_kind = "Retained captured source library; manufacturer/process review required"
        tree[1] = alias
        # Reference/value text is added as metadata on these pad-only proposals.
        if not children(tree, "property"):
            tree.extend(read_sexpr('''(extra
              (property "Reference" "REF**" (at 0 0) (layer "F.Fab") (effects (font (size .6 .6))))
              (property "Value" "PROPOSAL" (at 0 0) (layer "F.Fab") (effects (font (size .6 .6)) (hide yes))))''')[1:])
        dest = library / (alias + ".kicad_mod")
        # Shared aliases must have identical actual geometry. Body maxima vary
        # between MPNs, so use per-reference aliases when a plan box differs.
        text = sexpr(tree) + "\n"
        if dest.exists() and dest.read_text() != text:
            alias += "_" + ref
            tree[1] = alias
            dest = library / (alias + ".kicad_mod")
            text = sexpr(tree) + "\n"
        dest.write_text(text)
        b = box(tree)
        physical_pads = {str(p[1]) for p in children(tree, "pad") if str(p[1])}
        assert physical_pads == {p["number"] for p in c["pins"]}, (ref, physical_pads)
        rows.append(dict(ref=ref, parent_part=c["part"], parent_footprint=c["footprint"],
                         proposed_footprint="NF06P:" + alias, library_sha256=sha(dest),
                         courtyard_bbox_mm=b, courtyard_area_mm2=(b[2] - b[0]) * (b[3] - b[1]),
                         land_basis=land_kind,
                         historical_geometry_exemplar=selected.get("geometry_exemplar_ref") if selected else None,
                         exact_current_MPN_and_height_reconciled=False,
                         electrical_complete_tolerance_accepted=False,
                         manufacturer_process_accepted=False))
    assert len(rows) == len(parts) == 265
    (source / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (ROOT / "land-inventory.json").write_text(json.dumps(dict(
        revision="NF06P-265-actual-land-placement-inputs", source_seal_files_verified=counts,
        source_manifest_sha256=sha(source / "manifest.json"), rows=rows,
        all265_electrical_parts_values_and_pin_contracts_unchanged=True,
        recommended_lands_are_proposals_not_electrical_or_process_adoption=True,
        physical_qualified=False, fabrication_released=False), indent=2) + "\n")
    assert all(verified(p) == counts[str(p)] for p in [PARENT, NP])
    print("Captured265 exact circuit identities and actual-land placement proposals; parents unchanged")


if __name__ == "__main__":
    main()
