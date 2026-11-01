"""Fresh native NF03C schematic/export/ERC/parity; no PCB or physical acceptance."""
import json
import os
from pathlib import Path
import subprocess
from hardware.electronics.common.flat_schematic import generate
from hardware.electronics.common.netlists import netlist
from hardware.qualification.boards.startup_negative_protection.capture import sha
from .circuit import ROOT, components


def main():
    assert not (ROOT / "handoff.json").exists(), "Immutable NF03C; create a successor"
    parts=components()
    # Native drawing references must describe actual proposed power connectivity.
    generate(ROOT,'NF03C','negative_startup',parts,
             [(20,45,'NF03C PRIVATE COMPLETE TWO-RAIL SCHEMATIC PROPOSAL. NOT AN E28 PCB OR BUILD RELEASE.'),
              (20,55,'Series pass before E28 J1.3/J1.5; existing protected bulk/B2B unchanged. Source Kelvin inputs must move separately.'),
              (20,65,'RAMP filter drawing/loaded gate/partial-power/complete effective C/SOA/current/thermal receiving holds remain.')],
             (1100,3450),[(name,round(x/2.54)*2.54,20.32) for name,x in [('AGND',20),('GUARDED_12V_FORCE',90),('DIG5_FORCE',170),('AUX2V6',250),('N19_P03_SRC',330),('N12_P03_SRC',410),('N19_VIN',490),('N12_VIN',570)]])
    out=ROOT/'generated'
    cli='/private/tmp/rmx-kicad/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
    env=dict(os.environ,KICAD_CONFIG_HOME='/private/tmp/rmx-kicad-config')
    commands=[]
    for args in [[cli,'--version'],[cli,'sch','export','netlist','--format','kicadxml','--output',str(out/'netlist.xml'),str(ROOT/'negative_startup.kicad_sch')],[cli,'sch','erc','--format','json','--output',str(out/'erc.json'),str(ROOT/'negative_startup.kicad_sch')]]:
        run=subprocess.run(args,env=env,text=True,capture_output=True,timeout=120)
        commands.append(dict(command=args,returncode=run.returncode,stdout=run.stdout,stderr=run.stderr))
        assert run.returncode==0,(args,run.stdout,run.stderr)
    (out/'native-commands.json').write_text(json.dumps(commands,indent=2)+'\n')
    actual,pins=netlist(out/'netlist.xml')
    nc=[]
    for c in parts:
        for p in c['pins']:
            if p['net'] is None:
                v=pins[c['ref']].pop(p['number']);assert v.startswith('unconnected-('),(c,p,v)
                nc.append(dict(ref=c['ref'],pin=p['number'],exported=v))
    expected={c['ref']:{p['number']:p['net'] for p in c['pins'] if p['net'] is not None} for c in parts}
    differences=[dict(ref=r,expected=p,actual=pins.get(r)) for r,p in expected.items() if p!=pins.get(r)]
    assert set(actual)==set(expected)
    assert not differences,differences
    erc=json.loads((out/'erc.json').read_text());issues=[v for s in erc['sheets'] for v in s['violations']]
    counts={k:sum(v['severity']==k for v in issues) for k in ['error','warning']}
    report=dict(revision='NF03C-private-native-schematic',parts=len(parts),erc=counts,pin_parity_differences=differences,
                source_sha256={str(f.relative_to(ROOT)):sha(f) for f in [ROOT/'circuit.py',ROOT/'generate.py',ROOT/'parameters.json',ROOT/'integration.json',ROOT/'negative_startup.kicad_sch',ROOT/'components.json']},
                artifact_sha256={str(f.relative_to(ROOT)):sha(f) for f in [out/'netlist.xml',out/'erc.json',out/'native-commands.json']},
                no_connect_inventory=nc,power_stage_native_schematic_authored=True,pcb_implemented=False,
                e28_native_integration_implemented=False,physical_qualified=False,startup_qualified=False,fabrication_released=False)
    (out/'current-native.json').write_text(json.dumps(report,indent=2)+'\n')
    print('NF03C',len(parts),'parts',counts,'parity',len(differences))

if __name__=='__main__':main()
