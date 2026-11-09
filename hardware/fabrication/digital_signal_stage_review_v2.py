"""Native net-by-net witnesses and plots for a digital routing checkpoint."""
import argparse,json,subprocess,sys
from collections import defaultdict
from pathlib import Path
from hardware.fabrication.audit_candidate import sha,native_evidence_errors
ROOT=Path(__file__).resolve().parent

def run():
    assert sys.platform=='linux','Mac CAD remains disabled'
    import pcbnew
    parser=argparse.ArgumentParser();parser.add_argument('--source',required=True);args=parser.parse_args()
    assert args.source and all(c.isalnum() or c in '-_' for c in args.source)
    out=ROOT/'staging'/args.source;pcb=out/'digital_core.kicad_pcb';rp=out/'review.json';review=json.loads(rp.read_text())
    assert not native_evidence_errors(pcb.with_suffix('.kicad_pro'),review)
    assert review['status']['counts']['schematic_parity']==review['status']['counts']['erc']==0
    findings=json.loads((out/'drc.json').read_text())['violations']
    assert all(v['type']=='via_dangling' and v['severity']=='warning' for v in findings)
    board=pcbnew.LoadBoard(str(pcb));board.BuildConnectivity();conn=board.GetConnectivity();conn.RecalculateRatsnest()
    pads={(f.GetReference(),p.GetNumber()):p for f in board.GetFootprints() for p in f.Pads() if p.GetNumber()}
    nets=defaultdict(list)
    for key,p in pads.items():
        if p.GetNetname() and not p.GetNetname().startswith('unconnected-'):nets[p.GetNetname()].append((key,p))
    rows=[]
    for net,items in sorted(nets.items()):
        groups=[];remaining={p.m_Uuid.AsString():key for key,p in items};objects={p.m_Uuid.AsString():p for key,p in items}
        while remaining:
            uid=next(iter(remaining));connected={v.m_Uuid.AsString() for v in conn.GetConnectedItems(objects[uid])}|{uid}
            members=sorted(remaining.keys()&connected);groups.append([list(remaining[i]) for i in members])
            for i in members:remaining.pop(i)
        tracks=[t for t in board.GetTracks() if t.GetNetname()==net and t.GetClass()=='PCB_TRACK']
        layer_lengths={board.GetLayerName(layer):sum(t.GetLength()/1e6 for t in tracks if t.GetLayer()==layer) for layer in {t.GetLayer() for t in tracks}}
        rows.append(dict(net=net,pad_count=len(items),pad_groups=groups,all_pads_connected=len(groups)==1,
                         planar_copper_length_mm=sum(layer_lengths.values()),layer_lengths_mm=layer_lengths,
                         via_count=sum(t.GetNetname()==net and t.GetClass()=='PCB_VIA' for t in board.GetTracks())))
    power={'AGND','5V_DIG','V3V3_IO','/PROCESSOR/SEED_VIN','/PROCESSOR/V3V3_ANALOG'}
    assert all(r['all_pads_connected'] for r in rows if r['net'] in power)
    assert sum(r['pad_count'] for r in rows if r['net'] in power)==201
    local=ROOT/'staging/digital-local-cell-routes-01/construction.json'
    for r in json.loads(local.read_text())['routes']:
        p=pads[(r['ref'],'1')];q=pads[(r['owner'],r['owner_pin'])]
        assert q.m_Uuid.AsString() in {v.m_Uuid.AsString() for v in conn.GetConnectedItems(p)}
    thermal=ROOT/'staging/digital-distribution-native-02/distribution-connectivity-review.json'
    vias={v.m_Uuid.AsString():v for v in board.GetTracks() if v.GetClass()=='PCB_VIA'}
    for r in json.loads(thermal.read_text())['thermal_branches']:
        p=pads[(r['ref'],'33')];v=vias[r['via_uuid']]
        assert v.m_Uuid.AsString() in {v.m_Uuid.AsString() for v in conn.GetConnectedItems(p)}
    plots=out/'plots';plots.mkdir(exist_ok=False)
    plot_layers=[('front','F.Cu,F.Fab,Edge.Cuts'),('back','B.Cu,B.Fab,Edge.Cuts'),('ground','In1.Cu,Edge.Cuts'),('power','In2.Cu,Edge.Cuts')]
    if board.GetCopperLayerCount()>=6:plot_layers += [('inner-signals','In3.Cu,Edge.Cuts'),('back-ground','In4.Cu,Edge.Cuts')]
    if board.GetCopperLayerCount()==8:plot_layers += [('inner-signals-2','In5.Cu,Edge.Cuts'),('back-ground-2','In6.Cu,Edge.Cuts')]
    for name,layers in plot_layers:
        subprocess.run(['kicad-cli','pcb','export','pdf','--layers',layers,'--mode-single','--output',str(plots/(name+'.pdf')),str(pcb)],check=True,timeout=30)
    assert sha(pcb)==review['checked_PCB_sha256']
    from hardware.fabrication.capture_board import polygons
    planes=[dict(net=z.GetNetname(),layer=board.GetLayerName(layer),polygons=polygons(z.GetFilledPolysList(layer))) for z in board.Zones() if not z.GetIsRuleArea() for layer in z.GetLayerSet().Seq()]
    inputs=[pcb,pcb.with_suffix('.kicad_pro'),rp,local,thermal,Path(__file__),ROOT/'capture_board.py']
    (out/'stage-connectivity-review.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in inputs},nets=rows,planes=planes,retained_native_findings=findings,
        uncapped_open_connections=conn.GetUnconnectedCount(False),closed_nets=sum(r['all_pads_connected'] for r in rows),open_nets=sum(not r['all_pads_connected'] for r in rows),
        preserved_power_ground_pads=201,preserved_local_connections=39,preserved_thermal_connections=33,copper_layer_count=board.GetCopperLayerCount(),
        plots_sha256={p.name:sha(p) for p in plots.glob('*.pdf')},signal_integrity_power_thermal_and_fabrication_qualified=False),indent=2)+'\n')
    print('Native signal review:',sum(not r['all_pads_connected'] for r in rows),'open nets;',conn.GetUnconnectedCount(False),'opens; power/local/thermal witnesses preserved')

if __name__=='__main__':run()
