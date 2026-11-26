"""Crease-pattern geometry: build FOLD-format patterns and check local flat-foldability.

Patterns live on the unit square [0, 1] x [0, 1]. Creases are given as segments with
FOLD assignments: "M" mountain, "V" valley, "F" flat (precrease, not folded in the
final state), "B" border. Segments are split at every intersection so the result is a
proper planar crease graph.

Validation checks every interior vertex for the three local conditions a flat fold
needs: Kawasaki (alternating angles sum to 180 degrees), Maekawa (|M - V| = 2), and
big-little-big (the creases bounding a strictly smallest sector must differ). Passing
them means each vertex folds flat on its own; it does not prove the whole sheet folds
flat without self-intersection, which is NP-hard in general.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

Point = Tuple[float, float]
EPS = 1e-9
ANGLE_TOL = 1e-6  # radians; coords keep 10 decimals so this is ample


@dataclass
class Crease:
    a: Point
    b: Point
    assignment: str  # "M", "V", "F", or "B"


@dataclass
class VertexReport:
    vertex: int
    x: float
    y: float
    degree: int
    kawasaki: bool
    maekawa: bool
    big_little_big: bool

    @property
    def ok(self) -> bool:
        return self.kawasaki and self.maekawa and self.big_little_big


@dataclass
class ValidationReport:
    flat_foldable_locally: bool
    interior_vertices: int
    failures: List[VertexReport] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "flat_foldable_locally": self.flat_foldable_locally,
            "interior_vertices": self.interior_vertices,
            "checks": ["kawasaki", "maekawa", "big_little_big"],
            "failures": [
                {
                    "vertex": f.vertex,
                    "coords": [round(f.x, 4), round(f.y, 4)],
                    "kawasaki": f.kawasaki,
                    "maekawa": f.maekawa,
                    "big_little_big": f.big_little_big,
                }
                for f in self.failures
            ],
        }


def _intersect(p: Point, p2: Point, q: Point, q2: Point) -> Optional[Tuple[float, float]]:
    """Return (t, u) parameters where segment p->p2 meets q->q2, or None."""
    rx, ry = p2[0] - p[0], p2[1] - p[1]
    sx, sy = q2[0] - q[0], q2[1] - q[1]
    denom = rx * sy - ry * sx
    if abs(denom) < EPS:
        return None
    qpx, qpy = q[0] - p[0], q[1] - p[1]
    t = (qpx * sy - qpy * sx) / denom
    u = (qpx * ry - qpy * rx) / denom
    if -EPS <= t <= 1 + EPS and -EPS <= u <= 1 + EPS:
        return t, u
    return None


def _point_on_segment(pt: Point, a: Point, b: Point) -> Optional[float]:
    """Parameter t of pt along a->b if pt lies on the segment, else None."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    length2 = dx * dx + dy * dy
    if length2 < EPS:
        return None
    cross = (pt[0] - a[0]) * dy - (pt[1] - a[1]) * dx
    if abs(cross) > 1e-7:
        return None
    t = ((pt[0] - a[0]) * dx + (pt[1] - a[1]) * dy) / length2
    return t if -EPS <= t <= 1 + EPS else None


class CreasePattern:
    """Collects creases, splits them into a planar graph, and exports FOLD."""

    def __init__(self, title: str, description: str = ""):
        self.title = title
        self.description = description
        self.creases: List[Crease] = []

    def add(self, a: Point, b: Point, assignment: str) -> "CreasePattern":
        if assignment not in {"M", "V", "F", "B"}:
            raise ValueError(f"bad assignment {assignment!r}")
        self.creases.append(Crease(a, b, assignment))
        return self

    def build(self) -> Tuple[List[Point], List[Tuple[int, int]], List[str]]:
        creases = list(self.creases)
        corners = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
        for i in range(4):
            creases.append(Crease(corners[i], corners[(i + 1) % 4], "B"))

        # Collect split parameters for each crease: endpoints, crossings, and
        # endpoints of other creases that land on it (T-junctions).
        splits: List[List[float]] = [[0.0, 1.0] for _ in creases]
        for i, ci in enumerate(creases):
            for j in range(i + 1, len(creases)):
                cj = creases[j]
                hit = _intersect(ci.a, ci.b, cj.a, cj.b)
                if hit:
                    splits[i].append(hit[0])
                    splits[j].append(hit[1])
                for end in (cj.a, cj.b):
                    t = _point_on_segment(end, ci.a, ci.b)
                    if t is not None:
                        splits[i].append(t)
                for end in (ci.a, ci.b):
                    u = _point_on_segment(end, cj.a, cj.b)
                    if u is not None:
                        splits[j].append(u)

        vertices: List[Point] = []

        def vid(pt: Point) -> int:
            for k, v in enumerate(vertices):
                if abs(v[0] - pt[0]) < 1e-7 and abs(v[1] - pt[1]) < 1e-7:
                    return k
            vertices.append((pt[0], pt[1]))
            return len(vertices) - 1

        edges: Dict[Tuple[int, int], str] = {}
        for crease, ts in zip(creases, splits):
            ts = sorted(set(round(t, 10) for t in ts))
            pts = [
                (crease.a[0] + t * (crease.b[0] - crease.a[0]),
                 crease.a[1] + t * (crease.b[1] - crease.a[1]))
                for t in ts
            ]
            for p, q in zip(pts, pts[1:]):
                u, v = vid(p), vid(q)
                if u == v:
                    continue
                key = (min(u, v), max(u, v))
                # A real fold wins over a border/flat duplicate.
                if key not in edges or edges[key] in {"F", "B"}:
                    edges[key] = crease.assignment
        keys = sorted(edges)
        return vertices, keys, [edges[k] for k in keys]

    def to_fold(self) -> dict:
        vertices, edges, assignments = self.build()
        fold_angle = {"M": -180, "V": 180, "F": 0, "B": 0}
        return {
            "file_spec": 1.1,
            "file_creator": "Origami Pattern Studio",
            "file_classes": ["singleModel"],
            "frame_title": self.title,
            "frame_description": self.description,
            "frame_classes": ["creasePattern"],
            "frame_attributes": ["2D"],
            "vertices_coords": [[round(x, 10), round(y, 10)] for x, y in vertices],
            "edges_vertices": [list(e) for e in edges],
            "edges_assignment": assignments,
            "edges_foldAngle": [fold_angle[a] for a in assignments],
        }


