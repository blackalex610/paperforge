"""Every geom_* topic, each with the figure the real papers print beside it.

Two rules run through this file.

*The figure is laid out, not solved.* Points come from a canonical layout plus a
parameter along a segment; nothing here trigonometrically reconstructs the
stem's numbers. That is legitimate precisely because every paper since 2018
prints „Те не са начертани в мащаб и не са предназначени за директно измерване
на дължини и на ъгли.” — the student is told not to measure. What the figure
must get right is topology: M really between A and B, the foot of a height
really on the correct side, the labelled angle on the correct side of a cevian.

*Angles stay whole.* An angle chase whose answer is 63,5° is not an NVO item.
Parameter spaces are chosen so every intermediate and final angle is an
integer, and a draw that fails raises Retry rather than rounding.

Where a construction only closes for one special angle — the perpendicular
bisector of a hypotenuse gives a rational leg ratio at 30° and essentially
nowhere else — the template fixes that angle and varies the lengths instead,
which is exactly what the official papers do.
"""
from __future__ import annotations

import math
import random
from fractions import Fraction

from paperforge.blueprints import Slot
from paperforge.distractors import angle_options, numeric_options, shuffle_options
from paperforge.registry import GeneratedItem, Retry, template
from paperforge.scene import (
    Figure,
    add,
    angle_bisector_point,
    angle_deg,
    circumcentre,
    coordinate_grid,
    deg,
    foot_of_perpendicular,
    isosceles_triangle,
    lerp,
    line_intersection,
    midpoint,
    norm,
    parallelogram,
    parallelogram_from_angle,
    polar,
    right_trapezoid,
    right_triangle,
    scalene_triangle,
    scale,
    solid,
    sub,
    triangle_for_cevians,
    triangle_for_circumcentre,
    triangle_for_three_cevians,
    triangle_from_angles,
    triangle_with_extended_side,
    two_parallel_lines,
    unit,
)


# ─── triangle with cevians: height + angle bisector ──────────────────────────


#: p : q splitting a parallelogram's co-interior pair into whole degrees, the
#: smaller angle at least 20°. Was six hand-picked ratios.
_PARALLELOGRAM_RATIOS = [
    (p, q) for q in range(2, 14) for p in range(1, q)
    if math.gcd(p, q) == 1 and 180 % (p + q) == 0 and 180 * p // (p + q) >= 20
]


def angle_span(slot: Slot, lo: int, hi: int, *, step: int = 1) -> list[int]:
    """Every whole value in [lo, hi] a level may draw, instead of a hand-picked list.

    Real papers print angles such as 8°, 52° and 78° (2026 Q11, Q14), not only
    multiples of five, and a list of seven values is seven items a student
    starts recognising. The range is the template's own drawable range; the
    level decides how round the numbers are — easy prints multiples of ten,
    medium of five, actual any whole value, and extra hard only the awkward
    ones. ``step`` keeps a parity the template needs (an angle that is halved).
    """
    every = [v for v in range(lo, hi + 1) if v % step == 0]
    round10 = [v for v in every if v % 10 == 0]
    round5 = [v for v in every if v % 5 == 0]
    awkward = [v for v in every if v % 5]
    return slot.profile.tier(round10 if len(round10) >= 2 else
                             round5 if len(round5) >= 2 else every,
                             round5 if len(round5) >= 3 else every,
                             every,
                             awkward if len(awkward) >= 3 else every)


@template("tri_height_and_bisector",
          topics=["geom_triangle_cevians"], kinds=["mc"], weight=1.4, band="hard")
def tri_height_and_bisector(rng: random.Random, slot: Slot) -> GeneratedItem:
    """BH is a height, BL bisects ∠ABC; given ∠LBH and ∠HCB, find ∠BAC.

    The 2026 Q11 item. Chase: ∠HBC = 90 − ∠HCB, so ∠LBC = ∠LBH + ∠HBC and
    ∠ABC = 2·∠LBC, leaving ∠BAC = 180 − ∠ABC − ∠HCB.
    """
    gamma = rng.choice(angle_span(slot, 61, 80, step=1))                     # ∠HCB
    lbh = rng.choice(angle_span(slot, 3, 14, step=1))   # ∠LBH
    hbc = 90 - gamma
    lbc = lbh + hbc
    abc = 2 * lbc
    key = 180 - abc - gamma
    if key <= 20 or abc <= 10 or key + abc + gamma != 180:
        raise Retry("angle chase must stay inside a valid triangle")

    # Drawn to the stem's angles, with one exaggeration: ∠LBH is often 3–9°,
    # an arc no one can read, so the drawing opens it to at least 15°. The
    # angle between a bisector and a height from one vertex is |∠A − ∠C| / 2,
    # so that sets the drawn ∠A; ∠C stays true up to the cap below, and
    # ∠A < ∠C keeps L between A and H exactly as in the official figure.
    # 20° gives the value room inside its own angle; the drawn ∠A = γ − 2·20°
    # must stay readable too, which caps it for the smallest γ.
    # ∠C is drawn at most 70°: nearer 80° the foot H comes within 21 units of
    # C, and the arc at C runs into the right-angle square at H. At least 66°,
    # too, or the cap on ∠LBH below narrows its wedge past what its value fits.
    shown_gamma = min(max(gamma, 66), 70)
    shown_lbh = min(max(lbh, 20), (shown_gamma - 26) / 2)
    f = triangle_from_angles(shown_gamma - 2 * shown_lbh, shown_gamma, rng=rng)
    A, B, C = f.points["A"], f.points["B"], f.points["C"]
    # The helper builds on a horizontal base AB with the apex C. Here the
    # height and the bisector drop from B onto AC, so AC is the base: the
    # helper's apex is this item's B, and its B is this item's C.
    f.points = {"A": A, "B": C, "C": B}
    A, B, C = f.points["A"], f.points["B"], f.points["C"]
    H = f.put("H", foot_of_perpendicular(B, A, C))
    L = line_intersection(B, angle_bisector_point(B, A, C, 100.0), A, C)
    if L is None:
        raise Retry("the bisector missed AC")
    f.put("L", L)
    f.path(["A", "B", "C"], close=True)
    f.seg("B", "H")
    f.seg("B", "L")
    f.right_angle("H", "B", "C")
    f.angle("C", "H", "B", label=deg(gamma), radius=22)
    f.angle("B", "L", "H", label=deg(lbh), radius=40)
    f.angle("A", "B", "C", arcs=1, fill=True, radius=21)

    options, letter = angle_options(key, extras=[abc, lbc, gamma + lbh], rng=rng)
    return GeneratedItem(
        topic=slot.topic, kind="mc", points=slot.points,
        stem=(f"На чертежа $BH$ е височина, а $BL$ е ъглополовяща на $\\sphericalangle ABC$ "
              f"в $\\triangle ABC$. Ако $\\sphericalangle LBH = {lbh}^\\circ$ и "
              f"$\\sphericalangle HCB = {gamma}^\\circ$, то мярката на $\\sphericalangle BAC$ е:"),
        options=options, correct_answer=letter, difficulty="hard",
        scene=f.to_spec(aria=(f"Триъгълник ABC с височина BH и ъглополовяща BL към страната AC; "
                              f"отбелязани са ъгъл {lbh} градуса при B и {gamma} градуса при C"), rng=rng),
        solution=(rf"$\sphericalangle HBC = 90^\circ - {gamma}^\circ = {hbc}^\circ$, "
                  rf"$\sphericalangle LBC = {lbh}^\circ + {hbc}^\circ = {lbc}^\circ$, "
                  rf"$\sphericalangle ABC = {abc}^\circ$ и "
                  rf"$\sphericalangle BAC = 180^\circ - {abc}^\circ - {gamma}^\circ = {key}^\circ$"),
        signature=f"tri_hb:{gamma}:{lbh}",
    )


@template("tri_bisector_isosceles",
          topics=["geom_triangle_cevians"], kinds=["mc"], weight=1.1, band="hard")
def tri_bisector_isosceles(rng: random.Random, slot: Slot) -> GeneratedItem:
    """CN bisects ∠ACB with AN = CN; given ∠CNB, find ∠ABC — the 2021 Q14 shape."""
    cnb = rng.choice(angle_span(slot, 54, 88, step=2))
    # ∠ANC = 180 − ∠CNB; AN = CN makes △ANC isosceles, so ∠NAC = ∠NCA.
    anc = 180 - cnb
    nac = (180 - anc) // 2
    if (180 - anc) % 2:
        raise Retry("need whole base angles")
    acb = 2 * nac                       # CN bisects the angle at C
    key = 180 - nac - acb
    if key <= 10 or acb <= 10:
        raise Retry("degenerate triangle")

    # Every angle is fixed by the stem, so draw it to them: N is then the real
    # foot of the bisector and AN = CN holds in the picture, not just the ticks.
    f = triangle_from_angles(nac, key, rng=rng)
    A, B, C = f.points["A"], f.points["B"], f.points["C"]
    N = line_intersection(C, angle_bisector_point(C, A, B, 100.0), A, B)
    if N is None:
        raise Retry("the bisector missed AB")
    f.put("N", N, dot=True)
    f.path(["A", "B", "C"], close=True)
    f.seg("C", "N")
    f.tick("A", "N", count=1)
    f.tick("C", "N", count=1)
    f.angle("C", "A", "N", arcs=2, radius=20)
    f.angle("C", "N", "B", arcs=2, radius=26)
    f.angle("N", "C", "B", label=deg(cnb), radius=24)
    f.angle("B", "C", "A", arcs=1, fill=True, radius=20)

    options, letter = angle_options(key, extras=[acb, nac, anc], rng=rng)
    return GeneratedItem(
        topic=slot.topic, kind="mc", points=slot.points,
        stem=(f"В $\\triangle ABC$ отсечката $CN$ е ъглополовяща на "
              f"$\\sphericalangle ACB$ $(N \\in AB)$, $\\sphericalangle CNB = {cnb}^\\circ$ "
              f"и $AN = CN$. Мярката на $\\sphericalangle ABC$ е:"),
        options=options, correct_answer=letter, difficulty="hard",
        scene=f.to_spec(aria=("Триъгълник ABC с ъглополовяща CN към страната AB, "
                              f"като AN = CN и ъгъл CNB е {cnb} градуса"), rng=rng),
        solution=(rf"$\sphericalangle ANC = {anc}^\circ$, а от $AN = CN$ следва "
                  rf"$\sphericalangle NAC = \sphericalangle NCA = {nac}^\circ$. "
                  rf"Тогава $\sphericalangle ACB = {acb}^\circ$ и "
                  rf"$\sphericalangle ABC = {key}^\circ$"),
        signature=f"tri_bi_iso:{cnb}",
    )


# ─── the incentre angle ──────────────────────────────────────────────────────

@template("incentre_angle",
          topics=["geom_bisectors_incentre", "geom_triangle_cevians"],
          kinds=["mc", "short"], weight=1.4, band="hard")
def incentre_angle(rng: random.Random, slot: Slot) -> GeneratedItem:
    """Bisectors from A and B meet at O; ∠AOB = 90° + ∠C/2.

    2026 Q20 and 2020 Q16 are the same template six years apart, with the
    vertex roles rotated and the given angle changed — which is the clearest
    evidence in the corpus that the ministry is already working this way.
    """
    gamma = rng.choice(angle_span(slot, 30, 86, step=2))
    aob = 90 + gamma // 2
    if gamma % 2:
        raise Retry("γ must be even so ∠AOB is whole")

    # ∠C is the unknown, so the drawing may show it true; the base angles are
    # a free split of what is left.
    rest = 180 - gamma
    alpha_drawn = rest * rng.uniform(0.40, 0.60)
    f = _incentre_figure(rng, alpha_drawn, rest - alpha_drawn, to_sides=True)
    f.angle("O", "A", "B", label=deg(aob), radius=13)

    stem = (f"Ъглополовящите на $\\sphericalangle BAC$ и $\\sphericalangle ABC$ се "
            f"пресичат в точка $O$, като $\\sphericalangle AOB = {aob}^\\circ$.")
    aria = ("Триъгълник ABC с ъглополовящи от A и от B, пресичащи се в точка O, "
            f"като ъгъл AOB е {aob} градуса")
    solution = (rf"$\sphericalangle AOB = 90^\circ + \frac{{\sphericalangle ACB}}{{2}}$, "
                rf"значи ${aob}^\circ - 90^\circ = \frac{{\sphericalangle ACB}}{{2}}$ "
                rf"и $\sphericalangle ACB = {gamma}^\circ$")

    if slot.kind == "short":
        return GeneratedItem(
            topic=slot.topic, kind="short", points=slot.points,
            stem=stem + " Намерете мярката на $\\sphericalangle ACB$.",
            correct_answer=f"{gamma}°", difficulty="hard",
            scene=f.to_spec(aria=aria, rng=rng), solution=solution,
            signature=f"incentre:{gamma}",
        )

    options, letter = angle_options(gamma, extras=[aob - 90, 180 - aob, gamma * 2], rng=rng)
    return GeneratedItem(
        topic=slot.topic, kind="mc", points=slot.points,
        stem=stem + " Мярката на $\\sphericalangle ACB$ е:",
        options=options, correct_answer=letter, difficulty="hard",
        scene=f.to_spec(aria=aria, rng=rng), solution=solution,
        signature=f"incentre:{gamma}",
    )


# ─── parallel lines ──────────────────────────────────────────────────────────

def _zigzag_figure(beta: float, alpha: float, rng: random.Random) -> "Figure":
    """Parallels b (top) and a (bottom), B on b, A on a, C between them, with
    ∠(b, BC) = β and ∠(a, AC) = α measured from the left-hand ray of each line.

    B and A used to be put at fixed heights while the lines were sampled, so
    they floated up to 16 units off their lines with the angle arcs hanging in
    empty space. They are now constructed *on* the lines, and C where the two
    arms actually meet. An arm flatter than 25° against its line would push A
    or B off the page, so it is drawn at 25°; the label still says the value.
    """
    f = two_parallel_lines(rng=rng)
    # The lines as far apart as the page allows, and C at the height that
    # makes BC and CA about equally long: a steep arm between close lines was
    # 45 units long, and the values at its two ends were printed in one heap.
    top, bottom = rng.uniform(26.0, 34.0), rng.uniform(138.0, 146.0)
    for name, y in (("bL", top), ("bR", top), ("aL", bottom), ("aR", bottom)):
        f.points[name] = (f.points[name][0], y)
    theta_b = math.radians(max(180 - beta, 25))      # BC below line b
    theta_a = math.radians(max(180 - alpha, 25))     # AC above line a
    sb, sa = math.sin(theta_b), math.sin(theta_a)
    share = min(max(sb / (sa + sb) * rng.uniform(0.92, 1.08), 0.35), 0.65)
    cy = top + (bottom - top) * share
    back_b = (cy - top) / math.tan(theta_b)
    back_a = (bottom - cy) / math.tan(theta_a)
    lo, hi = 40.0 + max(back_b, back_a), 214.0
    if lo > hi:
        raise Retry("the zigzag does not fit between the lines")
    cx = rng.uniform(lo, hi) if hi - lo > 1 else lo
    f.put("C", (cx, cy), dot=True)
    f.put("B", (cx - back_b, top), dot=True)
    f.put("A", (cx - back_a, bottom), dot=True)
    f.line("bL", "bR", label="b")
    f.line("aL", "aR", label="a")
    f.seg("B", "C")
    f.seg("C", "A")
    return f


@template("parallels_zigzag", topics=["geom_parallel_lines", "geom_lines_angles"],
          kinds=["mc"], weight=1.4)
def parallels_zigzag(rng: random.Random, slot: Slot) -> GeneratedItem:
    """Two parallels joined by a zigzag through C; find ∠ACB.

    2023 Q12 and 2026 Q12. Draw the third parallel through C and the answer is
    (180 − β) + (180 − α), which is why the two given angles are both obtuse.
    """
    beta = rng.choice(angle_span(slot, 105, 150))      # at B, against line b
    alpha = rng.choice(angle_span(slot, 135, 168))          # at A, against line a
    key = (180 - beta) + (180 - alpha)
    if key <= 15 or key >= 170:
        raise Retry("the zigzag angle must be clearly drawable")

    f = _zigzag_figure(beta, alpha, rng)
    f.angle("B", "bL", "C", label=deg(beta), radius=24)
    f.angle("A", "aL", "C", label=deg(alpha), radius=24)
    f.angle("C", "B", "A", arcs=1, fill=True, radius=20)

    options, letter = angle_options(
        key, extras=[180 - beta, 180 - alpha, beta - alpha + 180], rng=rng)
    return GeneratedItem(
        topic=slot.topic, kind="mc", points=slot.points,
        stem=("На чертежа правите $a$ и $b$ са успоредни. По данните на чертежа "
              "мярката на $\\sphericalangle ACB$ е:"),
        options=options, correct_answer=letter, difficulty="medium",
        scene=f.to_spec(aria=(f"Две успоредни прави a и b, свързани с начупена линия през точка C; "
                              f"отбелязани са {beta} градуса при B и {alpha} градуса при A"), rng=rng),
        solution=(rf"През $C$ построяваме права, успоредна на $a$ и $b$. Тогава "
                  rf"$\sphericalangle ACB = (180^\circ - {beta}^\circ) + "
                  rf"(180^\circ - {alpha}^\circ) = {key}^\circ$"),
        signature=f"par_zigzag:{beta}:{alpha}",
    )


#: (num, den) with 180·num/(num + den) whole and the angle comfortably drawable.
_ADJ_FRACTIONS = [(1, 2), (2, 1), (1, 3), (3, 1), (1, 4), (4, 1), (1, 5), (5, 1),
                  (2, 3), (3, 2), (4, 5), (5, 4), (2, 7), (7, 2), (5, 7), (7, 5),
                  (3, 7), (7, 3), (7, 11), (11, 7), (5, 13), (13, 5)]
