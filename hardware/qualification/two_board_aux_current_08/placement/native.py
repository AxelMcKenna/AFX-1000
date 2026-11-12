"""Load standalone library with pinned Linux KiCad, export actual pad geometry."""
import hashlib,json,sys
from pathlib import Path
import pcbnew
src=Path(sys.argv[1]);out=Path(sys.argv[2]); rows=[]
def mm(v):return None if v is None else pcbnew.ToMM(v)
for p in sorted((src/'AUX_READY.pretty').glob('*.kicad_mod')):
    f=pcbnew.FootprintLoad(str(p.parent),p.stem)
    assert f is not None,p
    pads=[]
    for q in f.Pads():
        pads.append({'number':q.GetNumber(),'at_mm':[pcbnew.ToMM(q.GetPosition().x),pcbnew.ToMM(q.GetPosition().y)],'size_mm':[pcbnew.ToMM(q.GetSize().x),pcbnew.ToMM(q.GetSize().y)],'mask_margin_mm':pcbnew.ToMM(q.GetLocalSolderMaskMargin()),'paste_margin_mm':mm(q.GetLocalSolderPasteMargin())})
    rows.append({'file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'pads':pads})
(out/'native-footprints.json').write_text(json.dumps({'native_version':pcbnew.Version(),'board_written':False,'footprints':rows},indent=2)+'\n')
