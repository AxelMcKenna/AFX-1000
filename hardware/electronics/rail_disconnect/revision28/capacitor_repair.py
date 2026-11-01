"""Install manufacturer-supported timing-cap cases and joint escape clearances."""

from .capacitor_patterns import main as patterns
from .integrate_positive import native_parts, write_schematic
from .relocate import main as move

TARGETS = {
    "R86": (49, 2.5, 0, "F"),
    "R117": (33, 18.5, 0, "B"),
    "C36": (49, 10, 90, "F"),
    "R7": (42, 22.5, 0, "B"),
    "R11": (53, 33.5, 90, "B"),
    "R88": (111, 17.5, 0, "F"),
    "R138": (69, 37.5, 0, "F"),
    "R31": (61.5, 34.5, 0, "B"),
    "R113": (66.5, 39, 0, "B"),
    "C39": (45, 6.5, 90, "B"),
    "C41": (45, 10.75, 0, "B"),
    "C49": (37.5, 18.5, 90, "F"),
    "C46": (133.5, 8, 0, "F"),
    "C50": (40.5, 20, 0, "B"),
    "C43": (124, 14.25, 0, "B"),
    "C45": (114, 27, 0, "B"),
    "C47": (131.5, 23.5, 0, "F"),
    "C51": (143.5, 21.5, 0, "B"),
    "C61": (51.5, 42, 0, "B"),
    "C62": (56.5, 42, 0, "B"),
    "C63": (61.5, 42, 0, "B"),
    "C64": (66.5, 42, 0, "B"),
    "C65": (71.5, 42, 0, "B"),
}


def main():
    patterns()
    parts = native_parts()
    write_schematic(parts)
    move(TARGETS, "manufacturer-capacitor-repair", drop_refs=("J2",))


if __name__ == "__main__":
    main()
