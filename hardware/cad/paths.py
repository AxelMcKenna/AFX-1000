"""Keep large CAD exports outside editable designs and small verification records."""

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "build/artifacts/cad"
PREVIEWS = ROOT / "docs/assets/hardware"


def update_previews(names):
    PREVIEWS.mkdir(parents=True, exist_ok=True)
    for name in names:
        shutil.copy2(ARTIFACTS / (name + ".png"), PREVIEWS / (name + ".png"))
