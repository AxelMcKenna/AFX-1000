"""Linux-only native PCB loading/DRC of placement-only TB04 files.

No schematic parity or ERC claim: source circuits have not been integrated.
All existing rule severities are retained. Open nets and warnings are reported.
"""
import hashlib,json,shutil,subprocess,sys
from collections import Counter
from pathlib import Path


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def run():
    assert sys.platform=='linux','Native CAD is Linux-only'
    import pcbnew
    repo=Path(__file__).resolve().parents[2];staging=repo/'hardware/fabrication/staging'
    source=staging/'two-board-placement-cad-01';out=staging/'two-board-placement-native-01';out.mkdir(exist_ok=False)
    result=dict(source_sha256={str(Path(__file__).relative_to(repo)):sha(Path(__file__))},boards={},schematic_parity_checked=False,ERC_checked=False,complete_fit_verified=False,fabrication_released=False)
    for name in ['signal_main','power_protection']:
        for ext in ['.kicad_pcb','.kicad_pro']:
            p=source/(name+ext);result['source_sha256'][str(p.relative_to(repo))]=sha(p);shutil.copyfile(p,out/p.name)
        pcb=out/(name+'.kicad_pcb');pro=out/(name+'.kicad_pro')
        settings=json.loads(pro.read_text());severities=settings['board']['design_settings']['rule_severities']
        ignored=[k for k,v in severities.items() if v=='ignore'];assert not ignored,ignored
        cmd=['kicad-cli','pcb','drc','--all-track-errors','--severity-all','--format','json','-o',str(out/(name+'-drc.json')),str(pcb)]
        p=subprocess.run(cmd,capture_output=True,text=True,timeout=65)
        (out/(name+'-drc.log')).write_text(p.stdout+p.stderr)
        assert p.returncode==0,(name,p.returncode,p.stderr)
        drc=json.loads((out/(name+'-drc.json')).read_text())
        board=pcbnew.LoadBoard(str(pcb));assert board
        board.BuildConnectivity();conn=board.GetConnectivity();conn.RecalculateRatsnest()
        native=dict(footprints=len(list(board.GetFootprints())),tracks=len(list(board.GetTracks())),zones=board.GetAreaCount(),uncapped_open_connections=conn.GetUnconnectedCount(),
            DRC_violation_types=dict(Counter(v['type'] for v in drc.get('violations',[]))),
            DRC_severity_counts=dict(Counter(v['severity'] for v in drc.get('violations',[]))),
            ignored_rule_categories=ignored,command=cmd,returncode=p.returncode)
        result['boards'][name]=native
        print(name,json.dumps(native),flush=True)
    result['artifact_sha256']={p.name:sha(p) for p in out.iterdir() if p.is_file()}
    (out/'review.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':run()
