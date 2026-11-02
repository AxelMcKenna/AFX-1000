"""Reuse an existing centred via before testing new-drill spacing."""
import math
from hardware.fabrication.nf_softstart_cell_routes import JointScreen


class ExistingViaScreen(JointScreen):
    def via_legal(self, net, xy):
        centred=[other for other,pt in self.vias+self.new_vias if math.dist(pt,xy)<1e-7]
        if centred:
            return all(other==net for other in centred)
        return super().via_legal(net,xy)