#: p% with 180·p/(100 + p) whole.
_ADJ_PERCENTS = [20, 25, 50, 80, 125, 150, 200, 300, 400]
#: How the stem says a whole ratio.
_TIMES_WORDS = {2: "два", 3: "три", 4: "четири", 5: "пет"}


def _adjacent_figure(angle: int, rng: random.Random) -> dict:
    """A line through O and a ray OR, both adjacent angles marked (no values)."""
    f = Figure(width=250, height=150)
    O = f.put("O", (125.0, 108.0))
    f.put("L", polar(O, 105, 180), hidden=True)
    f.put("Rt", polar(O, 105, 0), hidden=True)
    drawn = min(max(angle, 28), 152)            # keep both arcs legible
    f.put("R", polar(O, 92, drawn))
    f.line("L", "Rt")
    f.seg("O", "R")
    # Clearly different radii: at 24 and 30 the single arc and the double one
    # ran together into what looked like three concentric arcs over one angle.
    f.angle("O", "Rt", "R", arcs=1, radius=17)
    f.angle("O", "R", "L", arcs=2, radius=31)
    return f.to_spec(aria="Права и лъч от точка O върху нея, образуващи два съседни ъгъла",
                     rng=rng, upright=True)


@template("adjacent_angle_ratio", topics=["geom_lines_angles"], kinds=["mc"], weight=1.2)
def adjacent_angle_ratio(rng: random.Random, slot: Slot) -> GeneratedItem:
    """One of two adjacent angles is a given part of the other — 2022 Q11, 2023 Q11.

    2022 phrases it as a fraction („5/4 от съседния му”), 2023 as a percentage
    („80% от другия”); both are kept. The papers print no figure, but every
    geometry slot here carries one, and this template used to be rejected on
    every draw for lacking it — registered, counted in coverage, never served.
    """
    if rng.random() < 0.6:
        num, den = rng.choice(_ADJ_FRACTIONS)
        key_f = Fraction(180 * num, num + den)
        sig = f"{num}/{den}"
        if den == 1:
            # „4/1 от съседния” is how nobody says it; a whole ratio is
            # „четири пъти по-голяма”.
            times = _TIMES_WORDS[num]
            relation = f"е {times} пъти по-голяма от мярката на съседния му ъгъл"
            in_solution = rf"е {times} пъти по-голям от $y$"
        else:
            part = rf"$\frac{{{num}}}{{{den}}}$"
            relation = f"е {part} от мярката на съседния му ъгъл"
            in_solution = f"е {part} от $y$"
    else:
        pct = rng.choice(_ADJ_PERCENTS)
        part = rf"${pct}\%$"
        relation = f"е {part} от мярката на съседния му ъгъл"
        in_solution = f"е {part} от $y$"
        key_f = Fraction(180 * pct, 100 + pct)
        sig = f"{pct}%"
    if key_f.denominator != 1:
        raise Retry("need a whole-number angle")
    angle = key_f.numerator
    neighbour = 180 - angle
    if not 15 <= angle <= 165:
        raise Retry("angle out of a drawable range")

    ask_neighbour = rng.random() < 0.5
    key = neighbour if ask_neighbour else angle
    asked = "съседния му ъгъл" if ask_neighbour else "този ъгъл"
    options, letter = angle_options(key, extras=[180 - key, abs(angle - neighbour), 90],
                                    rng=rng)
    return GeneratedItem(
        topic=slot.topic, kind="mc", points=slot.points,
        stem=(f"Мярката на един ъгъл {relation}. "
              f"Мярката на {asked} е:"),
        options=options, correct_answer=letter, difficulty="medium",
        scene=_adjacent_figure(angle, rng),
        solution=(rf"Съседните ъгли се допълват до $180^\circ$. Ако съседният е $y$, "
                  rf"ъгълът {in_solution}, откъдето $y = {neighbour}^\circ$, а ъгълът е "
                  rf"${angle}^\circ$"),
        signature=f"adj_ratio:{sig}:{ask_neighbour}",
    )


#: k → how the stem says "k times the sum of its two neighbours".
_NEIGHBOUR_MULTIPLES = {
    Fraction(1): "е равна на сбора от мерките на двата му съседни ъгъла",
    Fraction(2): "е два пъти по-голяма от сбора от мерките на двата му съседни ъгъла",
    Fraction(4): "е четири пъти по-голяма от сбора от мерките на двата му съседни ъгъла",
    Fraction(3, 2): (r"е равна на $\frac{3}{2}$ от сбора от мерките на двата му "
                     r"съседни ъгъла"),
    Fraction(1, 3): "е три пъти по-малка от сбора от мерките на двата му съседни ъгъла",
    Fraction(1, 4): "е четири пъти по-малка от сбора от мерките на двата му съседни ъгъла",
}


