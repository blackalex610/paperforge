# PaperForge

**A procedural, self-verifying exam generator.** PaperForge writes complete, original
papers for Bulgaria’s national 7th-grade mathematics exam (НВО). Each paper has the real
format, point weights and topic order. Every answer key is computed, never typed, and
every figure is geometrically checked before it is drawn. No paper reaches a student
without first passing a verifier.

**Live demo → https://paperforge-demo.vercel.app** (every page load writes a new paper; toggle *Answer key*)

It is the generation engine behind [SmartNVO](https://smartnvo.vercel.app), extracted
here as a standalone, dependency-free library with a CLI, an HTTP API and a demo.

```
$ python -m paperforge --seed 42
НВО 2026 · Като на НВО · seed 42 · 24 items · 100 pts · built and verified in 94 ms
 1. (2 т.) Стойността на израза 20 - 10·(-1/2) е:
      А) 15   Б) 25   В) -5   Г) 5
      → Б
 ...
```

---

## The problem

A practice-exam product lives or dies on two things at once:

1. **Every question must be correct.** A wrong key doesn’t just waste a student’s time:
   they learn the wrong method and trust the product less. Language models make fluent,
   confident mistakes in exactly this kind of content, so they aren’t the author here.
2. **The supply must feel endless.** A student who practises daily will notice the same
   question coming back. The previous approach drew each of 23 slots from ~5 transcribed
   official variants; within a dozen papers, students were seeing repeats.

A 7th-grade exam also has details a generic generator gets wrong: decimal commas,
Cyrillic option letters А/Б/В/Г, prices in euro since 2026, and figures that must be
*topologically* truthful (M really is the midpoint; the foot of a height really lands
inside the side) even though the paper states they are not to scale.

## The approach

PaperForge models the exam the way its authors do: as a **blueprint** of positions,
filled from **templates**, gated by a **verifier**.

```
 blueprint slot ─► eligible templates ─► sample parameters ─► stem + key + distractors + figure
 (format as data)  (scarcity-ordered,       │  (reject bad draws,           │
                    difficulty-weighted)    │   never round)                ▼
                                            └──────── Retry ◄──────── verify.check_item
                                                                             │
                           rebalance answer letters ◄── every slot filled ◄──┘
                                      │
                                      └─► verify.check_paper ─► Paper  (pure function of the seed)
```

All of it was derived from the **thirteen official papers from 2015–2026** and their
official marking schemes. The realism study in [`docs/realism-study.md`](docs/realism-study.md)
audits the generator against that corpus item by item.

## Engineering highlights

**Exam formats are data, validated at import.** [`blueprints.py`](paperforge/blueprints.py)
describes the 2024–25 (23 items) and 2026 (24 items) formats as data: positions, topics,
point vectors and item kinds. `Blueprint.validate()` runs on import and enforces
invariants read off every paper since 2015 (Part 1 = 65 points, Part 2 = 35, a contiguous
geometry block, kinds in order). A malformed format fails at startup, not mid-exam. A new
exam era is one entry in that file.

**Templates are parameter spaces with rejection sampling.** 127 templates
([`templates/`](paperforge/templates)) each register with a decorator that declares the
topics, item kinds and difficulty band they can fill. A draw that yields an ugly number
(an angle of 63.5°, a non-terminating decimal) raises `Retry` and is resampled rather than
rounded. Parameter spaces are deliberately wider than needed and narrowed by rejection.
Each item carries a `signature`, so one paper can never contain the same draw twice.

**Slots are filled in order of scarcity.** Several templates serve more than one topic.
Filling slots by position lets a flexible slot take the only template a later slot could
use. Ordering by candidate count removes that collision without special cases, a small
constraint-satisfaction heuristic in [`assemble.py`](paperforge/assemble.py).

**Wrong answers are modelled, not random.** Every distractor in the corpus fits one of
eight error families: sign flip, arrested computation, bracket permutation,
supplement/complement, wrong angle in the figure, reciprocal, factor-sign permutation,
off-by-a-factor. [`distractors.py`](paperforge/distractors.py) generates candidates
from those families, filters out implausible ones (a negative length, a value 50× off)
and rejects the draw if fewer than three survive.

**One expression tree renders the stem and computes the key.** Part 2 algebra is built on
[`poly.py`](paperforge/poly.py): an `Expr` tree that emits its own LaTeX and evaluates to
an exact rational polynomial (`fractions.Fraction`, no floats). The printed question and
its answer come from the same object, so they cannot drift apart. Before this change,
four hand-transcribed items shipped with keys that didn’t match their stems.

**Word problems draw free quantities and solve for the rest.** A story states several
facts that constrain each other. Drawing them independently is how an earlier version
produced a bus-and-car problem whose three facts contradicted each other. Each builder
samples only what is free, derives the rest, and rejects draws a real key would not print.

**Figures are data, with declared contracts.** [`scene.py`](paperforge/scene.py) emits a
declarative scene spec (named points, segments, angle arcs, ticks, fills), and a single
React component draws every figure ([`SceneRenderer.tsx`](web/src/components/SceneRenderer.tsx)).
Layouts are *sampled*, so no two papers print the same triangle. Each layout declares its
invariants as predicates (`angle_below`, `sides_differ`, `points_inside`…) and resamples
until they hold. Every figure is then *posed* by a random similarity transform, which
provably preserves every claim a figure makes.

**Labels are placed against all the ink.** [`figure_labels.py`](paperforge/figure_labels.py)
places every point name and angle value against every stroke, arc and other label in the
figure. It fits arc radii to the space the angle actually has and keeps everything inside
the canvas. The verifier then rejects clashes. This came out of a blind visual audit of
generated figures: every class of fault found by eye became an automated check, until
**500 of 500** freshly generated figures passed review.

**The verifier is a gate, not a linter.** [`verify.py`](paperforge/verify.py) checks every
item, then the whole paper: exactly one correct option, Bulgarian prose outside math
mode, no leva, no three-decimal options, balanced answer letters, no two items printing
the same picture (via a label-blind `geometry_hash`), label and arc clearance. A failing
item is resampled, and a paper that still fails is never served.

**Difficulty changes the items, never the format.** Four levels
([`difficulty.py`](paperforge/difficulty.py)) re-weight template choice by band and let
templates size their own number pools. Positions, topics and points stay identical, so a
score means the same thing at every level. `actual` is byte-identical to generating with
no level at all, and a test asserts it.

**Deterministic by construction.** A paper is a pure function of
`(format, level, seed)`. The same seed produces a byte-identical paper, so any paper can be
shared by URL and the HTTP API caches seeded responses at the edge for a year.

## How correctness is defended

**1,422 tests** (`pytest`, ~8 minutes). The ones that earn their keep:

| Test file | What it proves |
|---|---|
| `test_part2_keys.py` | Every Part 2 key is **re-derived from the printed stem** by a LaTeX reader independent of the code that generated it. It fails on each of the four historical key bugs. |
| `test_part1_keys.py` | The same independent re-derivation for Part 1 templates. |
| `test_part2_figures.py` | Every claim of every geometry proof (“△MAD ≅ △DCP”, “MD = DP”) is **measured on its own drawn figure**. Marking steps add up to the item’s points. |
| `test_figures.py` | Each figure asserts the topology its stem promises (betweenness, midpoints, perpendicularity) on the posed output. Every layout closes on every draw. |
| `test_blueprint_generation.py` | 500 papers generate without a single failure. Point totals, letter balance and slot eligibility hold. |
| `test_realism.py` | Every template passes the verifier in every slot it claims. Every position has room for ≥ 80 distinct items. |
| `test_difficulty.py` | Levels change the items and never the format. Each registered template can actually build something. |
| `test_service.py` | The HTTP contract: determinism, 400s for bad input, key stripping, edge-cache headers, served over a real socket. |

## By the numbers

| | |
|---|---|
| Item templates | 127 |
| Official papers the model was derived from | 13 (2015–2026) |
| Distinct Part 1 combinations, 2026 format | ≥ 2.7 × 10⁶¹ (counted lower bound, [`scripts/measure_capacity.py`](scripts/measure_capacity.py)) |
| Distinct whole papers | ≥ 2.7 × 10⁷² (2026 format) · ≥ 1.2 × 10⁷⁴ (2024–25 format) |
| Thinnest Part 1 position | ≥ 203 distinct items (was 21) |
| Part 2 extended items | 5 algebra shapes / 7,468 items · 6 word-problem shapes / 6,899 items · 12 proof figures / ~2,000 items |
| Time to build and verify a paper | ~90 ms median, ~180 ms p95 (single core, CPython 3.11) |
| Runtime dependencies | **none**, standard library only |

## Using it

**Library**

```python
from paperforge.service import generate

paper = generate(blueprint="nvo2026", difficulty="extra_hard", seed=42)
paper["questions"][0]["question"]   # 'Стойността на израза $…$ е:'
paper["meta"]                       # {'seed': 42, 'generation_ms': 93.8, 'verified': True, …}
```

**CLI**

```bash
python -m paperforge --blueprint classic --difficulty easy --seed 7
python -m paperforge --json --no-key > paper.json
```

**HTTP API** (deployed on Vercel as zero-dependency Python functions)

```
GET /api/generate?blueprint=nvo2026&difficulty=actual&seed=42[&short=1][&key=0]
GET /api/catalog
```

A seeded response is served with `Cache-Control: s-maxage=31536000, immutable`. An unseeded
request picks a seed, reports it in `meta.seed`, and is not cached.

**Development**

```bash
pip install -e ".[dev]" && pytest          # engine + tests (Python ≥ 3.10)
npm ci
python scripts/dev_server.py &              # api/ on :8787
npm run dev                                 # demo on :5173, proxied to the API
```

## Layout

```
paperforge/
  blueprints.py      the exam formats, validated at import
  difficulty.py      four levels and the knobs they turn
  registry.py        GeneratedItem, the @template decorator, slot eligibility
  templates/         127 item templates: numbers, algebra, word problems, data, geometry, corpus
  distractors.py     the eight wrong-answer families; Bulgarian number formatting
  poly.py            exact polynomials; Expr trees that render their own LaTeX
  part2_*.py         extended items: generalised transcriptions and twelve geometry proofs
  scene.py           declarative figure specs and sampled, contract-checked layouts
  figure_labels.py   label, arc and tick placement against all ink
  verify.py          the item- and paper-level gate
  assemble.py        the generation loop
  api.py, service.py the JSON payload and the request surface
api/                 Vercel Python functions (generate, catalog)
web/                 the demo (Vite + React + KaTeX)
tests/               1,422 tests
docs/                design notes, realism study, figure coverage audit
```

## Further reading

- [`docs/generation.md`](docs/generation.md): the design in depth, and how to add a template.
- [`docs/realism-study.md`](docs/realism-study.md): the audit against the official papers. It covers what was wrong, what changed, and what is still open.
- [`docs/figure-coverage.md`](docs/figure-coverage.md): the 209 figures extracted from the real papers, classified into 59 archetypes. Every archetype that recurs in two or more papers is covered.

---

© 2026 SmartNVO. All rights reserved.
