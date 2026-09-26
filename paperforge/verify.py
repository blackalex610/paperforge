"""The gate every item and every paper has to clear.

Nothing reaches a student that has not passed through here. The checks are
split in two because the failures are different in kind:

  * ``check_item`` catches a template producing something malformed — four
    options that are not four, a key that is not one of them, a figure that
    references a point it never placed. These are bugs, and they fail loudly.
  * ``check_paper`` catches an *assembly* that is individually fine but
    collectively wrong — the same template twice, every answer on Б, a points
    total that is not 65.

Two checks look pedantic and are not:

*Latin letters in the option key.* A Latin "B" beside a Cyrillic "В" is the
single most common way a generated Bulgarian paper gives itself away, and it
silently breaks answer comparison at grading time.

*Cyrillic inside ``$…$``.* The router's ``_normalize_math_delimiters`` strips
Cyrillic out of math spans to work around KaTeX noglyph boxes. A stem that puts
Bulgarian inside the math therefore arrives at the student with words missing.
The fix is to never write it, so it is an error here rather than a surprise
there.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Iterable, Sequence

from paperforge.blueprints import Blueprint, Slot
from paperforge.distractors import OPTION_LETTERS
from paperforge.figure_labels import arc_problems, grid_label_problems, label_problems, strokes
from paperforge.registry import GeneratedItem
from paperforge.scene import (
    MIN_ANGLE_DEG,
    MIN_BOX_MARGIN,
    SCENE_KINDS,
    SCHEMATIC_SHAPES,
    SOLID_SHAPES,
    geometry_hash,
)

_CYRILLIC = re.compile(r"[А-Яа-яЁё]")
_MATH_SPAN = re.compile(r"\$([^$]*)\$")
#: Unfilled-template markers. Deliberately NOT `\{\w*\}` — LaTeX is full of
#: legitimate braces (`\frac{1}{5}`, `x^{2}`), so that pattern flags every
#: correct stem. Empty braces, on the other hand, are neither valid LaTeX nor
#: anything a template means to emit.
_PLACEHOLDER = re.compile(r"\{\s*\}|\bTODO\b|\bFIXME\b|\bNone\b|\bnan\b")
# "лв." / "лева" / "стотинки" as words — not the "лв" inside "допълват"
_LEVA = re.compile(r"(?<![А-Яа-я])(лв\.?|лева|стотинк\w*)(?![А-Яа-я])")
# a digit, the decimal comma (plain or KaTeX's {,}), then three or more digits
_LONG_DECIMAL = re.compile(r"\d(?:\{,\}|,)\d{3,}")
_LATIN_OPTION = re.compile(r"^[ABCD]$")
#: A LaTeX command, or an escaped space, left outside `$…$`.
_LATEX_COMMAND = re.compile(r"\\(?:[A-Za-z]+|[ ,;!])")


class VerificationError(ValueError):
    """An item or a paper failed a check it must not fail."""


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def merge(self, other: "Report") -> "Report":
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        return self

    def raise_if_failed(self, context: str) -> None:
        if self.errors:
            raise VerificationError(f"{context}: " + "; ".join(self.errors))


# ─── item-level ──────────────────────────────────────────────────────────────

def check_item(item: GeneratedItem, slot: Slot) -> Report:
    r = Report()

    if item.kind != slot.kind:
        r.errors.append(f"kind {item.kind!r} does not match slot kind {slot.kind!r}")
    if item.total_points != slot.total_points:
        r.errors.append(
            f"points {item.points} sum to {item.total_points}, slot wants {slot.total_points}")

    _check_text(item.stem, "stem", r)
    if not _CYRILLIC.search(item.stem):
        r.errors.append("stem contains no Cyrillic — an NVO stem is written in Bulgarian")

    if item.kind == "mc":
        _check_multiple_choice(item, r)
    else:
        _check_written(item, slot, r)

    _check_parts(item, slot, r)
    _check_scene(item, slot, r)
    return r


def _check_text(text: str, label: str, r: Report) -> None:
    if not text or not text.strip():
        r.errors.append(f"{label} is empty")
        return
    if text.count("$") % 2:
        r.errors.append(f"{label} has an unbalanced math delimiter")
    if _PLACEHOLDER.search(text):
        r.errors.append(f"{label} still contains a placeholder: {_PLACEHOLDER.search(text).group()!r}")
    if _LEVA.search(text):
        r.errors.append(
            f"{label} prices in leva — Bulgaria has used the euro since 1 Jan 2026 and "
            f"the June 2026 paper prices in „евро”")
    for span in _MATH_SPAN.findall(text):
        if _CYRILLIC.search(span):
            r.errors.append(
                f"{label} has Cyrillic inside a math span (\"{span[:40]}\") — it will be "
                f"stripped before the student sees it")
    outside = _MATH_SPAN.sub("", text)
    if _LATEX_COMMAND.search(outside):
        r.errors.append(
            f"{label} has LaTeX outside a math span "
            f"(\"{_LATEX_COMMAND.search(outside).group()}\") — it renders as literal text")


def _check_multiple_choice(item: GeneratedItem, r: Report) -> None:
    options = item.options or []
    if len(options) != 4:
        r.errors.append(f"expected 4 options, got {len(options)}")
        return
    for i, opt in enumerate(options):
        _check_text(opt, f"option {OPTION_LETTERS[i] if i < 4 else i}", r)
        if _LONG_DECIMAL.search(opt):
            # 13 papers, 2015–2026: no option carries three decimals. One that
            # does is almost always a repeating value printed rounded (1/48 as
            # „0,021"), which is not an answer anyone can compute to.
            r.errors.append(f"option {opt!r} has more than two decimal places")
    if len(set(options)) != len(options):
        dupes = [o for o, n in Counter(options).items() if n > 1]
        r.errors.append(f"duplicate options: {dupes}")

    key = item.correct_answer
    if not isinstance(key, str):
        r.errors.append(f"multiple-choice key must be a letter, got {type(key).__name__}")
        return
    if _LATIN_OPTION.match(key):
        r.errors.append(f"key {key!r} is a Latin letter — NVO options are Cyrillic А/Б/В/Г")
    elif key not in OPTION_LETTERS:
        r.errors.append(f"key {key!r} is not one of {OPTION_LETTERS}")


def _check_written(item: GeneratedItem, slot: Slot, r: Report) -> None:
    if item.options:
        r.errors.append(f"{item.kind} item must not carry options")
    answers = item.correct_answer
    if slot.parts > 1:
        if not isinstance(answers, list):
            r.errors.append(f"{slot.parts}-part item needs a list of answers")
        elif len(answers) != slot.parts:
            r.errors.append(f"expected {slot.parts} answers, got {len(answers)}")
    elif isinstance(answers, list):
        if not answers:
            r.errors.append("answer list is empty")
    elif not str(answers).strip():
        r.errors.append("answer is empty")


def _check_parts(item: GeneratedItem, slot: Slot, r: Report) -> None:
    if slot.parts > 1:
        if not item.parts:
            r.errors.append(f"slot has {slot.parts} parts but the item declares none")
        elif len(item.parts) != slot.parts:
            r.errors.append(f"item declares {len(item.parts)} parts, slot wants {slot.parts}")
        else:
            for i, part in enumerate(item.parts):
                _check_text(part, f"part {i + 1}", r)
    elif item.parts and item.kind != "open":
        r.errors.append("single-part slot must not declare sub-parts")


def _check_scene(item: GeneratedItem, slot: Slot, r: Report) -> None:
    if slot.diagram and item.scene is None:
        r.errors.append("slot expects a figure but the item produced none")
    if item.scene is None:
        return

    kind = item.scene.get("kind")
    if kind not in SCENE_KINDS:
        r.errors.append(f"unknown scene kind {kind!r}")
        return
    if not item.scene.get("aria"):
        r.warnings.append("figure has no aria description")

    if kind == "solid" and item.scene.get("shape") not in SOLID_SHAPES:
        r.errors.append(f"unknown solid shape {item.scene.get('shape')!r}")
    if kind == "schematic" and item.scene.get("shape") not in SCHEMATIC_SHAPES:
        r.errors.append(f"unknown schematic shape {item.scene.get('shape')!r}")
    _check_scene_text_is_plain(item.scene, r)
    if kind == "figure":
        _check_figure(item.scene, r)
    if kind == "bars":
        _check_bars(item.scene, r)
    if kind == "linegraph":
        _check_linegraph(item.scene, r)
    if kind == "grid":
        for problem in grid_label_problems(item.scene):
            r.errors.append(f"label clash: {problem}")


def _check_scene_text_is_plain(scene: dict, r: Report) -> None:
    """Scene labels are drawn as SVG <text>, so LaTeX in them renders literally.

    A label written as "$12$" shows the dollar signs to the student. The table
    scene is the exception — its cells go through the normal text renderer, so
    math markup there is correct.
    """
    if scene.get("kind") == "table":
        return

    suspect: list[str] = [t.get("text", "") for t in scene.get("texts", [])]
    suspect += [str(a.get("label") or "") for a in scene.get("angles", [])]
    suspect += [str(ln.get("label") or "") for ln in scene.get("lines", [])]
    suspect += [str(v) for v in (scene.get("labels") or {}).values()]

    for text in suspect:
        if "$" in text or "\\frac" in text or "\\sphericalangle" in text:
            r.errors.append(f"figure label {text!r} contains markup that will render literally")


def _check_figure(scene: dict, r: Report) -> None:
    """Every mark must reference a point the figure actually placed."""
    names = set(scene.get("points", {}))
    if not names:
        r.errors.append("figure has no points")
        return

    def ref(value: str | None, where: str) -> None:
        if value is not None and value not in names:
            r.errors.append(f"{where} references undefined point {value!r}")

    for seg in scene.get("segments", []):
        ref(seg.get("from"), "segment"); ref(seg.get("to"), "segment")
    for ray in scene.get("rays", []):
        ref(ray.get("from"), "ray"); ref(ray.get("to"), "ray")
    for line in scene.get("lines", []):
        ref(line.get("from"), "line"); ref(line.get("to"), "line")
    for ang in scene.get("angles", []):
        for k in ("at", "from", "to"):
            ref(ang.get(k), "angle")
    for ang in scene.get("rightAngles", []):
        for k in ("at", "from", "to"):
            ref(ang.get(k), "right angle")
    for tick in scene.get("ticks", []):
        ref(tick.get("from"), "tick"); ref(tick.get("to"), "tick")

    _check_inside_box(scene, r)
    _check_named_points_apart(scene, r)
    _check_label_clearance(scene, r)
    for problem in arc_problems(scene):
        r.errors.append(f"mark clash: {problem}")
    squares = {ra.get("at") for ra in scene.get("rightAngles", [])}
    for ang in scene.get("angles", []):
        if ang.get("fill") and ang.get("at") in squares:
            # The shaded sector covers the square at its own vertex.
            r.errors.append(f"figure shades an angle at {ang.get('at')} on top of the "
                            f"right-angle square there")
        if (ang.get("label") or "").strip() == "90°":
            # A right angle is marked with the square, as in every paper; an
            # arc labelled „90°” reads as a measured angle that happens to be 90.
            r.errors.append(f"figure marks the right angle at {ang.get('at')} with an arc "
                            f"and „90°” instead of the right-angle square")
    _check_angles_are_legible(scene, r)
    _check_marks_sit_on_drawn_lines(scene, r)
    _check_points_not_nearly_on_lines(scene, r)


def _check_inside_box(scene: dict, r: Report) -> None:
    """Anything past the viewBox is simply not drawn, and nothing says so."""
    width = scene.get("width", 0)
    height = scene.get("height", 0)
    for name, (x, y) in scene.get("points", {}).items():
        margin = min(x, y, width - x, height - y)
        if margin < MIN_BOX_MARGIN:
            r.errors.append(
                f"point {name} at ({x}, {y}) is {margin:.1f} from the edge of the "
                f"{width}×{height} box, under the {MIN_BOX_MARGIN} minimum")


#: Two named points closer than this are one blot with two names.
MIN_POINT_GAP = 8.0


def _check_named_points_apart(scene: dict, r: Report) -> None:
    """Two named points drawn a hair apart cannot be told apart.

    The label placer can always find two separate spots for the names, so
    this is not a label check: it is the points themselves.
    """
    hidden = set(scene.get("hidden", ()))
    named = sorted((n, p) for n, p in scene.get("points", {}).items() if n not in hidden)
    for i, (a, pa) in enumerate(named):
        for b, pb in named[i + 1:]:
            if math.dist(pa, pb) < MIN_POINT_GAP:
                r.errors.append(
                    f"points {a} and {b} are drawn {math.dist(pa, pb):.1f} apart — "
                    f"on top of each other")


def _check_label_clearance(scene: dict, r: Report) -> None:
    """No text may touch a stroke, a dot, another text, or the canvas edge.

    This used to measure the distance between label *centres* against a fixed
    22-unit gap. That caught two names printed on top of each other and missed
    everything else: a name printed across a line was invisible to it, which is
    how „H” shipped on top of the altitude it names in every figure that drew
    one. The text boxes are now checked against the ink itself — see
    ``figure_labels``.
    """
    for problem in label_problems(scene):
        r.errors.append(f"label clash: {problem}")


def _on_stroke(v: tuple, d: tuple, ink: list) -> bool:
    """Is there a drawn stroke leaving point v in direction d?"""
    for a, b in ink:
        ab = (b[0] - a[0], b[1] - a[1])
        n = math.hypot(*ab)
        if n < 1e-9:
            continue
        u = (ab[0] / n, ab[1] / n)
        # v must lie on the stroke's line, and the stroke must run along d.
        if abs((v[0] - a[0]) * u[1] - (v[1] - a[1]) * u[0]) > 0.6:
            continue
        if abs(u[0] * d[1] - u[1] * d[0]) > 0.02:
            continue
        # A short step from v along d has to land inside the stroke.
        probe = (v[0] + d[0] * 3.0, v[1] + d[1] * 3.0)
        t = (probe[0] - a[0]) * u[0] + (probe[1] - a[1]) * u[1]
        if -0.6 <= t <= n + 0.6:
            return True
    return False


def _straight_ink(scene: dict) -> list:
    """Segments, full lines and rays, as the renderer extends them."""
    return [(a, b) for a, b, tag in strokes(scene)
            if tag.split(":")[0] in ("seg", "line", "ray")]


def _check_marks_sit_on_drawn_lines(scene: dict, r: Report) -> None:
    """An angle arc, a right-angle mark or a tick drawn against nothing is wrong.

    The arc of an angle is drawn between two arms, and both arms have to be
    drawn — otherwise the mark is at the wrong vertex. That is not hypothetical:
    three templates passed the vertex in the middle, the way ∠BAC is written,
    to a helper that takes it first, and printed the angle at A on B, against a
    side that was never drawn, for as long as they existed.
    """
    pts = {k: tuple(v) for k, v in scene.get("points", {}).items()}
    ink = _straight_ink(scene)

    def arm(at: str, to: str) -> tuple:
        v, p = pts[at], pts[to]
        n = math.dist(v, p)
        return v, ((p[0] - v[0]) / n, (p[1] - v[1]) / n) if n else (0.0, 0.0)

    for kind, marks in (("angle", scene.get("angles", [])),
                        ("right angle", scene.get("rightAngles", []))):
        for m in marks:
            if not all(m.get(k) in pts for k in ("at", "from", "to")):
                continue
            for end in ("from", "to"):
                v, d = arm(m["at"], m[end])
                if not _on_stroke(v, d, ink):
                    r.errors.append(
                        f"{kind} at {m['at']} is drawn against {m['at']}{m[end]}, "
                        f"which is not a drawn line")
    for t in scene.get("ticks", []):
        a, b = t.get("from"), t.get("to")
        if a in pts and b in pts:
            v, d = arm(a, b)
            if not _on_stroke(v, d, ink):
                r.errors.append(f"tick on {a}{b}, which is not a drawn segment")


def _check_points_not_nearly_on_lines(scene: dict, r: Report) -> None:
    """A named point a hair off a line reads as a point that was meant to be on it.

    The parallel-line items put B at a fixed height while the lines through it
    were sampled, so B floated up to 16 units off line b, with its angle arc
    hanging in empty space. That case is caught more precisely by
    `_check_marks_sit_on_drawn_lines`, since B's arc was drawn against line b;
    this catches the unmarked version. Four units (≈ 6 px) is where a point
    reads as ambiguous — on the line, or not? A real construction may pass a
    line a little further from a point than that, and it is drawn as it is.
    """
    pts = scene.get("points", {})
    hidden = set(scene.get("hidden", ()))
    ink = _straight_ink(scene)
    for name, p in pts.items():
        if name in hidden:
            continue
        for a, b in ink:
            ab = (b[0] - a[0], b[1] - a[1])
            n = math.hypot(*ab)
            if n < 1e-9:
                continue
            t = ((p[0] - a[0]) * ab[0] + (p[1] - a[1]) * ab[1]) / (n * n)
            if not 0.02 < t < 0.98:
                continue
            off = abs((p[0] - a[0]) * ab[1] - (p[1] - a[1]) * ab[0]) / n
            if 0.8 < off < 4.0:
                r.errors.append(
                    f"point {name} is {off:.1f} off a drawn line — on it, or clearly away")
                break


def _check_angles_are_legible(scene: dict, r: Report) -> None:
    """An arc across 4° is a smudge — the student cannot tell what is marked."""
    points = scene.get("points", {})
    for ang in scene.get("angles", []):
        if ang.get("reflex"):
            continue  # the drawn sweep is the 360° complement; not this check
        try:
            at, frm, to = (points[ang[k]] for k in ("at", "from", "to"))
        except KeyError:
            continue  # undefined point — already reported above
        d1 = (frm[0] - at[0], frm[1] - at[1])
        d2 = (to[0] - at[0], to[1] - at[1])
        n1, n2 = math.hypot(*d1), math.hypot(*d2)
        if not n1 or not n2:
            r.errors.append(f"angle at {ang['at']} has a zero-length arm")
            continue
        cos = max(-1.0, min(1.0, (d1[0] * d2[0] + d1[1] * d2[1]) / (n1 * n2)))
        drawn = math.degrees(math.acos(cos))
        if drawn < MIN_ANGLE_DEG:
            r.errors.append(
                f"angle at {ang['at']} is drawn at {drawn:.1f}°, under the "
                f"{MIN_ANGLE_DEG}° legibility minimum")


def _check_bars(scene: dict, r: Report) -> None:
    cats = scene.get("categories", [])
    for series in scene.get("series", []):
        if len(series.get("values", [])) != len(cats):
            r.errors.append(
                f"series {series.get('name')!r} has {len(series.get('values', []))} values "
                f"for {len(cats)} categories")
    y_max = scene.get("yMax", 0)
    step = scene.get("yStep") or 0
    for series in scene.get("series", []):
        for v in series.get("values", []):
            if v > y_max:
                r.errors.append(f"bar value {v} exceeds the axis maximum {y_max}")
            # A bar the student must read has to end on a gridline, or exactly
            # halfway between two. 36 on an axis ruled every 5 can only be
            # guessed, and a guess is not what the item is testing.
            if step and not _on_grid(v, step / 2):
                r.errors.append(f"bar value {v} ends between the gridlines (step {step})")


def _on_grid(value: float, step: float) -> bool:
    k = value / step
    return abs(k - round(k)) < 1e-6


def _check_linegraph(scene: dict, r: Report) -> None:
    """Every corner of a plotted line must sit on a grid crossing.

    The journey items ask when the rest started and how long it lasted; a
    corner at 9 min on a grid ruled every 5 min cannot be read.
    """
    xs = scene.get("xGridStep") or scene.get("xStep") or 0
    ys = scene.get("yStep") or 0
    for series in scene.get("series", []):
        for x, y in series.get("points", []):
            if (xs and not _on_grid(x, xs)) or (ys and not _on_grid(y, ys)):
                r.errors.append(f"graph corner ({x:g}; {y:g}) is off the grid")


# ─── paper-level ─────────────────────────────────────────────────────────────

#: How far the А/Б/В/Г counts may drift from uniform before we rebalance.
#: 2022 shipped 8 of 18 on Б, which is the kind of thing a student notices.
LETTER_TOLERANCE = 2


def check_paper(items: Sequence[GeneratedItem], slots: Sequence[Slot],
                blueprint: Blueprint | None = None) -> Report:
    r = Report()

    if len(items) != len(slots):
        r.errors.append(f"{len(items)} items for {len(slots)} slots")
        return r

    for item, slot in zip(items, slots):
        r.merge(check_item(item, slot))

    total = sum(i.total_points for i in items)
    expected = sum(s.total_points for s in slots)
    if total != expected:
        r.errors.append(f"paper totals {total} points, slots want {expected}")

    codes = [i.template_code for i in items if i.template_code]
    repeated = [c for c, n in Counter(codes).items() if n > 1]
    if repeated:
        r.errors.append(f"template used more than once: {repeated}")

    sigs = [i.signature for i in items if i.signature]
    dup_sigs = [s for s, n in Counter(sigs).items() if n > 1]
    if dup_sigs:
        r.errors.append(f"identical parameter draw appears twice: {dup_sigs}")

    stems = [i.stem for i in items]
    dup_stems = [s for s, n in Counter(stems).items() if n > 1]
    if dup_stems:
        r.errors.append(f"identical stem appears twice: {[s[:50] for s in dup_stems]}")

    # Two items may not print the same picture. Before layouts were sampled this
    # fired on half of all papers — `median_to_hypotenuse` and
    # `median_hypotenuse_from_median` both drew the canonical right triangle,
    # and nothing compared them because their stems and signatures differ.
    figures = [geometry_hash(i.scene) for i in items if i.scene]
    dup_figures = [h for h, n in Counter(figures).items() if n > 1]
    if dup_figures:
        repeated = [i.template_code for i in items
                    if i.scene and geometry_hash(i.scene) in dup_figures]
        r.errors.append(f"the same figure is drawn more than once: {sorted(repeated)}")

    r.merge(check_letter_balance(items))

    if blueprint is not None and len(slots) == len(blueprint.slots):
        if sum(i.total_points for i, s in zip(items, slots) if s.section == "part1") != 65:
            r.errors.append("Part 1 must total exactly 65 points")
        if sum(i.total_points for i, s in zip(items, slots) if s.section == "part2") != 35:
            r.errors.append("Part 2 must total exactly 35 points")

    return r


def check_letter_balance(items: Iterable[GeneratedItem]) -> Report:
    r = Report()
    letters = [i.correct_answer for i in items
               if i.kind == "mc" and isinstance(i.correct_answer, str)]
    if len(letters) < 8:
        return r
    counts = Counter(letters)
    target = len(letters) / 4
    for letter in OPTION_LETTERS:
        drift = abs(counts.get(letter, 0) - target)
        if drift > LETTER_TOLERANCE + 0.75:
            r.warnings.append(
                f"answer letter {letter} appears {counts.get(letter, 0)} times "
                f"against a target of {target:.1f}")
    return r


def letter_histogram(items: Iterable[GeneratedItem]) -> dict[str, int]:
    counts = Counter(i.correct_answer for i in items
                     if i.kind == "mc" and isinstance(i.correct_answer, str))
    return {letter: counts.get(letter, 0) for letter in OPTION_LETTERS}
