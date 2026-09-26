"""Where the text on a plane figure goes: point names, angle values, side lengths.

A figure is only as readable as its labels. The layouts are sampled, so no one
places a label by hand any more, and the first placer here only looked at the
*points*: it kept a name clear of the other names and nothing else. That is how
„H” came to be printed across the very altitude it names, on the right-angle
mark that says it is an altitude, in every paper that drew one — the one spot
that looks empty to a placer that cannot see lines.

So every label is placed against everything the renderer will actually draw:
segments, full lines, rays, the angle arcs, right-angle marks, tick marks,
dots, and every label placed before it. Each label gets a ring of candidate
spots, each spot is scored on its clearance, and the best one wins. Two passes,
so a label placed early can move out of the way of one placed later.

The geometry of the text is estimated, not measured — Python cannot ask a
browser how wide „120°” sets in Georgia. The per-glyph widths below were taken
from the rendered figures and rounded *up*, so an estimate errs toward giving a
label more room than it needs, never less.

`label_problems` reports what the placer could not avoid, and the verifier
turns that into an error, so a figure whose labels collide fails in CI instead
of in front of a student.
"""
from __future__ import annotations

import math
from typing import Any, Iterable, Sequence

Pt = tuple[float, float]
Box = tuple[float, float, float, float]  # x0, y0, x1, y1

#: Font sizes the renderer uses (SceneRenderer.tsx: MathLabel defaults).
POINT_FONT = 11.5
ANGLE_FONT = 10.5
TEXT_FONT = 10.5
#: Half the stroke width: a label this close to a line centre touches the ink.
INK = 0.7
#: Below this much clearance (viewBox units, ≈1.6 px each) a label reads as
#: touching whatever it is next to.
MIN_CLEAR = 0.8
#: A dot is drawn with this radius.
DOT_R = 2.3


# ─── text metrics ────────────────────────────────────────────────────────────

def _glyph_em(ch: str) -> float:
    if ch in "MWmw":
        return 0.86
    if ch in "Iijl|":
        return 0.34
    if ch.isupper():
        return 0.72
    if ch.isdigit():
        return 0.58
    if ch == "°":
        return 0.44
    if ch in " .,:;'":
        return 0.3
    if ch in "+-=<>":
        return 0.62
    if ch.isalpha():
        return 0.56
    return 0.6


def _split_sub(text: str) -> tuple[str, str]:
    """`s_{AB}` → ("s", "AB"), exactly as the renderer's splitSubscript does."""
    if "_" not in text:
        return text, ""
    base, _, sub = text.partition("_")
    return base, sub.strip("{}")


def text_width(text: str, size: float) -> float:
    base, sub = _split_sub(text)
    return (sum(_glyph_em(c) for c in base) * size
            + sum(_glyph_em(c) for c in sub) * size * 0.72)


def text_box(x: float, y: float, text: str, size: float, anchor: str = "middle") -> Box:
    """The ink box of `text` set with its baseline at y, anchored at x."""
    w = text_width(text, size)
    if anchor == "start":
        x0 = x
    elif anchor == "end":
        x0 = x - w
    else:
        x0 = x - w / 2.0
    _, sub = _split_sub(text)
    bottom = y + (0.42 if sub else 0.22) * size
    return (x0, y - 0.74 * size, x0 + w, bottom)


def _baseline_for_centre(cx: float, cy: float, text: str, size: float) -> Pt:
    """Anchor (x, baseline y) that puts the ink box's centre at (cx, cy)."""
    x0, y0, x1, y1 = text_box(0.0, 0.0, text, size)
    return (cx, cy - (y0 + y1) / 2.0)


# ─── distances ───────────────────────────────────────────────────────────────

def _pt_seg(p: Pt, a: Pt, b: Pt) -> float:
    ax, ay = a
    dx, dy = b[0] - ax, b[1] - ay
    den = dx * dx + dy * dy
    t = 0.0 if den == 0 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / den))
    return math.hypot(p[0] - (ax + t * dx), p[1] - (ay + t * dy))


def _pt_box(p: Pt, box: Box) -> float:
    x0, y0, x1, y1 = box
    dx = max(x0 - p[0], 0.0, p[0] - x1)
    dy = max(y0 - p[1], 0.0, p[1] - y1)
    return math.hypot(dx, dy)


def _inside(p: Pt, box: Box) -> bool:
    return box[0] <= p[0] <= box[2] and box[1] <= p[1] <= box[3]


def _segs_cross(a: Pt, b: Pt, c: Pt, d: Pt) -> bool:
    def orient(p: Pt, q: Pt, r: Pt) -> float:
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    o1, o2 = orient(a, b, c), orient(a, b, d)
    o3, o4 = orient(c, d, a), orient(c, d, b)
    return (o1 > 0) != (o2 > 0) and (o3 > 0) != (o4 > 0)


def seg_box_dist(a: Pt, b: Pt, box: Box) -> float:
    """Distance from segment AB to a box; 0 when it touches or crosses it."""
    if _inside(a, box) or _inside(b, box):
        return 0.0
    x0, y0, x1, y1 = box
    corners = ((x0, y0), (x1, y0), (x1, y1), (x0, y1))
    for i in range(4):
        if _segs_cross(a, b, corners[i], corners[(i + 1) % 4]):
            return 0.0
    return min(min(_pt_seg(c, a, b) for c in corners), _pt_box(a, box), _pt_box(b, box))


def box_gap(p: Box, q: Box) -> float:
    """Signed gap between two boxes: positive apart, negative overlapping."""
    gx = max(p[0] - q[2], q[0] - p[2])
    gy = max(p[1] - q[3], q[1] - p[3])
    if gx >= 0 and gy >= 0:
        return math.hypot(gx, gy)
    return max(gx, gy)


# ─── what the renderer draws ─────────────────────────────────────────────────

def _unit(v: Pt) -> Pt:
    n = math.hypot(v[0], v[1])
    return (0.0, 0.0) if n == 0 else (v[0] / n, v[1] / n)


def arc_span(c: Pt, frm: Pt, to: Pt, reflex: bool) -> tuple[float, float]:
    """Start angle and signed sweep of an angle mark — the renderer's arcPath."""
    a1 = math.atan2(frm[1] - c[1], frm[0] - c[0])
    a2 = math.atan2(to[1] - c[1], to[0] - c[0])
    delta = a2 - a1
    while delta <= -math.pi:
        delta += 2 * math.pi
    while delta > math.pi:
        delta -= 2 * math.pi
    if reflex:
        delta = delta - 2 * math.pi if delta > 0 else delta + 2 * math.pi
    return a1, delta


def _arc_polyline(c: Pt, r: float, a1: float, delta: float) -> list[tuple[Pt, Pt]]:
    steps = max(2, int(abs(delta) / math.radians(8)) + 1)
    pts = [(c[0] + r * math.cos(a1 + delta * i / steps), c[1] + r * math.sin(a1 + delta * i / steps))
           for i in range(steps + 1)]
    return list(zip(pts, pts[1:]))


