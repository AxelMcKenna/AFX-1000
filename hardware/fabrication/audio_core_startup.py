"""AC02: buffer the shared-core requests and qualify settling with ADC bias."""

import argparse
import copy
import json
import shutil
import sys
from pathlib import Path

from hardware.electronics.common.flat_schematic import generate
from hardware.electronics.common.sexpr import a, children, first, read_sexpr, sexpr
from hardware.fabrication import audio_core_integration as parent
from hardware.fabrication.audit_audio_core import check as parent_check
from hardware.fabrication.audit_candidate import sha

REPO = Path(__file__).resolve().parents[2]
OLD = REPO / "hardware/fabrication/staging/audio-core-integration-01"
OUT = OLD.parent / "audio-core-startup-02"


def extra(ref, part, nets, kinds, xy, footprint, source):
    return dict(ref=ref, part=part, footprint=footprint, source=source,
        note="AC02 startup repair; package/process and installed qualification remain open",
        x=xy[0], y=xy[1], pins=[dict(number=str(n), name=str(n), kind=kinds.get(str(n), "passive"),
            side="L" if int(n) % 2 else "R", net=net) for n, net in nets.items()])


EXTRA = [
    extra("U210", "SN74LVC2G17DCKR",
          {"1":"CHIP_REQUEST", "2":"AGND", "3":"SETTLE_ENABLE", "4":"ADC_DRV_ENABLE", "5":"V3V3_IO", "6":"CHIP_EN"},
          {"1":"input", "2":"power_in", "3":"input", "4":"output", "5":"power_in", "6":"output"},
          (100.33,650.24), "Package_TO_SOT_SMD:SOT-363_SC-70-6", "https://www.ti.com/lit/ds/symlink/sn74lvc2g17.pdf"),
    extra("U211", "SN74LVC1G17DCKR",
          {"1":None, "2":"ADC_BIAS_WINDOW_OK", "3":"AGND", "4":"ADC_BIAS_IO", "5":"V3V3_IO"},
          {"1":"no_connect", "2":"input", "3":"power_in", "4":"output", "5":"power_in"},
          (300.99,650.24), "Package_TO_SOT_SMD:SOT-353_SC-70-5", "https://www.ti.com/lit/ds/symlink/sn74lvc1g17.pdf"),
    extra("U212", "SN74LVC1G08DCKR",
          {"1":"SETTLE_ENABLE", "2":"ADC_BIAS_IO", "3":"AGND", "4":"DRIVER_SETTLE_READY", "5":"V3V3_IO"},
          {"1":"input", "2":"input", "3":"power_in", "4":"output", "5":"power_in"},
          (501.65,650.24), "Package_TO_SOT_SMD:SOT-353_SC-70-5", "https://www.ti.com/lit/ds/symlink/sn74lvc1g08.pdf"),
    *[extra("C"+str(230+i), "100nF 16V X7R", {"1":"V3V3_IO","2":"AGND"}, {},
            (100.33+200.66*i,749.3), "Capacitor_SMD:C_0805_2012Metric", "") for i in range(3)],
]
GLOBAL = {"AGND", "CHIP_EN", "ADC_DRV_ENABLE", "ADC_BIAS_WINDOW_OK"}


def global_label(label, net):
    label[0], label[1] = a("global_label"), net
    if not children(label, "shape"):
        label.insert(2, [a("shape"), a("passive")])


def terminal_label(tree, ref, number):
    symbol = next(s for s in children(tree,"symbol") if parent.prop(s,"Reference")[2] == ref)
    lib = next(s for s in children(first(tree,"lib_symbols"),"symbol") if s[1] == first(symbol,"lib_id")[1])
    pin = next(p for unit in children(lib,"symbol") for p in children(unit,"pin") if str(first(p,"number")[1]) == str(number))
    at, p = first(symbol,"at"), first(pin,"at")
    pos = (round(float(at[1])+float(p[1]),4), round(float(at[2])-float(p[2]),4))
    wire = next(w for w in children(tree,"wire") if pos in {parent.point(p) for p in children(first(w,"pts"),"xy")})
    other = next(parent.point(p) for p in children(first(wire,"pts"),"xy") if parent.point(p) != pos)
    return next(n for n in tree if isinstance(n,list) and n and n[0] in ("label","global_label") and parent.point(first(n,"at")) == other)


