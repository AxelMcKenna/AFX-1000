"""Remove two superseded power assertions exposed by TBI01 native ERC."""
import json
import shutil
from pathlib import Path
from hardware.electronics.common.sexpr import children, read_sexpr, sexpr
from hardware.fabrication.audio_core_ports import remove_header
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, OUT as SOURCE, prop, sha

OUT = STAGING / "two-board-signal-integration-02"


def build():
    assert not OUT.exists()
    paths = [Path(__file__), REPO / "hardware/fabrication/audio_core_ports.py",
             REPO / "hardware/fabrication/audio_core_integration.py",
             STAGING / "two-board-signal-native-01/erc.json",
             STAGING / "two-board-signal-native-01/drc.json"]
    paths += [p for p in SOURCE.rglob("*") if p.is_file()]
    shutil.copytree(SOURCE, OUT)
    changes = []
    for file, ref, reason in [
        ("A_codec.kicad_sch", "#A_CODEC_FLAG0", "Joined V3V3_IO is driven by Daisy D_U1001.38; external-input flag is superseded"),
        ("D_processor.kicad_sch", "#D_PROCESSOR_FLAG2", "Joined AGND already retains audio #A_ADC_FLAG3; duplicate assertion removed"),
    ]:
        path = OUT / file
        tree = read_sexpr(path.read_text())
        symbols = [s for s in children(tree, "symbol") if prop(s, "Reference")[2] == ref]
        assert len(symbols) == 1
        remove_header(tree, symbols[0])
        path.write_text(sexpr(tree) + "\n")
        changes.append(dict(sheet=file, removed_nonphysical_power_flag=ref, reason=reason))
    record = json.loads((SOURCE / "construction.json").read_text())
    record["source_sha256"] = {str(p.relative_to(REPO)): sha(p) for p in paths}
    record["superseded_power_assertions"] = changes
    record["all_electrical_components_and_pins_retained"] = True
    record["native_validation_pending"] = True
    (OUT / "construction.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(changes))


if __name__ == "__main__":
    build()
