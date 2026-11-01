"""Immutable scoped AP03 mechanical/pressure-bound handoff."""

import json

from .audit import errors
from .stage import OUT, PARENT, ROOT, sha, write


def seal():
    target=ROOT/"handoff.json"
    if target.exists():
        raise RuntimeError("Sealed AP03 cannot be overwritten")
    bad=errors()
    if bad:
        raise RuntimeError("Cannot seal failed/stale evidence: "+repr(bad))
    tests=json.loads((OUT/"portable-tests.json").read_text())
    if tests["returncode"] or tests["tests_passed"]!=16:
        raise RuntimeError("Portable regression evidence failed")
    main=json.loads((OUT/"current-native/verification.json").read_text())
    seated=json.loads((OUT/"mating-seated/verification.json").read_text())
    files={str(p.relative_to(ROOT)):sha(p) for p in ROOT.rglob("*")
           if p.is_file() and p!=target and "__pycache__" not in p.parts and p.suffix!=".pyc"}
    write(target,dict(revision="AP03",candidate="318.28mm2meter/rearapproachmechanicalprototype",
          files_sha256=files,parent_folder=str(PARENT),parent_handoff_sha256=sha(PARENT/"handoff.json"),
          parent_originals_modified=False,main_native_cases=len(main["cases"]),
          renewed_nominal_interface_cases=len(seated["cases"]),all_requested_native_geometry_clear=True,
          portable_tests_passed=16,actual_base_pins=899,additional_whole_pins_removed=19,
          actual_meter_faceted_net_total_mm2=318.2787004060937,rear_wall_Y=[137,139],
          continuous_approach_requirement_right_min_mm2=204.43330390277606,
          additional_receiving_sensitivity_right_mm2=183.29162987847008,
          actual_BASE_STEP_valid_single_solid=True,complete_modeled_review_objects=21,
          complete_modeled_review_triangles=826258,unchanged_parent_mesh_families_reused=16,
          fresh_changed_mesh_families=5,actual_flow_or_split_verified=False,
          physical_qualified=False,thermal_qualified=False,electrical_qualified=False,
          structural_qualified=False,full_wiring_qualified=False,fabrication_released=False,
          latest_board_wire_candidates_adopted=False,review_assembly_fabricable_as_one_part=False,
          adopted=False))
    print(json.dumps(dict(files=len(files),handoff_sha256=sha(target))))


if __name__=="__main__":
    seal()
