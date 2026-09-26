"""The one request-shaped entry point: parameters in, a verified paper out.

The CLI, the HTTP function in ``api/`` and the tests all call ``generate``, so
there is exactly one place that decides what a request may ask for and what a
response contains. Everything here is a pure function of its arguments — the
same ``(blueprint, difficulty, seed, short)`` always returns the same paper,
which is what makes a paper shareable by URL and cacheable forever.
"""
from __future__ import annotations

import random
import time
from typing import Any

from paperforge.api import blueprint_catalogue, difficulty_catalogue, exam_payload
from paperforge.assemble import generate_paper
from paperforge.blueprints import BLUEPRINTS, DEFAULT_BLUEPRINT
from paperforge.difficulty import normalize
from paperforge.registry import all_templates

VERSION = "1.0.0"

#: Seeds are unsigned 32-bit so they fit comfortably in a URL and a JS number.
MAX_SEED = 2**32 - 1


class BadRequest(ValueError):
    """A parameter the caller can fix."""


def parse_seed(raw: str | int | None) -> int:
    """A caller-supplied seed, or a fresh random one when none is given."""
    if raw is None or raw == "":
        return random.SystemRandom().randint(0, MAX_SEED)
    try:
        seed = int(raw)
    except (TypeError, ValueError):
        raise BadRequest(f"seed must be an integer, got {raw!r}") from None
    if not 0 <= seed <= MAX_SEED:
        raise BadRequest(f"seed must be between 0 and {MAX_SEED}")
    return seed


def generate(*, blueprint: str | None = None, difficulty: str | None = None,
             seed: int | str | None = None, short: bool = False,
             include_key: bool = True) -> dict[str, Any]:
    """Build one paper and describe how it was built.

    Raises ``BadRequest`` for an unknown blueprint or a malformed seed. A paper
    that fails verification is never returned — ``generate_paper`` resamples
    item by item, and if the assembled paper still fails the paper-level
    checks this raises rather than serve it.
    """
    code = blueprint or DEFAULT_BLUEPRINT
    if code not in BLUEPRINTS:
        raise BadRequest(f"unknown blueprint {code!r}; expected one of {sorted(BLUEPRINTS)}")
    seed = parse_seed(seed)

    started = time.perf_counter()
    paper = generate_paper(code, seed=seed, short=short, difficulty=normalize(difficulty))
    elapsed_ms = (time.perf_counter() - started) * 1000

    if not paper.report.ok:
        raise RuntimeError(f"paper failed verification: {paper.report.errors}")

    payload = exam_payload(paper, format_="short" if short else "full")
    # The generator's exam_id is a random uuid; a seeded paper gets a stable one.
    payload["exam_id"] = f"{code}-{paper.profile.code}-{'s' if short else 'f'}-{seed}"
    for question, (_, item, slot) in zip(payload["questions"], paper.numbered()):
        question["template"] = item.template_code or "part2_bank"
        question["section"] = slot.section
        # ``marking`` is the grader's copy of the same text; one field is enough.
        question.pop("marking", None)
        question["solution"] = item.solution
        if not include_key:
            for field in ("correct_answer", "solution", "partial_credit"):
                question.pop(field, None)

    payload["meta"] = {
        "engine": f"paperforge {VERSION}",
        "seed": seed,
        "generation_ms": round(elapsed_ms, 1),
        "verified": True,
        "warnings": list(paper.report.warnings),
        "template_count": len(all_templates()),
    }
    return payload


def catalogue() -> dict[str, Any]:
    """What a client needs to build its pickers."""
    return {
        "engine": f"paperforge {VERSION}",
        "blueprints": blueprint_catalogue(),
        "difficulties": difficulty_catalogue(),
        "template_count": len(all_templates()),
    }
