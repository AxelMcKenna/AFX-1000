"""Native pad-to-source power witnesses, thermal branches and copper plots."""
import json,math,subprocess,sys
from pathlib import Path
from hardware.fabrication.audit_candidate import sha,native_evidence_errors
from hardware.fabrication.capture_board import polygons
ROOT=Path(__file__).resolve().parent

def run():
    assert sys.platform=='linux','Mac CAD remains disabled'
    import pcbnew
    out=ROOT/'staging/digital-distribution-native-01';pcb=out/'digital_core.kicad_pcb'
    rp=out/'review.json';review=json.loads(rp.read_text());assert not native_evidence_errors(pcb.with_suffix('.kicad_pro'),review)
    board=pcbnew.LoadBoard(str(pcb));board.BuildConnectivity();conn=board.GetConnectivity();conn.RecalculateRatsnest()
    pads={(f.GetReference(),p.GetNumber()):p for f in board.GetFootprints() for p in f.Pads() if p.GetNumber()}
    roots={'AGND':('J1001','2'),'5V_DIG':('J1001','1'),'/PROCESSOR/SEED_VIN':('R1001','2'),
           'V3V3_IO':('U1001','38'),'/PROCESSOR/V3V3_ANALOG':('U1001','21')}
    rows=[]
    for net,key in roots.items():
        root=pads[key];assert root.GetNetname()==net
        connected={v.m_Uuid.AsString() for v in conn.GetConnectedItems(root)}|{root.m_Uuid.AsString()}
        members=[(k,p) for k,p in pads.items() if p.GetNetname()==net]
        assert all(p.m_Uuid.AsString() in connected for k,p in members),(net,[k for k,p in members if p.m_Uuid.AsString() not in connected])
        rows.append(dict(net=net,source=list(key),pad_count=len(members),pads=[list(k) for k,p in members],all_native_connected=True))
    local=ROOT/'staging/digital-local-cell-routes-01/construction.json'
    for r in json.loads(local.read_text())['routes']:
        p=pads[(r['ref'],'1')];q=pads[(r['owner'],r['owner_pin'])]
        assert q.m_Uuid.AsString() in {v.m_Uuid.AsString() for v in conn.GetConnectedItems(p)}
    ep=ROOT/'staging/digital-plane-escapes-01/construction.json';thermal=[]
    vias={v.m_Uuid.AsString():v for v in board.GetTracks() if v.GetClass()=='PCB_VIA'}
    for r in json.loads(ep.read_text())['routes']:
        if not r['owner'].get('thermal_branch'):continue
        ref=r['owner']['ref'];p=pads[(ref,'33')];v=vias[r['via_uuid']]
        assert v.m_Uuid.AsString() in {i.m_Uuid.AsString() for i in conn.GetConnectedItems(p)}
        thermal.append(dict(ref=ref,via_uuid=r['via_uuid'],via_mm=r['via_mm'],width_mm=r['width_mm'],exposed_pad_and_input_ground_native_connected=True))
    plane_rows=[]
    for z in board.Zones():
        assert not z.GetIsRuleArea();layer=z.GetLayer();poly=pcbnew.SHAPE_POLY_SET(z.GetFilledPolysList(layer));before=poly.Area()/1e12
        original=polygons(poly)
        # KiCad stores integer-nanometre vertices. Unfracture can move join
        # intersections by one grid step. Bound area change by perimeter times
        # two grid steps; retain both values rather than assert bit-exact area.
        perimeter=sum(math.dist(p,q) for row in original for ring in [row['outer'],*row['holes']] for p,q in zip(ring,ring[1:]+ring[:1]))
        tolerance=perimeter*2e-6
        poly.Unfracture();after=poly.Area()/1e12
        assert abs(before-after)<=tolerance,(z.GetNetname(),before,after,tolerance)
        plane_rows.append(dict(net=z.GetNetname(),layer=board.GetLayerName(layer),area_mm2=after,native_fractured_area_mm2=before,
            unfracture_area_delta_mm2=after-before,integer_grid_area_tolerance_mm2=tolerance,polygons=polygons(poly)))
    plots=out/'plots';plots.mkdir(exist_ok=False)
    for name,layers in [('front','F.Cu,F.Fab,Edge.Cuts'),('back','B.Cu,B.Fab,Edge.Cuts'),('ground','In1.Cu,Edge.Cuts'),('power','In2.Cu,Edge.Cuts')]:
        subprocess.run(['kicad-cli','pcb','export','pdf','--layers',layers,'--mode-single','--output',str(plots/(name+'.pdf')),str(pcb)],check=True,timeout=30)
    assert sha(pcb)==review['checked_PCB_sha256']
    inputs=[pcb,pcb.with_suffix('.kicad_pro'),rp,local,ep,Path(__file__),ROOT/'capture_board.py']
    result=dict(source_sha256={str(p):sha(p) for p in inputs},power_nets=rows,thermal_branches=thermal,planes=plane_rows,
        preserved_local_pad_pairs=39,uncapped_open_connections=conn.GetUnconnectedCount(False),
        plots_sha256={p.name:sha(p) for p in plots.glob('*.pdf')},all_five_power_and_ground_nets_native_connected=True,
        current_capacity_voltage_noise_signal_return_and_thermal_performance_qualified=False,fabrication_released=False)
    (out/'distribution-connectivity-review.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Native power witnesses',[(r['net'],r['pad_count']) for r in rows],'; thermal branches',len(thermal))

if __name__=='__main__':run()
