"""TB05: include both-face terminal courtyards and every NPTH drill reserve."""
from pathlib import Path
import numpy as np
from shapely.geometry import box
from hardware.fabrication import two_board_placement_v4 as prior
from hardware.electronics.common.sexpr import children,first,read_sexpr
from hardware.electronics.output_stage.check_placement import courtyard

base=prior.base
capture_parent=prior.capture_with_new_mounts
PackerParent=prior.Packer


def capture():
    c=capture_parent();fps={}
    for role,s in c['sources'].items():
        for f in children(read_sexpr((base.REPO/s['path']).read_text()),'footprint'):
            r=next(v[2] for v in children(f,'property') if v[1]=='Reference');fps[(role,r)]=f
    for p in c['parts']:
        f=fps[(p['role'],p['ref'])];x,y=p['source_xy'];op='B' if p['side']=='F' else 'F';extras=[]
        try:
            b=courtyard(f,op+'.CrtYd');extras.append(dict(side=op,bounds=base.offset(b,-x,-y),kind='opposite_face_courtyard'))
        except AssertionError:pass
        for pad in children(f,'pad'):
            if pad[2]=='np_thru_hole':
                b=base.offset(base.pad_box(f,pad,.25),-x,-y)
                for side in ['F','B']:extras.append(dict(side=side,bounds=b,kind='NPTH_reserve'))
        p['additional_planar_reserves']=extras
    c['source_sha256'][str(Path(__file__).relative_to(base.REPO))]=base.sha(Path(__file__))
    c['source_sha256'][str(Path(prior.__file__).relative_to(base.REPO))]=base.sha(Path(prior.__file__))
    return c


class Packer(PackerParent):
    def legal(self,p,xy,fixed_inlet=False,ignore=()):
        if not super().legal(p,xy,fixed_inlet,ignore):return False
        for e in p['additional_planar_reserves']:
            bb=base.offset(e['bounds'],*xy)
            if not fixed_inlet and not self.edge.covers(box(*bb)):return False
            for k in self.keys(bb):
                for other,ident in self.spatial[e['side']].get(k,[]):
                    if ident not in ignore and base.overlap(bb,other,base.GAP):return False
        return True

    def install(self,p,xy,fixed=False):
        super().install(p,xy,fixed)
        for e in p['additional_planar_reserves']:
            b=base.offset(e['bounds'],*xy);self.paint(self.mask[e['side']],b,base.GAP);self.add_obstacle(e['side'],b,p['id'])

    def find(self,p,target):
        free=self.sums(self.mask[p['side']]|self.context_mask(p),p['body_relative_xy'])
        op='B' if p['side']=='F' else 'F'
        for t in p['tails_relative_xy']:free &= self.sums(self.mask[op]|self.context_mask(p,tail=True),t)
        for e in p['additional_planar_reserves']:free &= self.sums(self.mask[e['side']],e['bounds'])
        iy,ix=np.nonzero(free)
        if not len(ix):return None
        costs=(self.x[ix]-target[0])**2+(self.y[iy]-target[1])**2
        for index in np.argsort(costs)[:100]:
            xy=[float(self.x[ix[index]]),float(self.y[iy[index]])]
            if self.legal(p,xy):return xy
        return None


if __name__=='__main__':
    prior.capture_with_new_mounts=capture;prior.Packer=Packer
    prior.build('two-board-placement-05')