def _on_border(pt: Sequence[float]) -> bool:
    x, y = pt
    return x < 1e-7 or y < 1e-7 or x > 1 - 1e-7 or y > 1 - 1e-7


def _big_little_big(sectors: List[float], types: List[str]) -> bool:
    """Single-vertex crimp test. sectors[i] lies between crease i and crease i+1."""
    sectors, types = list(sectors), list(types)
    while len(types) > 2:
        n = len(types)
        progressed = False
        for i in range(n):
            prev_s, cur, next_s = sectors[i - 1], sectors[i], sectors[(i + 1) % n]
            if cur <= prev_s + ANGLE_TOL and cur <= next_s + ANGLE_TOL:
                j = (i + 1) % n
                if types[i] != types[j]:
                    # Crimp: remove creases i and i+1, merging three sectors into one.
                    merged = prev_s - cur + next_s
                    keep = [k for k in range(n) if k not in (i, j)]
                    new_types = [types[k] for k in keep]
                    new_sectors: List[float] = []
                    for k in keep:
                        if k == (i - 1) % n:
                            new_sectors.append(merged)
                        else:
                            new_sectors.append(sectors[k])
                    sectors, types = new_sectors, new_types
                    progressed = True
                    break
                strictly = cur < prev_s - ANGLE_TOL and cur < next_s - ANGLE_TOL
                if strictly:
                    return False
        if not progressed:
            return False
    # Each crimp removes one M and one V and shrinks the total angle by twice the
    # crimped sector, so what remains is two same-type creases with equal sectors.
    return (len(types) == 2 and types[0] == types[1]
            and abs(sectors[0] - sectors[1]) < 1e-5)


def validate(fold: dict) -> ValidationReport:
    coords = fold["vertices_coords"]
    incident: Dict[int, List[Tuple[float, str]]] = {i: [] for i in range(len(coords))}
    for (u, v), a in zip(fold["edges_vertices"], fold["edges_assignment"]):
        if a not in {"M", "V"}:
            continue
        for p, q in ((u, v), (v, u)):
            ang = math.atan2(coords[q][1] - coords[p][1], coords[q][0] - coords[p][0])
            incident[p].append((ang % (2 * math.pi), a))

    failures: List[VertexReport] = []
    interior = 0
    for i, rays in incident.items():
        if _on_border(coords[i]) or not rays:
            continue
        interior += 1
        rays.sort()
        angles = [r[0] for r in rays]
        types = [r[1] for r in rays]
        n = len(rays)
        sectors = [((angles[(k + 1) % n] - angles[k]) % (2 * math.pi)) or 2 * math.pi
                   for k in range(n)]
        if n % 2 == 0:
            alt = sum(s if k % 2 == 0 else -s for k, s in enumerate(sectors))
            kawasaki = abs(alt) < 1e-5
        else:
            kawasaki = False
        m = types.count("M")
        maekawa = abs(m - (n - m)) == 2
        blb = kawasaki and _big_little_big(sectors, types)
        report = VertexReport(i, coords[i][0], coords[i][1], n, kawasaki, maekawa, blb)
        if not report.ok:
            failures.append(report)
    return ValidationReport(not failures, interior, failures)
