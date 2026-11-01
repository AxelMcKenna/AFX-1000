"""New actual local F/B return fills on isolated native-checked routing draft."""

import hashlib
import json
import shutil
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "routing/plane-view-pass2"
OUT = ROOT / "routing/ground-fills-pass3"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


OUT.mkdir(exist_ok=True)
assert not (OUT / "input.kicad_pcb").exists(), "Preserve candidate"
board = pcbnew.LoadBoard(str(SRC / "output.kicad_pcb"))
for layer in [pcbnew.F_Cu, pcbnew.B_Cu]:
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(board.FindNet("/GND"))
    z.SetZoneName("FPC_LOCAL_RETURN_" + board.GetLayerName(layer))
    z.SetLocalClearance(pcbnew.FromMM(0.2))
    z.SetMinThickness(pcbnew.FromMM(0.2))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    o = z.Outline()
    o.NewOutline()
    for x, y in [(0.5, 0.5), (65.5, 0.5), (65.5, 37.5), (0.5, 37.5)]:
        o.Append(pcbnew.FromMM(x), pcbnew.FromMM(y))
    board.Add(z)
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(str(OUT / "input.kicad_pcb"), board)
for name in ["input", "output"]:
    shutil.copy2(SRC / "input.kicad_pro", OUT / (name + ".kicad_pro"))
shutil.copy2(SRC / "output.kicad_sch", OUT / "input.kicad_sch")
shutil.copy2(SRC / "output.kicad_sch", OUT / "output.kicad_sch")
shutil.copy2(SRC / "fp-lib-table", OUT / "fp-lib-table")
(OUT / "return-fill-proposal.json").write_text(
    json.dumps(
        dict(
            parent_sha256=sha(SRC / "output.kicad_pcb"),
            pcb_sha256=sha(OUT / "input.kicad_pcb"),
            added_layers=["F.Cu", "B.Cu"],
            actual_fill_and_native_DRC_required=True,
            quiet_noise_ampacity_and_PDN_qualified=False,
            physical_qualified=False,
        ),
        indent=2,
    )
    + "\n"
)
