"""Actual protected DIGITAL force-lead termination, no mated header contacts.

Selected Alpha3079 AWG14 tinned-copper wires have nominal1.8796mm conductor
OD and3.4036..3.6068mm insulationOD. Finished hole2.2+/-.1mm is an assembly
candidate: verify actual pretinned bundle insertion, solder fill and pull test.
Copper land4.2mm nominal leaves>=.95mm annulus at2.3mm maximum finished hole.
Wire temp105C rating is not an assembled-current or solder-joint qualification.
"""

from ...common.sexpr import children, first, read_sexpr, sexpr
from .manufacturer import ROOT

WIRE = dict(
    part_positive="Alpha3079 OR005",
    part_return="Alpha3079 BK005",
    awg=14,
    conductor_mm2=2.08,
    conductor_nominal_od_mm=1.8796,
    insulation_od_mm=[3.4036, 3.6068],
    temperature_c=[-40, 105],
    minimum_bend_radius_mm=18.034,
    installed_length_max_m=0.150,
    source_joint_acceptance_max_ohm=0.0005,
    source_joint_measured=False,
    destination_joint_accepted=False,
    strain_relief_accepted=False,
    source="https://www.alphawire.com/disteAPI/SpecPDF/DownloadProductSpecPdf?productPartNumber=3079",
)


def footprint():
    fp = read_sexpr("""(footprint "AWG14_Force_2x1_P6mm" (version 20241229)
      (generator pcbnew) (layer "F.Cu") (attr through_hole)
      (property "Reference" "J" (at 0 -3) (layer "F.Fab") (effects (font (size .8 .8))))
      (property "Value" "AWG14_DIG_FORCE" (at 0 9) (layer "F.Fab") (effects (font (size .8 .8)) (hide yes)))
      (pad "1" thru_hole circle (at 0 0) (size 4.2 4.2) (drill 2.2) (layers "*.Cu" "*.Mask"))
      (pad "2" thru_hole circle (at 0 6) (size 4.2 4.2) (drill 2.2) (layers "*.Cu" "*.Mask"))
      (fp_rect (start -2.35 -2.35) (end 2.35 8.35) (stroke (width .05) (type default)) (fill none) (layer "F.CrtYd"))
      (fp_rect (start -2.35 -2.35) (end 2.35 8.35) (stroke (width .05) (type default)) (fill none) (layer "B.CrtYd")))""")
    return fp


def check(fp):
    pads = children(fp, "pad")
    assert len(pads) == 2
    for n, pad in enumerate(pads):
        assert pad[1:4] == [str(n + 1), "thru_hole", "circle"]
        assert list(map(float, first(pad, "at")[1:])) == [0, n * 6]
        assert list(map(float, first(pad, "size")[1:])) == [4.2, 4.2]
        assert float(first(pad, "drill")[1]) == 2.2
        assert set(first(pad, "layers")[1:]) == {"*.Cu", "*.Mask"}
    return dict(WIRE, finished_hole_mm=[2.1, 2.3], manufacturing_accepted=False, physical_qualified=False)


def main():
    fp = footprint()
    check(fp)
    (ROOT / "RMX_E28.pretty/AWG14_Force_2x1_P6mm.kicad_mod").write_text(sexpr(fp) + "\n")


if __name__ == "__main__":
    main()
