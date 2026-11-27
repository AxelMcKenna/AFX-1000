"""Separate declared seating planes and touch-module reservations from foreign solids."""
import json,shutil
from pathlib import Path
from hardware.cad.assembly_workflow import workflow as w
HERE=Path(__file__).resolve().parent

def run():
    d,c,k,_=w.load_manifest(HERE/'candidate.json');out=HERE/'diagnosis';out.mkdir(exist_ok=False)
    for ident in ['coverage_controls_cooling','coverage_sensor_cooling','coverage_lid_guide_cooling']:
        _,folder=w.job('check',k[ident],c);dest=out/ident;dest.mkdir()
        for name in ['result.json','geometry.scad','geometry.stl','native.log']:shutil.copyfile(folder/name,dest/name)
    sensor=k['coverage_sensor_cooling']['left'];lid=k['coverage_lid_guide_cooling']['left'];cooling=k['coverage_sensor_cooling']['right'];non_shell=[n for n in cooling if n!='cooling_shell'];controls=k['coverage_controls_cooling']['left']
    definitions=[('sensor_non_shell',sensor,non_shell),('sensor_shell',sensor,['cooling_shell']),('lid_non_shell',lid,non_shell),('lid_shell',lid,['cooling_shell']),('controls_without_touch',[n for n in controls if n!='controls_touch_module_receiving'],cooling),('touch_non_shell',['controls_touch_module_receiving'],non_shell),('touch_shell',['controls_touch_module_receiving'],['cooling_shell'])]
    results=[]
    for name,left,right in definitions:
        q={'id':'coverage02_'+name,'left':left,'right':right,'expect':'empty'};r,_=w.execute('check',q,c);assert not r['runtime_failure'];results.append({'check':q,'passed':r['passed'],'mesh':r['mesh'],'cache':w.relative(w.job('check',q,c)[1])});print(name,r['passed'],flush=True)
    (out/'results.json').write_text(json.dumps({'results':results,'source_sha256':{w.relative(Path(__file__)):w.sha(Path(__file__)),w.relative(HERE/'candidate.json'):w.sha(HERE/'candidate.json')},'fabrication_released':False},indent=2)+'\n')
if __name__=='__main__':run()
