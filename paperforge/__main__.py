"""Command line: ``python -m paperforge [--blueprint nvo2026] [--seed 42] ...``

Prints a readable paper by default, or the exact JSON the HTTP API returns with
``--json``.
"""
from __future__ import annotations

import argparse
import json
import re
import sys

from paperforge.blueprints import BLUEPRINTS
from paperforge.difficulty import PROFILES
from paperforge.service import BadRequest, generate


def _plain(tex: str) -> str:
    """Just enough LaTeX-to-text for a terminal."""
    tex = re.sub(r"\\frac\{(\w+)\}\{(\w+)\}", r"\1/\2", tex)
    tex = re.sub(r"\\frac\{([^{}]*)\}\{([^{}]*)\}", r"(\1)/(\2)", tex)
    tex = re.sub(r"\\(?:cdot|times)", "·", tex)
    for cmd, char in (("le", "≤"), ("ge", "≥"), ("infty", "∞"), ("neq", "≠"),
                      ("in", "∈"), ("sqrt", "√"), ("pi", "π")):
        tex = re.sub(rf"\\{cmd}(?![a-zA-Z])", char, tex)
    tex = tex.replace("{,}", ",").replace("\\circ", "°").replace("$", "")
    tex = re.sub(r"\\(?:left|right|,|;|!)", "", tex)
    return tex


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="paperforge", description=__doc__.splitlines()[0])
    parser.add_argument("--blueprint", choices=sorted(BLUEPRINTS), default="nvo2026")
    parser.add_argument("--difficulty", choices=sorted(PROFILES), default="actual")
    parser.add_argument("--seed", type=int, help="omit for a random paper")
    parser.add_argument("--short", action="store_true", help="the short practice form")
    parser.add_argument("--no-key", action="store_true", help="leave the answer key out")
    parser.add_argument("--json", action="store_true", help="print the API payload")
    args = parser.parse_args(argv)

    try:
        paper = generate(blueprint=args.blueprint, difficulty=args.difficulty,
                         seed=args.seed, short=args.short, include_key=not args.no_key)
    except BadRequest as exc:
        parser.error(str(exc))

    if args.json:
        json.dump(paper, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return 0

    out = sys.stdout
    if hasattr(out, "reconfigure"):
        out.reconfigure(encoding="utf-8")
    meta = paper["meta"]
    print(f"{paper['blueprint_label']} · {paper['difficulty_label']} · seed {meta['seed']} "
          f"· {len(paper['questions'])} items · {paper['total_points']} pts "
          f"· built and verified in {meta['generation_ms']} ms\n")
    for q in paper["questions"]:
        pts = "+".join(map(str, q["points"]))
        figure = "  [figure]" if q["diagram"] else ""
        print(f"{q['number']:>2}. ({pts} т.) {_plain(q['question'])}{figure}")
        for opt in q["options"] or []:
            print(f"      {_plain(opt)}")
        if "correct_answer" in q:
            key = q["correct_answer"]
            key = " | ".join(key) if isinstance(key, list) else key
            print(f"      → {_plain(key)}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