def strokes(spec: dict[str, Any]) -> list[tuple[Pt, Pt, str]]:
    """Every inked segment of a figure scene, tagged with what drew it."""
    P = {k: (float(v[0]), float(v[1])) for k, v in spec["points"].items()}
    out: list[tuple[Pt, Pt, str]] = []
    for s in spec.get("segments") or []:
        out.append((P[s["from"]], P[s["to"]], f"seg:{s['from']}{s['to']}"))
    for ln in spec.get("lines") or []:
        a, b = P[ln["from"]], P[ln["to"]]
        d = _unit((b[0] - a[0], b[1] - a[1]))
        pad = ln.get("pad", 22.0)
        out.append(((a[0] - d[0] * pad, a[1] - d[1] * pad),
                    (b[0] + d[0] * pad, b[1] + d[1] * pad), f"line:{ln['from']}{ln['to']}"))
    for ry in spec.get("rays") or []:
        a, b = P[ry["from"]], P[ry["to"]]
        d = _unit((b[0] - a[0], b[1] - a[1]))
        ext = ry.get("extend", 26.0)
        out.append((a, (b[0] + d[0] * ext, b[1] + d[1] * ext), f"ray:{ry['from']}{ry['to']}"))
    for i, an in enumerate(spec.get("angles") or []):
        c = P[an["at"]]
        a1, delta = arc_span(c, P[an["from"]], P[an["to"]], bool(an.get("reflex")))
        r0 = an.get("r", 20.0)
        for k in range(an.get("arcs", 1) or 1):
            for a, b in _arc_polyline(c, r0 - 4 * k, a1, delta):
                out.append((a, b, f"arc:{i}"))
    for ra in spec.get("rightAngles") or []:
        c = P[ra["at"]]
        u = _unit((P[ra["from"]][0] - c[0], P[ra["from"]][1] - c[1]))
        v = _unit((P[ra["to"]][0] - c[0], P[ra["to"]][1] - c[1]))
        s = ra.get("size", 9.0)
        p1 = (c[0] + u[0] * s, c[1] + u[1] * s)
        p3 = (c[0] + v[0] * s, c[1] + v[1] * s)
        p2 = (p1[0] + v[0] * s, p1[1] + v[1] * s)
        out.append((p1, p2, f"right:{ra['at']}"))
        out.append((p2, p3, f"right:{ra['at']}"))
    for tk in spec.get("ticks") or []:
        a, b = P[tk["from"]], P[tk["to"]]
        t = tk.get("at", 0.5)
        mid = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
        d = _unit((b[0] - a[0], b[1] - a[1]))
        perp = (-d[1], d[0])
        n = tk.get("count", 1) or 1
        for k in range(n):
            off = (k - (n - 1) / 2) * 3.6
            cx, cy = mid[0] + d[0] * off, mid[1] + d[1] * off
            out.append(((cx + perp[0] * 4.2, cy + perp[1] * 4.2),
                        (cx - perp[0] * 4.2, cy - perp[1] * 4.2), f"tick:{tk['from']}{tk['to']}"))
    return out


def _dots(spec: dict[str, Any]) -> list[tuple[str, Pt]]:
    return [(n, tuple(spec["points"][n])) for n in spec.get("dots") or [] if n in spec["points"]]


def _line_ends(spec: dict[str, Any], ln: dict[str, Any]) -> tuple[Pt, Pt]:
    """Where a full line visibly starts and ends: extended by its pad, then
    clipped to the canvas, since the renderer draws it past the edge."""
    P = spec["points"]
    a, b = P[ln["from"]], P[ln["to"]]
    d = _unit((b[0] - a[0], b[1] - a[1]))
    pad = ln.get("pad", 22.0)
    s = (a[0] - d[0] * pad, a[1] - d[1] * pad)
    e = (b[0] + d[0] * pad, b[1] + d[1] * pad)
    w, h = float(spec["width"]), float(spec["height"])
    t0, t1 = 0.0, 1.0
    dx, dy = e[0] - s[0], e[1] - s[1]
    for p, q in ((-dx, s[0]), (dx, w - s[0]), (-dy, s[1]), (dy, h - s[1])):
        if p == 0:
            continue
        r = q / p
        if p < 0:
            t0 = max(t0, r)
        else:
            t1 = min(t1, r)
    return (s[0] + dx * t0, s[1] + dy * t0), (s[0] + dx * t1, s[1] + dy * t1)


def line_label_boxes(spec: dict[str, Any]) -> list[Box]:
    """The names printed beside full lines, where the renderer will set them."""
    P = spec["points"]
    boxes = []
    for ln in spec.get("lines") or []:
        if not ln.get("label"):
            continue
        if ln.get("labelAt"):
            x, y = ln["labelAt"]
            boxes.append(text_box(x, y, ln["label"], POINT_FONT))
            continue
        a, b = P[ln["from"]], P[ln["to"]]
        d = _unit((b[0] - a[0], b[1] - a[1]))
        pad = ln.get("pad", 22.0)
        e = (b[0] + d[0] * pad, b[1] + d[1] * pad)
        boxes.append(text_box(e[0] + 8, e[1] - 5, ln["label"], POINT_FONT, "start"))
    return boxes


# ─── placement ───────────────────────────────────────────────────────────────

class _Label:
    """One piece of text to place, and the spots it may go."""

    def __init__(self, key: str, text: str, size: float, owner: Pt | None,
                 candidates: list[tuple[Pt, float]], home: Iterable[str] = ()):
        self.key = key
        self.text = text
        self.size = size
        self.owner = owner                  # the point the label names, if any
        # (box centre, preference penalty), most preferred first — so the
        # first spot that is clear of everything is the best one and the
        # search can stop there.
        self.candidates = sorted(candidates, key=lambda c: c[1])
        self.clear = False                  # did it find a spot clear of everything?
        # Stroke tags this text belongs to: a line's name may sit close to
        # its own line, just not on it — nearness to it is association.
        self.home = set(home)
        # The point the text belongs to — a named point, or an angle's vertex.
        # A straight line from it to the text must not cross another line: a
        # value on the far side of a cevian from its own arc reads as the
        # angle on that side.
        self.origin: Pt | None = owner
        # For an angle's value: its own sector (start, sweep), and the
        # directions of every drawn line leaving the vertex. Between two of
        # those lines lies a neighbouring angle, and a value set there reads
        # as that angle's.
        self.sector: tuple[float, float] | None = None
        self.rays: list[float] = []
        # A drawn line leaves the vertex inside the angle: its value belongs
        # outside the arms (see `_angle_candidates`).
        self.split = False
        self.anchor: Pt | None = None
        self.box: Box | None = None


def _within_canvas(anchor: Pt, box: Box, w: float, h: float) -> bool:
    # The renderer draws a placed scene's labels exactly where they are put
    # (`labelsPlaced`), so the only constraint is that the ink stays on the
    # canvas — not the old clamp margin, which pushed the name of a point on
    # the top edge down onto the edge itself.
    return box[0] >= 1.0 and box[2] <= w - 1.0 and box[1] >= 1.0 and box[3] <= h - 1.0


#: Clearance is capped at this, so anything further away cannot change a score
#: and is skipped by a bounding-box test before the exact distance is taken.
_REACH = 6.0


def _in_polygon(p: Pt, poly: Sequence[Pt]) -> bool:
    inside = False
    for (x1, y1), (x2, y2) in zip(poly, list(poly[1:]) + [poly[0]]):
        if (y1 > p[1]) != (y2 > p[1]):
            if p[0] < x1 + (p[1] - y1) * (x2 - x1) / (y2 - y1):
                inside = not inside
    return inside


