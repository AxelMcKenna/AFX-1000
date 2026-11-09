"""Branch route reservations while reusing immutable native geometry and indexes.

Only added tracks, new vias and the native-obstacle cache dictionary may be
modified in a branch. Captured geometry and spatial indexes remain read-only.
"""
import copy
from hardware.fabrication.digital_via_spacing_close_margin import CloseMarginViaScreen


def branch(screen):
    assert type(screen) is CloseMarginViaScreen
    result=copy.copy(screen)
    result.added=list(screen.added)
    result.new_vias=list(screen.new_vias)
    result._obstacle_cache=dict(screen._obstacle_cache)
    return result
