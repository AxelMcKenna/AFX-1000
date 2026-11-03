"""Six-layer control clearances with reference coverage on both ground planes."""
import math

from hardware.fabrication.audio_main_global_controls import SignalScreen


class LayeredSignalScreen(SignalScreen):
    def __init__(self, captured):
        from shapely.geometry import Point
        from shapely.ops import unary_union
        from shapely.strtree import STRtree

        from hardware.fabrication.route_nf_surface import shape

        self.layers = ("F.Cu", "In2.Cu", "In3.Cu", "B.Cu")
        assert captured["copper_layers"] == ["F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu"]
        self.outline = shape(captured["outline"]).buffer(-.61)
        self.via_outline = shape(captured["outline"]).buffer(-.81)
        self.reference = unary_union([shape(z["polygons"]) for z in captured["zones"]
                                     if z["layer"] == "In1.Cu" and not z["keepout"] and z["net"] == "AGND"])
        self.geometry = {layer: [] for layer in self.layers}
        self.via_geometry, self.vias, self.new_vias, self.added = [], [], [], []
        for o in captured["objects"]:
            copper = shape([p for ps in o["layers"].values() for p in ps])
            if not copper.is_empty:
                self.via_geometry.append((o["net"], copper, o["kind"]))
            for layer, ps in o["layers"].items():
                if layer in self.geometry and ps:
                    self.geometry[layer].append((o["net"], shape(ps), .31))
            if o.get("npth"):
                radius = math.hypot(*o["drill_mm"])/2+.001
                hole = Point(o["position_mm"]).buffer(radius/math.cos(math.pi/128), quad_segs=32)
                self.via_geometry.append((None, hole, "HOLE"))
                for layer in self.layers:
                    self.geometry[layer].append((None, hole, .36))
            if o["kind"] == "PCB_VIA":
                self.vias.append((o["net"], tuple(o["position_mm"])))
        protected = set()
        for z in captured["zones"]:
            if not z["keepout"] or not z["polygons"]:
                continue
            g = shape(z["polygons"])
            sensitive = not z["prohibit_tracks"] and z["layer"] in ("In1.Cu", "In2.Cu")
            # Keep the additional GPIO copper away from the protected analog
            # nodes on all three routed faces, including under the components.
            key = (g.wkb, sensitive)
            if sensitive and key not in protected:
                for layer in self.layers:
                    self.geometry[layer].append((None, g, .11))
                self.via_geometry.append((None, g, "KEEPOUT"))
                protected.add(key)
            elif z["prohibit_tracks"] and z["layer"] in self.layers:
                self.geometry[z["layer"]].append((None, g, .11))
            if z["prohibit_vias"]:
                self.via_geometry.append((None, g, "KEEPOUT"))
        self.trees = {layer: STRtree([g for _, g, _ in rows]) for layer, rows in self.geometry.items()}
        self.via_tree = STRtree([g for _, g, _ in self.via_geometry])
        self._added_count = self._via_count = -1

        self.references = {name: unary_union([shape(z["polygons"]) for z in captured["zones"]
                           if z["layer"] == name and not z["keepout"] and z["net"] == "AGND"])
                           for name in ("In1.Cu", "In4.Cu")}
        assert all(not g.is_empty for g in self.references.values())
        self.reference = self.references["In1.Cu"].intersection(self.references["In4.Cu"])