def _score(lab: _Label, centre: Pt, pref: float, ink: list, dots: list[tuple[str, Pt]],
           others: list[Box], names: dict[str, Pt], w: float, h: float
           ) -> tuple[float, Pt, Box, bool, bool] | None:
    """Score one spot. The fourth element says whether every clearance hit its
    cap — nothing at a less preferred spot can then score higher; the fifth,
    whether the spot took no penalty at all."""
    anchor = _baseline_for_centre(centre[0], centre[1], lab.text, lab.size)
    box = text_box(anchor[0], anchor[1], lab.text, lab.size)
    if not _within_canvas(anchor, box, w, h):
        return None
    bx0, by0, bx1, by1 = box[0] - _REACH, box[1] - _REACH, box[2] + _REACH, box[3] + _REACH
    clear = 20.0
    for a, b, tag, (sx0, sy0, sx1, sy1) in ink:
        if sx1 < bx0 or sx0 > bx1 or sy1 < by0 or sy0 > by1:
            continue
        d = seg_box_dist(a, b, box) - INK
        if d < clear:
            clear = d
    gap = 20.0
    for o in others:
        if o[2] < bx0 or o[0] > bx1 or o[3] < by0 or o[1] > by1:
            continue
        g = box_gap(box, o)
        if g < gap:
            gap = g
    dot_clear = min((_pt_box(p, box) - DOT_R for _, p in dots), default=20.0)
    point_clear = min((_pt_box(p, box) - 1.0 for n, p in names.items()
                       if lab.owner is None or p != lab.owner), default=20.0)
    s = 3.0 * min(clear, 4.0) + 3.0 * min(gap, 4.0) + 2.0 * min(dot_clear, 3.0) \
        + 1.5 * min(point_clear, 3.0) - pref
    saturated = clear >= 4.0 and gap >= 4.0 and dot_clear >= 3.0 and point_clear >= 3.0
    ok = clear >= MIN_CLEAR and gap >= MIN_CLEAR and dot_clear >= MIN_CLEAR
    if clear < MIN_CLEAR:
        s -= 30.0 - 4.0 * clear
    if gap < MIN_CLEAR:
        s -= 40.0 - 4.0 * gap
    if dot_clear < MIN_CLEAR:
        s -= 25.0
    if lab.owner is not None:
        own = _pt_box(lab.owner, box)
        if own < 2.0:
            s -= 30.0                         # the name would sit on its own point
            saturated = ok = False
        # A name must be nearer its own point than any other, or it names the
        # wrong one.
        rival = min((_pt_box(p, box) for n, p in names.items() if p != lab.owner), default=99.0)
        if rival < own + 1.5:
            s -= 12.0
            saturated = ok = False
    if lab.sector is not None and len(lab.rays) >= 2 and lab.origin is not None:
        if _in_neighbour_angle(lab.origin, centre, lab.sector, lab.rays):
            s -= 15.0
            saturated = ok = False
    if lab.sector is not None and lab.origin is not None \
            and not _in_sector(lab.origin, centre, lab.sector):
        # Outside its own arms a value is read by nearness alone, so it must
        # be nearer its own vertex than any other named point: 80° set past
        # the arm CA, next to H, reads as an angle at H.
        own = _pt_box(lab.origin, box)
        if any(_pt_box(p, box) < own + 1.5 for p in names.values() if p != lab.origin):
            s -= 12.0
            saturated = ok = False
    if lab.origin is not None:
        v = lab.origin
        for a, b, tag, _ in ink:
            if tag.split(":")[0] not in ("seg", "line", "ray"):
                continue
            if _pt_seg(v, a, b) < 1.0:
                continue           # a line through the vertex itself is an arm
            if _segs_cross(v, centre, a, b):
                # Worse than sitting just outside the arms (preference 18+),
                # which at least stays on the vertex's own side of every line.
                s -= 25.0
                saturated = ok = False
                break
    if lab.home:
        # ...and a line's name must be nearer its own line than any other, and
        # an angle's value nearer its own arc than any other arc.
        kinds = {t.split(":")[0] for t in lab.home}
        own_line = min((seg_box_dist(a, b, box) for a, b, tag, _ in ink if tag in lab.home),
                       default=0.0)
        rival_line = min((seg_box_dist(a, b, box) for a, b, tag, _ in ink
                          if tag not in lab.home and tag.split(":")[0] in kinds),
                         default=99.0)
        if rival_line < own_line + 2.0:
            s -= 12.0
            saturated = ok = False
    return s, anchor, box, saturated, ok


def _place(labels: list[_Label], ink, dots, fixed: list[Box], names, w, h, passes: int = 2) -> None:
    for n in range(passes):
        if n and all(lab.clear for lab in labels):
            break          # the second pass only helps a label that had to compromise
        for lab in labels:
            others = fixed + [o.box for o in labels if o is not lab and o.box is not None]
            best = None
            for centre, pref in lab.candidates:
                r = _score(lab, centre, pref, ink, dots, others, names, w, h)
                if r is None:
                    continue
                if best is None or r[0] > best[0]:
                    best = r
                if r[3]:
                    break  # clear of everything at the most preferred spot left
            if best is not None:
                lab.anchor, lab.box, lab.clear = best[1], best[2], best[3]


def _with_boxes(raw: list[tuple[Pt, Pt, str]]) -> list:
    return [(a, b, tag, (min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])))
            for a, b, tag in raw]


def _pull_inside(spec: dict[str, Any], labels: list[_Label], P: dict[str, Pt], dots,
                 fixed: list[Box], names: dict[str, Pt], w: float, h: float) -> None:
    """Shrink an arc to let its value inside the angle.

    A value set outside its arms is the placer's last resort, and it is often
    only needed because the arc pushes the value out past a nearby line: ∠HCB
    beside a height, whose inside is a thin triangle with no room past a
    radius-22 arc. A smaller arc leaves room next to the vertex. Angles split
    by a line through their inside keep the value outside on purpose, and
    are left alone.
    """
    for lab in labels:
        if not lab.key.startswith("an:") or lab.box is None or lab.sector is None \
                or lab.split or lab.origin is None:
            continue
        box = lab.box
        if _in_sector(lab.origin, ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2), lab.sector):
            continue
        i = int(lab.key[3:])
        an = spec["angles"][i]
        r0 = float(an.get("r", 20.0))
        floor = MIN_ARC_R + 4.0 * ((an.get("arcs", 1) or 1) - 1)
        others = fixed + [o.box for o in labels if o is not lab and o.box is not None]
        a1, delta = lab.sector
        # Smaller arcs first; then, for a narrow angle, larger ones: its wedge
        # is only wide enough for the value far from the vertex, and a value
        # out there with its arc left near the vertex is nearer the next
        # vertex's arc than its own.
        arms = min(math.dist(lab.origin, P[an["from"]]), math.dist(lab.origin, P[an["to"]]))
        radii = [r0 - d for d in range(2, 41, 2) if r0 - d >= floor] + \
                [r0 + d for d in range(4, 61, 4) if r0 + d <= arms - 24.0]
        placed = False
        for r in radii:
            an["r"] = r
            ink = _with_boxes(strokes(spec))
            if _arc_clashes(spec, i, P, set(spec.get("hidden") or []), [x[:3] for x in ink],
                            margin=MARK_BERTH):
                continue
            inside = sorted((cp for cp in _angle_candidates(lab.origin, r, a1, delta, lab.text)
                             if _in_sector(lab.origin, cp[0], lab.sector)), key=lambda cp: cp[1])
            for centre, pref in inside:
                res = _score(lab, centre, pref, ink, dots, others, names, w, h)
                if res is not None and res[4]:
                    lab.anchor, lab.box, lab.clear = res[1], res[2], res[3]
                    placed = True
                    break
            if placed:
                break
        if not placed:
            an["r"] = r0


#: A value further than this past its own arc reads as detached from it.
ARC_GAP = 10.0


