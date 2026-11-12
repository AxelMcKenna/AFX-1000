"""Generate standalone manufacturer-land-pattern candidates; never edit a PCB."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
BASE=HERE.parent

def pad(n,x,y,w,h,mask=.05,paste=None):
    extra=f'(solder_mask_margin {mask})'
    if paste is not None: extra+=f'(solder_paste_margin {paste})'
    return f'(pad "{n}" smd roundrect (at {x} {y}) (size {w} {h}) (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio {min(.05/min(w,h),.25)}) {extra})'

def build():
    records=[]; lib=HERE/'AUX_READY.pretty';lib.mkdir(exist_ok=True)
    def emit(name,refs,mpn,body,cy,pads,source,pages,note):
        s=f'(footprint "{name}" (version 20241229) (generator "aux_land_review") (layer "F.Cu") (attr smd)\n'
        s+=f'(descr "{note}")\n'
        for key,value,y,layer in [('Reference','REF**',-cy[1]/2-1,'F.SilkS'),('Value',name,cy[1]/2+1,'F.Fab')]:
            s+=f'(property "{key}" "{value}" (at 0 {y}) (layer "{layer}") (effects (font (size 0.6 0.6) (thickness 0.1))))\n'
        for size,layer,width in [(body,'F.Fab',.1),(cy,'F.CrtYd',.05)]:
            s+=f'(fp_rect (start {-size[0]/2} {-size[1]/2}) (end {size[0]/2} {size[1]/2}) (stroke (width {width}) (type solid)) (fill none) (layer "{layer}"))\n'
        marker_x=(cy[0]/2+.15) if name=='Coilcraft_XAL4040' else (-cy[0]/2-.15)
        s+=f'(fp_circle (center {marker_x} {-cy[1]/2}) (end {marker_x+.1} {-cy[1]/2}) (stroke (width .1) (type solid)) (fill none) (layer "F.SilkS"))\n'
        s+='\n'.join(pads)+')\n'; (lib/f'{name}.kicad_mod').write_text(s)
        records.append(dict(footprint='AUX_READY:'+name,references=refs,mpn=mpn,body_max_mm=body,courtyard_mm=cy,source=source,pdf_pages=pages,source_sha256=hashlib.sha256((BASE/source).read_bytes()).hexdigest(),note=note))
    emit('TI_DQC0010A',['P_U900'],'TPS62175DQCR',[2.1,3.1,.8],[2.9,3.6],
         [pad(i,-.95,(i-3)*.5,.5,.25) for i in range(1,6)]+[pad(11-i,.95,(i-3)*.5,.5,.25) for i in range(1,6)]+[pad(11,0,0,.84,2.4)],
         'fast_inhibit/primary/tps62175.pdf',[31,32],'TI 4218281/A. Thermal vias not embedded; process and thermal review required. EP paste aperture remains process-review item.')
    emit('TI_DSE0006A',['E_U900','P_U902'],'TPS3703A5330DSER / TPS3703A5500DSER',[1.55,1.55,.8],[2.5,2.05],
         [pad(1,-.55,-.5,.9,.35,-.05,-.05),pad(2,-.6,0,.8,.35,-.05,-.05),pad(3,-.6,.5,.8,.35,-.05,-.05)]+[pad(n,.6,y,.7,.25) for n,y in [(4,.5),(5,0),(6,-.5)]],
         'fast_inhibit/primary/tps3703.pdf',[37,38,39],'TI 4220552/B. Left copper enlarged 0.05 per edge for SMD openings; right NSMD. Pin 1 opening center -0.55 from fixed outer edge. Stencil openings match TI 0.125-mm example.')
    emit('Coilcraft_XAL4040',['P_L900'],'XAL4040-103MEC',[4.3,4.3,4.1],[4.8,4.8],[pad(1,1.185,0,.98,3.4),pad(2,-1.185,0,.98,3.4)],
         'schematic_candidate/primary/xal4000.pdf',[4],'Coilcraft 806-4. 2.37 mm is pad center spacing, not gap. Right terminal marked short lead is pad 1 / SW; verify orientation during assembly.')
    emit('Vishay_CRCW2512',['P_R902'],'CRCW25124R70FKEG',[6.5,3.3,.7],[8.15,4],[pad(1,-3.1,0,1.45,3.5),pad(2,3.1,0,1.45,3.5)],
         'held_rail/primary/crcw.pdf',[11],'Vishay 20035 reflow recommendation G4.75 Y1.45 X3.50 Z7.65; courtyard adds 0.25 mm around land extent.')
    emit('KEMET_D_7343_LevelB',['P_C902','P_C905'],'T520D227M010ATE025',[7.6,4.6,3.1],[9.12,5.1],[pad(1,-3.12,0,2.37,2.43),pad(2,3.12,0,2.37,2.43)],
         'placement/primary/kem-t2076.pdf',[28],'KEMET T2076 2019 Table 2 density B. W2.43 L2.37 S3.87 V1=9.12 V2=5.10. Pin 1 anode left. Package maximum body from exact-part sheet in held_rail.')
    emit('TI_DBV0005A',['P_U901'],'TPS7A2033PDBVR',[3.0,3.55,1.45],[4.2,4.05],
         [pad(n,-1.3,y,1.1,.6) for n,y in [(1,-.95),(2,0),(3,.95)]]+[pad(n,1.3,y,1.1,.6) for n,y in [(4,.95),(5,-.95)]],
         'held_rail/primary/tps7a20.pdf',[56,57,58],'TI 4214839/K NSMD recommendation. Replaces generic assigned footprint whose 1.325 mm pad length differs from TI 1.1 mm recommendation. Body field conservatively covers total leads.')
    (HERE/'footprints.json').write_text(json.dumps({'pcb_modified':False,'parts':records},indent=2)+'\n')
    (HERE/'fp-lib-table').write_text('(fp_lib_table (lib (name "AUX_READY") (type "KiCad") (uri "${KIPRJMOD}/AUX_READY.pretty") (options "") (descr "Manufacturer land review candidates")))\n')
if __name__=='__main__':build()
