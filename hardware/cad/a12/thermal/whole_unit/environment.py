"""Record the actual optional numerical runtime used for WU01 replay."""

import json
import platform
import sys
from pathlib import Path

from hardware.cad.a12.thermal.generate import REPO, sha

from .ledger import OUT


def main():
    import numpy
    import scipy
    from scipy.sparse.linalg._dsolve import linsolve

    paths = [Path(__file__).resolve(), OUT / "analysis.json", OUT / "ledger.json"]
    report = dict(
        python=sys.version,
        executable=sys.executable,
        platform=platform.platform(),
        numpy=numpy.__version__,
        scipy=scipy.__version__,
        solver="scipy.sparse.linalg.spsolve",
        optional_umfpack_available=not linsolve.noScikit,
        selected_backend="SuperLU" if linsolve.noScikit else "spsolve default selection",
        source_sha256={str(p.relative_to(REPO)): sha(p) for p in paths},
        solver_is_physical_validation=False,
    )
    (OUT / "environment.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