def _hug_arcs(spec: dict[str, Any], labels: list[_Label], P: dict[str, Pt], hidden: set,
              fixed: list[Box]) -> None:
    """Draw the arc of a narrow angle out to its value.

    A narrow angle only opens wide enough for its value far from the vertex,
    so the value floated 30–40 units past its arc — and next to whatever
    point was there instead: „18°” for ∠B sat beside F, inside the sliver
    FBC, and read as an angle at F. Drafting practice is the other way round:
    the arc goes out to the value. That is done wherever the longer arc still
    clears every point, mark and text; otherwise the arc stays as it was.
    """
    boxes = fixed + [lab.box for lab in labels if lab.box is not None]
    for lab in labels:
        if not lab.key.startswith("an:") or lab.box is None or lab.sector is None:
            continue
        i = int(lab.key[3:])
        an = spec["angles"][i]
        if an.get("fill"):
            continue
        c = P[an["at"]]
        centre = ((lab.box[0] + lab.box[2]) / 2, (lab.box[1] + lab.box[3]) / 2)
        if not _in_sector(c, centre, lab.sector):
            continue
        r = float(an.get("r", 20.0))
        near = _pt_box(c, lab.box)
        if near - r <= ARC_GAP:
            continue
        # 3 units short of the nearest corner of the value keeps every point
        # of the arc at least that far from every point of the text.
        arms = min(math.dist(c, P[an["from"]]), math.dist(c, P[an["to"]])) - 4.0
        target = min(near - 3.0, arms)
        # The longest arc that clears everything, down to a modest gain: a
        # tick on the arm can stop it short of the value but still let it
        # close most of the gap.
        rr = target
        while rr > r + 2.0:
            an["r"] = round(rr, 1)
            if _arc_is_clear(spec, i, c, P, hidden, [b for b in boxes if b is not lab.box]):
                break
            rr -= 1.5
        else:
            an["r"] = r


def _arc_is_clear(spec: dict[str, Any], i: int, c: Pt, P: dict[str, Pt], hidden: set,
                  boxes: list[Box]) -> bool:
    ink = strokes(spec)
    own = [(a, b) for a, b, tag in ink if tag == f"arc:{i}"]
    others = [(a, b) for a, b, tag in ink
              if tag.split(":")[0] in ("seg", "line", "ray") and _pt_seg(c, a, b) > 1.0]
    # A wider berth than the verifier's minimum: an arc drawn out to its value
    # and ending right on the tick of the side it meets reads as one mark.
    return (not _arc_clashes(spec, i, P, hidden, ink, margin=MARK_BERTH)
            and all(min(seg_box_dist(a, b, box) for a, b in own) >= INK + 1.5 for box in boxes)
            and all(_seg_seg(s, t, a, b) >= 1.5 for s, t in own for a, b in others))


def _point_candidates(p: Pt, centre: Pt, text: str) -> list[tuple[Pt, float]]:
    out = []
    ow = _unit((p[0] - centre[0], p[1] - centre[1]))
    half_w = text_width(text, POINT_FONT) / 2.0
    for k in range(16):
        t = 2 * math.pi * k / 16
        u = (math.cos(t), math.sin(t))
        # Horizontal neighbours need more reach than vertical ones: a label is
        # wider than it is tall.
        base = 5.5 + half_w * abs(u[0]) + 4.5 * abs(u[1])
        for extra in (0.0, 1.5, 3.0, 5.0, 8.0):
            rho = base + extra
            c = (p[0] + u[0] * rho, p[1] + u[1] * rho)
            outward = u[0] * ow[0] + u[1] * ow[1]
            out.append((c, 0.35 * extra - 1.2 * outward))
    return out


def _angle_candidates(c: Pt, r: float, a1: float, delta: float, text: str,
                      split: bool = False) -> list[tuple[Pt, float]]:
    """Spots for an angle's value: inside the angle first, just outside its
    arms as a fallback.

    `split` says a drawn line leaves the vertex *inside* the angle — the
    diagonal of a rhombus, the height in an isosceles triangle. Then every
    spot inside lies in one of the parts, where 48° reads as the measure of
    that part rather than of the whole angle the arc spans, so outside the
    arms is preferred instead.
    """
    out = []
    inside_extra = 20.0 if split else 0.0
    half = max(text_width(text, ANGLE_FONT), 0.94 * ANGLE_FONT) / 2.0
    for f in (0.5, 0.4, 0.6, 0.3, 0.7, 0.2, 0.8):
        a = a1 + delta * f
        u = (math.cos(a), math.sin(a))
        reach = r + 3.5 + half * abs(u[0]) + 4.5 * abs(u[1])
        # A narrow angle only opens wide enough for its value far from the
        # vertex, so the reach goes a long way out — along the angle's own
        # bisector, where the value still reads as belonging to it.
        for extra in (0.0, 2.0, 4.0, 7.0, 11.0, 16.0, 22.0, 30.0, 40.0, 52.0):
            rho = reach + extra
            out.append(((c[0] + u[0] * rho, c[1] + u[1] * rho),
                        inside_extra + 0.3 * extra + 3.0 * abs(f - 0.5)))
    # A narrow angle has no room inside its own arc; let the value sit just
    # past either end of it, where the papers put it too.
    # Rotation past an arm is measured in degrees, not as a share of the
    # angle: a quarter of a 20° angle is 5°, still on top of the arm.
    sign = 1.0 if delta >= 0 else -1.0
    for past in (12.0, 20.0, 30.0, 45.0):
        for a, side in ((a1 - sign * math.radians(past), 0.0),
                        (a1 + delta + sign * math.radians(past), 0.2)):
            u = (math.cos(a), math.sin(a))
            for extra in (0.0, 3.0, 6.0, 10.0, 15.0):
                rho = r + 3.5 + half * abs(u[0]) + 4.5 * abs(u[1]) + extra
                # Outside the arms reads as a different angle, so these only
                # win when every spot inside the angle, however far out, clashes.
                out.append(((c[0] + u[0] * rho, c[1] + u[1] * rho),
                            18.0 + side + 0.3 * extra + 0.08 * past))
    return out


def _rays_from(c: Pt, ink: list) -> list[float]:
    """Directions (radians, 0..2π) of every drawn line leaving vertex c."""
    out: list[float] = []
    for a, b, tag, _ in ink:
        if tag.split(":")[0] not in ("seg", "line", "ray") or _pt_seg(c, a, b) > 1.0:
            continue
        for end in (a, b):
            if math.dist(end, c) >= 2.0:
                t = math.atan2(end[1] - c[1], end[0] - c[0]) % (2 * math.pi)
                if all(abs((t - u + math.pi) % (2 * math.pi) - math.pi) > 0.02 for u in out):
                    out.append(t)
    return sorted(out)


def _in_sector(c: Pt, p: Pt, sector: tuple[float, float], tol: float = 0.0) -> bool:
    """Is p, seen from c, inside the angle (start, signed sweep), give or take tol radians?"""
    t = math.atan2(p[1] - c[1], p[0] - c[0])
    a1, delta = sector
    s = ((t - a1) if delta >= 0 else (a1 - t)) % (2 * math.pi)
    return s <= abs(delta) + tol or s >= 2 * math.pi - tol


