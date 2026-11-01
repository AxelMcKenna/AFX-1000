"""Independent literal contract for the three-edge larger-housing proposal."""

import copy

from ...common.sexpr import a, first


def check_outline_only(before, after):
    assert len(before) == len(after), "No board objects may be added or removed"
    changes = []
    for index, (old, new) in enumerate(zip(before, after)):
        if old == new:
            continue
        assert isinstance(old, list) and isinstance(new, list)
        assert old[0] == new[0] == "gr_line", "Only existing outline lines may change"
        assert first(old, "layer")[1] == first(new, "layer")[1] == "Edge.Cuts"
        restored = copy.deepcopy(new)
        count = 0
        for key in ("start", "end"):
            point = first(restored, key)
            if float(point[2]) == 154.5:
                assert float(point[1]) in (105, 256), "Preserve the existing left/right rim coordinates"
                point[2] = a("145.25")
                count += 1
        assert count and restored == old, "Nothing beyond the exact bottom endpoint may change"
        changes.append(index)
    assert len(changes) == 3, "Exactly the three original bottom-edge objects must change"
    return dict(
        changed_indices=changes,
        every_other_literal_board_object_unchanged=True,
        all_existing_boss_reliefs_holes_copper_lands_zones_rules_and_ports_preserved=True,
        native_housing_support_and_electrical_qualification=False,
    )
