"""Finite additional return paths; callers must verify length and native field support."""
import math


def v_paths(start, end):
    distance = math.dist(start, end)
    if distance < 1e-12:
        return
    dx, dy = end[0] - start[0], end[1] - start[1]
    for fraction in (.25, .5, .75):
        for offset in (-.7, -.6, -.5, -.4, -.3, -.2, -.1, .1, .2, .3, .4, .5, .6, .7):
            middle = [round(start[0] + fraction * dx - offset * dy / distance, 6),
                      round(start[1] + fraction * dy + offset * dx / distance, 6)]
            path = [start, middle, end]
            if sum(math.dist(a, b) for a, b in zip(path, path[1:])) <= 2.5 + 1e-9:
                yield path