def _in_neighbour_angle(c: Pt, p: Pt, sector: tuple[float, float], rays: list[float]) -> bool:
    """Is p, seen from c, inside an angle between two drawn lines other than
    the marked one? The open side of the figure (a gap over 180°) does not count."""
    t = math.atan2(p[1] - c[1], p[0] - c[0]) % (2 * math.pi)
    a1, delta = sector
    lo = (a1 if delta >= 0 else a1 + delta) % (2 * math.pi)
    if (t - lo) % (2 * math.pi) < abs(delta):
        return False                        # inside the marked angle itself
    for i, r0 in enumerate(rays):
        r1 = rays[(i + 1) % len(rays)]
        gap = (r1 - r0) % (2 * math.pi) or 2 * math.pi
        if (t - r0) % (2 * math.pi) < gap:
            return gap < math.pi - 0.05
    return False


def _ray_inside(c: Pt, a1: float, delta: float, ink: list) -> bool:
    """Does a drawn line leave vertex c strictly inside the angle (a1, a1+δ)?"""
    margin = math.radians(3.0)
    lo, hi = (a1, a1 + delta) if delta >= 0 else (a1 + delta, a1)
    for a, b, tag, _ in ink:
        if tag.split(":")[0] not in ("seg", "line", "ray"):
            continue
        if _pt_seg(c, a, b) > 1.0:
            continue
        for end in (a, b):
            if math.dist(end, c) < 2.0:
                continue
            t = math.atan2(end[1] - c[1], end[0] - c[0])
            # bring t into the window [lo, lo + 2π)
            while t < lo:
                t += 2 * math.pi
            while t >= lo + 2 * math.pi:
                t -= 2 * math.pi
            if lo + margin < t < hi - margin:
                return True
    return False


def _along_candidates(a: Pt, b: Pt, centroid: Pt, text: str, size: float,
                      ts: Sequence[float] | None = None) -> list[tuple[Pt, float]]:
    d = _unit((b[0] - a[0], b[1] - a[1]))
    n = (-d[1], d[0])
    mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    if (mid[0] + n[0] - centroid[0]) ** 2 + (mid[1] + n[1] - centroid[1]) ** 2 < \
       (mid[0] - n[0] - centroid[0]) ** 2 + (mid[1] - n[1] - centroid[1]) ** 2:
        n = (-n[0], -n[1])
    half_w = text_width(text, size) / 2.0
    half_h = 0.5 * size
    # Distance from the line to the box centre that just clears the ink.
    reach = half_w * abs(n[0]) + half_h * abs(n[1]) + 2.5
    out = []
    order = list(ts) if ts else [0.5, 0.42, 0.58, 0.34, 0.66, 0.26, 0.74]
    if ts:
        # A name for a whole line may also sit just past the line's end, on its
        # continuation, which is where the papers usually print „s_AB”.
        along = half_w * abs(d[0]) + half_h * abs(d[1]) + 3.0
        for end, sign in ((b, 1.0), (a, -1.0)):
            if (sign > 0 and max(ts) > 0.8) or (sign < 0 and min(ts) < 0.2):
                for extra in (0.0, 3.0):
                    out.append(((end[0] + d[0] * sign * (along + extra),
                                 end[1] + d[1] * sign * (along + extra)), 0.5 + 0.4 * extra))
    for rank, t in enumerate(order):
        base = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
        for extra in (0.0, 2.0, 4.0, 7.0):
            for side, pen in ((1.0, 0.0), (-1.0, 5.0)):
                rho = reach + extra
                out.append(((base[0] + n[0] * side * rho, base[1] + n[1] * side * rho),
                            pen + 0.4 * extra + (1.5 * rank if ts else 4.0 * abs(t - 0.5))))
    return out


def _t_on(a: Pt, b: Pt, p: Pt) -> float:
    """Where p projects onto AB: 0 at A, 1 at B."""
    ab = (b[0] - a[0], b[1] - a[1])
    den = ab[0] * ab[0] + ab[1] * ab[1]
    return 0.0 if den == 0 else ((p[0] - a[0]) * ab[0] + (p[1] - a[1]) * ab[1]) / den


def _cuts(a: Pt, b: Pt, pts: Iterable[Pt]) -> list[float]:
    """Positions along AB of the named points drawn on it between its ends."""
    return sorted(t for p in pts
                  if 0.04 < (t := _t_on(a, b, p)) < 0.96 and _pt_seg(p, a, b) < 1.0)


def _reads_as_part(t: float, cuts: list[float]) -> bool:
    """A length at t along a side cut at `cuts`: is it centred on one part
    rather than on the whole side?"""
    bounds = [0.0] + cuts + [1.0]
    for lo, hi in zip(bounds, bounds[1:]):
        if lo <= t <= hi:
            return abs(t - (lo + hi) / 2) < abs(t - 0.5)
    return False


def _line_name_candidates(s: Pt, e: Pt, text: str) -> list[tuple[Pt, float]]:
    """Beside either visible end of a full line, the way the papers name one."""
    d = _unit((e[0] - s[0], e[1] - s[1]))
    n = (-d[1], d[0])
    half_w = text_width(text, POINT_FONT) / 2.0
    reach = half_w * abs(n[0]) + 0.5 * POINT_FONT * abs(n[1]) + 2.5
    out = []
    for end, inward, pen0 in ((e, (-d[0], -d[1]), 0.0), (s, d, 0.5)):
        for back in (10.0, 16.0, 24.0, 34.0):
            base = (end[0] + inward[0] * back, end[1] + inward[1] * back)
            for side in (1.0, -1.0):
                for extra in (0.0, 2.5):
                    rho = reach + extra
                    out.append(((base[0] + n[0] * side * rho, base[1] + n[1] * side * rho),
                                pen0 + 0.08 * back + 0.4 * extra + (0.3 if side < 0 else 0.0)))
    return out


