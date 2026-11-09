"""Add the declared mounting/tool reserve to the local-route screen."""
import json
from pathlib import Path
from shapely.geometry import LineString, Point
import hardware.fabrication.route_two_board_power_local as build
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha

BaseScreen=build.routing.Screen


class MountScreen(BaseScreen):
    def __init__(self,cap):
        super().__init__(cap)
        self.mounts=[(o['ref'],Point(o['position_mm']),max(3.6,max(o['drill_mm'])/2+.5))
            for o in cap['objects'] if o['kind']=='PAD' and o.get('npth') and (o['ref'].startswith('H') or '_H' in o['ref'])]
        assert len(self.mounts)==15

    def legal(self,net,layer,points):
        if not super().legal(net,layer,points):return False
        line=LineString(points)
        return all(line.distance(center)>radius+.1+.01 for ref,center,radius in self.mounts)


def run():
    build.OUT=STAGING/'two-board-power-local-02'
    build.routing.Screen=MountScreen
    build.run()
    p=build.OUT/'local-routing.json';data=json.loads(p.read_text())
    data['source_sha256'][str(Path(__file__).relative_to(REPO))]=sha(Path(__file__))
    data['mount_reserve_radius_mm']='max(3.6, hole radius + 0.5); 0.01mm additional route margin'
    data['mount_clearance_scope']='New outer-layer routes only; complete installed fastener geometry still requires review'
    data['supersedes_trial']='local-01: N12_PERMIT entered the provisional N_H101 tool/head reserve despite passing electrical DRC'
    p.write_text(json.dumps(data,indent=2)+'\n')


if __name__=='__main__':run()
