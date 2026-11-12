"""Screen proposed pairwise centerlines; does not emit copper or qualify routing."""
from pathlib import Path
import json,math,xml.etree.ElementTree as ET
from shapely.geometry import LineString,box
from shapely.affinity import rotate,translate,scale
from shapely.ops import unary_union
from .individual import HERE,geometry,polygons
from hardware.electronics.common.sexpr import read_sexpr,children,first

def run(root):
    proposal=json.loads((HERE/'individual-placement.json').read_text());cap,board,area,obstacles,target=geometry(root)
    xml=ET.parse(HERE.parent/'held_rail/native-03/candidate-netlist.xml')
    nets={(n.attrib['ref'],n.attrib['pin']):net.attrib['name'] for net in xml.findall('./nets/net') for n in net.findall('node')}
    poses={p['ref']:p for g in proposal['groups'].values() if g['chosen'] for p in g['chosen']['parts']};points={};pad_shapes={}
    for ref,p in poses.items():
        lib,name=p['footprint'].split(':');fp=(HERE/'AUX_READY.pretty'/f'{name}.kicad_mod') if lib=='AUX_READY' else HERE.parent/'held_rail/authored/libraries'/f'{lib}.pretty'/f'{name}.kicad_mod'
        for pad in children(read_sexpr(fp.read_text()),'pad'):
            at=first(pad,'at');x,y=map(float,at[1:3]);w,h=map(float,first(pad,'size')[1:3]);angle=float(at[3]) if len(at)>3 else 0
            g=translate(rotate(box(-w/2,-h/2,w/2,h/2),-angle,origin=(0,0)),x,y)
            g=scale(g,xfact=-1 if p['layer']=='B.Cu' else 1,yfact=1,origin=(0,0));g=translate(rotate(g,-p['rotation_deg'],origin=(0,0)),*p['at_mm']);pad_shapes[ref,pad[1]]=g
        for pin,xy in proposal['footprints'][ref]['pads'].items():
            x,y=xy;x=-x if p['layer']=='B.Cu' else x;a=math.radians(p['rotation_deg']);points[ref,pin]=[p['at_mm'][0]+x*math.cos(a)+y*math.sin(a),p['at_mm'][1]-x*math.sin(a)+y*math.cos(a)]
    for o in cap['objects']:
        if (o.get('ref'),o.get('pin')) in {('E_U31','6'),('E_U31','8'),('E_U29','8'),('E_U1','1'),('E_U2','1'),('E_U3','1'),('E_U4','1')}:points[o['ref'],o['pin']]=o['position_mm']
    pairs=[('P_C900','1','P_U900','2'),('P_C900','2','P_U900','1'),('P_U900','9','P_L900','1'),('P_L900','2','P_C901','1'),('P_C901','2','P_U900','1'),('P_U900','5','P_R900','2'),('P_U900','5','P_R901','1'),('P_R900','1','P_C901','1'),('P_C901','1','P_R902','1'),('P_C901','1','P_U902','1'),('P_R902','2','P_C902','1'),('P_C902','1','P_C905','1'),('P_C902','1','P_U901','1'),('P_U901','1','P_C903','1'),('P_U901','5','P_C904','1'),('P_U901','5','P_R903','1'),('P_U902','2','P_C906','1'),('E_U900','2','E_C900','1'),('E_U900','4','E_R900','2'),('E_U900','4','E_U31','6')]
    pairs += [('P_U902','4','E_U900','4'),('P_U901','5','E_U900','2')]+[('P_U901','5',r,p) for r,p in [('E_U1','1'),('E_U2','1'),('E_U3','1'),('E_U4','1'),('E_U29','8'),('E_U31','8')]]
    rows=[]
    for ar,ap,br,bp in pairs:
        aa=(ar,ap);bb=(br,bp);assert nets[aa]==nets[bb],(aa,bb,nets.get(aa),nets.get(bb))
        net=nets[aa];layer=poses[ar]['layer'];a=points[aa];b=points[bb];line=LineString([a,b]);width=.3;clearance=.2
        hit=[]
        for o in cap['objects']:
            if o['net']==net or (o.get('ref'),o.get('pin')) in [aa,bb]:continue
            if any(line.buffer(width/2+clearance).intersects(g) for g in polygons(o['layers'].get(layer,[]))):hit.append(o['uuid'])
        new_hits=[r+'.'+p for (r,p),g in pad_shapes.items() if nets.get((r,p))!=net and poses[r]['layer']==layer and line.buffer(width/2+clearance).intersects(g)]
        rows.append({'foreign_proposed_pad_hits':new_hits,'from':f'{ar}.{ap}','to':f'{br}.{bp}','net':net,'layer':layer,'points_mm':[a,b],'straight_length_mm':line.length,'width_mm':width,'foreign_existing_copper_hits':hit,'straight_path_clear_of_captured_surface_objects':not hit,'straight_path_clear_of_proposed_foreign_pads':not new_hits})
    crossings=[]
    for i,a in enumerate(rows):
        for j,b in enumerate(rows[i+1:],i+1):
            if a['net']!=b['net'] and a['layer']==b['layer'] and LineString(a['points_mm']).distance(LineString(b['points_mm']))<.5:crossings.append([i,j])
    vin=[points[k] for k in [('P_C900','1'),('P_U900','2'),('P_U900','1'),('P_C900','2')]]
    from shapely.geometry import Polygon
    out={'foreign_net_centerline_clearance_conflict_path_indices':crossings,'status':'necessary_path_screen_not_route_acceptance','paths':rows,'new_pad_points_mm':{r+'.'+p:xy for (r,p),xy in points.items()},'input_loop_vertex_bounding_area_mm2':Polygon(vin).convex_hull.area,'assumed_0p3mm_35um_copper_resistance_ohm_per_mm_at125C':1.724e-5*(1+.00393*105)/(.3*.035),'unchecked':['detailed pad escape and minimum finished clearance','mutual new trace crossings','all reference plane paths','layer transfer/vias','filled-zone interaction','return distribution resistance','actual foil thickness and temperature','thermal/EMI suitability','housing clearance'],'pcb_modified':False,'qualified':False}
    (HERE/'path-screen.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({'path_count':len(rows),'existing_copper_clear':sum(not r['foreign_existing_copper_hits'] for r in rows),'input_loop_vertex_bounding_area_mm2':out['input_loop_vertex_bounding_area_mm2']},indent=2))
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);run(p.parse_args().root)