@template("angle_equals_neighbours", topics=["geom_lines_angles"], kinds=["mc"], weight=1.1)
def angle_equals_neighbours(rng: random.Random, slot: Slot) -> GeneratedItem:
    """One angle at a crossing is k times the sum of its two neighbours — 2024 Q10.

    Both neighbours are 180 − x, so x = 2k(180 − x) and x = 360k / (1 + 2k).
    The paper's k = 1 gives 120°, which is what this template used to print
    every time; k ∈ {1/4, 1/3, 1, 3/2, 2, 4} gives 60°, 72°, 120°, 135°, 144°
    and 160°, and the question asks for either the larger or the smaller angle.
    """
    k = rng.choice(list(_NEIGHBOUR_MULTIPLES))
    x = Fraction(360) * k / (1 + 2 * k)
    if x.denominator != 1:
        raise Retry("need a whole angle")
    x = int(x)
    other = 180 - x
    larger = rng.random() < 0.6
    key = max(x, other) if larger else min(x, other)

    f = Figure(width=250, height=150)
    O = f.put("O", (128.0, 78.0))
    tilt = rng.uniform(-14, 14)
    f.put("P1", polar(O, 108, 180 + tilt), hidden=True)
    f.put("P2", polar(O, 108, tilt), hidden=True)
    f.put("Q1", polar(O, 104, 180 + tilt + x), hidden=True)
    f.put("Q2", polar(O, 104, tilt + x), hidden=True)
    f.line("P1", "P2")
    f.line("Q1", "Q2")
    f.angle("O", "P2", "Q2", arcs=1, fill=True, radius=26)

    options, letter = angle_options(key, extras=[180 - key, 120, 90, x // 2], rng=rng)
    return GeneratedItem(
        topic=slot.topic, kind="mc", points=slot.points,
        stem=("При пресичането на две прави мярката на един от получените ъгли "
              f"{_NEIGHBOUR_MULTIPLES[k]}. Мярката на "
              f"{'по-големия' if larger else 'по-малкия'} от получените ъгли е:"),
        options=options, correct_answer=letter, difficulty="medium",
        scene=f.to_spec(aria="Две пресичащи се прави с отбелязан един от получените ъгли",
                        rng=rng),
        solution=(rf"Съседните ъгли са по $180^\circ - x$. От условието "
                  rf"$x = {bg_k(k)}\cdot 2(180^\circ - x)$, откъдето $x = {x}^\circ$; "
                  rf"другите ъгли са ${other}^\circ$"),
        signature=f"angle_eq_neigh:{k}:{larger}",
    )


def bg_k(k: Fraction) -> str:
    return str(k.numerator) if k.denominator == 1 else rf"\frac{{{k.numerator}}}{{{k.denominator}}}"


@template("concurrent_lines_angle", topics=["geom_lines_angles"], kinds=["mc"], weight=1.1)
def concurrent_lines_angle(rng: random.Random, slot: Slot) -> GeneratedItem:
    """Three lines through one point; find the third angle — the 2021 Q12 shape."""
    a = rng.choice([35, 40, 45, 50, 55])
    b = rng.choice([30, 35, 40, 45])
    key = 180 - a - b
    if key <= 40:
        raise Retry("the unknown angle must stay obtuse enough to read")

    # Drawn to its angles: b leaves c at a° on the left, a leaves it at b° on
    # the right, so the angle between them below c is α = 180 − a − b exactly.
    # It used to be drawn at fixed bearings whatever the stem said, and the
    # unknown was never named — the stem asks for „ъгъл α”.
    f = Figure(width=250, height=160)
    O = f.put("O", (126.0, 80.0))
    f.put("cL", polar(O, 100, 180), hidden=True)
    f.put("cR", polar(O, 100, 0), hidden=True)
    f.put("aL", polar(O, 96, 180 + b), hidden=True)
    f.put("aR", polar(O, 96, b), hidden=True)
    f.put("bL", polar(O, 96, 180 - a), hidden=True)
    f.put("bR", polar(O, 96, -a), hidden=True)
    f.line("cL", "cR", label="c", pad=4.0)
    f.line("aL", "aR", label="a", pad=4.0)
    f.line("bL", "bR", label="b", pad=4.0)
    f.angle("O", "cL", "bL", label=deg(a), radius=30)
    f.angle("O", "aR", "cR", label=deg(b), radius=30)
    f.angle("O", "aL", "bR", arcs=1, fill=True, radius=24, label="α")

    options, letter = angle_options(key, extras=[a + b, 180 - a, 180 - b], rng=rng)
    return GeneratedItem(
        topic=slot.topic, kind="mc", points=slot.points,
        stem=("Правите $a$, $b$ и $c$ се пресичат в точка $O$. По данните от чертежа "
              "мярката на ъгъл $\\alpha$ е:"),
        options=options, correct_answer=letter, difficulty="medium",
        scene=f.to_spec(aria=(f"Три прави, пресичащи се в точка O, с отбелязани ъгли "
                              f"{a} и {b} градуса и търсен ъгъл алфа"), rng=rng),
        solution=(rf"Трите ъгъла при $O$ от едната страна на права $c$ дават "
                  rf"$180^\circ$: $\alpha = 180^\circ - {a}^\circ - {b}^\circ = {key}^\circ$"),
        signature=f"concurrent:{a}:{b}",
    )


# ─── right triangles ─────────────────────────────────────────────────────────

@template("perp_bisector_of_hypotenuse",
          topics=["geom_right_triangle"], kinds=["mc"], weight=1.3, band="hard")
def perp_bisector_of_hypotenuse(rng: random.Random, slot: Slot) -> GeneratedItem:
    """The perpendicular bisector of AB meets leg AC at M; find CM.

    2026 Q13. With ∠BAC = α the chase gives CM = AC·cos2α/(1+cos2α); that is
    rational only at α = 30°, where it collapses to AC/3. The official paper
    fixes 30° and varies AC, and so does this — varying α instead would produce
    surds, which no NVO key ever prints.
    """
    alpha = 30
    ac = rng.choice(slot.profile.tier([12, 15, 18, 21], list(range(9, 34, 3)),
                                      list(range(9, 49, 3)), list(range(21, 61, 3))))
    if ac % 3:
        raise Retry("AC must divide by 3 for a whole answer")
    key = ac // 3

    # Drawn at the stated 30°. The sampled layout put C anywhere on the
    # semicircle, and whenever it landed left of centre the bisector met the
    # line AC *past* C — M was printed in the air above the triangle.
    f = right_triangle(rng=rng, alpha=alpha)
    A, B, C = f.points["A"], f.points["B"], f.points["C"]
    mid_ab = midpoint(A, B)
    # The perpendicular bisector of AB is vertical here (AB is horizontal), so
    # M is its real intersection with AC rather than a guessed parameter.
    perp_dir = (0.0, -1.0)
    far = add(mid_ab, scale(perp_dir, 200.0))
    M = line_intersection(mid_ab, far, A, C)
    if M is None:
        raise Retry("the perpendicular bisector missed AC")
    f.put("M", M, dot=True)
    f.put("S", mid_ab, hidden=True)
    f.path(["A", "B", "C"], close=True)
    f.seg("M", "B")
    # The bisector runs a little past M and a little below AB, as printed.
    f.put("s1", add(mid_ab, scale(perp_dir, -12.0)), hidden=True)
    f.put("s2", add(M, scale(perp_dir, 26.0)), hidden=True)
    f.seg("s1", "s2", dash=True, weight=1.0)
    f.right_angle("S", "B", "s2", size=7.0)
    f.tick("A", "S", count=1)
    f.tick("S", "B", count=1)
    f.right_angle("C", "A", "B")
    f.angle("A", "B", "C", label=deg(alpha), radius=26)
    f.label_along("s1", "s2", "s_{AB}", ts=(0.95, 0.88))

    options, letter = numeric_options(
        key, [ac // 2, ac - key, key * 2, ac], rng=rng, positive_only=True,
        fmt=str, suffix="cm")
    return GeneratedItem(
        topic=slot.topic, kind="mc", points=slot.points,
        stem=(f"Симетралата на хипотенузата $AB$ на правоъгълния $\\triangle ABC$ "
              f"пресича катета му $AC$ в точка $M$. Ако $AC = {ac}$ cm и "
              f"$\\sphericalangle BAC = {alpha}^\\circ$, то дължината на $CM$ е:"),
        options=options, correct_answer=letter, difficulty="hard",
        scene=f.to_spec(aria=("Правоъгълен триъгълник ABC с прав ъгъл при C, симетрала "
                              "на хипотенузата AB, пресичаща катета AC в точка M"), rng=rng),
        solution=(rf"$MA = MB$, значи $\sphericalangle MBA = {alpha}^\circ$ и "
                  rf"$\sphericalangle BMC = {2 * alpha}^\circ$. В правоъгълния "
                  rf"$\triangle BMC$ катетът $CM$ лежи срещу ъгъл "
                  rf"${90 - 2 * alpha}^\circ$, откъдето $CM = \frac{{AC}}{{3}} = {key}$ cm"),
        signature=f"perp_hyp:{ac}",
    )


def _median_figure(rng: random.Random, alpha: float | None) -> "Figure":
    """Right triangle, right angle at C, and the median CM to the hypotenuse.

    AM = MB is ticked: every item on this figure says M is the midpoint, and
    without the ticks the segment could as well be a height or a bisector.
    Drawn at ∠CAB = α when the stem gives it.
    """
    f = right_triangle(rng=rng, alpha=alpha)
    A, B, C = f.points["A"], f.points["B"], f.points["C"]
    f.put("M", midpoint(A, B), dot=True)
    f.path(["A", "B", "C"], close=True)
    f.seg("C", "M")
    f.right_angle("C", "A", "B")
    f.tick("A", "M", count=1)
    f.tick("M", "B", count=1)
    return f


@template("median_to_hypotenuse",
          topics=["geom_median_hypotenuse", "geom_right_triangle"],
          kinds=["short", "mc"], weight=1.4, band="easy")
def median_to_hypotenuse(rng: random.Random, slot: Slot) -> GeneratedItem:
    """M is the midpoint of hypotenuse AB: find CM and ∠CMB.

    2026 Q19, a two-part short-answer item. CM = AB/2 because M is the
    circumcentre; then △AMC is isosceles, so ∠CMB = 2·∠CAB as an exterior
    angle. Both parts are independent, which is what the ministry's memo asks
    of short-answer items.
    """
    ab = rng.choice(slot.profile.tier([16, 20, 24], list(range(12, 41, 4)),
                                      list(range(10, 61, 2)), list(range(22, 81, 2))))
    alpha = rng.choice(angle_span(slot, 12, 42))
    cm = ab // 2
    cmb = 2 * alpha
    if ab % 2 or cmb >= 90:
        raise Retry("keep CM whole and ∠CMB acute so the figure reads")

    two_part = slot.kind == "short" and slot.parts == 2
    # The figure marks what its own stem says and nothing more. The one-part
    # item gives only AB and asks for CM, and it used to print the two-part
    # item's figure — a ∠CAB its stem never mentions, and ∠CMB shaded as if it
    # were the question.
    f = _median_figure(rng, alpha if two_part else None)
    if two_part:
        f.angle("A", "B", "C", label=deg(alpha), radius=26)
        f.angle("M", "C", "B", arcs=1, fill=True, radius=20)

    aria = ("Правоъгълен триъгълник ABC с прав ъгъл при C и медиана CM към "
            "хипотенузата AB")
    solution = (rf"А) $M$ е центърът на описаната окръжност, значи "
                rf"$CM = MA = MB = \frac{{AB}}{{2}} = {cm}$ cm. "
                rf"Б) $\triangle AMC$ е равнобедрен, затова "
                rf"$\sphericalangle ACM = {alpha}^\circ$ и "
                rf"$\sphericalangle CMB = {alpha}^\circ + {alpha}^\circ = {cmb}^\circ$")

    if two_part:
        return GeneratedItem(
            topic=slot.topic, kind="short", points=slot.points,
            stem=(f"В правоъгълния $\\triangle ABC$ хипотенузата $AB$ има дължина "
                  f"${ab}$ cm, $\\sphericalangle CAB = {alpha}^\\circ$ и точка $M$ "
                  f"е средата на $AB$."),
            parts=["А) Намерете дължината на $CM$.",
                   "Б) Намерете мярката на $\\sphericalangle CMB$."],
            correct_answer=[f"{cm} cm", f"{cmb}°"],
            difficulty="medium", scene=f.to_spec(aria=aria, rng=rng), solution=solution,
            signature=f"median_hyp:{ab}:{alpha}",
        )

    options, letter = numeric_options(
        cm, [ab, ab // 4, cm * 3, ab - cm + 2], rng=rng, positive_only=True,
        fmt=str, suffix="cm")
    return GeneratedItem(
        topic=slot.topic, kind="mc", points=slot.points,
        stem=(f"В правоъгълния $\\triangle ABC$ хипотенузата $AB$ има дължина ${ab}$ cm "
              f"и точка $M$ е средата на $AB$. Дължината на $CM$ е:"),
        options=options, correct_answer=letter, difficulty="easy",
        scene=f.to_spec(aria=aria, rng=rng), solution=solution,
        signature=f"median_hyp:{ab}:{alpha}",
    )


@template("right_triangle_perimeter",
          topics=["geom_right_triangle"], kinds=["mc"], weight=1.0)
def right_triangle_perimeter(rng: random.Random, slot: Slot) -> GeneratedItem:
    """Perimeter from two legs of a Pythagorean triple — the 2023 Q14 shape."""
    a, b, c = rng.choice([(3, 4, 5), (6, 8, 10), (5, 12, 13), (9, 12, 15), (8, 15, 17)])
    key = a + b + c

    options, letter = numeric_options(
        key, [a + b, c * 2, a + b + c - a, a * b], rng=rng, positive_only=True,
        fmt=str, suffix="cm")
    # Drawn with the legs in their true ratio (∠A lies opposite BC = a), so the
    # side labelled 12 is not drawn shorter than the one labelled 9.
    f = right_triangle(rng=rng, alpha=math.degrees(math.atan2(a, b)))
    f.path(["A", "B", "C"], close=True)
    f.right_angle("C", "A", "B")
    # Plain text, not LaTeX: scene labels are drawn as SVG <text>, so "$12$"
    # would render with the dollar signs visible.
    f.label_along("A", "C", str(b))
    f.label_along("C", "B", str(a))
    return GeneratedItem(
        topic=slot.topic, kind="mc", points=slot.points,
        stem=(f"Катетите на правоъгълния $\\triangle ABC$ "
              f"$(\\sphericalangle ACB = 90^\\circ)$ са ${a}$ cm и ${b}$ cm. "
              f"Периметърът на триъгълника е:"),
        options=options, correct_answer=letter, difficulty="medium",
        scene=f.to_spec(aria=f"Правоъгълен триъгълник с катети {a} и {b}", rng=rng),
        solution=(rf"$AB = \sqrt{{{a}^2 + {b}^2}} = {c}$ cm, а периметърът е "
                  rf"${a} + {b} + {c} = {key}$ cm"),
        signature=f"rt_perim:{a}:{b}",
    )


# ─── quadrilaterals ──────────────────────────────────────────────────────────

@template("parallelogram_isosceles_cut",
          topics=["geom_quadrilateral"], kinds=["mc"], weight=1.3, band="hard")
def parallelogram_isosceles_cut(rng: random.Random, slot: Slot) -> GeneratedItem:
    """M on AB with AD = AM; given ∠MDC, find ∠BCD — the 2026 Q14 shape.

    DC ∥ AB makes ∠MDC and ∠DMA alternate, so △ADM is isosceles with base
    angles ∠MDC, and ∠BCD = ∠DAB = 180° − 2·∠MDC.
    """
    mdc = rng.choice(angle_span(slot, 36, 70))
    key = 180 - 2 * mdc
    if key <= 20:
        raise Retry("the parallelogram angle must stay drawable")

    # Drawn at ∠DAB = 180° − 2·∠MDC with AM really equal to AD. The ticks
    # used to be one stroke on AD and two on AM — which says AD ≠ AM, the
    # opposite of the stem.
    f = parallelogram_from_angle(key, rng.uniform(0.52, 0.66), rng=rng)
    A, B, C, D = (f.points[k] for k in "ABCD")
    f.put("M", lerp(A, B, math.dist(A, D) / math.dist(A, B)), dot=True)
    f.path(["A", "B", "C", "D"], close=True)
    f.seg("D", "M")
    f.angle("D", "M", "C", label=deg(mdc), radius=24)
    f.angle("C", "B", "D", arcs=1, fill=True, radius=22)
    f.tick("A", "D", count=1)
    f.tick("A", "M", count=1)

    options, letter = angle_options(key, extras=[mdc, 2 * mdc, 180 - mdc], rng=rng)
    return GeneratedItem(
        topic=slot.topic, kind="mc", points=slot.points,
        stem=(f"Точка $M$ е от страната $AB$ на успоредника $ABCD$. Ако $AD = AM$ и "
              f"$\\sphericalangle MDC = {mdc}^\\circ$, то мярката на "
              f"$\\sphericalangle BCD$ е:"),
        options=options, correct_answer=letter, difficulty="hard",
        scene=f.to_spec(aria=("Успоредник ABCD с точка M върху AB, отсечка DM и "
                              f"отбелязан ъгъл MDC от {mdc} градуса"), rng=rng),
        solution=(rf"$DC \parallel AB$, значи $\sphericalangle DMA = "
                  rf"\sphericalangle MDC = {mdc}^\circ$. От $AD = AM$ следва "
                  rf"$\sphericalangle ADM = {mdc}^\circ$ и "
                  rf"$\sphericalangle DAB = 180^\circ - {2 * mdc}^\circ = {key}^\circ$. "
                  rf"Тогава $\sphericalangle BCD = \sphericalangle DAB = {key}^\circ$"),
        signature=f"par_iso_cut:{mdc}",
    )


@template("rhombus_bisector_angle",
          topics=["geom_quadrilateral"], kinds=["mc"], weight=1.2, band="hard")
def rhombus_bisector_angle(rng: random.Random, slot: Slot) -> GeneratedItem:
    """In rhombus ABCD, AL bisects ∠BAC; find ∠ALB — the 2024 Q12 shape."""
    bad = rng.choice(angle_span(slot, 36, 84, step=4))
    if bad % 4:
        raise Retry("∠BAD must divide by 4 so every step stays whole")
    bac = bad // 2                 # the diagonal bisects the rhombus angle
    bal = bac // 2                 # AL bisects that
    abc = 180 - bad
    key = 180 - abc - bal
    if key <= 5:
        raise Retry("degenerate")

    # A rhombus at the stated ∠BAD: the sampled one was always 45–55°, so an
    # 80° angle was printed on a visibly narrow corner.
    f = parallelogram_from_angle(bad, 1.0, rng=rng)
    A, B, C, D = (f.points[k] for k in "ABCD")
    f.path(["A", "B", "C", "D"], close=True)
    f.seg("A", "C")
    L = line_intersection(A, angle_bisector_point(A, B, C, 300.0), B, C)
    if L is None:
        raise Retry("the bisector missed BC")
    f.put("L", L, dot=True)
    f.seg("A", "L")
    f.angle("A", "B", "D", label=deg(bad), radius=26)

    options, letter = angle_options(key, extras=[bac, bal, abc], rng=rng)
    return GeneratedItem(
        topic=slot.topic, kind="mc", points=slot.points,
        stem=(f"В ромба $ABCD$ $\\sphericalangle BAD = {bad}^\\circ$, а $AL$ "
              f"$(L \\in BC)$ е ъглополовящата на $\\sphericalangle BAC$. "
              f"Мярката на $\\sphericalangle ALB$ е:"),
        options=options, correct_answer=letter, difficulty="hard",
        scene=f.to_spec(aria=(f"Ромб ABCD с диагонал AC и ъглополовяща AL, "
                              f"като ъгъл BAD е {bad} градуса"), rng=rng),
        solution=(rf"Диагоналът $AC$ е ъглополовяща, значи "
                  rf"$\sphericalangle BAC = {bac}^\circ$ и "
                  rf"$\sphericalangle BAL = {bal}^\circ$. В $\triangle ABL$ имаме "
                  rf"$\sphericalangle ABL = {abc}^\circ$, откъдето "
                  rf"$\sphericalangle ALB = {key}^\circ$"),
        signature=f"rhomb_bisec:{bad}",
    )


@template("parallelogram_angle_ratio",
          topics=["geom_quadrilateral"], kinds=["mc"], weight=1.0)
def parallelogram_angle_ratio(rng: random.Random, slot: Slot) -> GeneratedItem:
    """Two angles of a parallelogram in ratio p:q; find their difference — 2025 Q15."""
    p, q = rng.choice(_PARALLELOGRAM_RATIOS)
    total = p + q
    if 180 % total:
        raise Retry("the ratio must split 180° into whole parts")
    unit_deg = 180 // total
    small, big = p * unit_deg, q * unit_deg
    key = big - small

    # The stem gives only a ratio, so the angle is free to draw; at 1 : 8 the
    # true 20° makes a sliver, so the acute angle is drawn at 35° or more.
    shown_small = max(small, 35)
    f = parallelogram_from_angle(shown_small if rng.random() < 0.5 else 180 - shown_small,
                                 rng.uniform(0.55, 0.75), rng=rng)
    f.path(["A", "B", "C", "D"], close=True)
    f.angle("A", "B", "D", arcs=1, radius=24)
    f.angle("B", "C", "A", arcs=2, radius=24)

    options, letter = angle_options(key, extras=[small, big, small + big], rng=rng)
    return GeneratedItem(
        topic=slot.topic, kind="mc", points=slot.points,
        stem=(f"Мерките на два от ъглите на успоредник се отнасят както ${p} : {q}$. "
              f"Разликата от мерките на двата ъгъла е:"),
        options=options, correct_answer=letter, difficulty="medium",
        scene=f.to_spec(aria="Успоредник ABCD с отбелязани два съседни ъгъла", rng=rng),
        solution=(rf"Съседните ъгли са със сбор $180^\circ$, значи една част е "
                  rf"${unit_deg}^\circ$ и ъглите са ${small}^\circ$ и ${big}^\circ$; "
                  rf"разликата е ${key}^\circ$"),
        signature=f"par_ratio:{p}:{q}",
    )


# ─── congruent triangles ─────────────────────────────────────────────────────

def _congruent_pair(alpha: float, beta: float, rng: random.Random) -> "Figure":
    """△ABC drawn at ∠A = α, ∠B = β, and △NMP a turned copy of it with
    N ↔ A, M ↔ B, P ↔ C — two triangles that are actually congruent.

    They used to be two fixed shapes whatever the stem said: an item asking
    the student to *use* the congruence showed two triangles that visibly
    were not.
    """
    f = Figure(width=280, height=160)
    a, b = math.radians(alpha), math.radians(beta)
    ac = math.sin(b) / math.sin(a + b)
    unit_pts = {"A": (0.0, 0.0), "B": (1.0, 0.0), "C": (ac * math.cos(a), -ac * math.sin(a))}
    turn = math.radians(rng.uniform(150.0, 210.0))
    mirror = rng.random() < 0.5

    def turned(p):
        x, y = (-p[0], p[1]) if mirror else p
        return (x * math.cos(turn) - y * math.sin(turn), x * math.sin(turn) + y * math.cos(turn))

    copy = {"N": turned(unit_pts["A"]), "M": turned(unit_pts["B"]), "P": turned(unit_pts["C"])}

    def box(pts):
        xs, ys = [p[0] for p in pts.values()], [p[1] for p in pts.values()]
        return min(xs), min(ys), max(xs), max(ys)

    l0, l1 = box(unit_pts), box(copy)
    gap_units = 0.28
    span_x = (l0[2] - l0[0]) + gap_units + (l1[2] - l1[0])
    span_y = max(l0[3] - l0[1], l1[3] - l1[1])
    k = min((f.width - 40) / span_x, (f.height - 40) / span_y) * rng.uniform(0.9, 0.98)
    left_x = (f.width - k * span_x) / 2.0
    for name, p in unit_pts.items():
        f.put(name, (left_x + k * (p[0] - l0[0]), f.height / 2 + k * (p[1] - (l0[1] + l0[3]) / 2)))
    right_x = left_x + k * ((l0[2] - l0[0]) + gap_units)
    for name, p in copy.items():
        f.put(name, (right_x + k * (p[0] - l1[0]), f.height / 2 + k * (p[1] - (l1[1] + l1[3]) / 2)))
    return f


@template("congruent_triangles_angle",
          topics=["geom_two_triangles"], kinds=["mc"], weight=1.4)
def congruent_triangles_angle(rng: random.Random, slot: Slot) -> GeneratedItem:
    """Two triangles congruent by SAS; find the matching angle.

    2020 Q14 and 2021 Q10 are this item with *identical* numbers, one year
    apart — 47° and 56°, answer 77° both times.
    """
    alpha = rng.choice([42, 45, 47, 50, 54, 58])
    gamma = rng.choice([52, 56, 60, 64, 68])
    key = 180 - alpha - gamma
    if key <= 25:
        raise Retry("the third angle must be comfortably positive")

    f = _congruent_pair(alpha, key, rng)
    f.path(["A", "B", "C"], close=True)
    f.path(["M", "N", "P"], close=True)
    f.angle("A", "B", "C", label=deg(alpha), radius=22)
    f.angle("C", "A", "B", label=deg(gamma), radius=20)
    f.angle("P", "M", "N", label=deg(gamma), radius=20)
    f.tick("A", "C", count=1)
    f.tick("N", "P", count=1)
    f.tick("B", "C", count=2)
    f.tick("M", "P", count=2)

    options, letter = angle_options(key, extras=[alpha, gamma, alpha + gamma], rng=rng)
    return GeneratedItem(
        topic=slot.topic, kind="mc", points=slot.points,
        stem=(f"Дадени са $\\triangle ABC$ и $\\triangle MNP$, за които $AC = NP$, "
              f"$BC = MP$, $\\sphericalangle CAB = {alpha}^\\circ$ и "
              f"$\\sphericalangle ACB = \\sphericalangle MPN = {gamma}^\\circ$. "
              f"Мярката на $\\sphericalangle NMP$ е:"),
        options=options, correct_answer=letter, difficulty="medium",
        scene=f.to_spec(aria=("Два триъгълника ABC и MNP с равни съответни страни "
                              "и равни ъгли при C и P"), rng=rng),
        solution=(rf"По първи признак $\triangle ABC \cong \triangle NMP$, значи "
                  rf"$\sphericalangle NMP = \sphericalangle ABC = 180^\circ - "
                  rf"{alpha}^\circ - {gamma}^\circ = {key}^\circ$"),
        signature=f"congr:{alpha}:{gamma}",
    )


@template("isosceles_from_equal_segments",
          topics=["geom_two_triangles"], kinds=["mc"], weight=1.0, band="hard")
def isosceles_from_equal_segments(rng: random.Random, slot: Slot) -> GeneratedItem:
    """F on AB with AC = CF = BF; given the angle relation, find ∠ACB — 2024 Q14.

    With ∠B = x, △CFB is isosceles so ∠FCB = x and the exterior ∠CFA = 2x;
    AC = CF makes △ACF isosceles with ∠A = ∠AFC = 2x. Then in △ABC:
    2x + x + ∠ACB = 180.
    """
    x = rng.choice(angle_span(slot, 18, 40))
    key = 180 - 3 * x
    if key <= 20:
        raise Retry("∠ACB must stay positive and readable")

    # Drawn to the angles the chase produces (2x, x, 180 − 3x), with F where
    # CF = BF really holds. All three equal segments carry the same single
    # tick: BF used to carry two, which says BF ≠ CF — against the stem.
    f = triangle_from_angles(2 * x, x, rng=rng)
    A, B, C = f.points["A"], f.points["B"], f.points["C"]
    mid_bc = midpoint(B, C)
    F = line_intersection(mid_bc, add(mid_bc, (-(C[1] - B[1]), C[0] - B[0])), A, B)
    if F is None:
        raise Retry("F did not land on AB")
    f.put("F", F, dot=True)
    f.path(["A", "B", "C"], close=True)
    f.seg("C", "F")
    f.tick("A", "C", count=1)
    f.tick("C", "F", count=1)
    f.tick("F", "B", count=1)
    # Only ∠CBA is given. Marking ∠CAB too would make the equal-segment
    # conditions decorative — the student is meant to derive it from AC = CF.
    f.angle("B", "C", "A", label=deg(x), radius=22)
    f.angle("C", "A", "B", arcs=1, fill=True, radius=20)

    options, letter = angle_options(key, extras=[2 * x, x, 180 - 2 * x], rng=rng)
    return GeneratedItem(
        topic=slot.topic, kind="mc", points=slot.points,
        stem=(f"В $\\triangle ABC$ върху страната $AB$ е взета точка $F$ така, че "
              f"$AC = CF = BF$. По данните от чертежа мярката на "
              f"$\\sphericalangle ACB$ е:"),
        options=options, correct_answer=letter, difficulty="hard",
        scene=f.to_spec(aria=("Триъгълник ABC с точка F върху AB, като AC = CF = BF, "
                              f"и отбелязан ъгъл при B от {x} градуса"), rng=rng),
        solution=(rf"От $CF = BF$ следва $\sphericalangle FCB = {x}^\circ$, а от "
                  rf"$AC = CF$ — $\sphericalangle CAF = {2 * x}^\circ$. В "
                  rf"$\triangle ABC$: $\sphericalangle ACB = 180^\circ - "
                  rf"{2 * x}^\circ - {x}^\circ = {key}^\circ$"),
        signature=f"iso_eq_seg:{x}",
    )


# ─── ordering sides by angles ────────────────────────────────────────────────

def _readable_angles(alpha: float, beta: float, floor: float = 24.0) -> tuple[float, float]:
    """Base angles to draw a triangle whose angles are α, β and 180 − α − β.

    True when every angle is at least `floor`. Otherwise all three are pulled
    toward 60° by the same factor — which keeps their *order*, the one thing an
    ordering item needs the figure to get right, while opening the sliver.
    """
    gamma = 180.0 - alpha - beta
    low = min(alpha, beta, gamma)
    if low >= floor:
        return alpha, beta
    t = (floor - low) / (60.0 - low)
    return alpha + (60.0 - alpha) * t, beta + (60.0 - beta) * t


@template("order_sides_by_angles",
          topics=["geom_side_ordering"], kinds=["mc"], weight=1.4, band="hard")
def order_sides_by_angles(rng: random.Random, slot: Slot) -> GeneratedItem:
    """Given one angle and the ratio of the other two, order the sides — 2024 Q15."""
    beta = rng.choice([40, 50, 60, 70, 80])
    rest = 180 - beta
    # Only offer ratios that actually split the remaining angle into whole
    # degrees. Drawing blind and retrying works too, but most ratios fail for
    # most β, so the template would spend its resample budget on arithmetic
    # that is decidable up front.
    usable = [(p, q) for p, q in [(3, 4), (2, 3), (1, 2), (3, 5), (4, 5), (5, 7), (1, 3), (1, 4)]
              if rest % (p + q) == 0]
    if not usable:
        raise Retry(f"no ratio divides {rest}°")
    p, q = rng.choice(usable)
    alpha = rest * p // (p + q)          # ∠BAC, opposite BC
    gamma = rest * q // (p + q)          # ∠ACB, opposite AB
    if len({alpha, beta, gamma}) != 3:
        raise Retry("all three angles must differ so the ordering is strict")

    # side opposite each angle: a=BC↔α, b=AC↔β, c=AB↔γ
    by_angle = sorted([(alpha, "BC"), (beta, "AC"), (gamma, "AB")])
    correct = " < ".join(name for _, name in by_angle)
    others = [
        " < ".join(name for _, name in reversed(by_angle)),
        " < ".join(name for _, name in [by_angle[1], by_angle[0], by_angle[2]]),
        " < ".join(name for _, name in [by_angle[0], by_angle[2], by_angle[1]]),
    ]
    options, letter = shuffle_options(f"${correct}$", [f"${o}$" for o in others], rng=rng)

    # Drawn to its angles. The question is which side is longest, so a random
    # triangle that drew the longest side shortest printed a wrong answer next
    # to the right one.
    f = triangle_from_angles(*_readable_angles(alpha, beta), rng=rng, on_longest=True)
    f.path(["A", "B", "C"], close=True)
    f.angle("B", "A", "C", label=deg(beta), radius=24)

    return GeneratedItem(
        topic=slot.topic, kind="mc", points=slot.points,
        stem=(f"В $\\triangle ABC$ $\\sphericalangle ABC = {beta}^\\circ$ и "
              f"$\\sphericalangle BAC : \\sphericalangle ACB = {p} : {q}$. "
              f"Вярното неравенство за страните на триъгълника е:"),
        options=options, correct_answer=letter, difficulty="hard",
        scene=f.to_spec(aria=f"Триъгълник ABC с отбелязан ъгъл при B от {beta} градуса", rng=rng),
        solution=(rf"$\sphericalangle BAC = {alpha}^\circ$ и "
                  rf"$\sphericalangle ACB = {gamma}^\circ$. Срещу по-малък ъгъл лежи "
                  rf"по-малка страна, откъдето ${correct}$"),
        signature=f"order_sides:{beta}:{p}:{q}",
    )


# ─── coordinate geometry ─────────────────────────────────────────────────────

@template("coordinate_fourth_vertex",
          topics=["geom_coordinate"], kinds=["mc"], weight=1.4)
def coordinate_fourth_vertex(rng: random.Random, slot: Slot) -> GeneratedItem:
    """Three vertices given; which point completes a parallelogram — 2026 Q10.

    The other candidates are the traps a student actually falls into: a point
    that looks right on the grid but makes a trapezium, and near misses of
    the right one.
    """
    ax, ay = rng.randint(0, 2), rng.randint(1, 3)
    bx = ax + rng.randint(2, 4)
    by = ay
    cx, cy = bx - rng.randint(0, 2), ay + rng.randint(2, 3)
    # The paper asks for the vertex that completes a parallelogram with the
    # three given ones; using B + C − A keeps the answer in the first quadrant.
    kx, ky = bx + cx - ax, by + cy - ay
    if not (0 <= kx <= 7 and 0 <= ky <= 6):
        raise Retry("keep every point on the printed grid")

    # Three points close a parallelogram three ways — A + C − B and A + B − C
    # complete one too, since the stem fixes no order of the vertices. The
    # first was offered as „the wrong diagonal”, so every such item had two
    # right answers. Neither may be a candidate. Nor may one of the given
    # vertices: offering "S(2;5)" when C is already (2;5) is not a
    # distractor, it is a typo the student has to work around.
    given = {(ax, ay), (bx, by), (cx, cy)}
    closing = {(ax + cx - bx, ay + cy - by), (ax + bx - cx, ay + by - cy)}
    pool = [(ax, cy), (cx, ay - 1), (bx, cy + 1), (ax - 1, cy),
            (kx + 1, ky), (kx, ky + 1), (kx - 1, ky - 1)]
    candidates: list[tuple[int, int]] = [(kx, ky)]
    for pt in pool:
        if pt in given or pt in closing or pt in candidates:
            continue
        if not (0 <= pt[0] <= 7 and 0 <= pt[1] <= 6):
            continue
        candidates.append(pt)
    if len(candidates) < 4:
        raise Retry("need four distinct on-grid candidates, including the key")
    candidates = candidates[:4]

    names = ["P", "Q", "R", "S"]
    pts = list(candidates)
    rng.shuffle(pts)
    key_index = pts.index((kx, ky))
    labelled = [f"${n}\\left({x};{y}\\right)$" for n, (x, y) in zip(names, pts)]
    options, letter = shuffle_options(labelled[key_index],
                                      [o for i, o in enumerate(labelled) if i != key_index],
                                      rng=rng)

    return GeneratedItem(
        topic=slot.topic, kind="mc", points=slot.points,
        stem=(f"В координатна система са дадени точките $A\\left({ax};{ay}\\right)$, "
              f"$B\\left({bx};{by}\\right)$ и $C\\left({cx};{cy}\\right)$. "
              f"Коя от точките $P$, $Q$, $R$ и $S$ определя с дадените точки "
              f"върхове на успоредник?"),
        options=options, correct_answer=letter, difficulty="medium",
        scene=coordinate_grid(
            points=[("A", ax, ay), ("B", bx, by), ("C", cx, cy)],
            aria=(f"Координатна система с отбелязани точки A({ax};{ay}), "
                  f"B({bx};{by}) и C({cx};{cy})")),
        solution=(rf"Точката ${names[key_index]}\left({kx};{ky}\right)$ е такава, че "
                  rf"$\vec{{AB}} = \vec{{C{names[key_index]}}}$, затова "
                  rf"$AB{names[key_index]}C$ е успоредник. Никоя от другите точки "
                  rf"не допълва дадените до успоредник"),
        signature=f"coord_par:{ax}:{ay}:{bx}:{cx}:{cy}",
    )


@template("coordinate_triangle_area",
          topics=["geom_coordinate"], kinds=["mc"], weight=1.1, band="hard")
def coordinate_triangle_area(rng: random.Random, slot: Slot) -> GeneratedItem:
    """Reflect a point in the y-axis and find the triangle's area — 2025 Q10."""
    ax = -rng.randint(2, 4)
    ay = -rng.randint(1, 3)
    bx, by = rng.randint(1, 3), rng.randint(1, 3)
    cx = -ax                                # C is A reflected in Oy
    base = cx - ax                          # horizontal, length 2|ax|
    height = abs(by - ay)
    key = Fraction(base * height, 2)
    if key.denominator != 1:
        raise Retry("area must be whole for a clean option list")
    key = key.numerator

    wrong = [key * 2, key // 2 if key % 2 == 0 else key + 1, base * height, key + base]
    options, letter = numeric_options(key, wrong, rng=rng, positive_only=True,
                                      fmt=lambda v: f"{v}\\,\\text{{cm}}^2")
    return GeneratedItem(
        topic=slot.topic, kind="mc", points=slot.points,
        stem=(f"На чертежа в координатна система $Oxy$ с единична отсечка $1$ cm са "
              f"отбелязани точките $A$ и $B$. Точката $C$ е симетрична на точка $A$ "
              f"спрямо ординатната ос $Oy$. Лицето на $\\triangle ABC$ е:"),
        options=options, correct_answer=letter, difficulty="hard",
        scene=coordinate_grid(
            points=[("A", ax, ay), ("B", bx, by)],
            x_range=(-5, 5), y_range=(-4, 4), unit_label="1 cm",
            aria=f"Координатна система с точки A({ax};{ay}) и B({bx};{by})"),
        solution=(rf"$C\left({cx};{ay}\right)$, основата $AC$ е ${base}$ cm, "
                  rf"височината от $B$ е ${height}$ cm, а лицето е "
                  rf"$\frac{{{base} \cdot {height}}}{{2}} = {key}$ cm$^2$"),
        signature=f"coord_area:{ax}:{ay}:{bx}:{by}",
    )


# ─── 3D solids ───────────────────────────────────────────────────────────────

@template("solid_box_volume", topics=["geom_quadrilateral", "geom_right_triangle"],
          kinds=["mc"], weight=0.6)
def solid_box_volume(rng: random.Random, slot: Slot) -> GeneratedItem:
    """A box with its three dimensions in three different units — 2022 Q18.

    Every paper carries at most one 3D item and it is always an illustration
    with dimension labels, never a figure to measure — so this draws from the
    static solid library rather than the plane-geometry renderer.
    """
    dm = [rng.choice([2, 3, 4, 5]) for _ in range(3)]
    key = dm[0] * dm[1] * dm[2]
    labels = {
        "w": f"{dm[0] * 10} cm",
        "d": f"{dm[1] * 100} mm",
        "h": f"{dm[2]} dm",
    }
    # ×100 and ×1000 are the unit slips this item is really about, but both sit
    # outside the plausibility band and were discarded, leaving too few options
    # to build from. Keep the one-step slip and fill the rest with the other
    # mistakes that stay in band: dropping a dimension, adding instead of
    # multiplying, doubling.
    wrong = [key * 10, dm[0] * dm[1], dm[0] + dm[1] + dm[2], key * 2]
    options, letter = numeric_options(key, wrong, rng=rng, positive_only=True, fmt=str)
    return GeneratedItem(
        topic=slot.topic, kind="mc", points=slot.points,
        stem=(f"Трите измерения на правоъгълен паралелепипед са {labels['w']}, "
              f"{labels['d']} и {labels['h']}. Обемът му в кубически дециметри е:"),
        options=options, correct_answer=letter, difficulty="medium",
        scene=solid(shape="box", labels=labels,
                    aria=("Правоъгълен паралелепипед с означени три измерения: "
                          f"{labels['w']}, {labels['d']} и {labels['h']}")),
        solution=(rf"Привеждаме към дециметри: ${dm[0]}$ dm, ${dm[1]}$ dm и ${dm[2]}$ dm, "
                  rf"откъдето $V = {dm[0]} \cdot {dm[1]} \cdot {dm[2]} = {key}$ dm$^3$"),
        signature=f"box_vol:{dm[0]}:{dm[1]}:{dm[2]}",
    )


# ═════════════════════════════════════════════════════════════════════════════
# Band partners for the geometry block.
#
# Every figure here is laid out canonically and then labelled — none of them
# solves for its own coordinates. That is the licence the scale notice grants
# („не са начертани в мащаб”), and it is why an item can carry ∠ACB = 34° on a
# triangle drawn at 50° without being wrong. What each figure does have to get
# right is topology: the point between the correct two points, the marked angle
# on the correct side of the cevian.
# ═════════════════════════════════════════════════════════════════════════════

@template("parallels_transversal_cointerior",
          topics=["geom_parallel_lines", "geom_lines_angles"], kinds=["mc"],
          weight=1.2, band="easy")
def parallels_transversal_cointerior(rng: random.Random, slot: Slot) -> GeneratedItem:
    """One transversal across two parallels — the co-interior pair sums to 180°.

    The gentlest item in this topic and the one the geometry block usually
    opens with: a single named property, one subtraction, no chase.
    """
    alpha = rng.choice(angle_span(slot, 106, 151, step=1))
    key = 180 - alpha

    f = two_parallel_lines(rng=rng)
    # P sits on b, Q on a, to the left of it — so the transversal leans the way
    # the printed figures draw it and the two marked angles are the co-interior
    # pair rather than a corresponding one. Both are constructed on their
    # lines, at the stated angle: they used to sit at fixed heights while the
    # lines were sampled, up to 16 units off them. A transversal flatter than
    # 40° runs off the page, so it is drawn no flatter; the label says the value.
    top, bottom = f.points["bL"][1], f.points["aL"][1]
    lean = math.radians(min(alpha, 140))
    run = (bottom - top) / math.tan(math.pi - lean)
    px = rng.uniform(max(60.0, 40.0 + run), 214.0) if 40.0 + run < 214.0 else 214.0
    f.put("P", (px, top), dot=True)
    f.put("Q", (px - run, bottom), dot=True)
    f.line("bL", "bR", label="b")
    f.line("aL", "aR", label="a")
    f.seg("P", "Q")
    f.angle("P", "bR", "Q", label=deg(alpha), radius=26)
    f.angle("Q", "aR", "P", arcs=1, fill=True, radius=22)

    options, letter = angle_options(key, extras=[alpha, 2 * key], rng=rng)
    return GeneratedItem(
        topic=slot.topic, kind="mc", points=slot.points,
        stem=("На чертежа правите $a$ и $b$ са успоредни и са пресечени от "
              "правата $PQ$. По данните на чертежа мярката на отбелязания "
              "ъгъл при върха $Q$ е:"),
        options=options, correct_answer=letter, difficulty="easy",
        scene=f.to_spec(aria=(f"Две успоредни прави a и b, пресечени от правата PQ; "
                              f"при P е отбелязан ъгъл {alpha} градуса, а при Q — "
                              f"търсеният ъгъл"), rng=rng),
        solution=(rf"Двата отбелязани ъгъла са вътрешни едностранни, затова "
                  rf"сборът им е $180^\circ$ и търсеният ъгъл е "
                  rf"$180^\circ - {alpha}^\circ = {key}^\circ$"),
        signature=f"par_cointerior:{alpha}",
    )


@template("parallels_zigzag_reverse",
          topics=["geom_parallel_lines", "geom_lines_angles"], kinds=["mc"],
          weight=1.0, band="hard")
def parallels_zigzag_reverse(rng: random.Random, slot: Slot) -> GeneratedItem:
    """The 2026 Q12 zigzag run backwards: given ∠ACB and one obtuse angle, find the other.

    Same figure and same identity as ``parallels_zigzag`` — ∠ACB = (180 − β) +
    (180 − α) — but with the unknown moved onto the line, so the student has to
    rearrange rather than add. Harder for exactly the reason the forward
    version is not.
    """
    beta = rng.choice(angle_span(slot, 105, 150))      # given, at B on b
    alpha = rng.choice(angle_span(slot, 135, 168))          # the unknown, at A on a
    acb = (180 - beta) + (180 - alpha)
    if acb <= 15 or acb >= 170:
        raise Retry("the zigzag angle must be clearly drawable")
    key = alpha

    f = _zigzag_figure(beta, alpha, rng)
    f.angle("B", "bL", "C", label=deg(beta), radius=24)
    if acb == 90:
        f.right_angle("C", "B", "A")       # the papers mark a right angle, not „90°”
    else:
        f.angle("C", "B", "A", label=deg(acb), radius=20)
    f.angle("A", "aL", "C", arcs=1, fill=True, radius=24)

    options, letter = angle_options(
        key, extras=[acb + beta, 360 - beta - acb - 10, 180 - acb], rng=rng)
    return GeneratedItem(
        topic=slot.topic, kind="mc", points=slot.points,
        stem=("На чертежа правите $a$ и $b$ са успоредни. По данните на чертежа "
              "мярката на отбелязания ъгъл при върха $A$ е:"),
        options=options, correct_answer=letter, difficulty="hard",
        scene=f.to_spec(aria=(f"Две успоредни прави a и b, свързани с начупена линия през "
                              f"точка C; отбелязани са {beta} градуса при B и {acb} градуса "
                              f"при C, търси се ъгълът при A"), rng=rng),
        solution=(rf"През $C$ построяваме права, успоредна на $a$ и $b$, откъдето "
                  rf"$\sphericalangle ACB = (180^\circ - {beta}^\circ) + "
                  rf"(180^\circ - \alpha)$. От ${acb}^\circ = {180 - beta}^\circ + "
                  rf"(180^\circ - \alpha)$ следва $\alpha = {key}^\circ$"),
        signature=f"par_zigzag_rev:{beta}:{alpha}",
    )


# ─── ordering sides and angles ───────────────────────────────────────────────

@template("order_angles_by_sides",
          topics=["geom_side_ordering"], kinds=["mc"], weight=1.2, band="easy")
def order_angles_by_sides(rng: random.Random, slot: Slot) -> GeneratedItem:
    """Given three side lengths, order the angles — the converse of 2024 Q15.

    One named theorem, applied once: the larger angle lies opposite the larger
    side. Any scalene triangle with whole sides up to 20 cm, not eight fixed ones.
    """
    a, b, c = rng.sample(range(3, slot.profile.tier(12, 15, 20, 30)), 3)
    if not (a + b > c and a + c > b and b + c > a):
        raise Retry("the three lengths must form a triangle")
    # a = BC (opposite ∠BAC), b = AC (opposite ∠ABC), c = AB (opposite ∠ACB)
    by_side = sorted([(a, "BAC"), (b, "ABC"), (c, "ACB")])
    names = [n for _, n in by_side]

    def chain(order):
        return " < ".join(rf"\sphericalangle {n}" for n in order)

    correct = chain(names)
    others = [
        chain(list(reversed(names))),
        chain([names[1], names[0], names[2]]),
        chain([names[0], names[2], names[1]]),
    ]
    options, letter = shuffle_options(f"${correct}$", [f"${o}$" for o in others], rng=rng)

    # Drawn so the longest side *looks* longest — the whole question is the
    # order, and a random triangle printed it backwards some of the time.
    ang_a = math.degrees(math.acos((b * b + c * c - a * a) / (2 * b * c)))
    ang_b = math.degrees(math.acos((a * a + c * c - b * b) / (2 * a * c)))
    f = triangle_from_angles(*_readable_angles(ang_a, ang_b), rng=rng, on_longest=True)
    f.path(["A", "B", "C"], close=True)
    f.label_along("B", "C", f"{a} cm")
    f.label_along("A", "C", f"{b} cm")
    f.label_along("A", "B", f"{c} cm")

    return GeneratedItem(
        topic=slot.topic, kind="mc", points=slot.points,
        stem=(f"В $\\triangle ABC$ страните са $BC = {a}$ cm, $AC = {b}$ cm и "
              f"$AB = {c}$ cm. Вярното неравенство за ъглите на триъгълника е:"),
        options=options, correct_answer=letter, difficulty="easy",
        scene=f.to_spec(aria=(f"Триъгълник ABC със страни BC = {a} cm, AC = {b} cm "
                              f"и AB = {c} cm"), rng=rng),
        solution=(rf"Срещу по-малка страна лежи по-малък ъгъл. От "
                  rf"${by_side[0][0]} < {by_side[1][0]} < {by_side[2][0]}$ "
                  rf"следва ${correct}$"),
        signature=f"order_angles:{a}:{b}:{c}",
    )


@template("order_sides_two_given_angles",
          topics=["geom_side_ordering"], kinds=["mc"], weight=1.1, band="medium")
def order_sides_two_given_angles(rng: random.Random, slot: Slot) -> GeneratedItem:
    """Two angles given outright, order the sides — 2024 Q15 without the ratio
    step. Any two of the three angles may be the given ones."""
    angles = {"BAC": 0, "ABC": 0, "ACB": 0}
    x, y = rng.randint(20, 110), rng.randint(20, 110)
    z = 180 - x - y
    if z < 20 or len({x, y, z}) != 3:
        raise Retry("all three angles must differ and stay drawable")
    given = rng.choice([("BAC", "ABC"), ("ABC", "ACB"), ("BAC", "ACB")])
    missing = next(k for k in angles if k not in given)
    angles[given[0]], angles[given[1]], angles[missing] = x, y, z
    opposite = {"BAC": "BC", "ABC": "AC", "ACB": "AB"}
    by_angle = sorted((v, opposite[k]) for k, v in angles.items())
    names = [n for _, n in by_angle]

    def chain(order):
        return " < ".join(order)

    correct = chain(names)
    others = [
        chain(list(reversed(names))),
        chain([names[1], names[0], names[2]]),
        chain([names[0], names[2], names[1]]),
    ]
    options, letter = shuffle_options(f"${correct}$", [f"${o}$" for o in others], rng=rng)

    vertex = {"BAC": ("A", "B", "C"), "ABC": ("B", "A", "C"), "ACB": ("C", "A", "B")}
    f = triangle_from_angles(*_readable_angles(angles["BAC"], angles["ABC"]), rng=rng,
                             on_longest=True)
    f.path(["A", "B", "C"], close=True)
    for k in given:
        v, p1, p2 = vertex[k]
        if angles[k] == 90:
            f.right_angle(v, p1, p2)       # the papers mark a right angle, not „90°”
        else:
            f.angle(v, p1, p2, label=deg(angles[k]), radius=24)

    return GeneratedItem(
        topic=slot.topic, kind="mc", points=slot.points,
        stem=(f"В $\\triangle ABC$ $\\sphericalangle {given[0]} = {angles[given[0]]}^\\circ$ и "
              f"$\\sphericalangle {given[1]} = {angles[given[1]]}^\\circ$. Вярното неравенство "
              f"за страните на триъгълника е:"),
        options=options, correct_answer=letter, difficulty="medium",
        scene=f.to_spec(aria=(f"Триъгълник ABC с ъгли {angles[given[0]]} и "
                              f"{angles[given[1]]} градуса"), rng=rng),
        solution=(rf"$\sphericalangle {missing} = 180^\circ - {x}^\circ - {y}^\circ "
                  rf"= {z}^\circ$. Срещу по-малък ъгъл лежи по-малка страна, "
                  rf"откъдето ${correct}$"),
        signature=f"order_sides2:{given}:{x}:{y}",
    )


# ─── the median to the hypotenuse, at two more levels ────────────────────────

@template("median_hypotenuse_from_median",
          topics=["geom_median_hypotenuse", "geom_right_triangle"],
          kinds=["short", "mc"], weight=1.1, band="medium")
def median_hypotenuse_from_median(rng: random.Random, slot: Slot) -> GeneratedItem:
    """The 2026 Q19 identity run backwards: CM given, find AB and ∠ACM."""
    cm = rng.choice(slot.profile.tier([6, 8, 10], list(range(5, 16)),
                                      list(range(4, 26)), list(range(11, 41))))
    alpha = rng.choice(angle_span(slot, 16, 64))
    ab = 2 * cm

    two_part = slot.kind == "short" and slot.parts == 2
    # Only the two-part stem gives ∠CAB, and only it asks for ∠ACM — so only
    # its figure marks them.
    f = _median_figure(rng, alpha if two_part else None)
    if two_part:
        f.angle("A", "B", "C", label=deg(alpha), radius=26)
        # ∠ACM lies inside the right angle at C, so a shaded sector would
        # cover half of the right-angle square; a plain arc drawn clear of the
        # square marks it without hiding the square.
        f.angle("C", "A", "M", arcs=1, radius=22)

    aria = ("Правоъгълен триъгълник ABC с прав ъгъл при C и медиана CM към "
            "хипотенузата AB")
    solution = (rf"А) $CM$ е медиана към хипотенузата, значи "
                rf"$AB = 2\cdot CM = {ab}$ cm. "
                rf"Б) $MA = MC$, затова $\triangle AMC$ е равнобедрен и "
                rf"$\sphericalangle ACM = \sphericalangle CAM = {alpha}^\circ$")

    if two_part:
        return GeneratedItem(
            topic=slot.topic, kind="short", points=slot.points,
            stem=(f"В правоъгълния $\\triangle ABC$ с прав ъгъл при върха $C$ "
                  f"точка $M$ е средата на хипотенузата $AB$, $CM = {cm}$ cm и "
                  f"$\\sphericalangle CAB = {alpha}^\\circ$."),
            parts=["А) Намерете дължината на $AB$.",
                   "Б) Намерете мярката на $\\sphericalangle ACM$."],
            correct_answer=[f"{ab} cm", f"{alpha}°"],
            difficulty="medium", scene=f.to_spec(aria=aria, rng=rng), solution=solution,
            signature=f"median_from_cm:{cm}:{alpha}",
        )

    options, letter = numeric_options(
        ab, [cm, cm * 4, ab + 2, cm * 3], rng=rng, positive_only=True,
        fmt=str, suffix="cm")
    return GeneratedItem(
        topic=slot.topic, kind="mc", points=slot.points,
        stem=(f"В правоъгълния $\\triangle ABC$ с прав ъгъл при върха $C$ точка "
              f"$M$ е средата на хипотенузата $AB$ и $CM = {cm}$ cm. "
              f"Дължината на $AB$ е:"),
        options=options, correct_answer=letter, difficulty="medium",
        scene=f.to_spec(aria=aria, rng=rng), solution=solution,
        signature=f"median_from_cm:{cm}:{alpha}",
    )


@template("median_hypotenuse_equilateral",
          topics=["geom_median_hypotenuse", "geom_right_triangle"],
          kinds=["short", "mc"], weight=1.0, band="hard")
def median_hypotenuse_equilateral(rng: random.Random, slot: Slot) -> GeneratedItem:
    """∠CAB = 30° makes △CMB equilateral, so BC is half the hypotenuse.

    Two steps stacked: the median to the hypotenuse gives MB = MC, and the 60°
    at M then forces the third side equal too. This is the 30–60–90 fact that
    Part 2 geometry proofs lean on, asked directly.
    """
    ab = rng.choice(slot.profile.tier([12, 16, 20], list(range(8, 41, 4)),
                                      list(range(8, 61, 2)), list(range(22, 81, 2))))
    cmb = 60
    bc = ab // 2
    if ab % 2:
        raise Retry("keep the half-hypotenuse whole")

    two_part = slot.kind == "short" and slot.parts == 2
    if two_part:
        f = _median_figure(rng, 30)
    else:
        # The one-part stem never mentions M, so its figure does not draw a
        # median the student was not told about — that is half the solution.
        f = right_triangle(rng=rng, alpha=30)
        f.path(["A", "B", "C"], close=True)
        f.right_angle("C", "A", "B")
    f.angle("A", "B", "C", label=deg(30), radius=26)

    aria = ("Правоъгълен триъгълник ABC с прав ъгъл при C, ъгъл 30 градуса при A "
            + ("и медиана CM към хипотенузата AB, като AM = MB" if two_part else ""))
    solution = (rf"А) $\sphericalangle ACM = 30^\circ$ от равнобедрения "
                rf"$\triangle AMC$, затова $\sphericalangle CMB = 30^\circ + "
                rf"30^\circ = {cmb}^\circ$. "
                rf"Б) $MB = MC$ и ъгълът между тях е ${cmb}^\circ$, значи "
                rf"$\triangle CMB$ е равностранен и "
                rf"$BC = MB = \frac{{{ab}}}{{2}} = {bc}$ cm")

    if two_part:
        return GeneratedItem(
            topic=slot.topic, kind="short", points=slot.points,
            stem=(f"В правоъгълния $\\triangle ABC$ с прав ъгъл при върха $C$ "
                  f"хипотенузата $AB$ има дължина ${ab}$ cm, "
                  f"$\\sphericalangle CAB = 30^\\circ$ и точка $M$ е средата на $AB$."),
            parts=["А) Намерете мярката на $\\sphericalangle CMB$.",
                   "Б) Намерете дължината на $BC$."],
            correct_answer=[f"{cmb}°", f"{bc} cm"],
            difficulty="hard", scene=f.to_spec(aria=aria, rng=rng), solution=solution,
            signature=f"median_equilat:{ab}",
        )

    options, letter = numeric_options(
        bc, [ab, bc * 3, ab - bc + 2, bc + 2], rng=rng, positive_only=True,
        fmt=str, suffix="cm")
    return GeneratedItem(
        topic=slot.topic, kind="mc", points=slot.points,
        stem=(f"В правоъгълния $\\triangle ABC$ с прав ъгъл при върха $C$ "
              f"хипотенузата $AB$ има дължина ${ab}$ cm и "
              f"$\\sphericalangle CAB = 30^\\circ$. Дължината на $BC$ е:"),
        options=options, correct_answer=letter, difficulty="hard",
        scene=f.to_spec(aria=aria, rng=rng), solution=solution,
        signature=f"median_equilat:{ab}",
    )


# ─── the incentre angle, at two more levels ──────────────────────────────────

def _drawable_base_angles(alpha: float, beta: float, floor: float = 32.0,
                          cap: float = 135.0) -> tuple[float, float]:
    """Base angles to *draw* a triangle with, given the ones the stem states.

    True where they are readable. A 16° vertex halved by a bisector leaves two
    8° slivers that no arc can mark, so a small angle is drawn at `floor`. And
    the pair is squeezed to at most `cap`: as the base angles grow the
    incentre sinks toward AB, and past about 135° there is no room left
    between O and AB for the value of ∠AOB — it was pushed below the base,
    among the arcs at B, where it read as ∠ABC.
    """
    a, b = max(alpha, floor), max(beta, floor)
    if a + b > cap:
        k = cap / (a + b)
        a, b = a * k, b * k
        # Squeezing can pull the smaller angle back under the floor.
        if a < floor:
            a, b = floor, cap - floor
        elif b < floor:
            a, b = cap - floor, floor
    return a, b


def _incentre_figure(rng: random.Random, alpha: float, beta: float, *,
                     to_sides: bool = False) -> "Figure":
    """Triangle ABC, drawn at base angles α and β, with the bisectors from A
    and B meeting at O.

    Each bisector is marked the way the papers mark one: both halves of the
    angle it splits carry the same arc, one arc at A and two at B, so the two
    vertices are told apart. The old figure put the marks for A on O and C —
    `Figure.angle` takes the vertex first, and it was handed ∠OAB in the order
    it is written.
    """
    a, b = _drawable_base_angles(alpha, beta)
    f = triangle_from_angles(a, b, rng=rng)
    A, B, C = f.points["A"], f.points["B"], f.points["C"]
    O = line_intersection(A, angle_bisector_point(A, B, C, 200.0),
                          B, angle_bisector_point(B, A, C, 200.0))
    if O is None:
        raise Retry("bisectors did not meet")
    if math.dist(O, foot_of_perpendicular(O, A, B)) < 28.0:
        # ∠AOB opens toward AB; with O this low its value has no room there.
        raise Retry("the incentre sits too close to AB to mark ∠AOB")
    f.put("O", O, dot=True)
    f.path(["A", "B", "C"], close=True)
    if to_sides:
        # The papers draw the bisectors through to the opposite sides.
        ta = line_intersection(A, O, B, C)
        tb = line_intersection(B, O, A, C)
        if ta is None or tb is None:
            raise Retry("bisector did not reach the opposite side")
        f.put("Ta", ta, hidden=True)
        f.put("Tb", tb, hidden=True)
        f.seg("A", "Ta")
        f.seg("B", "Tb")
    else:
        f.seg("A", "O")
        f.seg("B", "O")
    f.angle("A", "B", "O", arcs=1, radius=26)
    f.angle("A", "O", "C", arcs=1, radius=26)
    f.angle("B", "A", "O", arcs=2, radius=24)
    f.angle("B", "O", "C", arcs=2, radius=24)
    return f


@template("incentre_angle_from_base_angles",
          topics=["geom_bisectors_incentre", "geom_triangle_cevians"],
          kinds=["short", "mc"], weight=1.2, band="medium")
def incentre_angle_from_base_angles(rng: random.Random, slot: Slot) -> GeneratedItem:
    """Given ∠A and ∠B, find ∠AOB where the bisectors from A and B meet.

    ∠AOB = 180° − (∠A + ∠B)/2, taken straight from the triangle AOB. The
    forward direction of the 2026 Q20 identity, and the gentler one: no
    rearranging, just halve and subtract.
    """
    alpha = rng.choice([40, 44, 50, 56, 60, 64, 70])
    beta = rng.choice([48, 52, 56, 62, 66, 74])
    if (alpha + beta) % 2 or alpha + beta >= 170 or alpha + beta <= 60:
        raise Retry("need a whole half-sum inside a valid triangle")
    key = 180 - (alpha + beta) // 2
    gamma = 180 - alpha - beta

    f = _incentre_figure(rng, alpha, beta)
    f.angle("O", "A", "B", arcs=1, fill=True, radius=16)

    aria = (f"Триъгълник ABC с ъглополовящи от A и B, които се пресичат в точка O; "
            f"ъглите при A и B са {alpha} и {beta} градуса")
    solution = (rf"В $\triangle AOB$ ъглите при $A$ и $B$ са "
                rf"$\frac{{{alpha}^\circ}}{{2}}$ и $\frac{{{beta}^\circ}}{{2}}$, "
                rf"затова $\sphericalangle AOB = 180^\circ - "
                rf"\frac{{{alpha}^\circ + {beta}^\circ}}{{2}} = {key}^\circ$ "
                rf"(което е и $90^\circ + \frac{{{gamma}^\circ}}{{2}}$)")
    stem = (f"В $\\triangle ABC$ ъглополовящите на $\\sphericalangle BAC$ и "
            f"$\\sphericalangle ABC$ се пресичат в точка $O$. Ако "
            f"$\\sphericalangle BAC = {alpha}^\\circ$ и "
            f"$\\sphericalangle ABC = {beta}^\\circ$, намерете мярката на "
            f"$\\sphericalangle AOB$.")

    if slot.kind == "short":
        return GeneratedItem(
            topic=slot.topic, kind="short", points=slot.points,
            stem=stem, correct_answer=f"{key}°", difficulty="medium",
            scene=f.to_spec(aria=aria, rng=rng), solution=solution,
            signature=f"incentre_fwd:{alpha}:{beta}",
        )

    options, letter = angle_options(key, extras=[gamma, 90 + gamma // 2, alpha + beta],
                                    rng=rng)
    return GeneratedItem(
        topic=slot.topic, kind="mc", points=slot.points,
        stem=stem.replace("намерете мярката на $\\sphericalangle AOB$.",
                          "то мярката на $\\sphericalangle AOB$ е:"),
        options=options, correct_answer=letter, difficulty="medium",
        scene=f.to_spec(aria=aria, rng=rng), solution=solution,
        signature=f"incentre_fwd:{alpha}:{beta}",
    )


@template("incentre_find_second_angle",
          topics=["geom_bisectors_incentre"], kinds=["short", "mc"],
          weight=1.0, band="hard")
def incentre_find_second_angle(rng: random.Random, slot: Slot) -> GeneratedItem:
    """Given ∠AOB and ∠BAC, find ∠ABC — the identity rearranged twice.

    From ∠AOB = 180° − (∠A + ∠B)/2 comes ∠A + ∠B = 360° − 2·∠AOB, and the
    second angle follows. Two rearrangements deep, which is what separates this
    from the ``incentre_angle`` item it shares a figure with.
    """
    aob = rng.choice([100, 105, 110, 115, 120, 125, 130])
    alpha = rng.choice([30, 36, 40, 44, 50, 54, 60])
    key = 360 - 2 * aob - alpha
    if key <= 15 or alpha + key >= 170:
        raise Retry("the second angle must fit inside a valid triangle")
    gamma = 180 - alpha - key

    f = _incentre_figure(rng, alpha, key)
    f.angle("O", "A", "B", label=deg(aob), radius=13)

    aria = (f"Триъгълник ABC с ъглополовящи от A и B, пресичащи се в точка O; "
            f"ъгъл AOB е {aob} градуса, а ъгълът при A е {alpha} градуса")
    solution = (rf"От $\sphericalangle AOB = 180^\circ - "
                rf"\frac{{\sphericalangle A + \sphericalangle B}}{{2}}$ следва "
                rf"$\sphericalangle A + \sphericalangle B = 360^\circ - "
                rf"2\cdot {aob}^\circ = {360 - 2 * aob}^\circ$, "
                rf"откъдето $\sphericalangle ABC = {360 - 2 * aob}^\circ - "
                rf"{alpha}^\circ = {key}^\circ$")
    stem = (f"В $\\triangle ABC$ ъглополовящите на $\\sphericalangle BAC$ и "
            f"$\\sphericalangle ABC$ се пресичат в точка $O$, като "
            f"$\\sphericalangle AOB = {aob}^\\circ$ и "
            f"$\\sphericalangle BAC = {alpha}^\\circ$.")

    if slot.kind == "short":
        return GeneratedItem(
            topic=slot.topic, kind="short", points=slot.points,
            stem=stem + " Намерете мярката на $\\sphericalangle ABC$.",
            correct_answer=f"{key}°", difficulty="hard",
            scene=f.to_spec(aria=aria, rng=rng), solution=solution,
            signature=f"incentre_second:{aob}:{alpha}",
        )

    options, letter = angle_options(key, extras=[gamma, 360 - 2 * aob, aob - alpha],
                                    rng=rng)
    return GeneratedItem(
        topic=slot.topic, kind="mc", points=slot.points,
        stem=stem + " Мярката на $\\sphericalangle ABC$ е:",
        options=options, correct_answer=letter, difficulty="hard",
        scene=f.to_spec(aria=aria, rng=rng), solution=solution,
        signature=f"incentre_second:{aob}:{alpha}",
    )


# ─── coordinates and two-triangle configurations ─────────────────────────────

@template("coordinate_reflection",
          topics=["geom_coordinate"], kinds=["mc"], weight=1.1, band="easy")
def coordinate_reflection(rng: random.Random, slot: Slot) -> GeneratedItem:
    """The point symmetric to A about one of the axes — one sign changes."""
    x = rng.randint(1, 5)
    y = rng.randint(1, 4)
    about_x_axis = rng.random() < 0.5
    if about_x_axis:
        key, axis = (x, -y), "абсцисната ос"
    else:
        key, axis = (-x, y), "ординатната ос"

    def pair(p):
        return f"$({p[0]}; {p[1]})$"

    wrongs = [pair(p) for p in [(-x, -y), (-x, y) if about_x_axis else (x, -y), (y, x)]]
    options, letter = shuffle_options(pair(key), wrongs, rng=rng)

    scene = coordinate_grid(
        points=[("A", x, y)],
        x_range=(-6, 6), y_range=(-5, 5),
        aria=f"Координатна система с отбелязана точка A с координати {x} и {y}",
    )
    return GeneratedItem(
        topic=slot.topic, kind="mc", points=slot.points,
        stem=(f"Точката, симетрична на точката $A({x}; {y})$ спрямо {axis}, "
              f"има координати:"),
        options=options, correct_answer=letter, difficulty="easy",
        scene=scene,
        solution=(f"При симетрия спрямо {axis} се променя знакът само на "
                  f"{'ординатата' if about_x_axis else 'абсцисата'}, "
                  f"откъдето {pair(key)}"),
        signature=f"coord_reflect:{x}:{y}:{about_x_axis}",
    )


@template("two_triangles_on_a_line",
          topics=["geom_two_triangles"], kinds=["mc"], weight=1.1, band="medium")
def two_triangles_on_a_line(rng: random.Random, slot: Slot) -> GeneratedItem:
    """Two triangles standing on one line through their shared vertex — 2024 Q11.

    A, C and E are collinear, so ∠BCA + ∠BCD + ∠DCE = 180°. Each outer angle
    comes from its own triangle's angle sum, which makes the answer
    α + β + γ + δ − 180°.
    """
    alpha = rng.choice([40, 45, 50, 55, 60, 65])     # ∠BAC
    beta = rng.choice([50, 55, 60, 65, 70, 75])      # ∠ABC
    gamma = rng.choice([40, 45, 50, 55, 60])         # ∠DEC
    delta = rng.choice([50, 55, 60, 65, 70])         # ∠CDE
    if alpha + beta >= 170 or gamma + delta >= 170:
        raise Retry("each triangle must close")
    key = alpha + beta + gamma + delta - 180
    if key <= 15 or key >= 165:
        raise Retry("the angle at C must be drawable")

    # Drawn to the stem's angles, both triangles on the line through C. The
    # marks used to go to the wrong vertices — `Figure.angle` takes the vertex
    # first and was handed ∠BAC in the order it is written — so the labels read
    # ∠ABC = α, ∠BCA = …, and the shaded "unknown" sat outside the figure at B.
    # Read off that picture, the answer came out wrong.
    def apex(base_left: float, base_right: float, x0: float, length: float):
        a, b = math.radians(base_left), math.radians(base_right)
        side = length * math.sin(b) / math.sin(a + b)
        return (x0 + side * math.cos(a), -side * math.sin(a))

    left_c = 180 - alpha - beta                 # ∠BCA
    right_c = 180 - gamma - delta               # ∠DCE
    right_len = rng.uniform(0.85, 1.15)
    f = Figure()
    f.put("A", (0.0, 0.0))
    f.put("C", (1.0, 0.0), dot=True)
    f.put("E", (1.0 + right_len, 0.0))
    f.put("B", apex(alpha, left_c, 0.0, 1.0))
    f.put("D", apex(right_c, gamma, 1.0, right_len))
    xs = [p[0] for p in f.points.values()]
    ys = [p[1] for p in f.points.values()]
    k = min((f.width - 40) / (max(xs) - min(xs)), (f.height - 40) / (max(ys) - min(ys)))
    f.points = {n: (20 + k * (p[0] - min(xs)), f.height - 20 + k * p[1])
                for n, p in f.points.items()}
    f.line("A", "E")
    f.path(["A", "B", "C"], close=True)
    f.path(["C", "D", "E"], close=True)
    f.angle("A", "B", "C", label=deg(alpha), radius=22)
    f.angle("B", "A", "C", label=deg(beta), radius=22)
    f.angle("D", "C", "E", label=deg(delta), radius=22)
    f.angle("E", "D", "C", label=deg(gamma), radius=22)
    f.angle("C", "B", "D", arcs=1, fill=True, radius=20)

    options, letter = angle_options(
        key, extras=[180 - alpha - beta, 180 - gamma - delta,
                     (180 - alpha - beta) + (180 - gamma - delta)], rng=rng)
    return GeneratedItem(
        topic=slot.topic, kind="mc", points=slot.points,
        stem=("На чертежа точките $A$, $C$ и $E$ лежат на една права. "
              "По данните от чертежа мярката на $\\sphericalangle BCD$ е:"),
        options=options, correct_answer=letter, difficulty="medium",
        scene=f.to_spec(aria=(f"Триъгълници ABC и CDE с общ връх C върху правата AE; "
                              f"отбелязани са ъгли {alpha}, {beta}, {delta} и {gamma} градуса"), rng=rng),
        solution=(rf"$\sphericalangle BCA = 180^\circ - {alpha}^\circ - {beta}^\circ "
                  rf"= {180 - alpha - beta}^\circ$ и $\sphericalangle DCE = "
                  rf"{180 - gamma - delta}^\circ$. Понеже $A$, $C$ и $E$ са на една "
                  rf"права, $\sphericalangle BCD = 180^\circ - "
                  rf"{180 - alpha - beta}^\circ - {180 - gamma - delta}^\circ = {key}^\circ$"),
        signature=f"two_tri_line:{alpha}:{beta}:{gamma}:{delta}",
    )


# ─── archetypes the coverage audit found missing ─────────────────────────────
# Seven figures that recur across two or more of the thirteen official papers
# but that no template could draw. See docs/nvo-figures/coverage.md for the
# archetype × paper matrix these were chosen from.

#: A marked arc needs more room than `verify.MIN_ANGLE_DEG` strictly demands.
#: Checking against the bare minimum leaves a draw that passes the verifier and
#: still reads as a smudge, so templates that mark an angle they constructed
#: hold themselves to this instead.
MIN_MARKED_ANGLE = 16.0

#: Two cevian feet on the same side need at least this much room, a little over
#: `verify.MIN_LABEL_GAP`, or their labels are rejected for overlapping.
MIN_FOOT_LABEL_GAP = 25.0


@template("tri_height_bisector_median",
          topics=["geom_triangle_cevians"], kinds=["mc"], weight=1.3, band="hard")
def tri_height_bisector_median(rng: random.Random, slot: Slot) -> GeneratedItem:
    """CP height, CL bisector, CM median from one vertex; find ∠PCL.

    The densest recurring figure in the corpus — 2015, 2017, 2019, 2020 and
    2023 all print a triangle carrying three cevians from the same vertex.

    The chase collapses to a small identity worth knowing: ∠ACL is half of
    ∠ACB and ∠ACP is 90° − α, so

        ∠PCL = (180 − α − β)/2 − (90 − α) = (α − β)/2

    — the angle between a vertex's height and its bisector is half the
    difference of the other two angles, and the median is along for the ride.
    """
    alpha = rng.choice(angle_span(slot, 53, 73, step=1))          # ∠BAC
    beta = rng.choice(angle_span(slot, 31, 47, step=1))          # ∠ABC
    if (alpha - beta) % 2 or alpha - beta < 8:
        raise Retry("∠PCL must be a whole number of degrees, and readable")
    gamma = 180 - alpha - beta
    if gamma <= 30 or alpha <= beta:
        raise Retry("∠ACB must stay a healthy angle and α must exceed β")
    key = (alpha - beta) // 2

    # Drawn to its angles, with L the true foot of the bisector. It used to
    # sit on a generic layout with L anywhere between P and M: ∠A came out
    # near 75° for a stated 53°, P fell so close to A that the value of ∠A
    # had to go outside the triangle, where it read as an exterior angle.
    # One exaggeration: ∠PCL = (α − β)/2 may be 4°, so α and β are spread
    # apart symmetrically until it is drawn at MIN_MARKED_ANGLE, which keeps
    # ∠C true. α > β keeps the height's foot nearer A than the median's.
    spread = max(alpha - beta, 2 * MIN_MARKED_ANGLE)
    middle = (alpha + beta) / 2
    f = triangle_from_angles(middle + spread / 2, middle - spread / 2, rng=rng)
    A, B, C = f.points["A"], f.points["B"], f.points["C"]
    P = f.put("P", foot_of_perpendicular(C, A, B))
    M = f.put("M", midpoint(A, B))
    L = line_intersection(C, angle_bisector_point(C, A, B, 100.0), A, B)
    if L is None:
        raise Retry("the bisector missed AB")
    if norm(sub(M, L)) < MIN_FOOT_LABEL_GAP or norm(sub(L, P)) < MIN_FOOT_LABEL_GAP:
        raise Retry("the three feet on AB must leave room for their labels")
    f.put("L", L)
    f.path(["A", "B", "C"], close=True)
    f.segs([("C", "P"), ("C", "L"), ("C", "M")])
    f.right_angle("P", "C", "B")
    f.tick("A", "M")
    f.tick("M", "B")
    f.angle("A", "B", "C", label=deg(alpha), radius=24)
    f.angle("B", "C", "A", label=deg(beta), radius=24)
    f.angle("C", "P", "L", arcs=1, fill=True, radius=30)

    options, letter = angle_options(
        key, extras=[alpha - beta, gamma // 2, 90 - alpha, alpha + beta - 90], rng=rng)
    return GeneratedItem(
        topic=slot.topic, kind="mc", points=slot.points,
        stem=("На чертежа $CP$ е височина, $CL$ е ъглополовяща, а $CM$ е медиана "
              "в $\\triangle ABC$. Ако $\\sphericalangle BAC = "
              f"{alpha}^\\circ$ и $\\sphericalangle ABC = {beta}^\\circ$, то мярката "
              "на $\\sphericalangle PCL$ е:"),
        options=options, correct_answer=letter, difficulty="hard",
        scene=f.to_spec(aria=(f"Триъгълник ABC с височина CP, ъглополовяща CL и медиана CM "
                              f"от върха C; отбелязани са ъгли {alpha} и {beta} градуса "
                              f"при основата"), rng=rng),
        solution=(rf"$\sphericalangle ACB = 180^\circ - {alpha}^\circ - {beta}^\circ "
                  rf"= {gamma}^\circ$, значи $\sphericalangle ACL = {gamma // 2}^\circ$. "
                  rf"От правоъгълния $\triangle APC$ следва $\sphericalangle ACP = "
                  rf"90^\circ - {alpha}^\circ = {90 - alpha}^\circ$. Тогава "
                  rf"$\sphericalangle PCL = {gamma // 2}^\circ - ({90 - alpha}^\circ) "
                  rf"= {key}^\circ$"),
        signature=f"tri_hbm:{alpha}:{beta}",
    )


@template("tri_exterior_angle_at_base",
          topics=["geom_lines_angles"], kinds=["mc"], weight=1.2, band="easy")
def tri_exterior_angle_at_base(rng: random.Random, slot: Slot) -> GeneratedItem:
    """AB produced past B; given the exterior angle at B and ∠BAC, find ∠ACB.

    The exterior angle theorem as the 2015, 2022 and 2023 papers pose it: the
    exterior angle equals the sum of the two remote interior ones, so the
    answer is a single subtraction — which is why this one is banded easy.
    """
    ext = rng.choice(angle_span(slot, 95, 135, step=1))
    alpha = rng.choice(angle_span(slot, 28, 62, step=1))
    key = ext - alpha                                   # ∠ACB
    beta = 180 - ext                                    # ∠ABC, supplementary
    if key <= 20 or beta <= 20 or alpha + beta + key != 180:
        raise Retry("every angle of the triangle must stay readable")

    # Drawn to its angles, with E named: the stem is about ∠CBE, and E used to
    # be a hidden anchor with no label, so the angle it asks about was at a
    # point the figure never showed.
    f = triangle_from_angles(alpha, beta, rng=rng)
    A, B = f.points["A"], f.points["B"]
    f.put("E", add(B, scale(sub(B, A), rng.uniform(0.30, 0.42))))
    f.path(["A", "B", "C"], close=True)
    f.seg("B", "E")
    f.angle("A", "B", "C", label=deg(alpha), radius=24)
    f.angle("B", "C", "E", label=deg(ext), radius=22)
    f.angle("C", "A", "B", arcs=1, fill=True, radius=22)

    options, letter = angle_options(
        key, extras=[beta, ext, alpha, 180 - alpha], rng=rng)
    return GeneratedItem(
        topic=slot.topic, kind="mc", points=slot.points,
        stem=("На чертежа точката $E$ лежи върху продължението на страната $AB$ "
              "отвъд върха $B$. Ако $\\sphericalangle CBE = "
              f"{ext}^\\circ$ и $\\sphericalangle BAC = {alpha}^\\circ$, то мярката "
              "на $\\sphericalangle ACB$ е:"),
        options=options, correct_answer=letter, difficulty="easy",
        scene=f.to_spec(aria=(f"Триъгълник ABC със страна AB, продължена отвъд B до точка E; "
                              f"външният ъгъл при B е {ext} градуса, ъгълът при A е "
                              f"{alpha} градуса"), rng=rng),
        solution=(rf"Външният ъгъл при $B$ е равен на сбора от двата несъседни "
                  rf"вътрешни ъгъла: $\sphericalangle CBE = \sphericalangle BAC + "
                  rf"\sphericalangle ACB$, откъдето $\sphericalangle ACB = "
                  rf"{ext}^\circ - {alpha}^\circ = {key}^\circ$"),
        signature=f"tri_ext_base:{ext}:{alpha}",
    )


@template("tri_cevian_exterior_angle",
          topics=["geom_triangle_cevians"], kinds=["mc"], weight=1.1, band="medium")
def tri_cevian_exterior_angle(rng: random.Random, slot: Slot) -> GeneratedItem:
    """A cevian CD splits the base; ∠CDB is exterior to △ACD, so it is α + ∠ACD.

    The 2017, 2018 and 2024 shape. The exterior angle here is not made by
    producing a side but by the cevian itself — ∠ADC and ∠CDB are the two
    angles on the straight line AB at D.
    """
    alpha = rng.choice(angle_span(slot, 28, 67, step=1))          # ∠BAC
    delta = rng.choice(angle_span(slot, 13, 43, step=1))                  # ∠ACD
    key = alpha + delta                                 # ∠CDB
    if key >= 155 or key <= 40:
        raise Retry("∠CDB must be a readable angle strictly inside a straight one")

    # ∠A true, and D where CD really makes ∠ACD = δ with CA. ∠B is free, so
    # it is chosen to leave ∠ACB comfortably wider than δ.
    # A flat ∠B makes AC short, and AD with it: at ∠B = 32° D fell 38 units
    # from A, too close for ∠A's value to fit between its arc and CD, and it
    # went outside CA, next to the value of ∠ACD.
    room_b = 180 - alpha - max(delta, 22) - 22
    if room_b < 36:
        raise Retry("no room for ∠ACB to exceed ∠ACD")
    beta_drawn = rng.uniform(36, min(room_b, 70))
    f = triangle_from_angles(alpha, beta_drawn, rng=rng)
    A, B, C = f.points["A"], f.points["B"], f.points["C"]
    towards = sub(A, C)
    # A 13° arc is a smudge, and its value has nowhere to sit; hold the drawn
    # ∠ACD at 22° or more.
    shown_delta = max(delta, 22)
    t = math.radians(shown_delta) * (1 if (A[0] - C[0]) * (B[1] - C[1]) - (A[1] - C[1]) * (B[0] - C[0]) > 0 else -1)
    ray = (towards[0] * math.cos(t) - towards[1] * math.sin(t),
           towards[0] * math.sin(t) + towards[1] * math.cos(t))
    D = line_intersection(C, add(C, ray), A, B)
    if D is None:
        raise Retry("CD missed AB")
    if math.dist(A, D) < 0.27 * math.dist(A, B):
        raise Retry("D too close to A for the value of ∠A to sit inside it")
    f.put("D", D)
    f.path(["A", "B", "C"], close=True)
    f.seg("C", "D")
    f.angle("A", "B", "C", label=deg(alpha), radius=24)
    f.angle("C", "A", "D", label=deg(delta), radius=26)
    f.angle("D", "C", "B", arcs=1, fill=True, radius=22)

    options, letter = angle_options(
        key, extras=[180 - key, alpha, delta, 180 - alpha - delta], rng=rng)
    return GeneratedItem(
        topic=slot.topic, kind="mc", points=slot.points,
        stem=("На чертежа точката $D$ лежи върху страната $AB$ на $\\triangle ABC$. "
              f"Ако $\\sphericalangle BAC = {alpha}^\\circ$ и $\\sphericalangle ACD "
              f"= {delta}^\\circ$, то мярката на $\\sphericalangle CDB$ е:"),
        options=options, correct_answer=letter, difficulty="medium",
        scene=f.to_spec(aria=(f"Триъгълник ABC с отсечка CD към страната AB; отбелязани са "
                              f"ъгъл {alpha} градуса при A и {delta} градуса при C"), rng=rng),
        solution=(rf"$\sphericalangle CDB$ е външен ъгъл за $\triangle ACD$ при върха "
                  rf"$D$, затова е равен на сбора от несъседните вътрешни ъгли: "
                  rf"$\sphericalangle CDB = {alpha}^\circ + {delta}^\circ = {key}^\circ$"),
        signature=f"tri_cev_ext:{alpha}:{delta}",
    )


@template("rect_diagonals_angle",
          topics=["geom_quadrilateral"], kinds=["mc"], weight=1.2, band="medium")
def rect_diagonals_angle(rng: random.Random, slot: Slot) -> GeneratedItem:
    """Rectangle diagonals meet at O; given ∠AOB, find ∠ACB.

    The 2017 and 2026 figure. It turns on the property that makes a rectangle's
    diagonals special: they are equal and bisect each other, so all four
    half-diagonals are equal and every triangle at O is isosceles. ∠BOC is
    supplementary to ∠AOB, which hands back ∠OCB = ∠AOB/2.
    """
    theta = rng.choice(angle_span(slot, 50, 130, step=2))       # ∠AOB
    if theta % 2:
        raise Retry("∠ACB must be a whole number of degrees")
    key = theta // 2                                    # ∠ACB
    if key <= 20 or key >= 70:
        raise Retry("∠ACB must stay clear of the degenerate ends")

    # A rectangle whose diagonals really meet at θ: AB : BC = tan(θ/2).
    f = parallelogram_from_angle(90, 1.0 / math.tan(math.radians(theta / 2)), rng=rng)
    A, B, C, D = (f.points[n] for n in "ABCD")
    O = line_intersection(A, C, B, D)
    if O is None:
        raise Retry("degenerate rectangle has no diagonal crossing")
    f.put("O", O, dot=True)
    f.path(["A", "B", "C", "D"], close=True)
    f.segs([("A", "C"), ("B", "D")])
    f.angle("O", "A", "B", label=deg(theta), radius=22)
    f.angle("C", "A", "B", arcs=1, fill=True, radius=26)

    options, letter = angle_options(
        key, extras=[theta, 180 - theta, (180 - theta) // 2, 90 - key], rng=rng)
    return GeneratedItem(
        topic=slot.topic, kind="mc", points=slot.points,
        stem=("На чертежа $ABCD$ е правоъгълник, а диагоналите му се пресичат в "
              f"точка $O$. Ако $\\sphericalangle AOB = {theta}^\\circ$, то мярката "
              "на $\\sphericalangle ACB$ е:"),
        options=options, correct_answer=letter, difficulty="medium",
        scene=f.to_spec(aria=(f"Правоъгълник ABCD с двата диагонала и пресечната им точка O; "
                              f"ъгълът AOB е {theta} градуса"), rng=rng, upright=True),
        solution=(rf"Диагоналите на правоъгълник са равни и се разполовяват, затова "
                  rf"$OB = OC$ и $\triangle BOC$ е равнобедрен. От "
                  rf"$\sphericalangle BOC = 180^\circ - {theta}^\circ = "
                  rf"{180 - theta}^\circ$ следва $\sphericalangle ACB = "
                  rf"\dfrac{{180^\circ - {180 - theta}^\circ}}{{2}} = {key}^\circ$"),
        signature=f"rect_diag:{theta}",
    )


@template("tri_perpendicular_from_side_point",
          topics=["geom_triangle_cevians"], kinds=["mc"], weight=1.1, band="medium")
def tri_perpendicular_from_side_point(rng: random.Random, slot: Slot) -> GeneratedItem:
    """N on BC, NM ⟂ AB; given ∠BAC and ∠ACB, find ∠MNB.

    The 2018 and 2025 shape. Two steps: the triangle's angle sum gives ∠ABC,
    then the right triangle BMN gives ∠MNB as its complement.
    """
    alpha = rng.choice(angle_span(slot, 48, 77, step=1))                  # ∠BAC
    gamma = rng.choice(angle_span(slot, 48, 77, step=1))                  # ∠ACB
    beta = 180 - alpha - gamma
    key = 90 - beta                                     # ∠MNB
    if beta <= 20 or key <= 20 or key >= 80:
        raise Retry("both the triangle and the right triangle must stay readable")

    f = triangle_from_angles(alpha, beta, rng=rng)
    A, B, C = f.points["A"], f.points["B"], f.points["C"]
    N = f.put("N", lerp(B, C, rng.uniform(0.38, 0.58)))
    f.put("M", foot_of_perpendicular(N, A, B))
    f.path(["A", "B", "C"], close=True)
    f.seg("N", "M")
    f.right_angle("M", "N", "B")
    f.angle("A", "B", "C", label=deg(alpha), radius=24)
    f.angle("C", "A", "B", label=deg(gamma), radius=22)
    f.angle("N", "M", "B", arcs=1, fill=True, radius=20)

    options, letter = angle_options(
        key, extras=[beta, 90 - alpha, 90 - gamma, alpha + gamma - 90], rng=rng)
    return GeneratedItem(
        topic=slot.topic, kind="mc", points=slot.points,
        stem=("На чертежа точката $N$ лежи върху страната $BC$ на $\\triangle ABC$, "
              "а $NM \\perp AB$. Ако $\\sphericalangle BAC = "
              f"{alpha}^\\circ$ и $\\sphericalangle ACB = {gamma}^\\circ$, то мярката "
              "на $\\sphericalangle MNB$ е:"),
        options=options, correct_answer=letter, difficulty="medium",
        scene=f.to_spec(aria=(f"Триъгълник ABC с точка N върху BC и перпендикуляр NM към AB; "
                              f"отбелязани са ъгли {alpha} градуса при A и {gamma} градуса "
                              f"при C"), rng=rng),
        solution=(rf"$\sphericalangle ABC = 180^\circ - {alpha}^\circ - {gamma}^\circ "
                  rf"= {beta}^\circ$. В правоъгълния $\triangle BMN$ острите ъгли се "
                  rf"допълват до $90^\circ$, затова $\sphericalangle MNB = 90^\circ - "
                  rf"{beta}^\circ = {key}^\circ$"),
        signature=f"tri_perp_side:{alpha}:{gamma}",
    )


@template("tri_circumcentre_central_angle",
          topics=["geom_bisectors_incentre"], kinds=["mc", "short"],
          weight=1.2, band="hard")
def tri_circumcentre_central_angle(rng: random.Random, slot: Slot) -> GeneratedItem:
    """The perpendicular bisectors meet at O; given ∠BAC and ∠ABC, find ∠AOB.

    The 2019 and 2025 figure, both of which draw two of the three bisectors and
    call their meeting point O. The central angle over AB is twice the
    inscribed ∠ACB — the one genuinely non-obvious fact in the geometry that
    the seventh-grade syllabus reaches.
    """
    alpha = rng.choice(angle_span(slot, 45, 72, step=1))                      # ∠BAC
    beta = rng.choice(angle_span(slot, 45, 72, step=1))                      # ∠ABC
    gamma = 180 - alpha - beta
    key = 2 * gamma                                     # ∠AOB
    if gamma <= 30 or gamma >= 85 or key >= 175:
        raise Retry("the triangle must be acute for O to sit inside it")

    # O lies R·cos γ from AB, so past γ ≈ 70° it closes in on AB until the arc
    # of ∠AOB runs into the right-angle mark at the midpoint of AB. The drawing
    # takes the excess from ∠C and gives it to ∠A and ∠B, a few degrees each.
    excess = max(0, gamma - 70)
    f = triangle_from_angles(alpha + excess / 2, beta + excess / 2, rng=rng)
    A, B, C = f.points["A"], f.points["B"], f.points["C"]
    O = circumcentre(A, B, C)
    if O is None:
        raise Retry("degenerate triangle has no circumcentre")
    f.put("O", O, dot=True)
    # The feet of the two bisectors are not named in the stem, so they carry
    # no letters — only the marks that make each dashed line a *perpendicular
    # bisector*: equal halves, and the right angle, which used to be missing.
    f.put("P", midpoint(A, B), hidden=True)
    f.put("Q", midpoint(A, C), hidden=True)
    f.path(["A", "B", "C"], close=True)
    f.segs([("O", "A"), ("O", "B")])
    f.segs([("O", "P"), ("O", "Q")], dash=True)
    f.right_angle("P", "O", "B", size=7.0)
    f.right_angle("Q", "O", "C", size=7.0)
    f.tick("A", "P")
    f.tick("P", "B")
    f.tick("A", "Q", count=2)
    f.tick("Q", "C", count=2)
    f.angle("A", "B", "C", label=deg(alpha), radius=22)
    f.angle("B", "C", "A", label=deg(beta), radius=22)
    f.angle("O", "A", "B", arcs=1, fill=True, radius=20)

    stem = ("На чертежа симетралите на страните $AB$ и $AC$ на $\\triangle ABC$ "
            "се пресичат в точка $O$. Ако $\\sphericalangle BAC = "
            f"{alpha}^\\circ$ и $\\sphericalangle ABC = {beta}^\\circ$,")
    aria = (f"Остроъгълен триъгълник ABC със симетралите на AB и AC, пресичащи се "
            f"в точка O; отбелязани са ъгли {alpha} и {beta} градуса")
    solution = (rf"$\sphericalangle ACB = 180^\circ - {alpha}^\circ - {beta}^\circ "
                rf"= {gamma}^\circ$. Точката $O$ е центърът на описаната окръжност, "
                rf"защото $OA = OB = OC$. Централният ъгъл е два пъти вписания над "
                rf"същата дъга: $\sphericalangle AOB = 2 \cdot {gamma}^\circ "
                rf"= {key}^\circ$")

    if slot.kind == "short":
        return GeneratedItem(
            topic=slot.topic, kind="short", points=slot.points,
            stem=stem + " намерете мярката на $\\sphericalangle AOB$.",
            correct_answer=f"{key}°", difficulty="hard",
            scene=f.to_spec(aria=aria, rng=rng), solution=solution,
            signature=f"tri_circum:{alpha}:{beta}",
        )

    options, letter = angle_options(
        key, extras=[gamma, 180 - gamma, 2 * alpha, 2 * beta], rng=rng)
    return GeneratedItem(
        topic=slot.topic, kind="mc", points=slot.points,
        stem=stem + " то мярката на $\\sphericalangle AOB$ е:",
        options=options, correct_answer=letter, difficulty="hard",
        scene=f.to_spec(aria=aria, rng=rng), solution=solution,
        signature=f"tri_circum:{alpha}:{beta}",
    )


@template("line_through_vertex_angles",
          topics=["geom_lines_angles"], kinds=["mc"], weight=1.1, band="easy")
def line_through_vertex_angles(rng: random.Random, slot: Slot) -> GeneratedItem:
    """K, C, M collinear through the apex; the three angles at C fill a straight one.

    The 2019 and 2025 shape. No parallelism is needed and none is claimed — the
    whole content is that ∠KCA, ∠ACB and ∠BCM sit on one straight line at C.
    """
    alpha = rng.choice(angle_span(slot, 28, 62, step=1))              # ∠KCA
    gamma = rng.choice(angle_span(slot, 48, 82, step=1))              # ∠ACB
    key = 180 - alpha - gamma                           # ∠BCM
    if key <= 20:
        raise Retry("∠BCM must remain a readable angle")

    # The line is drawn parallel to AB because that is how the papers draw it,
    # but the item never uses the parallelism — only that K, C, M are collinear.
    # Parallel to AB, ∠KCA and ∠BCM are alternate to ∠A and ∠B, so drawing the
    # triangle at ∠A = α and ∠B = ∠BCM makes every marked angle true.
    f = triangle_from_angles(alpha, key, rng=rng)
    A, B, C = f.points["A"], f.points["B"], f.points["C"]
    d = unit(sub(B, A))
    reach = min(C[0] - 30.0, 230.0 - C[0], 58.0)
    if reach < 34.0:
        raise Retry("no room either side of C for the line and its labels")
    f.put("K", add(C, scale(d, -reach)))
    f.put("M", add(C, scale(d, reach)))
    f.path(["A", "B", "C"], close=True)
    f.segs([("K", "C"), ("C", "M")])
    f.angle("C", "K", "A", label=deg(alpha), radius=24)
    f.angle("C", "A", "B", label=deg(gamma), radius=32)
    f.angle("C", "B", "M", arcs=1, fill=True, radius=24)

    options, letter = angle_options(
        key, extras=[alpha, gamma, alpha + gamma, 180 - gamma], rng=rng)
    return GeneratedItem(
        topic=slot.topic, kind="mc", points=slot.points,
        stem=("На чертежа точките $K$, $C$ и $M$ лежат на една права. Ако "
              f"$\\sphericalangle KCA = {alpha}^\\circ$ и $\\sphericalangle ACB = "
              f"{gamma}^\\circ$, то мярката на $\\sphericalangle BCM$ е:"),
        options=options, correct_answer=letter, difficulty="easy",
        scene=f.to_spec(aria=(f"Триъгълник ABC и права през върха C с точки K и M от двете "
                              f"страни; отбелязани са ъгли {alpha} и {gamma} градуса при C"),
                        rng=rng),
        solution=(rf"Трите ъгъла при $C$ допълват изправен ъгъл, защото $K$, $C$ и $M$ "
                  rf"лежат на една права: $\sphericalangle BCM = 180^\circ - "
                  rf"{alpha}^\circ - {gamma}^\circ = {key}^\circ$"),
        signature=f"line_vertex:{alpha}:{gamma}",
    )


@template("symbolic_area_notched_rectangle",
          topics=["symbolic_perimeter"], kinds=["short", "mc"],
          weight=1.2, band="medium")
def symbolic_area_notched_rectangle(rng: random.Random, slot: Slot) -> GeneratedItem:
    """An L-shape: a rectangle x by y with a small corner cut out.

    The 2016 and 2019 composite-area shape. The figure is not decoration here —
    "the shaded part" has no meaning without it, which is why `fills` is scene
    data rather than styling.

    Every point is hidden. The papers label these with dimensions, not vertex
    names, and suppressing the letters also removes the label-collision risk
    entirely: seven points round a notch is exactly where `MIN_LABEL_GAP`
    would start rejecting draws.
    """
    # lengths, not angles: the level decides how big, not how round
    a = rng.choice(slot.profile.tier([2, 3], [2, 3, 4], [2, 3, 4, 5, 6], [3, 4, 5, 6, 7, 8]))
    b = rng.choice(slot.profile.tier([2, 3], [2, 3, 5], [2, 3, 4, 5, 6, 7], [3, 4, 5, 7, 8, 9]))
    cut = a * b

    f = Figure()
    left, right = 34.0, 214.0
    top, bottom = 40.0, 140.0
    notch_w = 30.0 + 11.0 * a
    notch_h = 18.0 + 8.0 * b
    if notch_w > (right - left) * 0.55 or notch_h > (bottom - top) * 0.62:
        raise Retry("the cut-out would swallow the shape it is cut from")

    f.put("A", (left, bottom), hidden=True)
    f.put("N1", (right - notch_w, bottom), hidden=True)
    f.put("N2", (right - notch_w, bottom - notch_h), hidden=True)
    f.put("N3", (right, bottom - notch_h), hidden=True)
    f.put("C", (right, top), hidden=True)
    f.put("D", (left, top), hidden=True)

    outline = ["A", "N1", "N2", "N3", "C", "D"]
    f.fill_region(outline)
    f.path(outline, close=True)
    f.label_along("D", "C", "x", italic=True)
    f.label_along("A", "D", "y", italic=True)
    f.label_along("N2", "N3", str(a))
    f.label_along("N1", "N2", str(b))

    scene = f.to_spec(
        aria=(f"Правоъгълник със страни x и y, от който е изрязан правоъгълник "
              f"със страни {a} и {b}; останалата защрихована част е с форма на буквата Г"),
        rng=rng, upright=True,
    )
    solution = (rf"Лицето на целия правоъгълник е $xy$, а на изрязания — "
                rf"${a} \cdot {b} = {cut}$. Защрихованата част е "
                rf"$xy - {cut}$.")

    if slot.kind == "short":
        return GeneratedItem(
            topic=slot.topic, kind="short", points=slot.points,
            stem=("На чертежа е показан правоъгълник със страни $x$ cm и $y$ cm, от "
                  "който е изрязан правоъгълник. Изразете чрез $x$ и $y$ лицето на "
                  "защрихованата част в квадратни сантиметри."),
            correct_answer=f"xy - {cut}",
            difficulty="medium", scene=scene, solution=solution,
            signature=f"notched:{a}:{b}",
        )

    options, letter = shuffle_options(
        rf"$xy - {cut}$",
        [rf"$xy + {cut}$", rf"$xy - {a + b}$", rf"$2(x + y) - {2 * (a + b)}$"],
        rng=rng,
    )
    return GeneratedItem(
        topic=slot.topic, kind="mc", points=slot.points,
        stem=("На чертежа е показан правоъгълник със страни $x$ cm и $y$ cm, от "
              "който е изрязан правоъгълник. Лицето на защрихованата част в "
              "квадратни сантиметри е:"),
        options=options, correct_answer=letter,
        difficulty="medium", scene=scene, solution=solution,
        signature=f"notched:{a}:{b}",
    )


# ─── archetypes that appear once in the corpus ───────────────────────────────
# The audit's two-paper bar was about fidelity to the historical corpus, not
# about usefulness: a template does not fire once just because its shape
# appeared once. Once registered it joins the eligible pool for its topic and
# is drawable on any paper, so these widen the thinnest slots -- three of them
# feed geom_quadrilateral, which had the least depth of any geometry slot.


@template("parallelogram_height_area",
          topics=["geom_quadrilateral"], kinds=["mc"], weight=1.1, band="medium")
def parallelogram_height_area(rng: random.Random, slot: Slot) -> GeneratedItem:
    """A 30° parallelogram: the height is half the slant side, so the area is whole.

    The 2017 shape. 30° is not decoration — it is the one angle at which the
    height comes out rational without a surd, which is exactly why the official
    figure uses it and why this template fixes it rather than sampling it.
    """
    # lengths, not angles: the level decides how big, not how round
    side = rng.choice(slot.profile.tier([6, 8], [6, 8, 10], list(range(4, 17, 2)),
                                        list(range(6, 21, 2))))
    base = rng.choice(slot.profile.tier([10, 12], [8, 10, 12, 14], list(range(7, 17)),
                                        list(range(9, 24, 2))))
    if side % 2:
        raise Retry("the height side/2 must be a whole number of centimetres")
    if side * 0.866 > base * 0.8:
        # With AD·cos 30° ≥ AB the foot of the height falls past B, on the
        # extension of AB — a different figure from the one printed here; and
        # just short of that, H is drawn on top of B.
        raise Retry("the foot of the height must land well inside AB")
    height = side // 2
    key = base * height

    # Drawn in its true proportions: AD : AB used to be clamped, so AD = 16 cm
    # was drawn shorter than AB = 11 cm.
    f = parallelogram_from_angle(30, max(0.35, side / base), rng=rng)
    A, B, D = f.points["A"], f.points["B"], f.points["D"]
    f.put("H", foot_of_perpendicular(D, A, B))
    f.path(["A", "B", "C", "D"], close=True)
    f.seg("D", "H", dash=True)
    f.right_angle("H", "D", "B")
    # A tighter arc than usual: the value has to fit between it and the height
    # DH, which a short AD brings to within 50 units of A.
    f.angle("A", "B", "D", label=deg(30), radius=20)
    # The lengths stay in the stem only. H cuts AB near its middle, so „15 cm”
    # had nowhere to go: centred it hit „H”, and beside it it read as HB.

    options, letter = numeric_options(
        key, [base * side, base * side // 2 + base, key * 2, base + side,
              2 * (base + side)], rng=rng, positive_only=True,
        suffix=r"\ \text{cm}^2")
    return GeneratedItem(
        topic=slot.topic, kind="mc", points=slot.points,
        stem=("На чертежа $ABCD$ е успоредник, а $DH$ е височина към страната "
              f"$AB$. Ако $\\sphericalangle DAB = 30^\\circ$, $AB = {base}$ cm и "
              f"$AD = {side}$ cm, то лицето на успоредника е:"),
        options=options, correct_answer=letter, difficulty="medium",
        scene=f.to_spec(aria=(f"Успоредник ABCD с височина DH към AB, ъгъл 30 градуса "
                              f"при A, AB = {base} cm и AD = {side} cm"),
                        rng=rng, upright=True),
        solution=(rf"В правоъгълния $\triangle AHD$ срещу ъгъла от $30^\circ$ стои "
                  rf"катетът $DH$, значи $DH = \frac{{AD}}{{2}} = {height}$ cm. "
                  rf"Лицето е $AB \cdot DH = {base} \cdot {height} = {key}$ cm$^2$"),
        signature=f"par_height:{base}:{side}",
    )


@template("square_diagonal_angle",
          topics=["geom_quadrilateral"], kinds=["mc"], weight=1.0, band="easy")
def square_diagonal_angle(rng: random.Random, slot: Slot) -> GeneratedItem:
    """A square's diagonal bisects its right angle, so ∠MAD = 45° − ∠MAC."""
    t = rng.choice(angle_span(slot, 5, 37, step=1))
    key = 45 - t
    if key <= 5:
        raise Retry("∠MAD must stay a readable angle")

    f = parallelogram(square=True, rng=rng)
    A, C, D = f.points["A"], f.points["C"], f.points["D"]
    # ∠DAM = arctan(DM/AD) and ∠MAC = 45° minus it, so M is put where ∠MAC is
    # the stated t — held between 20° and 28° so both arcs, and the value
    # inside the narrower one, stay readable.
    shown = min(max(t, 20), 28)
    f.put("M", lerp(D, C, math.tan(math.radians(45 - shown))), dot=True)
    f.path(["A", "B", "C", "D"], close=True)
    f.seg("A", "C")
    f.seg("A", "M")
    f.angle("A", "M", "C", label=deg(t), radius=30)
    f.angle("A", "D", "M", arcs=1, fill=True, radius=22)

    options, letter = angle_options(key, extras=[t, 45, 90 - t, 45 + t], rng=rng)
    return GeneratedItem(
        topic=slot.topic, kind="mc", points=slot.points,
        stem=("На чертежа $ABCD$ е квадрат, $AC$ е диагонал, а точката $M$ лежи "
              f"върху страната $DC$. Ако $\\sphericalangle MAC = {t}^\\circ$, то "
              "мярката на $\\sphericalangle MAD$ е:"),
        options=options, correct_answer=letter, difficulty="easy",
        scene=f.to_spec(aria=(f"Квадрат ABCD с диагонал AC и точка M върху DC; ъгълът "
                              f"MAC е {t} градуса"), rng=rng, upright=True),
        solution=(rf"Диагоналът на квадрат е ъглополовяща, затова "
                  rf"$\sphericalangle DAC = 45^\circ$. Тогава "
                  rf"$\sphericalangle MAD = 45^\circ - {t}^\circ = {key}^\circ$"),
        signature=f"sq_diag:{t}",
    )


@template("trapezoid_cointerior_angle",
          topics=["geom_quadrilateral"], kinds=["mc"], weight=1.0, band="easy")
def trapezoid_cointerior_angle(rng: random.Random, slot: Slot) -> GeneratedItem:
    """A right trapezoid: AB ∥ DC makes ∠ABC and ∠BCD co-interior."""
    bcd = rng.choice(angle_span(slot, 100, 143, step=1))
    key = 180 - bcd
    if not 25 <= key <= 85:
        raise Retry("∠ABC must be a readable acute angle")

    f = right_trapezoid(rng=rng)
    # Set the slant so ∠BCD is drawn at its stated measure.
    A, B, C, D = (f.points[n] for n in "ABCD")
    inset = (A[1] - D[1]) / math.tan(math.radians(180 - bcd))
    if inset > (B[0] - A[0]) * 0.7:
        raise Retry("the slant would leave no top side")
    f.put("C", (B[0] - inset, D[1]))
    f.path(["A", "B", "C", "D"], close=True)
    f.right_angle("A", "D", "B")
    f.right_angle("D", "A", "C")
    f.angle("C", "D", "B", label=deg(bcd), radius=24)
    f.angle("B", "A", "C", arcs=1, fill=True, radius=24)

    options, letter = angle_options(key, extras=[bcd, 90, bcd - 90, 360 - bcd], rng=rng)
    return GeneratedItem(
        topic=slot.topic, kind="mc", points=slot.points,
        stem=("На чертежа $ABCD$ е трапец с $AB \\parallel DC$ и $AD \\perp AB$. "
              f"Ако $\\sphericalangle BCD = {bcd}^\\circ$, то мярката на "
              "$\\sphericalangle ABC$ е:"),
        options=options, correct_answer=letter, difficulty="easy",
        scene=f.to_spec(aria=(f"Правоъгълен трапец ABCD с AB успоредна на DC; ъгълът "
                              f"BCD е {bcd} градуса"), rng=rng, upright=True),
        solution=(rf"$AB \parallel DC$, а $BC$ е трансверзала, затова "
                  rf"$\sphericalangle ABC$ и $\sphericalangle BCD$ са прилежащи "
                  rf"и се допълват до $180^\circ$: $\sphericalangle ABC = "
                  rf"180^\circ - {bcd}^\circ = {key}^\circ$"),
        signature=f"trap_coint:{bcd}",
    )


@template("triangle_midsegment_perimeter",
          topics=["geom_triangle_cevians"], kinds=["mc"], weight=1.0, band="medium")
def triangle_midsegment_perimeter(rng: random.Random, slot: Slot) -> GeneratedItem:
    """M and N are midpoints, so △MNC is a half-scale copy of △ABC."""
    sides = sorted(rng.sample(
        slot.profile.tier([6, 8, 10, 12], [6, 8, 10, 12, 14],
                          [6, 8, 10, 12, 14, 16, 18], [6, 8, 10, 12, 14, 16, 18, 20]), 3))
    a, b, c = sides
    if a + b <= c or len({a, b, c}) < 3:
        raise Retry("the three sides must make a scalene triangle")
    perim = a + b + c
    if perim % 2:
        raise Retry("the midsegment triangle's perimeter must be whole")
    key = perim // 2

    f = triangle_for_three_cevians(rng=rng)
    A, B, C = f.points["A"], f.points["B"], f.points["C"]
    f.put("M", midpoint(A, C), dot=True)
    f.put("N", midpoint(B, C), dot=True)
    f.path(["A", "B", "C"], close=True)
    f.seg("M", "N")
    f.tick("A", "M")
    f.tick("M", "C")
    f.tick("B", "N", count=2)
    f.tick("N", "C", count=2)

    options, letter = numeric_options(
        key, [perim, perim // 2 + c, c, perim - c, key * 2], rng=rng,
        positive_only=True, suffix=r"\ \text{cm}")
    return GeneratedItem(
        topic=slot.topic, kind="mc", points=slot.points,
        stem=("На чертежа точките $M$ и $N$ са среди съответно на страните $AC$ и "
              f"$BC$ на $\\triangle ABC$. Ако обиколката на $\\triangle ABC$ е "
              f"${perim}$ cm, то обиколката на $\\triangle MNC$ е:"),
        options=options, correct_answer=letter, difficulty="medium",
        scene=f.to_spec(aria=("Триъгълник ABC със средна отсечка MN, където M и N са "
                              "среди на AC и BC"), rng=rng),
        solution=(rf"$MN$ е средна отсечка, значи $MN = \frac{{AB}}{{2}}$, а също "
                  rf"$MC = \frac{{AC}}{{2}}$ и $NC = \frac{{BC}}{{2}}$. Всяка страна "
                  rf"на $\triangle MNC$ е два пъти по-малка, затова и обиколката е: "
                  rf"$\frac{{{perim}}}{{2}} = {key}$ cm"),
        signature=f"midseg:{a}:{b}:{c}",
    )


@template("isosceles_height_apex_angle",
          topics=["geom_right_triangle"], kinds=["mc"], weight=1.0, band="easy")
def isosceles_height_apex_angle(rng: random.Random, slot: Slot) -> GeneratedItem:
    """The height to the base of an isosceles triangle bisects the apex angle."""
    apex = rng.choice(angle_span(slot, 30, 104, step=2))
    if apex % 2:
        raise Retry("half the apex angle must be whole")
    key = 90 - apex // 2                       # the base angle
    if not 25 <= key <= 80:
        raise Retry("the base angle must stay readable")

    f = triangle_from_angles(key, key, rng=rng)
    A, B, C = f.points["A"], f.points["B"], f.points["C"]
    f.put("H", midpoint(A, B))
    f.path(["A", "B", "C"], close=True)
    f.seg("C", "H")
    f.right_angle("H", "C", "B")
    f.tick("A", "C")
    f.tick("B", "C")
    f.angle("C", "A", "B", label=deg(apex), radius=26)
    # The stem asks for ∠ABC, so that is the one shaded — it used to be ∠BAC.
    f.angle("B", "A", "C", arcs=1, fill=True, radius=22)

    options, letter = angle_options(
        key, extras=[apex, apex // 2, 180 - apex, 90 - apex], rng=rng)
    return GeneratedItem(
        topic=slot.topic, kind="mc", points=slot.points,
        stem=("На чертежа $\\triangle ABC$ е равнобедрен с $AC = BC$, а $CH$ е "
              f"височина към основата $AB$. Ако $\\sphericalangle ACB = {apex}"
              "^\\circ$, то мярката на $\\sphericalangle ABC$ е:"),
        options=options, correct_answer=letter, difficulty="easy",
        scene=f.to_spec(aria=(f"Равнобедрен триъгълник ABC с височина CH към основата "
                              f"AB; ъгълът при върха C е {apex} градуса"), rng=rng),
        solution=(rf"Височината към основата на равнобедрен триъгълник е и "
                  rf"ъглополовяща, значи $\sphericalangle HCB = "
                  rf"\frac{{{apex}^\circ}}{{2}} = {apex // 2}^\circ$. В правоъгълния "
                  rf"$\triangle HCB$ острите ъгли се допълват до $90^\circ$: "
                  rf"$\sphericalangle ABC = 90^\circ - {apex // 2}^\circ = {key}^\circ$"),
        signature=f"iso_height:{apex}",
    )


@template("segment_parts_algebraic",
          topics=["symbolic_perimeter"], kinds=["short", "mc"], weight=1.0, band="easy")
def segment_parts_algebraic(rng: random.Random, slot: Slot) -> GeneratedItem:
    """AB split into three parts given through x — the 2015 shape."""
    extra = rng.choice(angle_span(slot, 6, 19, step=1))
    x = rng.choice(angle_span(slot, 2, 11, step=1))
    total = 4 * x + extra                      # x + 2x + (x + extra)

    f = Figure()
    y = 92.0
    ax, bx = 30.0, 226.0
    # Parts drawn in their true order of size: halfway between true proportion
    # and equal thirds, so a 2-cm part is not a speck and x + 19 is not drawn
    # shorter than 2x.
    parts = [x, 2 * x, x + extra]
    shares = [0.55 * p / total + 0.45 / 3 for p in parts]
    c_at = ax + (bx - ax) * shares[0]
    d_at = c_at + (bx - ax) * shares[1]
    f.put("A", (ax, y), dot=True)
    f.put("C", (c_at, y), dot=True)
    f.put("D", (d_at, y), dot=True)
    f.put("B", (bx, y), dot=True)
    f.path(["A", "C", "D", "B"])
    f.label_along("A", "C", "x", italic=True)
    f.label_along("C", "D", "2x", italic=True)
    f.label_along("D", "B", f"x + {extra}", italic=True)

    scene = f.to_spec(
        aria=(f"Отсечка AB с точки C и D върху нея; частите са x, 2x и x + {extra}"),
        rng=rng, upright=True)
    solution = (rf"$AB = x + 2x + (x + {extra}) = 4x + {extra}$. От "
                rf"$4x + {extra} = {total}$ следва $4x = {total - extra}$ и "
                rf"$x = {x}$.")
    stem = ("На чертежа точките $C$ и $D$ лежат върху отсечката $AB$, а дължините "
            "на частите са означени на чертежа (в сантиметри). "
            f"Ако $AB = {total}$ cm,")

    if slot.kind == "short":
        return GeneratedItem(
            topic=slot.topic, kind="short", points=slot.points,
            stem=stem + " намерете $x$.", correct_answer=f"{x}",
            difficulty="easy", scene=scene, solution=solution,
            signature=f"seg_parts:{x}:{extra}",
        )

    options, letter = numeric_options(
        x, [total - extra, (total - extra) // 2, x + 1, x * 2, total // 4], rng=rng,
        positive_only=True)
    return GeneratedItem(
        topic=slot.topic, kind="mc", points=slot.points,
        stem=stem + " то $x$ е равно на:", options=options, correct_answer=letter,
        difficulty="easy", scene=scene, solution=solution,
        signature=f"seg_parts:{x}:{extra}",
    )


@template("coordinate_shaded_triangle_area",
          topics=["geom_coordinate"], kinds=["mc"], weight=1.0, band="medium")
def coordinate_shaded_triangle_area(rng: random.Random, slot: Slot) -> GeneratedItem:
    """All three vertices plotted and the triangle shaded — read its area off the grid.

    Distinct from `coordinate_triangle_area`, where the third vertex is not
    drawn and constructing it is the task. Here the triangle is given and the
    work is the area formula, which is why the polygon is filled: the shading
    is what says "this region", and it is the archetype the 2016 paper prints.
    """
    ax = rng.randint(-4, 0)
    ay = rng.randint(-3, 0)
    base = rng.choice([2, 3, 4, 5, 6])
    height = rng.choice([2, 3, 4, 5, 6])
    if (base * height) % 2:
        raise Retry("the area must be a whole number of square centimetres")
    key = base * height // 2

    bx, by = ax + base, ay
    cx, cy = ax + rng.choice([0, base]), ay + height
    if cx > 5 or bx > 5 or cy > 4:
        raise Retry("the triangle must fit inside the drawn grid")
    if (0, 0) in {(ax, ay), (bx, by), (cx, cy)}:
        # A vertex on the origin is one point with two names, „B” and „O”.
        raise Retry("no vertex on the origin")

    options, letter = numeric_options(
        key, [base * height, key + base, key + height, base + height, key * 2],
        rng=rng, positive_only=True, suffix=r"\ \text{cm}^2")
    return GeneratedItem(
        topic=slot.topic, kind="mc", points=slot.points,
        stem=("Върху координатната система е защрихован $\\triangle ABC$. "
              "Лицето му е:"),
        options=options, correct_answer=letter, difficulty="medium",
        scene=coordinate_grid(
            points=[("A", ax, ay), ("B", bx, by), ("C", cx, cy)],
            polygon=["A", "B", "C"], shaded=True,
            x_range=(-5, 5), y_range=(-4, 5), unit_label="1 cm",
            aria=(f"Координатна система със защрихован триъгълник ABC с върхове "
                  f"A({ax};{ay}), B({bx};{by}) и C({cx};{cy})")),
        solution=(rf"Основата $AB$ е ${base}$ cm, а височината от $C$ към нея е "
                  rf"${height}$ cm. Лицето е $\frac{{{base} \cdot {height}}}{{2}} "
                  rf"= {key}$ cm$^2$"),
        signature=f"coord_shaded:{ax}:{ay}:{base}:{height}:{cx}",
    )