def place_labels(spec: dict[str, Any]) -> None:
    """Fill in `labelOffsets`, each labelled angle's and line's `labelAt`, and
    the position of every `along` text, avoiding everything else drawn."""
    w, h = float(spec["width"]), float(spec["height"])
    P = {k: (float(v[0]), float(v[1])) for k, v in spec["points"].items()}
    hidden = set(spec.get("hidden") or [])
    names = {n: p for n, p in P.items() if n not in hidden}
    ink = [(a, b, tag, (min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])))
           for a, b, tag in strokes(spec)]
    dots = _dots(spec)
    fixed: list[Box] = []
    for t in spec.get("texts") or []:
        if not t.get("along"):
            fixed.append(text_box(t["x"], t["y"], t["text"], t.get("size", TEXT_FONT),
                                  t.get("anchor", "middle")))

    if names:
        cx = sum(p[0] for p in names.values()) / len(names)
        cy = sum(p[1] for p in names.values()) / len(names)
    else:
        cx, cy = w / 2, h / 2

    labels: list[_Label] = []
    for n, p in names.items():
        labels.append(_Label(f"pt:{n}", n, POINT_FONT, p, _point_candidates(p, (cx, cy), n)))
    for i, ln in enumerate(spec.get("lines") or []):
        if ln.get("label"):
            s, e = _line_ends(spec, ln)
            labels.append(_Label(f"ln:{i}", ln["label"], POINT_FONT, None,
                                 _line_name_candidates(s, e, ln["label"]),
                                 home={f"line:{ln['from']}{ln['to']}"}))
    for i, an in enumerate(spec.get("angles") or []):
        if not an.get("label"):
            continue
        c = P[an["at"]]
        a1, delta = arc_span(c, P[an["from"]], P[an["to"]], bool(an.get("reflex")))
        split = _ray_inside(c, a1, delta, ink)
        lab = _Label(f"an:{i}", an["label"], ANGLE_FONT, None,
                     _angle_candidates(c, an.get("r", 20.0), a1, delta, an["label"],
                                       split=split),
                     home={f"arc:{i}"})
        lab.split = split
        lab.origin = c
        lab.sector = (a1, delta)
        lab.rays = _rays_from(c, ink)
        labels.append(lab)
    for i, t in enumerate(spec.get("texts") or []):
        if t.get("along"):
            a, b = P[t["along"][0]], P[t["along"][1]]
            size = t.get("size", TEXT_FONT)
            cands = _along_candidates(a, b, (cx, cy), t["text"], size, t.get("alongT"))
            if not t.get("alongT"):
                cuts = _cuts(a, b, [p for n, p in names.items() if n not in t["along"]])
                if cuts:
                    # Well past any other spot: a length printed beside one
                    # part of a side reads as that part's.
                    cands = sorted(((c, p + (30.0 if _reads_as_part(_t_on(a, b, c), cuts) else 0.0))
                                    for c, p in cands), key=lambda cp: cp[1])
            labels.append(_Label(f"tx:{i}", t["text"], size, None, cands))

    fills = [[P[n] for n in fl["points"]] for fl in spec.get("fills") or []
             if all(n in P for n in fl["points"])]
    if fills:
        for lab in labels:
            if lab.key.startswith("tx:"):
                # A dimension printed inside the shaded region reads as a
                # measure *of* that region: „2” above the edge of a cut-out
                # became the height of the strip, not the width of the notch.
                lab.candidates = sorted(
                    ((c, p + (12.0 if any(_in_polygon(c, poly) for poly in fills) else 0.0))
                     for c, p in lab.candidates), key=lambda cp: cp[1])
    _place(labels, ink, dots, fixed, names, w, h)
    _pull_inside(spec, labels, P, dots, fixed, names, w, h)
    _hug_arcs(spec, labels, P, hidden, fixed)

    offsets: dict[str, list[float]] = {}
    for lab in labels:
        if lab.anchor is None:
            continue
        kind, _, ref = lab.key.partition(":")
        at = [round(lab.anchor[0], 2), round(lab.anchor[1], 2)]
        if kind == "pt":
            p = P[ref]
            offsets[ref] = [round(lab.anchor[0] - p[0], 2), round(lab.anchor[1] - p[1], 2)]
        elif kind == "an":
            spec["angles"][int(ref)]["labelAt"] = at
        elif kind == "ln":
            spec["lines"][int(ref)]["labelAt"] = at
        else:
            t = spec["texts"][int(ref)]
            t["x"], t["y"] = at
            t["anchor"] = "middle"
    spec["labelOffsets"] = offsets
    spec["labelsPlaced"] = True


# ─── coordinate grids ────────────────────────────────────────────────────────
# The grid renderer lays a grid out in pixels from its data ranges (GridView:
# cell 24, pad 22), so the same arithmetic is repeated here to place each point
# name. Always up and to the left, as it used to be, put the name of a point
# just below the origin on top of the „O”.

GRID_CELL, GRID_PAD = 24.0, 22.0
_GRID_OFFSETS = [(-10.0, -7.0), (10.0, -7.0), (-10.0, 17.0), (10.0, 17.0),
                 (-14.0, 5.0), (14.0, 5.0)]


def _grid_frame(scene: dict[str, Any]):
    (x0, x1), (y0, y1) = scene["xRange"], scene["yRange"]
    height = (y1 - y0) * GRID_CELL + GRID_PAD * 2
    width = (x1 - x0) * GRID_CELL + GRID_PAD * 2

    def sx(x: float) -> float:
        return GRID_PAD + (x - x0) * GRID_CELL

    def sy(y: float) -> float:
        return height - GRID_PAD - (y - y0) * GRID_CELL

    return sx, sy, width, height


#: Where „O” may go around the origin, most usual first.
_ORIGIN_OFFSETS = [(-10.0, 14.0), (10.0, 14.0), (-10.0, -6.0), (10.0, -6.0)]


def _grid_fixed(scene: dict[str, Any]):
    """Axes, the polygon, and the fixed texts every grid prints."""
    sx, sy, _, _ = _grid_frame(scene)
    (x0, x1), (y0, y1) = scene["xRange"], scene["yRange"]
    ink = [((sx(x0), sy(0)), (sx(x1) + 10, sy(0))), ((sx(0), sy(y0)), (sx(0), sy(y1) - 10))]
    pts = {p["name"]: (sx(p["x"]), sy(p["y"])) for p in scene.get("points", [])}
    poly = [pts[n] for n in scene.get("polygon") or [] if n in pts]
    if len(poly) > 1:
        ink += list(zip(poly, poly[1:] + poly[:1]))
    ox, oy = scene.get("originOffset") or _ORIGIN_OFFSETS[0]
    boxes = [text_box(sx(0) + ox, sy(0) + oy, "O", 11.0),
             text_box(sx(x1) + 6, sy(0) + 16, "x", 11.0),
             text_box(sx(0) - 12, sy(y1) - 6, "y", 11.0)]
    return ink, pts, boxes


def _place_origin(scene: dict[str, Any]) -> None:
    """Put „O” in the first corner of the origin that the figure leaves clear.

    It used to be fixed below and to the left, and a triangle whose side ran
    through (0; −0.5) was drawn straight through the letter.
    """
    sx, sy, _, _ = _grid_frame(scene)
    pts = {p["name"]: (sx(p["x"]), sy(p["y"])) for p in scene.get("points", [])}
    poly = [pts[n] for n in scene.get("polygon") or [] if n in pts]
    edges = list(zip(poly, poly[1:] + poly[:1])) if len(poly) > 1 else []
    best = None
    for rank, (dx, dy) in enumerate(_ORIGIN_OFFSETS):
        box = text_box(sx(0) + dx, sy(0) + dy, "O", 11.0)
        clear = min((seg_box_dist(a, b, box) - INK for a, b in edges), default=20.0)
        dots = min((_pt_box(q, box) - 2.6 for q in pts.values()), default=20.0)
        inside = len(poly) > 2 and _in_polygon(((box[0] + box[2]) / 2, (box[1] + box[3]) / 2), poly)
        score = min(clear, 3.0) + min(dots, 3.0) - 0.5 * rank - (2.0 if inside else 0.0)
        if clear < MIN_CLEAR:
            score -= 20.0
        if dots < MIN_CLEAR:
            score -= 20.0
        if best is None or score > best[0]:
            best = (score, [dx, dy])
    if best[1] != list(_ORIGIN_OFFSETS[0]):
        scene["originOffset"] = best[1]


def place_grid_labels(scene: dict[str, Any]) -> None:
    """Choose, for every plotted point, the corner its name goes in."""
    _place_origin(scene)
    ink, pts, fixed = _grid_fixed(scene)
    poly = [pts[n] for n in scene.get("polygon") or [] if n in pts]
    centre = (sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly)) \
        if len(poly) > 2 else None
    placed: list[Box] = []
    offsets: dict[str, list[float]] = {}
    for name, (px, py) in pts.items():
        best = None
        for rank, (dx, dy) in enumerate(_GRID_OFFSETS):
            box = text_box(px + dx, py + dy, name, POINT_FONT)
            clear = min((seg_box_dist(a, b, box) - INK for a, b in ink), default=20.0)
            gap = min((box_gap(box, o) for o in fixed + placed), default=20.0)
            dots = min((_pt_box(q, box) - 2.6 for n, q in pts.items()), default=20.0)
            score = min(clear, 3.0) + min(gap, 3.0) + min(dots, 3.0) - 0.5 * rank
            if centre is not None:
                # A vertex's name goes on the outside of the shaded triangle,
                # as in a figure: „A” set inside, between A and the origin,
                # sat nearer the „O” than its own corner looked.
                out = _unit((px - centre[0], py - centre[1]))
                off = _unit((dx, dy))
                score += 1.0 * (out[0] * off[0] + out[1] * off[1])
                mid = ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)
                if _in_polygon(mid, poly):
                    score -= 2.0
            if clear < MIN_CLEAR:
                score -= 20.0
            if gap < MIN_CLEAR:
                score -= 30.0
            if dots < MIN_CLEAR:
                score -= 20.0
            if best is None or score > best[0]:
                best = (score, [dx, dy], box)
        offsets[name] = best[1]
        placed.append(best[2])
    scene["labelOffsets"] = offsets


