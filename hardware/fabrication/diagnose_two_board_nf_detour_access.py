"""Add bounded, referenced layer detours to the startup surface plan."""
import itertools
import json
import math
from pathlib import Path
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union
from shapely.prepared import prep
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha
from hardware.fabrication.plan_two_board_startup_controls import anchored_fields
BASE=STAGING/'two-board-power-nf-logic-ground-native-02'
CAP=STAGING/'two-board-power-routing-inputs-nf-logic-ground-02/capture.json'
from hardware.fabrication.route_two_board_power_layer_detours import ViaScreen
import hardware.fabrication.route_nf_surface as routing

PLAN=STAGING/'two-board-nf-logic-route-plan-03/plan.json'
OUT=STAGING/'two-board-nf-detour-access-diagnosis-01'


def run():
    assert not OUT.exists()
    c=json.loads(CAP.read_text());p=json.loads(PLAN.read_text())
    for data in [c,p]:
        for n,h in data['source_sha256'].items():assert sha(Path(n) if Path(n).is_absolute() else REPO/n)==h,n
    audit_path=BASE/'nf-logic-ground-review.json'
    audit=json.loads(audit_path.read_text())
    assert audit['closed_connections']==14 and audit['all_other_native_groups_preserved'] and len(audit['repaired_pad_centers'])==26
    for name,h in audit['source_sha256'].items():assert sha(REPO/name)==h,name
    fields,excluded=anchored_fields(c)
    objects={o['uuid']:o for o in c['objects']}
    main=next(o['group'] for o in c['objects'] if o.get('ref')=='P_C103' and o.get('pin')=='2')
    reference={'F.Cu':'In1.Cu','In2.Cu':'In1.Cu'}
    holes={}
    for o in c['objects']:
        if o['kind']=='PCB_VIA':holes.setdefault(o['net'],[]).append(Point(o['position_mm']).buffer(o['width_mm']/2+.215))
    holes={n:unary_union(v) for n,v in holes.items()}
    protected={l:[] for l in c['copper_layers']};retained=[]
    for o in c['objects']:
        if o['kind']!='PCB_TRACK' or o['net']=='PWR_AGND':continue
        layer,=o['layers'];i=c['copper_layers'].index(layer)
        adjacent={c['copper_layers'][j] for j in [i-1,i+1] if 0<=j<len(c['copper_layers'])}
        band=LineString([o['position_mm'],o['end_mm']]).buffer(o['width_mm']/2).difference(holes.get(o['net'],Polygon()))
        if band.is_empty:continue
        for (l,gid),f in fields.items():
            if l in adjacent and band.difference(f.buffer(.0015)).area<1e-6:
                protected[l].append(band);retained.append(dict(track_uuid=o['uuid'],reference_layer=l,ground_group=gid))
    # Inflate once, then use prepared fields for the many exact route screens.
    protected_lines={l:prep(unary_union(v).buffer(.435)) for l,v in protected.items()}
    protected_vias=prep(unary_union([x for v in protected.values() for x in v]).buffer(.64))
    existing_fields={l:fields[r,main].buffer(.0015) for l,r in reference.items()}
    cache={};newreferences=[]
    def routefield(net,layer):
        key=(net,layer)
        if key not in cache:cache[key]=prep(existing_fields[layer].union(holes.get(net,Polygon())).buffer(-.100001))
        return cache[key]
    supply={l:unary_union([routing.shape(z['polygons']) for z in c['zones'] if z['layer']==l and z['net']!='PWR_AGND']) for l in c['copper_layers']}
    all_supply=prep(unary_union(list(supply.values())).buffer(.55))
    supply_lines={l:prep(supply[l].buffer(.315)) for l in reference}
    quietpaths=[STAGING/'two-board-power-digital-startup-native-02/digital-startup-routing.json',STAGING/'two-board-power-analog-cells-native-03/analog-cell-routing.json']
    quietids={u for f in quietpaths for q in json.loads(f.read_text())['quiet_ground_islands'] for u in q['zone_uuids']}
    quiet=prep(unary_union([routing.shape(z['authored_outline']).buffer(.55) for z in c['zones'] if z['uuid'] in quietids]))
    routing.SIGNAL_LAYERS=tuple(reference);routing.WIDTH=.2
    class ReferencedViaScreen(ViaScreen):
        def legal(self,net,layer,points):
            line=LineString(points)
            if supply_lines[layer].intersects(line) or quiet.intersects(line):return False
            if not routefield(net,layer).covers(line) or protected_lines[layer].intersects(line):return False
            if any(n!=net and l==layer and line.distance(band)<=.435 for n,l,band in newreferences):return False
            return super().legal(net,layer,points)
        def via_legal(self,net,xy):
            point=Point(xy)
            if all_supply.intersects(point) or quiet.intersects(point):return False
            if protected_vias.intersects(point):return False
            if any(n!=net and point.distance(band)<=.64 for n,l,band in newreferences):return False
            return super().via_legal(net,xy)
        def escapes(self,net,layer,point):
            # Quarter-millimetre via sites improve access around 0.65 mm pin
            # rows without reducing any copper, hole or reference clearance.
            sites=sorted((math.dist(point,(ix/4,iy/4)),(ix/4,iy/4))
                for ix in range(math.floor((point[0]-3.5)*4),math.ceil((point[0]+3.5)*4)+1)
                for iy in range(math.floor((point[1]-3.5)*4),math.ceil((point[1]+3.5)*4)+1))
            candidates=[];legal=[]
            for distance,xy in sites:
                if distance>3.5 or not self.via_legal(net,xy):continue
                legal.append((distance,xy));path=self.simple(net,layer,point,xy,5.5)
                if path:candidates.append((path[0],xy,path[1]))
                if len(candidates)>=16:break
            if not candidates:
                for distance,xy in legal[:8]:
                    path=self.grid_path(net,layer,point,xy,budget=4000)
                    if path and LineString(path).length<=5.5:candidates.append((LineString(path).length,xy,path))
            return sorted(candidates)[:16]
    assert not any(z['keepout'] for z in c['zones'])
    screen=ReferencedViaScreen(dict(c,zones=[]));routes=[];vias=[]
    for r in routes:
        line=LineString(r['path_mm']);screen.added.append((r['net'],r['layer'],line))
        newreferences.append((r['net'],r['reference_layer'],line.buffer(.1)))
    wanted={'ABS_AUX_READY','N19_F_WD_ARM','PWR_NF_MASKED_INVERTED_FAULT','E28_COMBINED_FAULT_REQUEST_HCS'}
    rows=[]
    for obj in c['objects']:
        if obj['kind']!='PAD' or obj['net'].rsplit('/',1)[-1] not in wanted:continue
        if 'F.Cu' not in obj['layers']:continue
        net=obj['net'];xy=obj['position_mm'];short=screen.escapes(net,'F.Cu',xy)
        expanded=None;tested=0
        if not short:
            sites=sorted((math.dist(xy,(ix/4,iy/4)),(ix/4,iy/4))
                for ix in range(math.floor((xy[0]-6)*4),math.ceil((xy[0]+6)*4)+1)
                for iy in range(math.floor((xy[1]-6)*4),math.ceil((xy[1]+6)*4)+1))
            for distance,site in sites:
                if not 3.5<distance<=6 or not screen.via_legal(net,site):continue
                tested+=1
                path=screen.simple(net,'F.Cu',xy,site,9)
                if path:expanded=dict(via_mm=site,path_mm=path[1],length_mm=path[0]);break
        rows.append(dict(ref=obj['ref'],pin=obj['pin'],net=net,xy_mm=xy,
                         covered=routefield(net,'F.Cu').covers(Point(xy)),
                         short_escape_count=len(short),nearest_short=short[0] if short else None,
                         expanded_escape=expanded,expanded_clear_sites_tested=tested))
        print(obj['ref'],obj['pin'],'short',len(short),'expanded',expanded is not None,flush=True)
    sources=[Path(__file__),CAP,PLAN,audit_path,*quietpaths,REPO/'hardware/fabrication/plan_two_board_startup_controls.py',
             REPO/'hardware/fabrication/route_two_board_power_layer_detours.py',REPO/'hardware/fabrication/route_two_board_power_local_v2.py',REPO/'hardware/fabrication/route_nf_surface.py']
    result=dict(source_sha256={str(f.relative_to(REPO)):sha(f) for f in sources},pads=rows,
                scope='Screened local escape diagnosis on TBP58, not an authored route or a complete connection proof.',fabrication_released=False)
    OUT.mkdir();(OUT/'diagnosis.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':run()
