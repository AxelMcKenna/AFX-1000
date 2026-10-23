"""Independent manufacturer footprint audits."""

import hashlib
import re


def footprint_review(path):
    text = path.read_text()
    actual = {}
    for number, x, y, w, h in re.findall(
        r'\(pad\s+"([^"]+)"\s+smd\s+rect\s+\(at\s+([-0-9.]+)\s+([-0-9.]+)\)\s+\(size\s+([-0-9.]+)\s+([-0-9.]+)\)',
        text,
    ):
        # KiCad library orientation differs from the landscape datasheet. This
        # explicit rotation is for the audit, not an installed board placement.
        actual[number] = [float(y), -float(x), float(h), float(w)]
    expected = {
        "1": [-3.8, 3.5, 0.8, 1.8],
        "2": [-0.6, 3.5, 0.8, 1.8],
        "3": [1.6, 3.5, 0.8, 1.8],
        "4": [3.8, 3.5, 0.8, 1.8],
        "8": [-3.8, -3.5, 0.8, 1.8],
        "7": [-0.6, -3.5, 0.8, 1.8],
        "6": [1.6, -3.5, 0.8, 1.8],
        "5": [3.8, -3.5, 0.8, 1.8],
    }
    assert actual == expected, (actual, expected)
    return dict(
        candidate="Relay_SMD:Relay_DPDT_Omron_G6K-2F-Y",
        library_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        top_view_pads_mm=actual,
        manufacturer_land_pattern_matches=True,
        physical_fit_verified=False,
    )
