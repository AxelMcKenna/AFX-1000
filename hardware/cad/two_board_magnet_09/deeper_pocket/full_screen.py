"""Use the unchanged shared workflow for this explicit candidate."""
from pathlib import Path
from hardware.cad.assembly_workflow import workflow
if __name__ == '__main__':
    original_loader = workflow.load_manifest
    candidate = Path(__file__).resolve().with_name('full.json')
    workflow.load_manifest = lambda: original_loader(candidate)
    workflow.main()
