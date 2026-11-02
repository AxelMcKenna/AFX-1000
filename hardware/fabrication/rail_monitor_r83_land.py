"""Separate E13 candidate with Bourns CRT0805 recommended R83 copper lands."""

import copy
import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.fabrication.audit_candidate import geometry_delta, native_evidence_errors, sha

REPO = Path(__file__).resolve().parents[2]
STAGING = REPO / "hardware/fabrication/staging"
SOURCE = STAGING / "rail-monitor-reserved-closed-native-02"
CANDIDATE = STAGING / "rail-monitor-r83-land-01"
NATIVE = STAGING / "rail-monitor-r83-land-native-01"
LIBRARY = "AFX_RailMonitor"
NAME = "Bourns_CRT0805"
FPID = LIBRARY + ":" + NAME


def reference(footprint):
    return next(p[2] for p in children(footprint, "property") if p[1] == "Reference")


def lands(original):
    result = copy.deepcopy(original)
    result[1] = FPID
    for pad in children(result, "pad"):
        if pad[1] not in ("1", "2"):
            raise ValueError("Unexpected pad in R83 footprint")
        pad[3] = a("rect")
        first(pad, "at")[1:3] = [-1 if pad[1] == "1" else 1, 0]
        first(pad, "size")[1:] = [1, 1.35]
        pad[:] = [n for n in pad if not (isinstance(n, list) and n and n[0] == "roundrect_rratio")]
    for rectangle in children(result, "fp_rect"):
        if first(rectangle, "layer")[1] == "F.CrtYd":
            first(rectangle, "start")[1:] = [-1.75, -0.95]
            first(rectangle, "end")[1:] = [1.75, 0.95]
    return result


def construct():
    review = json.loads((SOURCE / "review.json").read_text())
    if native_evidence_errors(SOURCE / "rail_monitor.kicad_pro", review) or not review["status"]["native_closed"]:
        raise ValueError("Require the current closed native parent")
    inputs = [SOURCE / ("rail_monitor" + suffix) for suffix in (".kicad_pcb", ".kicad_sch", ".kicad_pro")]
    inputs += [SOURCE / p for p in ("netlist.xml", "review.json", "fp-lib-table", "sym-lib-table")]
    inputs += sorted(p for p in (SOURCE / "libraries").rglob("*") if p.is_file())
    hashes = {str(p.relative_to(REPO)): sha(p) for p in inputs}
    CANDIDATE.mkdir(exist_ok=False)
    for path in inputs[:7]:
        shutil.copyfile(path, CANDIDATE / path.name)
    shutil.copytree(SOURCE / "libraries", CANDIDATE / "libraries")
    # The parent's receipt is input evidence, never a receipt for this new board.
    (CANDIDATE / "review.json").unlink()
    pcb = CANDIDATE / "rail_monitor.kicad_pcb"
    tree = read_sexpr(pcb.read_text())
    target = next(f for f in children(tree, "footprint") if reference(f) == "R83")
    assert target[1] == "Resistor_SMD:R_0805_2012Metric"
    original = copy.deepcopy(target)
    replacement = lands(target)
    tree[tree.index(target)] = replacement
    pcb.write_text(sexpr(tree) + "\n")
    schematic = CANDIDATE / "rail_monitor.kicad_sch"
    sch = read_sexpr(schematic.read_text())
    symbol = next(s for s in children(sch, "symbol") if reference(s) == "R83")
    next(p for p in children(symbol, "property") if p[1] == "Footprint")[2] = FPID
    schematic.write_text(sexpr(sch) + "\n")
    xml = CANDIDATE / "netlist.xml"
    netlist = ET.parse(xml)
    netlist.getroot().find("./components/comp[@ref='R83']/footprint").text = FPID
    netlist.write(xml, encoding="utf-8", xml_declaration=True)
    library = CANDIDATE / (LIBRARY + ".pretty")
    library.mkdir()
    prototype = read_sexpr((SOURCE / "libraries/Resistor_SMD.pretty/R_0805_2012Metric.kicad_mod").read_text())
    (library / (NAME + ".kicad_mod")).write_text(sexpr(lands(prototype)) + "\n")
    table = read_sexpr((CANDIDATE / "fp-lib-table").read_text())
    table.append([a("lib"), [a("name"), LIBRARY], [a("type"), "KiCad"],
                  [a("uri"), "${KIPRJMOD}/" + library.name], [a("options"), ""],
                  [a("descr"), "Bourns CRT0805 recommended copper lands; process acceptance pending"]])
    (CANDIDATE / "fp-lib-table").write_text(sexpr(table) + "\n")
    delta = geometry_delta(read_sexpr((SOURCE / pcb.name).read_text()), tree)
    assert delta["other_root_geometry_exact"]
    assert not any(any(rows.values()) for tag, rows in delta.items() if tag in ("segment", "via", "zone"))
    assert delta["footprint"]["changed"] == [str(first(original, "uuid")[1])]
    assert all(sha(REPO / name) == digest for name, digest in hashes.items())
    (CANDIDATE / "construction.json").write_text(json.dumps(dict(
        source_sha256=hashes, recipe_sha256=sha(Path(__file__)), changed_reference="R83", new_FPID=FPID,
        recommended_copper_pad_size_mm=[1, 1.35], recommended_inner_gap_mm=1,
        courtyard_half_extents_mm=[1.75, 0.95], candidate_body_maximum_mm=[2.15, 1.4, 0.65],
        manufacturer_url="https://www.bourns.com/docs/product-datasheets/crt.pdf",
        manufacturer_document_sha256="094e3bd73684274232f29cce9861062555f18e8316d0c974fe295f4adee46457",
        document_revision="01C, page 2; drawing visually reviewed",
        candidate_order_code="CRT0805-PT-1270ELF", exact_order_code_supply_confirmed=False,
        other_components_and_all_existing_routes_unchanged=True, native_review_pending=True,
        mask_paste_registration_and_assembly_accepted=False, installed_error_budget_qualified=False,
        mechanical_receiving_updated=False, fabrication_approved=False,
    ), indent=2) + "\n")
    print("Created isolated R83 copper-land candidate; current selected source unchanged")


if __name__ == "__main__":
    construct()