def grid_label_problems(scene: dict[str, Any], *, tol: float = 0.3) -> list[str]:
    ink, pts, fixed = _grid_fixed(scene)
    offs = scene.get("labelOffsets") or {}
    boxes = []
    for name, (px, py) in pts.items():
        dx, dy = offs.get(name, (-10.0, -7.0))
        boxes.append((name, text_box(px + dx, py + dy, name, POINT_FONT)))
    out = []
    for p in scene.get("points", []):
        if p["x"] == 0 and p["y"] == 0:
            out.append(f"grid point {p['name']} is on the origin, which is already called O")
    origin = fixed[0]
    if any(seg_box_dist(a, b, origin) < INK - tol for a, b in ink[2:]):
        out.append("grid label O sits on a side of the figure")
    if any(_pt_box(q, origin) < 2.6 - tol for q in pts.values()):
        out.append("grid label O covers a plotted point")
    for i, (name, box) in enumerate(boxes):
        if any(seg_box_dist(a, b, box) < INK - tol for a, b in ink):
            out.append(f"grid label {name} sits on a line")
        if any(box_gap(box, o) < -tol for o in fixed):
            out.append(f"grid label {name} overlaps an axis label")
        for other, obox in boxes[i + 1:]:
            if box_gap(box, obox) < -tol:
                out.append(f"grid labels {name} and {other} overlap")
    return out


# ─── reporting ───────────────────────────────────────────────────────────────

def label_boxes(spec: dict[str, Any]) -> list[tuple[str, Box]]:
    """Every text box on a figure, as the renderer will set it."""
    P = spec["points"]
    hidden = set(spec.get("hidden") or [])
    out: list[tuple[str, Box]] = []
    offs = spec.get("labelOffsets") or {}
    for n, p in P.items():
        if n in hidden:
            continue
        dx, dy = offs.get(n, (0.0, -8.0))
        out.append((f"point {n}", text_box(p[0] + dx, p[1] + dy, n, POINT_FONT)))
    for an in spec.get("angles") or []:
        if an.get("label") and an.get("labelAt"):
            x, y = an["labelAt"]
            out.append((f"angle {an['label']} at {an['at']}", text_box(x, y, an["label"], ANGLE_FONT)))
    for t in spec.get("texts") or []:
        out.append((f"text {t['text']}", text_box(t["x"], t["y"], t["text"],
                                                  t.get("size", TEXT_FONT), t.get("anchor", "middle"))))
    for i, b in enumerate(line_label_boxes(spec)):
        out.append((f"line label {i}", b))
    return out


def label_problems(spec: dict[str, Any], *, tol: float = 0.3) -> list[str]:
    """Labels that touch ink, touch each other, or leave the canvas."""
    if spec.get("kind") != "figure":
        return []
    w, h = float(spec["width"]), float(spec["height"])
    ink = strokes(spec)
    dots = _dots(spec)
    boxes = label_boxes(spec)
    problems = []
    for i, (what, box) in enumerate(boxes):
        for a, b, tag in ink:
            if seg_box_dist(a, b, box) < INK - tol:
                problems.append(f"{what} sits on {tag}")
                break
        for n, p in dots:
            if _pt_box(p, box) < DOT_R - tol:
                problems.append(f"{what} covers the dot at {n}")
                break
        for what2, box2 in boxes[i + 1:]:
            if box_gap(box, box2) < -tol:
                problems.append(f"{what} overlaps {what2}")
        if box[0] < -tol or box[1] < -tol or box[2] > w + tol or box[3] > h + tol:
            problems.append(f"{what} runs off the canvas")
    problems.extend(_separated_labels(spec))
    return problems


def _separated_labels(spec: dict[str, Any]) -> list[str]:
    """Labels cut off from the point or vertex they belong to by another line."""
    P = {k: (float(v[0]), float(v[1])) for k, v in spec["points"].items()}
    straight = [(a, b) for a, b, tag in strokes(spec) if tag.split(":")[0] in ("seg", "line", "ray")]
    hidden = set(spec.get("hidden") or [])
    offs = spec.get("labelOffsets") or {}
    pairs: list[tuple[str, Pt, Pt]] = []
    for n, p in P.items():
        if n in hidden or n not in offs:
            continue
        box = text_box(p[0] + offs[n][0], p[1] + offs[n][1], n, POINT_FONT)
        pairs.append((f"point {n}", p, ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)))
    for an in spec.get("angles") or []:
        if an.get("label") and an.get("labelAt"):
            box = text_box(an["labelAt"][0], an["labelAt"][1], an["label"], ANGLE_FONT)
            pairs.append((f"angle {an['label']} at {an['at']}", P[an["at"]],
                          ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)))
    out = []
    for what, origin, centre in pairs:
        for a, b in straight:
            if _pt_seg(origin, a, b) >= 1.0 and _segs_cross(origin, centre, a, b):
                out.append(f"{what} is across a line from what it labels")
                break
    ink = [(a, b, tag, None) for a, b, tag in strokes(spec)]
    for an in spec.get("angles") or []:
        if not (an.get("label") and an.get("labelAt")):
            continue
        c = P[an["at"]]
        rays = _rays_from(c, ink)
        if len(rays) < 3:
            continue
        box = text_box(an["labelAt"][0], an["labelAt"][1], an["label"], ANGLE_FONT)
        centre = ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)
        sector = arc_span(c, P[an["from"]], P[an["to"]], bool(an.get("reflex")))
        if _in_neighbour_angle(c, centre, sector, rays):
            out.append(f"angle {an['label']} at {an['at']} sits in a neighbouring angle")
    for an in spec.get("angles") or []:
        if not (an.get("label") and an.get("labelAt")):
            continue
        c = P[an["at"]]
        box = text_box(an["labelAt"][0], an["labelAt"][1], an["label"], ANGLE_FONT)
        centre = ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)
        if _in_sector(c, centre, arc_span(c, P[an["from"]], P[an["to"]], bool(an.get("reflex")))):
            continue
        own = _pt_box(c, box)
        for n, p in P.items():
            if n not in hidden and n != an["at"] and _pt_box(p, box) < own:
                out.append(f"angle {an['label']} at {an['at']} sits outside its arms, "
                           f"nearer {n} than its own vertex")
                break
    for t in spec.get("texts") or []:
        if not t.get("along") or t.get("alongT"):
            continue
        u, v = t["along"]
        a, b = P[u], P[v]
        cuts = _cuts(a, b, [p for n, p in P.items() if n not in hidden and n not in (u, v)])
        if cuts and _reads_as_part(_t_on(a, b, (t["x"], t["y"])), cuts):
            out.append(f"text {t['text']} for {u}{v} is printed beside one part of it")
    return out


