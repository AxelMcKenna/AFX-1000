"""Linux-only self-contained placement package with source libraries preserved."""
import copy,hashlib,json,os,shutil,sys
from pathlib import Path
from hardware.electronics.common.sexpr import a,children,first,read_sexpr,sexpr
REPO=Path(__file__).resolve().parents[2]
ROOT=REPO/'hardware/fabrication'
PREFIX={'audio_main':'A','digital_core':'D','power_supply':'P','input_protection':'I','rail_disconnect':'E','rail_monitor':'M','negative_startup_protection':'N','fan_health_protection':'F'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def run():
    assert sys.platform=='linux'
    source=ROOT/'staging/two-board-placement-cad-02';out=ROOT/'staging/two-board-placement-cad-03';out.mkdir(exist_ok=False)
    capfile=ROOT/'staging/two-board-placement-05/capture.json';cap=json.loads(capfile.read_text())
    hashes={str(Path(__file__).relative_to(REPO)):sha(Path(__file__)),str(capfile.relative_to(REPO)):sha(capfile)}
    libraries={};role_tables={};mapping=[]
    for role,s in cap['sources'].items():
        parent=(REPO/s['path']).parent;p=parent/'fp-lib-table';hashes[str(p.relative_to(REPO))]=sha(p)
        role_tables[role]={str(first(lib,'name')[1]):Path(str(first(lib,'uri')[1]).replace('${KIPRJMOD}',str(parent)).replace('${KICAD10_FOOTPRINT_DIR}',os.environ['KICAD10_FOOTPRINT_DIR'])) for lib in children(read_sexpr(p.read_text()),'lib')}
    byref={p['id']:p for p in cap['parts']}
    for board in ['signal_main','power_protection']:
        for ext in ['.kicad_pro','.kicad_dru']:
            p=source/(board+ext);hashes[str(p.relative_to(REPO))]=sha(p);shutil.copyfile(p,out/p.name)
        p=source/(board+'.kicad_pcb');hashes[str(p.relative_to(REPO))]=sha(p);tree=read_sexpr(p.read_text())
        for fp in children(tree,'footprint'):
            ref=next(p[2] for p in children(fp,'property') if p[1]=='Reference')
            old=str(fp[1])
            if not old:continue # Source's unassigned mechanical strain-footprint ID.
            lib,name=old.split(':',1)
            if ref in byref:
                role=byref[ref]['role'];newlib='TB05_'+PREFIX[role]+'_'+lib
                src=role_tables[role][lib]/(name+'.kicad_mod');assert src.is_file(),src
                hashes[str(src) if not src.is_relative_to(REPO) else str(src.relative_to(REPO))]=sha(src)
                target=out/'libraries'/(newlib+'.pretty')/(name+'.kicad_mod');target.parent.mkdir(parents=True,exist_ok=True)
                if target.exists():assert sha(target)==sha(src)
                else:shutil.copyfile(src,target)
            else:
                newlib='TB05_Mounts';target=out/'libraries'/(newlib+'.pretty')/(name+'.kicad_mod');target.parent.mkdir(parents=True,exist_ok=True)
                clone=copy.deepcopy(fp);clone[1]=name;first(clone,'at')[1:3]=[0,0]
                target.write_text(sexpr(clone)+'\n')
            libraries[newlib]='${KIPRJMOD}/libraries/'+newlib+'.pretty'
            fp[1]=newlib+':'+name;mapping.append(dict(ref=ref,old=old,new=str(fp[1])))
        (out/p.name).write_text(sexpr(tree)+'\n')
    table=[a('fp_lib_table'),[a('version'),7]]
    for name,uri in sorted(libraries.items()):table.append([a('lib'),[a('name'),name],[a('type'),'KiCad'],[a('uri'),uri],[a('options'),''],[a('descr'),'Source-bound placement library']])
    (out/'fp-lib-table').write_text(sexpr(table)+'\n')
    result=dict(source_sha256=hashes,library_identifier_map=mapping,geometry_changed=False,tracks_added=False,
        artifact_sha256={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()},fabrication_released=False)
    (out/'library-bundle.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Bundled',len(libraries),'source libraries;',len(mapping),'library identifiers mapped; placement geometry unchanged.')


if __name__=='__main__':run()
