"""Build a full 32-part receiving diagnostic with explicit unqualified allowances."""
import copy,hashlib,json,math
from pathlib import Path
from shapely.geometry import box,Polygon
from hardware.cad.assembly_workflow import workflow as w
from hardware.cad.assembly_workflow.pcb_updates.r44.build import boxes
from hardware.electronics.common.sexpr import read_sexpr,children,first
from hardware.electronics.output_stage.check_placement import courtyard
H=Path(__file__).resolve().parent
Q=w.ROOT/'hardware/qualification/two_board_aux_current_08'
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def main():
    previous=H/'previous-manifest.json';assert not previous.exists();previous.write_bytes((w.HERE/'current.json').read_bytes())
    data,parts,checks,_=w.load_manifest(previous);capture=w.ROOT/data['mechanical_capture'];c=json.loads(capture.read_text())
    schedule=Q/'package_envelopes/envelopes.json';e=json.loads(schedule.read_text());pcb=Q/e['source_board'];assert w.sha(pcb)==e['source_board_sha256']
    tree=read_sexpr(pcb.read_text());fps={next(p[2] for p in children(f,'property') if p[1]=='Reference'):f for f in children(tree,'footprint')}
    old={r[0]:r for r in c['component_envelopes']};power=next(b for b in c['boards'] if b['id']=='power');surface=power['z']+power['thickness'];rows=[];detail=[];sources=[Path(__file__),previous,capture,schedule,pcb]
    for part in e['parts']:
        ref=part['reference'];fp=fps[ref];assert first(fp,'layer')[1]=='F.Cu' or ref in old
        props={p[1]:p[2] for p in children(fp,'property')};assert props['MPN']==part['mpn']
        source=Q/part['source'];assert w.sha(source)==part['source_sha256'];sources.append(source)
        at=first(fp,'at');x,y=map(float,at[1:3]);angle=float(at[3]) if len(at)>3 else 0;assert angle%90==0
        a=math.radians(angle);length,width,height=part['max_envelope_mm']
        # Recorded drawing axes agree with the native Fab rectangle axes. For
        # passives the long package axis also follows the two-pad separation.
        fab=[s for s in children(fp,'fp_rect') if first(s,'layer')[1].endswith('Fab')];assert len(fab)==1,ref
        start=first(fab[0],'start');end=first(fab[0],'end');fx=abs(float(end[1])-float(start[1]));fy=abs(float(end[2])-float(start[2]));assert (fx<=fy)==(length<=width),ref
        corners=[(x+dx*math.cos(a)+dy*math.sin(a),y-dx*math.sin(a)+dy*math.cos(a)) for dx in [-length/2,length/2] for dy in [-width/2,width/2]]
        body=[min(p[0] for p in corners),min(p[1] for p in corners),max(p[0] for p in corners),max(p[1] for p in corners)]
        side=first(fp,'layer')[1];court=courtyard(fp,'F.CrtYd' if side=='F.Cu' else 'B.CrtYd')
        xy=[min(body[0]-.25,court[0]),min(body[1]-.25,court[1]),max(body[2]+.25,court[2]),max(body[3]+.25,court[3])]
        z=[surface-.2,surface+height+.5] if side=='F.Cu' else [power['z']-height-.5,power['z']+.2]
        if ref in old:
            prior=copy.deepcopy(old[ref]);
            if ref=='E_C13':prior[1]=[107.295,127.395,109.255,130.795]
            xy=[min(xy[0],prior[1][0]),min(xy[1],prior[1][1]),max(xy[2],prior[1][2]),max(xy[3],prior[1][3])];z=[min(z[0],prior[2][0]),max(z[1],prior[2][1])]
        rows.append([ref,[round(v,9) for v in xy],[round(v,9) for v in z]])
        detail.append(dict(ref=ref,pose=[x,y,angle,side],package_max_mm=part['max_envelope_mm'],native_fab_axes_mm=[fx,fy],package_xy_bounds=body,courtyard=court))
    assert len(rows)==32
    excluded=set(json.loads((w.HERE/'base.json').read_text())['replaced_allocations']);refs={r[0] for r in rows};others=[r for r in c['component_envelopes']+c['tail_envelopes'] if r[0] not in refs|excluded]
    def overlap(a,b):return box(*a[1]).intersection(box(*b[1])).area*max(0,min(a[2][1],b[2][1])-max(a[2][0],b[2][0]))
    collisions=[]
    for i,row in enumerate(rows):
        for peer in others+rows[i+1:]:
            volume=overlap(row,peer)
            if volume>0:collisions.append(dict(left=row[0],right=peer[0],volume_mm3=volume))
    scad=H/'probes.scad';scad.write_text(boxes('power_changed_receiving',rows)+boxes('power_unchanged_allocations',others));sources.append(scad)
    save(H/'registry.json',dict(schema_version=1,components=[dict(id=n,source=w.relative(scad),module=n,role='receiving',scene=False) for n in ['power_changed_receiving','power_unchanged_allocations']],source_sha256={w.relative(p):w.sha(p) for p in sources}))
    obstacles=[n for n in parts if n not in ['base_component_allocations','base_main_pcbs']]+['power_unchanged_allocations'];candidate=json.loads(previous.read_text());candidate['registries'].append(w.relative(H/'registry.json'));new=[dict(id=f'power_full_{i//8+1}',left=['power_changed_receiving'],right=obstacles[i:i+8],expect='empty') for i in range(0,len(obstacles),8)];candidate['checks'].extend(new);save(H/'candidate.json',candidate)
    signal=next(b for b in c['boards'] if b['id']=='signal');assert all(Polygon(signal['outline']).intersection(box(*r[1])).area==0 for r in rows)
    save(H/'scope.json',dict(rows=rows,parts=detail,peer_collisions=collisions,new_checks=[x['id'] for x in new],external_roles=obstacles,xy_allowance_per_side_mm=.25,above_package_allowance_mm=.5,allowances_process_qualified=False,old_allocations_never_shrunk=True,selected=False,physical_qualified=False,signal_substrate_xy_clear=True,own_power_contact_expected=True))
    print('Prepared 32 affected receiving envelopes;',len(collisions),'peer overlap witnesses;',len(new),'external checks')
if __name__=='__main__':main()
