"""Native routing capture with explicit raw/unfractured zone fidelity evidence."""
import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha
from hardware.fabrication.capture_partial_board import polygons


def run():
    assert sys.platform=='linux'
    import pcbnew
    source=Path(__file__).resolve().parent/'native-r7'
    output=Path(__file__).resolve().parent/'capture-r7';assert output.is_dir() and not list(output.iterdir())
    paths=[Path(__file__),REPO/'hardware/fabrication/capture_partial_board.py',
        source/'signal_main.kicad_pcb',source/'drc.json',source/'review.json']
    hashes={str(p):sha(p) for p in paths}
    drc=json.loads((source/'drc.json').read_text());review=json.loads((source/'review.json').read_text())
    assert not drc['violations'] and not drc['ignored_checks'];assert len(drc['schematic_parity'])==1
    board=pcbnew.LoadBoard(str(source/'signal_main.kicad_pcb'))
    board.BuildConnectivity();conn=board.GetConnectivity();conn.RecalculateRatsnest()
    opens=conn.GetUnconnectedCount(False);assert opens==230
    assert len(list(board.GetFootprints()))==477
    items=[p for f in board.GetFootprints() for p in f.Pads()]+list(board.GetTracks())
    byid={p.m_Uuid.AsString():p for p in items};assert len(byid)==len(items)
    groups={};membership={};by_net=defaultdict(list);padids=set()
    for uid,item in byid.items():
        if item.GetClass()=='PAD' and item.GetNumber() and item.GetNetname():padids.add(uid)
    for uid in sorted(padids):
        if uid in membership:continue
        item=byid[uid];net=item.GetNetname()
        # A legal net tie can physically join different named nets. Routing
        # clusters remain net-specific; do not infer a new logical net merge.
        connected={uid}|{p.m_Uuid.AsString() for p in conn.GetConnectedItems(item)}
        members={i for i in connected if i in byid and byid[i].GetNetname()==net}
        key=min(members);groups[key]=sorted(members);by_net[net].append(key)
        membership.update({m:key for m in members})
    group_opens=sum(len(keys)-1 for keys in by_net.values())
    assert group_opens==opens,(group_opens,opens)
    open_nets={net for net,keys in by_net.items() if len(keys)>1}
    open_groups={k:v for k,v in groups.items() if byid[k].GetNetname() in open_nets}
    layers=('F.Cu',*[f'In{i}.Cu' for i in range(1,board.GetCopperLayerCount()-1)],'B.Cu')
    rows=[]
    for uid,item in byid.items():
        pos=item.GetPosition();kind=item.GetClass()
        row=dict(uuid=uid,net=item.GetNetname(),kind=kind,position_mm=[pos.x/1e6,pos.y/1e6],layers={},group=membership.get(uid))
        for name in layers:
            layer=board.GetLayerID(name)
            if not item.IsOnLayer(layer):continue
            poly=pcbnew.SHAPE_POLY_SET();item.TransformShapeToPolygon(poly,layer,0,pcbnew.FromMM(.001),pcbnew.ERROR_OUTSIDE);poly.Simplify()
            row['layers'][name]=polygons(poly)
        if kind=='PAD':
            row.update(ref=item.GetParentFootprint().GetReference(),pin=item.GetNumber(),
                drill_mm=[item.GetDrillSize().x/1e6,item.GetDrillSize().y/1e6],
                orientation_degrees=item.GetOrientation().AsDegrees(),npth=int(item.GetAttribute())==int(pcbnew.PAD_ATTRIB_NPTH))
        elif kind=='PCB_TRACK':
            end=item.GetEnd();row.update(end_mm=[end.x/1e6,end.y/1e6],width_mm=item.GetWidth()/1e6)
        elif kind=='PCB_VIA':
            row.update(width_mm=item.GetWidth(pcbnew.F_Cu)/1e6,drill_mm=item.GetDrillValue()/1e6,
                via_type=int(item.GetViaType()),span=[board.GetLayerName(item.TopLayer()),board.GetLayerName(item.BottomLayer())])
        else:raise AssertionError(kind)
        rows.append(row)
    native_zones=list(board.Zones());assert native_zones
    zones=[];unfracture=[]
    for z in native_zones:
        for name in layers:
            layer=board.GetLayerID(name)
            if not z.IsOnLayer(layer):continue
            keep=z.GetIsRuleArea();original=z.Outline() if keep else z.GetFilledPolysList(layer)
            poly=pcbnew.SHAPE_POLY_SET(original);area_before=poly.Area()/1e12
            raw=polygons(poly)
            if not keep:poly.Unfracture()
            area_after=poly.Area()/1e12
            perimeter=sum(sum(math.dist(a,b) for a,b in zip(ring,ring[1:]+ring[:1]))
                for p in raw for ring in [p['outer'],*p['holes']])
            # Native integer-grid Unfracture can shift slit endpoints by a
            # fraction of 1nm. Export both representations for an independent
            # geometric fidelity check; area alone cannot establish fidelity.
            area_bound=max(1e-6,perimeter*2e-6)
            assert abs(area_before-area_after)<=area_bound
            unfracture.append(dict(uuid=z.m_Uuid.AsString(),layer=name,
                raw_filled_polygons=raw,raw_boundary_perimeter_mm=perimeter,
                maximum_boundary_displacement_mm=2e-6,maximum_symmetric_difference_area_mm2=area_bound,
                independent_geometric_verification_pending=True))
            zones.append(dict(uuid=z.m_Uuid.AsString(),net=z.GetNetname(),layer=name,keepout=keep,
                prohibit_tracks=bool(z.GetDoNotAllowTracks()) if keep else False,
                prohibit_vias=bool(z.GetDoNotAllowVias()) if keep else False,
                authored_outline=polygons(z.Outline()),polygons=polygons(poly),
                native_area_before_unfracture_mm2=area_before,native_area_after_unfracture_mm2=area_after))
    outline=pcbnew.SHAPE_POLY_SET();assert board.GetBoardPolygonOutlines(outline,False)
    result=dict(source_sha256=hashes,native_version=pcbnew.GetBuildVersion(),native_uncapped_opens=opens,
        DRC_unconnected_record_count=len(drc['unconnected_items']),
        complete_native_cluster_count=len(groups),open_net_count=len(open_nets),
        independent_sum_of_pad_cluster_gaps=group_opens,objects=rows,zones=zones,groups=open_groups,
        zone_unfracture_fidelity=unfracture,all_groups=groups,open_nets=sorted(open_nets),outline=polygons(outline),copper_layers=layers,
        obstacle_polygons_error='outside0.001mm',retained_native_findings=drc['violations'],
        footprints_captured=477,geometry_delta_requires_separate_audit=True,physical_qualified=False,fabrication_released=False)
    assert all(sha(Path(p))==h for p,h in hashes.items())
    (output/'capture.json').write_text(json.dumps(result,separators=(',',':'))+'\n')
    print(json.dumps(dict(objects=len(rows),zones=len(zones),open_nets=len(open_nets),open_clusters=len(open_groups),
        DRC_unconnected_records=len(drc['unconnected_items']),native_uncapped_opens=opens,cluster_gap_crosscheck=group_opens)))


if __name__=='__main__':run()
