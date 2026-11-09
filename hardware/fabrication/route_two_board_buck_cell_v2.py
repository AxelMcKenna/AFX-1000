"""Assign fresh graphic UUIDs when reusing the bootstrap footprint template."""
import json
import uuid
from collections import Counter
from pathlib import Path
from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, prop, sha
from hardware.fabrication import route_two_board_buck_cell as build


def run():
    original=build.rotate_footprint;changed=[]
    def place(f,target,rotation):
        n=original(f,target,rotation)
        if prop(f,'Reference')[2]==build.TEMPLATE and target==build.BOOT_XY:
            def refresh(node):
                if not isinstance(node,list):return
                if node and node[0]=='uuid':
                    old=str(node[1]);node[1]=str(uuid.uuid5(uuid.NAMESPACE_URL,'AFX:TBP12:C221:graphic:'+old))
                    changed.append([old,node[1]])
                else:
                    for item in node:refresh(item)
            for child in n:
                if isinstance(child,list) and child and child[0] not in ['uuid','pad','path']:
                    refresh(child)
        return n
    build.rotate_footprint=place
    build.OUT=STAGING/'two-board-power-buck-local-02'
    build.run()
    ids=[]
    def collect(n):
        if isinstance(n,list):
            if n and n[0]=='uuid':ids.append(str(n[1]))
            for child in n:collect(child)
    collect(read_sexpr((build.OUT/'power_protection.kicad_pcb').read_text()))
    assert len(ids)==len(set(ids)) and len(changed)==11
    path=build.OUT/'buck-local-routing.json';d=json.loads(path.read_text())
    d['source_sha256'][str(Path(__file__).relative_to(REPO))]=sha(Path(__file__))
    d.update(bootstrap_graphic_uuid_replacements=changed,unique_authored_board_uuid_count=len(ids),
             supersedes='buck-local-01 copied eleven template graphic UUIDs; native validation is reserved for this corrected successor')
    path.write_text(json.dumps(d,indent=2)+'\n')
    print('Verified',len(ids),'unique authored board UUIDs')


if __name__=='__main__':run()
