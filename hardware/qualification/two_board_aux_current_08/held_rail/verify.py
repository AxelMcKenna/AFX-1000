"""Reuse the exact pin-union and input-hash verifier on the held variant."""
from pathlib import Path
from ..schematic_candidate.verify import verify
HERE=Path(__file__).resolve().parent
if __name__=='__main__':verify(HERE.parent/'schematic_candidate/authored',here=HERE)
