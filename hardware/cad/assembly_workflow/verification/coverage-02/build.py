"""Screen cross-system physical interactions beyond the wire-focused checks."""
import json
from pathlib import Path
from hardware.cad.assembly_workflow import workflow as w
HERE=Path(__file__).resolve().parent

def run():
    previous=HERE/'previous-manifest.json'
    if not previous.exists():previous.write_bytes((w.HERE/'current.json').read_bytes())
    d,c,_,_=w.load_manifest(previous);m=json.loads(previous.read_text())
    controls=[n for n,x in c.items() if n.startswith('controls_') and n not in ['controls_lid','controls_guide'] and not (x['role']=='installed' and not x.get('scene',True))]
    sensor=[n for n in c if n.startswith('sensor_')]
    cooling=[n for n in c if n.startswith('cooling_')]
    m['checks']=[
      {'id':'coverage_controls_cooling','left':controls,'right':cooling,'expect':'empty'},
      {'id':'coverage_sensor_cooling','left':sensor,'right':cooling,'expect':'empty'},
      {'id':'coverage_lid_guide_cooling','left':['controls_lid','controls_guide'],'right':cooling,'expect':'empty'},
      {'id':'coverage_sensor_control_details','left':sensor,'right':['controls_button_mechanisms','controls_pot_body'],'expect':'empty'}]
    (HERE/'candidate.json').write_text(json.dumps(m,indent=2)+'\n');w.load_manifest(HERE/'candidate.json');print('Four explicit cross-system groups prepared; no contact exclusions')
if __name__=='__main__':run()
