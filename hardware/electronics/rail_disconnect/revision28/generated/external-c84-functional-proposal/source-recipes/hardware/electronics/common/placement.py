"""Board-independent footprint placement helpers."""

import json
import shutil
import uuid
from pathlib import Path

from .sexpr import Atom, a, children, first, read_sexpr


def project_settings():
    return {
        "rules": {
            "min_clearance": 0.25,
            "min_track_width": 0.25,
            "min_copper_edge_clearance": 0.5,
            "min_through_hole_diameter": 0.3,
            "min_via_annular_width": 0.15,
            "min_hole_clearance": 0.25,
        }
    }


def strip_and_flip(node, bottom):
    result = []
    for v in node:
        if isinstance(v, list):
            if v and v[0] in ("uuid", "version", "generator", "generator_version", "embedded_fonts", "model"):
                continue
            v = strip_and_flip(v, bottom)
            if bottom and v and v[0] in ("at", "xy", "start", "end", "center", "mid") and len(v) >= 3:
                v[2] = a(-float(v[2]))
                if v[0] == "at" and len(v) >= 4:
                    v[3] = a(-float(v[3]))
            result.append(v)
        elif bottom and isinstance(v, str) and not isinstance(v, Atom) and v.startswith(("F.", "B.")):
            result.append(("B." if v.startswith("F.") else "F.") + v[2:])
        else:
            result.append(v)
    if bottom and result and result[0] == "effects":
        just = children(result, "justify")
        if just:
            if a("mirror") not in just[0]:
                just[0].append(a("mirror"))
        else:
            result.append([a("justify"), a("mirror")])
    return result


def placed_footprint(component, pose, library, nets, origin=(100, 100), namespace="rmx:E06:"):
    ref = component["ref"]
    x, y, angle, side = pose
    footprint = strip_and_flip(read_sexpr(library.read_text()), side == "B")
    footprint[1] = component["footprint"]
    footprint = [v for v in footprint if not (isinstance(v, list) and v and v[0] in ("at", "path"))]
    footprint.append([a("at"), origin[0] + x, origin[1] + y, angle])
    footprint.append([a("uuid"), a(str(uuid.uuid5(uuid.NAMESPACE_URL, namespace + ref)))])
    for prop in children(footprint, "property"):
        if prop[1] == "Reference":
            prop[2] = ref
            first(prop, "layer")[1] = side + ".Fab"
        elif prop[1] == "Value":
            prop[2] = component["value"]
            first(prop, "layer")[1] = side + ".Fab"
            effects = first(prop, "effects")
            if not children(effects, "hide"):
                effects.append([a("hide"), a("yes")])
        elif prop[1] == "Datasheet":
            prop[2] = component["source"]
    for key, value in [("MPN", component["mpn"]), ("Datasheet", component["source"])]:
        if not any(p[1] == key for p in children(footprint, "property")):
            extra = read_sexpr(
                f'(property "{key}" {json.dumps(value)} (at 0 0 0) (layer "{side}.Fab") (effects (font (size .8 .8)) (hide yes)))'
            )
            if side == "B":
                first(extra, "effects").append([a("justify"), a("mirror")])
            footprint.append(extra)
    for pad in children(footprint, "pad"):
        number = str(pad[1])
        # Mechanical locating holes have no electrical terminal even though
        # KiCad expresses their through-board extent with the *.Cu wildcard.
        if not number and pad[2] == "np_thru_hole":
            assert not children(pad, "net"), "Nonplated locating hole must not carry a net"
            continue
        # Exposed-pad packages can have unnumbered stencil/mask-only windows.
        # Preserve those manufacturing apertures without inventing a net.
        if not number and not any(str(layer).endswith(".Cu") for layer in first(pad, "layers")[1:]):
            continue
        net = component["nets"][number]
        pad[:] = [v for v in pad if not (isinstance(v, list) and v and v[0] == "net")]
        pad.append([a("net"), nets[net], "/" + net])
    return footprint


def footprint_root(cli, explicit=None):
    if explicit:
        return explicit.resolve()
    executable = Path(shutil.which(cli) or cli).resolve()
    for path in (executable.parents[1] / "SharedSupport/footprints", Path("/usr/share/kicad/footprints")):
        if path.is_dir():
            return path
    raise RuntimeError("Pass --footprint-dir for installed KiCad libraries")
