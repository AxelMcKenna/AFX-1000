"""Capture actual E28 construction and rasterize native before/after plots."""
import json, subprocess
from pathlib import Path
from PIL import Image, ImageDraw
from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication.audit_candidate import sha

ROOT = Path(__file__).resolve().parent
OUT = ROOT/'staging/e28-cleanup-review-01'
FINAL = ROOT/'staging/e28-branch-cleanup-native-12'

def run():
    OUT.mkdir(exist_ok=False)
    pcb = FINAL/'rail_disconnect.kicad_pcb'
    tree = read_sexpr(pcb.read_text())
    setup = first(tree,'setup'); stack = first(setup,'stackup')
    layers = []
    for layer in children(stack,'layer'):
        layers.append(dict(name=layer[1],properties={v[0]:v[1:] for v in layer[2:]}))
    small = [v for v in children(tree,'via') if float(first(v,'drill')[1])<.3]
    assert len(small)==1
    construction = dict(source_sha256={str(p):sha(p) for p in [pcb,Path(__file__)]},
        declared_board_thickness_mm=float(first(first(tree,'general'),'thickness')[1]),
        native_stack_layers=layers, native_other_stack_fields=[v for v in stack[1:] if v[0]!='layer'],
        retained_small_via=small[0],supplier_stack_and_process_accepted=False,fabrication_released=False)
    (OUT/'construction-review.json').write_text(json.dumps(construction,indent=2)+'\n')
    outputs=[]; inputs=[pcb,Path(__file__)]
    names=['front',*[f'inner{i}' for i in range(1,7)],'back']
    for name in names:
        panels=[]
        for state in ['before','after']:
            folder=ROOT/f'staging/e28-{state}-cleanup-plots-01'
            inputs.extend([folder/'export.json',folder/(name+'.pdf')])
            pdf=folder/(name+'.pdf'); prefix=OUT/f'{state}-{name}'
            subprocess.run(['pdftoppm','-r','300','-f','1','-singlefile','-png',str(pdf),str(prefix)],check=True,timeout=30)
            raw=prefix.with_suffix('.png'); image=Image.open(raw).convert('RGB')
            # Native A4 landscape plot retains millimetre drawing coordinates.
            box=tuple(round(v*300/25.4) for v in [98,98,258,162])
            assert image.width>=box[2] and image.height>=box[3]
            crop=image.crop(box); crop.save(raw); outputs.append(raw)
            panel=Image.new('RGB',(crop.width,crop.height+40),'white')
            panel.paste(crop,(0,40));ImageDraw.Draw(panel).text((12,10),f'{state.upper()} / {name} / native plot, 300 dpi',fill='black')
            panels.append(panel)
        sheet=Image.new('RGB',(panels[0].width,panels[0].height*2),'white')
        for i,panel in enumerate(panels):sheet.paste(panel,(0,i*panel.height))
        dest=OUT/f'compare-{name}.png';sheet.save(dest);outputs.append(dest)
    (OUT/'assets.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in inputs},
        outputs_sha256={p.name:sha(p) for p in outputs},inspected=False,fabrication_released=False),indent=2)+'\n')
    print('Created construction record and eight before/after comparison sheets')

if __name__=='__main__':run()
