"""Read-only axis-to-actual-DIG-copper distance diagnostic.

Continuous sample-cover bound uses the 1-Lipschitz distance-to-surface property.
It only states the necessary circular tool radius at the fixed vertical axis;
no exact fastener, tool, bus installation or disassembly sequence is selected.
"""

import hashlib
import json
from pathlib import Path

import numpy as np
import vtk

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]
STL = REPO / "hardware/cad/a12/positive_links/generated/DIG-CU.stl"
SUPPORT = ROOT.parent / "generated/receiver-ear-support"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run():
    inputs = [
        STL,
        SUPPORT / "analysis.json",
        SUPPORT / "verification.json",
        ROOT.parent / "receiver_support_fit.py",
    ]
    hashes = {str(p.relative_to(REPO)): sha(p) for p in inputs}
    r = vtk.vtkSTLReader()
    r.SetFileName(str(STL))
    r.Update()
    mesh = r.GetOutput()
    dist = vtk.vtkImplicitPolyDataDistance()
    dist.SetInput(mesh)
    zs = np.linspace(7.65, 40.55, 6581)
    signed = np.array([dist.EvaluateFunction((182, 97.2, float(z))) for z in zs])
    index = int(np.argmin(np.abs(signed)))
    step = float(zs[1] - zs[0])
    observed = float(np.min(np.abs(signed)))
    lower = max(0, observed - step / 2)
    bounds = mesh.GetBounds()
    # The axis lies strictly outside the ENTIRE actual copper Y bounding box.
    # VTK gives one spurious negative pseudonormal sign exactly at a sharp
    # face level; distance magnitude is valid and no inside credit is taken.
    assert 97.2 < bounds[2]
    exterior_margin = bounds[2] - 97.2
    allocation = 0.45
    report = dict(
        method=__doc__,
        source_sha256=hashes,
        code_sha256=sha(Path(__file__)),
        vtk_version=vtk.vtkVersion.GetVTKVersion(),
        axis_world_xy_mm=[182, 97.2],
        axis_z_mm=[7.65, 40.55],
        sample_spacing_mm=step,
        distance_cover_subtraction_mm=step / 2,
        observed_min_axis_to_copper_mm=observed,
        continuous_lower_axis_to_surface_mm=lower,
        nearest_sample_z_mm=float(zs[index]),
        axis_outside_entire_copper_y_bbox=True,
        bbox_y_exterior_margin_mm=exterior_margin,
        signed_pseudonormal_negative_samples=int(np.sum(signed < 0)),
        signed_distance_not_used_as_inside_test=True,
        root_tool_nominal_od_mm=5.6,
        root_tool_radial_allocation_mm=allocation,
        root_tool_effective_od_mm=6.5,
        necessary_nominal_circular_tool_od_ceiling_from_sampled_minimum_mm=2 * max(0, observed - allocation),
        continuous_sufficient_nominal_od_for_this_copper_only_mm=2 * max(0, lower - allocation),
        this_is_not_a_tool_selection_or_full_obstacle_fit=True,
        root_native_actual_DIG_CU_intersection_mm3=11.3508465325,
        insulating_cover_removal_alone_solves_access=False,
        assembly_order_or_alternate_tool_selected=False,
        physical_qualified=False,
        fabrication_released=False,
    )
    assert hashes == {str(p.relative_to(REPO)): sha(p) for p in inputs}
    (ROOT / "generated/tool-axis.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k not in ["method", "source_sha256"]}, indent=2))


if __name__ == "__main__":
    run()
