"""E24 inductor lands from the manufacturer's recommended layout drawings."""

from .spec import ROOT


def generate():
    folder = ROOT / "RMX_Power.pretty"
    folder.mkdir(exist_ok=True)
    for name, pad_w, pad_h, center, body_w, body_d, court_w, court_d in [
        ("SRP7050WA", 3, 3.5, 3, 7.3, 7.3, 9.5, 8),
        ("SRP1050WA", 3.65, 5, 4.325, 11, 10, 12.8, 10.8),
    ]:
        text = f'''(footprint "{name}" (version 20240108) (generator pcbnew) (layer "F.Cu")
          (descr "Bourns {name}; manufacturer recommended pads; courtyard includes maximum case dimensions plus .25mm; process qualification open")
          (attr smd)
          (property "Reference" "REF**" (at 0 {-court_d / 2 - 1}) (layer "F.Fab") (effects (font (size .8 .8))))
          (property "Value" "{name}" (at 0 {court_d / 2 + 1}) (layer "F.Fab") (effects (font (size .8 .8)) (hide yes)))
          (fp_rect (start {-body_w / 2} {-body_d / 2}) (end {body_w / 2} {body_d / 2}) (stroke (width .1) (type solid)) (fill none) (layer "F.Fab"))
          (fp_rect (start {-court_w / 2} {-court_d / 2}) (end {court_w / 2} {court_d / 2}) (stroke (width .05) (type solid)) (fill none) (layer "F.CrtYd"))
          (pad "1" smd rect (at {-center} 0) (size {pad_w} {pad_h}) (layers "F.Cu" "F.Paste" "F.Mask"))
          (pad "2" smd rect (at {center} 0) (size {pad_w} {pad_h}) (layers "F.Cu" "F.Paste" "F.Mask")))
        '''
        (folder / (name + ".kicad_mod")).write_text(text.strip() + "\n")


if __name__ == "__main__":
    generate()
