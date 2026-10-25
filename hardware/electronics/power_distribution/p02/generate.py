"""Generate P02 native source schematic, custom pin symbols and review BOM."""

from ...common.flat_schematic import generate
from .spec import ROOT, components


def main():
    parts = components()
    generate(
        ROOT,
        "P02",
        "power_p02",
        parts,
        [
            (
                35,
                35,
                "P02 source module: 6V pre-module -> precision LT3083 digital / LT3045 analog. New source variant; no production release.",
            ),
            (
                35,
                1110,
                "U1 footprint unassigned intentionally. Source/output interfaces preserve nets; input4A guard, thermal spreader and all harness/contact/ground bounds need qualification.",
            ),
            (
                35,
                1120,
                "No feedback crosses E26. Remote large bulk is on postreg output; normal reference ramp does not bound a late E26 switch closure.",
            ),
        ],
        page=(850, 1200),
        flags=[("VIN_PROTECTED", 38.1, 1143), ("AGND", 101.6, 1143), ("POWER_READY", 165.1, 1143)],
    )
    # The common writer includes an empty footprint-library entry if a device
    # has no assigned package. Keep the explicit schematic hold, but remove the
    # empty library name instead of inventing a physically wrong module land.
    p = ROOT / "fp-lib-table"
    p.write_text("\n".join(line for line in p.read_text().splitlines() if '(name "")' not in line) + "\n")
    (ROOT / "generated").mkdir(exist_ok=True)
    (ROOT / "generated/verification.json").unlink(missing_ok=True)
    print(
        "P02 native schematic generated:", len(parts), "parts; U1 land pattern unassigned; build_ready:false"
    )


if __name__ == "__main__":
    main()
