"""The request surface: what the CLI and the HTTP function promise their callers."""
from __future__ import annotations

import json
import threading
from http.server import HTTPServer
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest

from api.catalog import handler as catalog_handler
from api.generate import handler as generate_handler
from paperforge.__main__ import main
from paperforge.service import MAX_SEED, BadRequest, catalogue, generate


def test_the_same_seed_is_the_same_paper():
    a = generate(blueprint="nvo2026", difficulty="actual", seed=1234)
    b = generate(blueprint="nvo2026", difficulty="actual", seed=1234)
    for paper in (a, b):
        paper["meta"].pop("generation_ms")
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_different_seeds_give_different_papers():
    stems = {tuple(q["question"] for q in generate(seed=s)["questions"]) for s in range(5)}
    assert len(stems) == 5


def test_an_unseeded_request_reports_the_seed_it_used():
    paper = generate()
    again = generate(seed=paper["meta"]["seed"])
    assert [q["question"] for q in paper["questions"]] == [q["question"] for q in again["questions"]]


@pytest.mark.parametrize("code, count", [("nvo2026", 24), ("classic", 23)])
def test_both_formats_are_full_papers_worth_a_hundred_points(code, count):
    paper = generate(blueprint=code, seed=7)
    assert len(paper["questions"]) == count
    assert sum(sum(q["points"]) for q in paper["questions"]) == 100
    assert paper["meta"]["verified"] is True


def test_the_key_can_be_left_out():
    paper = generate(seed=7, include_key=False)
    for q in paper["questions"]:
        assert not {"correct_answer", "solution", "partial_credit"} & q.keys()


@pytest.mark.parametrize("kwargs", [{"blueprint": "nvo1999"}, {"seed": "abc"},
                                    {"seed": -1}, {"seed": MAX_SEED + 1}])
def test_bad_parameters_are_the_callers_fault(kwargs):
    with pytest.raises(BadRequest):
        generate(**kwargs)


def test_catalogue_lists_both_formats_and_four_levels():
    cat = catalogue()
    assert {b["code"] for b in cat["blueprints"]} == {"nvo2026", "classic"}
    assert [d["code"] for d in cat["difficulties"]] == ["easy", "medium", "actual", "extra_hard"]


def test_cli_prints_a_paper(capsys):
    assert main(["--seed", "3"]) == 0
    assert "seed 3" in capsys.readouterr().out


@pytest.fixture
def serve():
    servers = []

    def start(handler):
        server = HTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        servers.append(server)
        return f"http://127.0.0.1:{server.server_port}"

    yield start
    for s in servers:
        s.shutdown()


def test_http_function_serves_a_cacheable_seeded_paper(serve):
    base = serve(generate_handler)
    with urlopen(f"{base}/api/generate?seed=11&blueprint=classic&difficulty=easy") as r:
        assert r.status == 200
        assert "immutable" in r.headers["Cache-Control"]
        body = json.loads(r.read())
    assert body["blueprint"] == "classic" and body["difficulty"] == "easy"
    assert body["meta"]["seed"] == 11


def test_http_function_rejects_a_bad_seed_with_400(serve):
    base = serve(generate_handler)
    with pytest.raises(HTTPError) as exc:
        urlopen(f"{base}/api/generate?seed=oops")
    assert exc.value.code == 400
    assert "seed" in json.loads(exc.value.read())["error"]


def test_http_catalog(serve):
    base = serve(catalog_handler)
    with urlopen(f"{base}/api/catalog") as r:
        assert json.loads(r.read())["template_count"] > 100
