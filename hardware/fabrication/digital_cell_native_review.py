"""Verify the 39 declared local connections and export both native copper faces."""
import json,subprocess,sys
from pathlib import Path
from hardware.fabrication.audit_candidate import native_evidence_errors,sha

ROOT=Path(__file__).resolve().parent

def run():
    assert sys.platform=='linux'
    import pcbnew
    folder=ROOT/'staging/digital-local-cell-native-01';pcb=folder/'digital_core.kicad_pcb';project=pcb.with_suffix('.kicad_pro')
    rp=folder/'review.json';review=json.loads(rp.read_text());assert not native_evidence_errors(project,review)
    for name,h in review['captured_hierarchy_sha256'].items():assert sha(folder/name)==h
    board=pcbnew.LoadBoard(str(pcb));board.BuildConnectivity();conn=board.GetConnectivity();conn.RecalculateRatsnest()
    pads={(f.GetReference(),p.GetNumber()):p for f in board.GetFootprints() for p in f.Pads() if p.GetNumber()}
    proof=ROOT/'staging/digital-local-cell-routes-01/construction.json';data=json.loads(proof.read_text());results=[]
    for r in data['routes']:
        p=pads[(r['ref'],'1')];q=pads[(r['owner'],r['owner_pin'])]
        assert p.GetNetname()==q.GetNetname()==r['net']
        ids={v.m_Uuid.AsString() for v in conn.GetConnectedItems(p)}
        assert q.m_Uuid.AsString() in ids,(r['ref'],r['owner'])
        results.append(dict(ref=r['ref'],owner=r['owner'],owner_pin=r['owner_pin'],native_connected=True,
                            actual_route_length_mm=r['length_mm'],native_pad_distance_mm=(p.GetPosition()-q.GetPosition()).EuclideanNorm()/1e6))
    out=folder/'plots';out.mkdir(exist_ok=False)
    for name,layers in [('front','F.Cu,F.Fab,Edge.Cuts'),('back','B.Cu,B.Fab,Edge.Cuts')]:
        subprocess.run(['kicad-cli','pcb','export','pdf','--layers',layers,'--mode-single','--output',str(out/(name+'.pdf')),str(pcb)],check=True,timeout=30)
    assert sha(pcb)==review['checked_PCB_sha256']
    inputs=[pcb,project,rp,proof,Path(__file__)]
    (folder/'local-connectivity-review.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in inputs},connections=results,
        checked_local_connections=len(results),uncapped_open_connections=conn.GetUnconnectedCount(False),
        plots_sha256={p.name:sha(p) for p in out.glob('*.pdf')},ground_returns_and_board_power_unfinished=True,
        signal_integrity_thermal_and_manufacturing_qualified=False,fabrication_released=False),indent=2)+'\n')
    print('Native confirmed',len(results),'local pad pairs; opens',conn.GetUnconnectedCount(False))

if __name__=='__main__':run()
