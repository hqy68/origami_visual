"""Traditional origami bases: computed crease patterns plus folding steps.

These bases are traditional (no designer owns them), so the crease patterns and the
written steps here are our own and safe to show in full. Each pattern is checked with
geometry.validate() when the module loads, and in the test suite.

Coordinates: unit square, origin at the bottom-left, viewed with the coloured side
facing you. Mountain/valley are as seen from that side.
"""
from __future__ import annotations

import itertools
import math
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

from .geometry import CreasePattern, validate

T = math.tan(math.pi / 8)  # tan(22.5 deg) ~= 0.4142
C = (0.5, 0.5)


def preliminary_base() -> CreasePattern:
    cp = CreasePattern("Preliminary (square) base",
                       "Four-flap base, closed point at the paper's centre.")
    cp.add((0.5, 0), (0.5, 1), "M").add((0, 0.5), (1, 0.5), "M")
    cp.add((0, 1), (1, 0), "V")
    cp.add((0, 0), (1, 1), "F")  # precreased; lies flat on the front and back faces
    return cp


def waterbomb_base() -> CreasePattern:
    cp = CreasePattern("Waterbomb base",
                       "Triangular base, the inside-out twin of the preliminary base.")
    cp.add((0, 0), (1, 1), "M").add((0, 1), (1, 0), "M")
    cp.add((0, 0.5), (1, 0.5), "V")
    cp.add((0.5, 0), (0.5, 1), "F")
    return cp


def kite_base() -> CreasePattern:
    cp = CreasePattern("Kite base", "Two edges folded to a diagonal; one long point.")
    cp.add((0, 0), (1, 1), "F")
    cp.add((0, 0), (1, T), "V").add((0, 0), (T, 1), "V")
    return cp


def fish_base() -> CreasePattern:
    """Two rabbit ears. P and Q are the incentres of the two halves of the square."""
    cp = CreasePattern("Fish base", "Two long points and two short fins.")
    p = (1 / math.sqrt(2), 1 - 1 / math.sqrt(2))
    q = (p[1], p[0])
    cp.add((0, 0), (1, 1), "F")
    for corner in ((0, 0), (1, 1)):
        cp.add(corner, p, "V").add(corner, q, "V")
    # At each rabbit-ear centre the two smallest sectors share the crease toward the
    # square's centre, so big-little-big forces it to be the odd one out.
    cp.add(p, (1, 0), "V").add(q, (0, 1), "V")
    cp.add(p, q, "M")
    return cp


def blintz_base() -> CreasePattern:
    cp = CreasePattern("Blintz base", "All four corners folded to the centre.")
    cp.add((0, 0), (1, 1), "F").add((0, 1), (1, 0), "F")
    mids = [(0.5, 0), (1, 0.5), (0.5, 1), (0, 0.5)]
    for i in range(4):
        cp.add(mids[i], mids[(i + 1) % 4], "V")
    return cp


def _bird_segments() -> List[Tuple[Tuple[float, float], Tuple[float, float], Optional[str]]]:
    """Bird base geometry. None means 'let the solver choose M or V'."""
    d = 0.5 * T  # 0.2071: where the 22.5 deg kite lines meet the midlines
    left, right, bottom, top = (d, 0.5), (1 - d, 0.5), (0.5, d), (0.5, 1 - d)
    segs: List[Tuple[Tuple[float, float], Tuple[float, float], Optional[str]]] = []
    # Midlines keep the preliminary base's mountains on the inner part.
    for pt in (left, right, bottom, top):
        segs.append((C, pt, "M"))
    segs += [((0, 0.5), left, None), ((1, 0.5), right, None),
             ((0.5, 0), bottom, None), ((0.5, 1), top, None)]
    # Petal corners (0,0) and (1,1) sit on the flat diagonal.
    segs.append(((0, 0), (1, 1), "F"))
    # Leg diagonal: inner half stays a valley as in the preliminary base.
    # Points where the hinge diamond crosses the (0,1)-(1,0) diagonal.
    ul = ((d + 0.5) / 2, (0.5 + 1 - d) / 2)
    lr = (1 - ul[0], 1 - ul[1])
    segs += [(C, ul, "V"), (C, lr, "V"), (ul, (0, 1), None), (lr, (1, 0), None)]
    # Hinge diamond.
    segs += [(left, bottom, None), (bottom, right, None),
             (right, top, None), (top, left, None)]
    # Kite lines from each corner to the two nearest diamond vertices.
    segs += [((0, 0), left, None), ((0, 0), bottom, None),
             ((1, 1), right, None), ((1, 1), top, None),
             ((0, 1), left, None), ((0, 1), top, None),
             ((1, 0), right, None), ((1, 0), bottom, None)]
    return segs


