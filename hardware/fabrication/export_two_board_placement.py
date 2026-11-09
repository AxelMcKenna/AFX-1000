"""Emit review-only KiCad placements; preserve every source pad's private net."""
import copy
import hashlib
import json
import uuid
from collections import Counter
from pathlib import Path
from hardware.electronics.common.sexpr import a,children,first,read_sexpr,sexpr
from hardware.fabrication.two_board_placement import ROOT,REPO,sha

FOLDER=ROOT/'staging/two-board-placement-04'
OUT=ROOT/'staging/two-board-placement-cad-01'


def uid(name):return str(uuid.uuid5(uuid.NAMESPACE_URL,'AFX:TB04:'+name))


def mechanical(name,xy,drill,radius):
    f=[a('footprint'),'AFX_Placement:'+name,[a('layer'),'F.Cu'],[a('uuid'),uid(name)],
       [a('at'),*xy],[a('property'),'Reference',name,[a('at'),0,0,0],[a('layer'),'F.SilkS'],[a('hide'),a('yes')],
        [a('effects'),[a('font'),[a('size'),1,1],[a('thickness'),.15]]]],
       [a('property'),'Value','PROPOSED_NPTH',[a('at'),0,0,0],[a('layer'),'F.Fab'],
        [a('effects'),[a('font'),[a('size'),1,1],[a('thickness'),.15]]]],
       [a('attr'),a('exclude_from_pos_files'),a('exclude_from_bom')],
       [a('pad'),'',a('np_thru_hole'),a('circle'),[a('at'),0,0],[a('size'),drill,drill],
        [a('drill'),drill],[a('layers'),'*.Cu','*.Mask'],[a('uuid'),uid(name+':pad')]]]
    for side in ['F','B']:
        f.append([a('fp_circle'),[a('center'),0,0],[a('end'),radius,0],[a('stroke'),[a('width'),.05],[a('type'),a('solid')]],
                  [a('fill'),a('none')],[a('layer'),side+'.CrtYd'],[a('uuid'),uid(name+':'+side)]])
    return f


def build():
    assert not OUT.exists();OUT.mkdir()
    cap=json.loads((FOLDER/'capture.json').read_text());plan=json.loads((FOLDER/'placement.json').read_text())
    audit=json.loads((FOLDER/'independent-placement-audit.json').read_text())
    assert plan['all_known_parts_placed'] and all(not audit[k] for k in ['source_errors','same_board_receiver_findings','cross_board_receiver_findings','context_findings','floor_findings'])
    originals={};original_trees={}
    for role,source in cap['sources'].items():
        path=REPO/source['path'];assert sha(path)==source['sha256']
        tree=read_sexpr(path.read_text());original_trees[role]=tree
        for f in children(tree,'footprint'):
            r=next(p[2] for p in children(f,'property') if p[1]=='Reference');originals[(role,r)]=f
    template=original_trees['digital_core'];ledger=[];files=[]
    for board in ['signal_main','power_protection']:
        selected=[p for p in cap['parts'] if p['target_board']==board]
        names=sorted({p['role']+'::'+n for p in selected for _,n,_ in p['pad_nets'] if n})
        netid={n:i+1 for i,n in enumerate(names)}
        tree=[a('kicad_pcb')]
        for tag in ['version','generator','generator_version','general','paper','layers','setup']:
            tree.extend(copy.deepcopy(children(template,tag)))
        first(first(tree,'general'),'thickness')[1]=1.6
        for n,i in netid.items():tree.append([a('net'),i,n])
        for part in selected:
            f=copy.deepcopy(originals[(part['role'],part['ref'])]);pose=plan['poses'][part['id']]
            first(f,'at')[1:3]=pose['xy']
            for prop in children(f,'property'):
                if prop[1]=='Reference':prop[2]=part['id']
            f[:]=[node for node in f if not (isinstance(node,list) and node and node[0] in ['path','sheetname','sheetfile'])]
            oldmap={str(n[1]):str(n[2]) for n in children(original_trees[part['role']],'net')}
            def rewrite(node,path='root'):
                if not isinstance(node,list):return
                if node and node[0]=='uuid':node[1]=uid(part['id']+':'+path)
                if node and node[0]=='net':
                    name=str(node[2]) if len(node)>2 else oldmap.get(str(node[1]),str(node[1]))
                    if name:
                        name=part['role']+'::'+name;node[:]=[a('net'),netid[name],name]
                    else:node[:]=[a('net'),0,'']
                for i,sub in enumerate(node):
                    if isinstance(sub,list):rewrite(sub,path+'/'+str(i))
            rewrite(f);tree.append(f)
            ledger.append(dict(new_ref=part['id'],source_role=part['role'],source_ref=part['ref'],board=board,
                source_footprint_sha256=hashlib.sha256(sexpr(originals[(part['role'],part['ref'])]).encode()).hexdigest(),
                source_pad_nets=part['pad_nets'],source_xy=part['source_xy'],new_xy=pose['xy'],value=part['value'],
                source_angle=part['angle'],source_side=part['side'],cross_source_nets_joined=False))
        polygon=cap['signal_polygon'] if board=='signal_main' else cap['power_polygon']
        for i,(p,q) in enumerate(zip(polygon,polygon[1:])):
            tree.append([a('gr_line'),[a('start'),*p],[a('end'),*q],[a('stroke'),[a('width'),.05],[a('type'),a('solid')]],
                         [a('layer'),'Edge.Cuts'],[a('uuid'),uid(board+':edge'+str(i))]])
        if board=='power_protection':
            for i,xy in enumerate(cap['power_mount_centres']):tree.append(mechanical('H_NEW'+str(i+1),xy,2.4,3.6))
            for i,xy in enumerate(cap['touch_post_hole_centres']):tree.append(mechanical('H_TOUCH'+str(i+1),xy,9,4.75))
        tree.append([a('gr_text'),'PLACEMENT STUDY ONLY - UNROUTED - NOT FOR FAB',[a('at'),165,190],
                     [a('layer'),'Dwgs.User'],[a('effects'),[a('font'),[a('size'),2,2],[a('thickness'),.25]]],
                     [a('uuid'),uid(board+':warning')]])
        path=OUT/(board+'.kicad_pcb');path.write_text(sexpr(tree)+'\n');files.append(path)
        project_source=(REPO/cap['sources']['digital_core']['path']).with_suffix('.kicad_pro')
        project=json.loads(project_source.read_text());project.setdefault('meta',{})['filename']=board+'.kicad_pro'
        project_path=OUT/(board+'.kicad_pro');project_path.write_text(json.dumps(project,indent=2)+'\n');files.append(project_path)
    (OUT/'part-and-net-map.json').write_text(json.dumps(ledger,indent=2)+'\n')
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),FOLDER/'capture.json',FOLDER/'placement.json',FOLDER/'independent-placement-audit.json']},
        artifact_sha256={p.name:sha(p) for p in files+[OUT/'part-and-net-map.json']},
        preserved_source_footprints=len(ledger),electrical_parts=audit['electrical_parts'],
        retired_old_mounts=cap['retired_mounts'],new_mount_holes=11,touch_post_clearance_holes=2,
        absent_codec='U201: approved footprint missing; reserved in study, not invented',
        reference_and_net_namespaces_explicit=True,cross_source_nets_joined=False,
        merged_schematic_created=False,routing_complete=False,complete_fit_verified=False,fabrication_released=False)
    (OUT/'export.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['preserved_source_footprints','electrical_parts','new_mount_holes','touch_post_clearance_holes']}))


if __name__=='__main__':build()
