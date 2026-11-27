from pathlib import Path
from hardware.cad.assembly_workflow import workflow
if __name__=='__main__':
    original=workflow.load_manifest
    workflow.load_manifest=lambda:original(Path(__file__).with_name('candidate.json'))
    workflow.main()
