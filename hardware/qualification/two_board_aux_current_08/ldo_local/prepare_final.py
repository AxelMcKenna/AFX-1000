"""Change only new C907 reference text; freeze all native inputs for this run."""
import copy,json,shutil
from pathlib import Path
from hardware.electronics.common.sexpr import read_sexpr,children,first,sexpr,Atom
from .immutable_inputs import prepare,sha
H=Path(__file__).resolve().parent;src=H/'native-07';stage=H/'final-stage-08';assert not stage.exists();shutil.copytree(H/'authored-v2',stage,symlinks=True)
board=read_sexpr((src/'power_protection.kicad_pcb').read_text());old=copy.deepcopy(board);fp=next(f for f in children(board,'footprint') if any(p[1:3]==['Reference','P_C907'] for p in children(f,'property')));ref=next(p for p in children(fp,'property') if p[1]=='Reference');before=copy.deepcopy(ref);first(ref,'at')[1:]=[Atom('184.5'),Atom('129'),Atom('0')];font=first(first(ref,'effects'),'font');first(font,'size')[1:]=[Atom('.8'),Atom('.8')]
# Keep stroke readable and within existing fabrication text settings.
t=next(iter(children(font,'thickness')),None)
if t:t[1]=Atom('.12')
else:font.append([Atom('thickness'),Atom('.12')])
(stage/'power_protection.kicad_pcb').write_text(sexpr(board)+'\n');bundle=H/'inputs-local-return-08';manifest=prepare(stage,bundle);manifest.update(source_board_sha256=sha(src/'power_protection.kicad_pcb'),candidate_board_sha256=sha(bundle/'power_protection.kicad_pcb'),script_sha256=sha(Path(__file__)),reference_before=before,reference_after=ref,bundle_name=bundle.name);(H/'inputs-local-return-08.json').write_text(json.dumps(manifest,indent=2)+'\n')
