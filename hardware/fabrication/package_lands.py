"""Own lands transcribed from the specified TI package examples.

DRB uses the central exposed-pad land and paste aperture; optional copper/paste
fingers and thermal vias are omitted. This deviation needs assembly acceptance.
"""

import json

from hardware.electronics.common.sexpr import read_sexpr

LIBRARY = "AFX_Package"
DRB = "TI_DRB0008A_TPS3431"
DCT = "TI_DCT0008A_SN74LVC1G74"


def footprint(kind):
    assert kind in (DRB,DCT)
    watchdog = kind == DRB
    x, width, height = (1.4,.6,.31) if watchdog else (1.9,1.1,.4)
    body = (1.55,1.55)
    # DCT outline 4220784/D permits 0.15 mm mould flash on the body-length
    # sides. Retain a 0.25 mm assembly margin beyond that maximum outline.
    courtyard = (1.95,1.8) if watchdog else (2.7,1.95)
    pads = []
    for number in range(1,9):
        px = -x if number <= 4 else x
        py = -.975+(number-1)*.65 if number <= 4 else .975-(number-5)*.65
        pads.append(f'''(pad "{number}" smd roundrect (at {px:.6f} {py:.6f})
          (size {width} {height}) (layers "F.Cu" "F.Paste" "F.Mask")
          (roundrect_rratio {(.05/min(width,height)):.8f}) (solder_mask_margin .05))''')
    if watchdog:
        pads += ['''(pad "9" smd roundrect (at 0 0) (size 1.5 1.75)
          (layers "F.Cu" "F.Mask") (roundrect_rratio .02857143) (solder_mask_margin .05))''',
          '''(pad "" smd roundrect (at 0 0) (size 1.34 1.55)
          (layers "F.Paste") (roundrect_rratio .03731343))''']
    shapes = []
    for layer, size, thickness in (("F.Fab",body,.1),("F.CrtYd",courtyard,.05)):
        bx,by = size
        shapes.append(f'''(fp_rect (start {-bx} {-by}) (end {bx} {by})
          (stroke (width {thickness}) (type default)) (fill none) (layer "{layer}"))''')
    shapes.append('''(fp_circle (center -2.05 -1.55) (end -1.95 -1.55)
          (stroke (width .12) (type default)) (fill none) (layer "F.SilkS"))''')
    result = f'''(footprint {json.dumps(LIBRARY+":"+kind)} (layer "F.Cu")
      (attr smd) (descr "Own TI land transcription; see hardware/fabrication/package-review.md")
      (property "Reference" "REF**" (at 0 -2.5) (layer "F.Fab") (effects (font (size .8 .8) (thickness .12))))
      (property "Value" {json.dumps(kind)} (at 0 2.5) (layer "F.Fab") (effects (font (size .8 .8)) (hide yes)))
      {''.join(shapes)} {''.join(pads)})'''
    return read_sexpr(result)