#: An arc nearer than this to another mark runs into it; a named point needs
#: a little more, for its dot.
MIN_ARC_CLEAR = 1.5
MIN_ARC_POINT = 4.0
#: What the placer keeps between marks it moves or resizes itself — arcs grown
#: toward their values, ticks slid along their sides. The verifier's minimum
#: above is "not touching"; at 4 units (≈6 px) an arc ending beside a tick
#: still read as one mark.
MARK_BERTH = 5.0


def _seg_seg(a: Pt, b: Pt, c: Pt, d: Pt) -> float:
    if _segs_cross(a, b, c, d):
        return 0.0
    return min(_pt_seg(a, c, d), _pt_seg(b, c, d), _pt_seg(c, a, b), _pt_seg(d, a, b))


def arc_problems(spec: dict[str, Any]) -> list[str]:
    """Angle arcs that run into a named point or another vertex's marks.

    ∠HCB was drawn at radius 22 with H only 21 from C, so its arc went through
    H and into the right-angle square there: the arc then no longer ends on
    the arm it measures from, and the square no longer reads as square.
    Concentric arcs at one vertex are left alone — two angles sharing an arm
    is exactly how the papers draw them.
    """
    if spec.get("kind") != "figure":
        return []
    P = {k: (float(v[0]), float(v[1])) for k, v in spec["points"].items()}
    hidden = set(spec.get("hidden") or [])
    ink = strokes(spec)
    out: list[str] = []
    for i in range(len(spec.get("angles") or [])):
        out.extend(_arc_clashes(spec, i, P, hidden, ink))
    out.extend(_tick_clashes(P, hidden, ink))
    return out


def _tick_clashes(P: dict[str, Pt], hidden: set, ink: list[tuple[Pt, Pt, str]],
                  only: str | None = None, margin: float = MIN_ARC_CLEAR) -> list[str]:
    """Ticks that run into a right-angle mark, another tick, or a named point.

    The tick halfway along AM landed on the foot P of a height whenever AP
    came out near AM/2, and the equal-length mark and the right angle read
    as one scribble. Arcs are checked against ticks in `_arc_clashes`.
    `only` restricts the check to the ticks with that tag.
    """
    out: list[str] = []
    ticks = [(a, b, tag) for a, b, tag in ink if tag.startswith("tick:")
             and (only is None or tag == only)]
    for a, b, tag in ticks:
        side = tag[5:]
        for c, d, other in ink:
            kind = other.split(":")[0]
            if other == tag or kind not in ("right", "tick", "arc"):
                continue
            if kind == "arc" and only is None:
                continue          # reported from the arc's side
            if _seg_seg(a, b, c, d) < margin:
                out.append(f"tick on {side} runs into {other}")
                break
        for n, p in P.items():
            if n in hidden or n in side:
                continue
            if _pt_seg(p, a, b) < MIN_ARC_POINT + (margin - MIN_ARC_CLEAR):
                out.append(f"tick on {side} runs into point {n}")
                break
    return out


def fit_ticks(spec: dict[str, Any]) -> None:
    """Slide a tick along its segment when the middle is taken.

    The middle of a side is where a midpoint, a cevian's foot or another
    side's tick tends to be. The marks say only "these are equal", so off
    the middle they say the same thing, and the papers draw them there too
    when the middle is busy.
    """
    ticks = spec.get("ticks") or []
    if not ticks:
        return
    P = {k: (float(v[0]), float(v[1])) for k, v in spec["points"].items()}
    hidden = set(spec.get("hidden") or [])
    for tk in ticks:
        if "at" in tk:
            continue               # placed by the template on purpose
        tag = f"tick:{tk['from']}{tk['to']}"
        # The middle if it has room; otherwise the spot with the most room,
        # not merely the first that clears: squeezed between a right-angle
        # mark and the next foot along, a tick that clears both still reads
        # as part of the clutter.
        best = (-1.0, 0.5)
        for rank, t in enumerate((0.5, 0.4, 0.6, 0.33, 0.67, 0.27, 0.73, 0.2, 0.8)):
            tk["at"] = t
            room = _tick_room(P, hidden, strokes(spec), tag) - 0.4 * rank
            if rank == 0 and room >= 2 * MARK_BERTH:
                best = (room, t)
                break
            if room > best[0]:
                best = (room, t)
        tk["at"] = best[1]
        if tk["at"] == 0.5:
            del tk["at"]


def _tick_room(P: dict[str, Pt], hidden: set, ink: list[tuple[Pt, Pt, str]], tag: str) -> float:
    """How far a tick is from the nearest other mark or named point."""
    side = tag[5:]
    own = [(a, b) for a, b, t in ink if t == tag]
    room = 20.0
    for c, d, other in ink:
        if other == tag or other.split(":")[0] not in ("right", "tick", "arc"):
            continue
        room = min(room, min(_seg_seg(a, b, c, d) for a, b in own))
    for n, p in P.items():
        if n in hidden or n in side:
            continue
        room = min(room, min(_pt_seg(p, a, b) for a, b in own) - (MIN_ARC_POINT - MIN_ARC_CLEAR))
    return room


def _arc_clashes(spec: dict[str, Any], i: int, P: dict[str, Pt], hidden: set,
                 ink: list[tuple[Pt, Pt, str]], margin: float = MIN_ARC_CLEAR) -> list[str]:
    angles = spec["angles"]
    an = angles[i]
    c = P[an["at"]]
    r = float(an.get("r", 20.0))
    sector = arc_span(c, P[an["from"]], P[an["to"]], bool(an.get("reflex")))
    own = [(a, b) for a, b, tag in ink if tag == f"arc:{i}"]
    what = f"arc of the angle at {an['at']}"
    out: list[str] = []
    for n, p in P.items():
        if n in hidden or n == an["at"]:
            continue
        near = min(_pt_seg(p, a, b) for a, b in own)
        if near < MIN_ARC_POINT or (math.dist(c, p) < r and _in_sector(c, p, sector, 0.05)):
            out.append(f"{what} runs into point {n}")
            break
    for a, b, tag in ink:
        kind, _, ref = tag.partition(":")
        if kind == "arc":
            if angles[int(ref)]["at"] == an["at"]:
                continue
        elif kind == "right":
            if ref == an["at"]:
                continue
        elif kind != "tick":
            continue
        if any(_seg_seg(s, t, a, b) < margin for s, t in own):
            out.append(f"{what} runs into {tag}")
            break
    return out


#: The smallest arc `fit_arcs` will shrink to; anything tighter is a dot with
#: a tail. Every further arc of a multi-arc mark is drawn 4 units inside.
MIN_ARC_R = 12.0


def fit_arcs(spec: dict[str, Any]) -> None:
    """Shrink every arc that runs into another mark, a unit at a time.

    Templates pick a radius per angle before the figure is posed and fitted,
    so a short arm — the foot of a height a few units from the vertex, two
    zig-zag vertices close together — can leave the arc reaching into the
    right-angle square or the neighbouring arc. The arcs in a clash shrink
    in turn, so neither is squeezed alone. What still clashes at the floor
    is left for the verifier to reject.
    """
    angles = spec.get("angles") or []
    if not angles:
        return
    P = {k: (float(v[0]), float(v[1])) for k, v in spec["points"].items()}
    hidden = set(spec.get("hidden") or [])
    for _ in range(40):
        ink = strokes(spec)
        moved = False
        for i, an in enumerate(angles):
            floor = MIN_ARC_R + 4.0 * ((an.get("arcs", 1) or 1) - 1)
            r = float(an.get("r", 20.0))
            if r - 1.0 >= floor and _arc_clashes(spec, i, P, hidden, ink):
                an["r"] = r - 1.0
                moved = True
        if not moved:
            break
