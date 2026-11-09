"""TB03: replace obsolete inlet mounts, preserving the exterior jack/switch."""
from pathlib import Path
from hardware.fabrication import two_board_placement_v2 as prior

original_capture=prior.base.capture


def capture():
    cap=original_capture()
    removed=[p for p in cap['parts'] if p['role']=='input_protection' and p['mechanical']]
    cap['parts']=[p for p in cap['parts'] if p not in removed]
    for p in removed:cap['retired_mounts'].append(dict(role=p['role'],ref=p['ref'],value=p['value'],reason='old inlet board mounts replaced; H1 head receiver conflicts with service USB'))
    cap['power_mount_centres'] += [[275,8],[307,35]]
    cap['source_sha256'][str(Path(__file__).relative_to(prior.base.REPO))]=prior.base.sha(Path(__file__))
    cap['source_sha256'][str(Path(prior.__file__).relative_to(prior.base.REPO))]=prior.base.sha(Path(prior.__file__))
    return cap


if __name__=='__main__':
    prior.base.capture=capture
    prior.build('two-board-placement-03')
