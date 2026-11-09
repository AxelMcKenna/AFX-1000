"""TB04: complete conditional placement, with explicit force/strain repack."""
import argparse
import copy
import json
import time
from collections import Counter
from pathlib import Path
from hardware.fabrication import two_board_placement as base
from hardware.fabrication.two_board_placement_v3 import capture as capture_with_new_mounts


class Packer(base.Packer):
    def __init__(self,cap):
        super().__init__(cap)
        for i,(x,y) in enumerate(cap['power_mount_centres']):
            for side in ['F','B']:
                self.add_obstacle(side,[x-3.6,y-3.6,x+3.6,y+3.6],f'proposed_power_mount_{i}')

    def install(self,p,xy,fixed=False):
        super().install(p,xy,fixed)
        if p['mechanical']:
            b=base.offset(p['body_relative_xy'],*xy)
            other='B' if p['side']=='F' else 'F'
            self.paint(self.mask[other],b,base.GAP)
            self.add_obstacle(other,b,p['id'])


def build(label):
    out=base.ROOT/'staging'/label;assert not out.exists()
    cap=capture_with_new_mounts();cap['source_sha256'][str(Path(__file__).relative_to(base.REPO))]=base.sha(Path(__file__))
    cap['fixed_exterior_inlet_refs']=['J1','S1']
    cap['force_strain_changes_mm']={'J4':[1.5,0],'H102':[3,0]}
    cap['force_strain_process_and_strength_approved']=False
    cap['identified_existing_receiving_clash']='I_J3 complete receiver intersects retained service_USB allocation; internal connector may move'
    out.mkdir();(out/'capture.json').write_text(json.dumps(cap,indent=2)+'\n')
    working=copy.deepcopy(cap);working['context']=[r for r in cap['context'] if not r['id'].startswith('inlet_')]
    pack=Packer(working);power=[p for p in cap['parts'] if p['target_board']=='power_protection'];failed=[];start=time.monotonic()
    for p in power:
        if p['role']=='input_protection' and (p['mechanical'] or p['ref'] in ['J1','S1']):pack.install(p,p['source_world_xy'],fixed=True)
    force=[p for p in power if p['role']=='negative_startup_protection' and p['ref'] in ['J2','J4','H101','H102']]
    for p in force:
        xy=[p['source_xy'][0]+112+(1.5 if p['ref']=='J4' else 3 if p['ref']=='H102' else 0),p['source_xy'][1]+137]
        pack.install(p,xy)
    remaining=[p for p in power if p['id'] not in pack.placed]
    remaining.sort(key=lambda p:(-((p['body_relative_xy'][2]-p['body_relative_xy'][0])*(p['body_relative_xy'][3]-p['body_relative_xy'][1])),p['id']))
    for i,p in enumerate(remaining):
        role=p['role'];xy=p['source_world_xy']
        if role=='negative_startup_protection':target=[172+p['source_xy'][0],143+p['source_xy'][1]]
        elif role=='fan_health_protection':target=[14+p['source_xy'][0],144+p['source_xy'][1]]
        elif role=='rail_monitor':target=[12+p['source_xy'][0]*2.7,35+p['source_xy'][1]*.08]
        else:target=xy
        if role in ['power_supply','rail_disconnect','input_protection'] and pack.legal(p,xy):chosen=xy
        else:chosen=pack.find(p,target)
        if chosen is None:failed.append(dict(id=p['id'],role=role,reason='bounded fixed-angle/fixed-face packing exhausted'))
        else:pack.install(p,chosen)
        if i%100==0:print(f'{i}/{len(remaining)} scanned; placed {len(pack.placed)}; missing {len(failed)}',flush=True)
    signal={p['id']:dict(xy=p['source_world_xy'],side=p['side'],angle=p['angle']) for p in cap['parts'] if p['target_board']=='signal_main'}
    result=dict(source_sha256={str((out/'capture.json').relative_to(base.REPO)):base.sha(out/'capture.json'),str(Path(__file__).relative_to(base.REPO)):base.sha(Path(__file__))},
        poses={**signal,**pack.placed},failed=failed,source_part_count=len(cap['parts']),placed_count=len(signal)+len(pack.placed),
        source_counts=dict(Counter(p['role'] for p in cap['parts'])),search_elapsed_seconds=time.monotonic()-start,
        all_known_parts_placed=not failed,old_nets_merged=False,old_copper_reused=False,
        complete_fit_verified=False,fabrication_released=False)
    (out/'placement.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['source_part_count','placed_count','failed','search_elapsed_seconds']}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--label',default='two-board-placement-04')
    build(parser.parse_args().label)
