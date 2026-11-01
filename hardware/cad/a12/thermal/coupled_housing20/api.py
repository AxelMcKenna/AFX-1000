"""Read-only input loader for separate installed-cooling requirement studies."""

import json
from pathlib import Path

from .geometry import build

ROOT = Path(__file__).resolve().parent


def load_inputs():
    def read(name):
        return json.loads((ROOT / name).read_text())

    c = read("geometry-contract.json")
    dims = read("sources/dimensions.json")
    d = read("sources/base-design.json")
    d["housing"] = dims["candidate_outer_shell"]
    d["shell_fasteners"] = dims["candidate_shell_fasteners_xy"]
    d["feet"]["centres"] = dims["new_feet_candidate_xy"]
    placements = read("sources/wu-analysis.json")["source_placements"]
    return c, d, placements, build(c, tuple(c["coarse_grid"]))