def build():
    assert parent_check() == json.loads((OLD/"integration-handoff.json").read_text())
    assert not OUT.exists()
    OUT.mkdir()
    for path in OLD.iterdir():
        if path.suffix in (".kicad_pro", ".kicad_sch", ".kicad_sym") or path.name == "sym-lib-table":
            shutil.copyfile(path, OUT/path.name)
    (OUT/"source-recipes").mkdir()
    shutil.copyfile(Path(__file__),OUT/"source-recipes/audio_core_startup.py.txt")
    expected = json.loads((OLD/"expected-circuit.json").read_text())
    adc = read_sexpr((OUT/"adc.kicad_sch").read_text())
    for label in [*children(adc,"label"), *children(adc,"global_label")]:
        if label[1] == "CHIP_EN":
            global_label(label,"ADC_DRV_ENABLE")
        elif label[1] == "BIAS_OK":
            global_label(label,"ADC_BIAS_WINDOW_OK")
    (OUT/"adc.kicad_sch").write_text(sexpr(adc)+"\n")
    codec = read_sexpr((OUT/"codec.kicad_sch").read_text())
    label = terminal_label(codec,"U207","6")
    assert label[1] == "CHIP_EN"
    label[0], label[1] = a("label"), "CHIP_REQUEST"
    label[:] = [n for n in label if not (isinstance(n,list) and n and n[0] == "shape")]
    for ref,pin in (("U208","3"),("U209","1")):
        label = terminal_label(codec,ref,pin)
        assert label[1] == "SETTLE_ENABLE"
        label[1] = "DRIVER_SETTLE_READY"
    additions = OUT/"additions"
    additions.mkdir()
    generate(additions,"AC02","audio_core",EXTRA,[],(750,900),[])
    new = read_sexpr((additions/"audio_core.kicad_sch").read_text())
    first(codec,"lib_symbols").extend(copy.deepcopy(children(first(new,"lib_symbols"),"symbol")))
    instance = first(first(next(s for s in children(codec,"symbol") if parent.prop(s,"Reference")[2] == "U201"),"instances"),"project")
    for s in children(new,"symbol"):
        ref = parent.prop(s,"Reference")[2]
        s = copy.deepcopy(s)
        first(s,"instances")[:] = [a("instances"),copy.deepcopy(instance)]
        first(first(first(s,"instances"),"project"),"path")[2:] = [[a("reference"),ref],[a("unit"),1]]
        codec.append(s)
    for tag in ("wire","label","no_connect"):
        for node in children(new,tag):
            node = copy.deepcopy(node)
            if tag == "label" and node[1] in GLOBAL:
                global_label(node,node[1])
            codec.append(node)
    first(codec,"paper")[:] = [a("paper"),"User",750,900]
    (OUT/"codec.kicad_sch").write_text(sexpr(codec)+"\n")
    table = read_sexpr((OUT/"sym-lib-table").read_text())
    table.extend(copy.deepcopy(children(read_sexpr((additions/"sym-lib-table").read_text()),"lib")))
    (OUT/"sym-lib-table").write_text(sexpr(table)+"\n")
    shutil.copyfile(additions/"RMX_AC02.kicad_sym",OUT/"RMX_AC02.kicad_sym")
    root = read_sexpr((OUT/"audio_core.kicad_sch").read_text())
    first(first(root,"title_block"),"rev")[1] = "AC02"
    for t in children(root,"text"):
        if "CHIP_EN/driver-enable" in str(t[1]):
            t[1] = "Buffered codec/ADC requests; independent ADC-bias fault gate; revised settling budget."
    (OUT/"audio_core.kicad_sch").write_text(sexpr(root)+"\n")
    for ref,part in expected.items():
        if part["source_domain"] == "ADC":
            part["pins"] = {k: {"CHIP_EN":"ADC_DRV_ENABLE","ADC/BIAS_OK":"ADC_BIAS_WINDOW_OK"}.get(v,v) for k,v in part["pins"].items()}
    expected["U207"]["pins"]["6"] = "CODEC/CHIP_REQUEST"
    expected["U208"]["pins"]["3"] = "CODEC/DRIVER_SETTLE_READY"
    expected["U209"]["pins"]["1"] = "CODEC/DRIVER_SETTLE_READY"
    for part in EXTRA:
        expected[part["ref"]] = dict(source_domain="CODEC",source_ref="AC02:"+part["ref"],value=part["part"],footprint=part["footprint"],
            pins={p["number"]:(p["net"] if p["net"] in GLOBAL or p["net"] is None else "CODEC/"+p["net"]) for p in part["pins"]})
    assert len(expected) == 216
    (OUT/"expected-circuit.json").write_text(json.dumps(expected,indent=2,sort_keys=True)+"\n")
    c = json.loads((OLD/"construction.json").read_text())
    c["cross_sheet_net_maps"]["ADC"].update(DRV_ENABLE="ADC_DRV_ENABLE",BIAS_OK="ADC_BIAS_WINDOW_OK")
    c["source_sha256"].update({str(p.relative_to(REPO)):sha(p) for p in (Path(__file__),OLD/"construction.json",OLD/"native-review.json",OLD/"integration-handoff.json")})
    c.update(electrical_parts=216,added_AC02_parts=[p["ref"] for p in EXTRA],
        deliberate_changes=["Buffered CHIP_EN; ADC request after clock/ramp flags","5V-tolerant buffered ADC-bias window inhibits timer/final qualification","C227 minimum effective capacitance1.6uF; maximum2.8uF and100nA injection retained"],
        unchanged_AC01_passive_values_and_analog_pin_nets=True,driver_enable_reference_timing_qualified=False)
    (OUT/"construction.json").write_text(json.dumps(c,indent=2)+"\n")
    documents={}
    for name,part in (("hcs08","sn74hcs08"),("lvc2g17","sn74lvc2g17"),("lvc1g17","sn74lvc1g17"),("lvc1g08","sn74lvc1g08"),("tps3808","tps3808"),("tps3890","tps3890")):
        documents[part]=dict(url="https://www.ti.com/lit/ds/symlink/"+part+".pdf",sha256=sha(Path("/private/tmp/afx-startup-"+name+".pdf")))
    (OUT/"primary-documents.json").write_text(json.dumps(documents,indent=2)+"\n")
    print("Built216-part AC02 buffered requests/bias-qualified settling; native ERC/export pending")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=("build","review"))
    args = parser.parse_args()
    if args.action == "build":
        build()
    else:
        assert sys.platform == "linux"
        parent.OUT = OUT
        parent.review()