@lru_cache(maxsize=1)
def _solve_bird() -> Tuple[str, ...]:
    segs = _bird_segments()
    free = [i for i, s in enumerate(segs) if s[2] is None]
    # Symmetry: the bird base has 180-degree rotational symmetry about the centre,
    # so pair each free segment with its rotated twin to shrink the search.
    def rot(p):
        return (round(1 - p[0], 6), round(1 - p[1], 6))

    def key(s):
        a, b = (round(s[0][0], 6), round(s[0][1], 6)), (round(s[1][0], 6), round(s[1][1], 6))
        return frozenset((a, b))

    index = {key(segs[i]): i for i in free}
    groups: List[List[int]] = []
    seen = set()
    for i in free:
        if i in seen:
            continue
        twin = index.get(frozenset(rot(p) for p in key(segs[i])))
        group = [i] if twin is None or twin == i else [i, twin]
        seen.update(group)
        groups.append(group)

    for choice in itertools.product("MV", repeat=len(groups)):
        assign = [s[2] for s in segs]
        for g, c in zip(groups, choice):
            for i in g:
                assign[i] = c
        cp = CreasePattern("probe")
        for (a, b, _), x in zip(segs, assign):
            cp.add(a, b, x)
        if validate(cp.to_fold()).flat_foldable_locally:
            return tuple(assign)  # type: ignore[arg-type]
    raise RuntimeError("no locally flat-foldable bird base assignment found")


def bird_base() -> CreasePattern:
    cp = CreasePattern("Bird base",
                       "Preliminary base with both faces petal-folded: four long flaps.")
    for (a, b, _), x in zip(_bird_segments(), _solve_bird()):
        cp.add(a, b, x)
    return cp


BASE_STEPS: Dict[str, List[str]] = {
    "preliminary": [
        "Start coloured side up. Valley-fold in half along both diagonals and unfold.",
        "Turn the paper over. Valley-fold in half edge to edge both ways and unfold.",
        "Turn back to the coloured side. Hold two opposite corners and bring all four "
        "corners together underneath, letting the creases collapse into a small square.",
        "Flatten with the open end pointing toward you: two flaps on each side.",
    ],
    "waterbomb": [
        "Start coloured side up. Valley-fold edge to edge both ways and unfold.",
        "Turn over. Valley-fold along both diagonals and unfold.",
        "Push the centre in and bring the left and right edge midpoints together "
        "underneath, collapsing the paper into a triangle.",
        "Flatten: a triangle with two flaps on each side, point up.",
    ],
    "kite": [
        "Valley-fold along one diagonal and unfold.",
        "Fold the two lower edges to lie along the diagonal crease, meeting at the "
        "centre line. The result looks like a kite.",
    ],
    "fish": [
        "Valley-fold along the diagonal from bottom-left to top-right and unfold.",
        "Kite-fold both edges at the bottom-left corner to that diagonal, then unfold.",
        "Kite-fold both edges at the top-right corner to the diagonal, then unfold.",
        "Using those creases, rabbit-ear the top-left corner: fold both nearby edges to "
        "the diagonal at once and swing the small flap that forms down to one side.",
        "Rabbit-ear the bottom-right corner the same way. You now have two long points "
        "and two short fins.",
    ],
    "blintz": [
        "Crease both diagonals and unfold to find the centre.",
        "Fold each of the four corners to the centre point.",
        "The result is a smaller square; it can be used as the starting square for "
        "any other base to get extra flaps.",
    ],
    "bird": [
        "Fold a preliminary base and place it with the open end pointing toward you.",
        "Fold the lower edges of the top layer to the centre line, then fold the top "
        "triangle down over them. Crease firmly.",
        "Unfold the last three folds.",
        "Petal fold: lift the bottom corner of the top layer up along the horizontal "
        "crease, letting the sides fold inward on the existing creases. Flatten into a "
        "long diamond.",
        "Turn over and repeat the last three steps on the other side.",
        "You now have a bird base: two long flaps at the bottom (split) and two on top.",
    ],
}

BASE_BUILDERS = {
    "preliminary": preliminary_base,
    "waterbomb": waterbomb_base,
    "kite": kite_base,
    "fish": fish_base,
    "blintz": blintz_base,
    "bird": bird_base,
}

BASE_FLAPS = {"kite": 1, "fish": 4, "preliminary": 4, "waterbomb": 4, "blintz": 4, "bird": 4}


@lru_cache(maxsize=None)
def get_base(base_id: str) -> dict:
    if base_id not in BASE_BUILDERS:
        raise KeyError(base_id)
    cp = BASE_BUILDERS[base_id]()
    fold = cp.to_fold()
    return {
        "id": base_id,
        "title": cp.title,
        "description": cp.description,
        "fold": fold,
        "validation": validate(fold).to_dict(),
        "steps": BASE_STEPS[base_id],
        "flaps": BASE_FLAPS[base_id],
    }


def all_bases() -> List[dict]:
    return [get_base(b) for b in BASE_BUILDERS]
