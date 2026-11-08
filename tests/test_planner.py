from dataclasses import replace
from itertools import product
import pytest
from pc_ontology.knowledge import KnowledgeBase
from pc_ontology.engine import Build, DEMOS, validate
from pc_ontology.planner import search


@pytest.fixture
def kb():
    k = KnowledgeBase()
    yield k
    k.close()


def test_automatic_build_within_budget(kb):
    report = search(kb, Build(budget=80000), limit=1, timeout=20)
    assert report.plans
    result = validate(kb, report.plans[0].build)
    assert result.status == "pass"
    assert result.total <= 80000
    assert len(report.plans[0].build.parts) == 8


def test_two_conflict_repair_with_locked_parts_is_minimum(kb):
    good = DEMOS["Совместимая сборка"]
    bad = replace(good, parts={**good.parts, "RAM": "ram_d4_32", "PSU": "psu_400"})
    report = search(kb, bad, repair=True, objective="changes", limit=1,
                    locked=[s for s in good.parts if s not in {"RAM", "PSU"}])
    assert report.complete
    assert len(report.plans[0].replacements) == 2
    assert report.plans[0].total == 91000
    assert {"R03", "R04", "R15"} <= set(report.plans[0].resolved)
    assert validate(kb, report.plans[0].build).status == "pass"


def test_search_cost_matches_exhaustive_small_domain(kb):
    good = DEMOS["Совместимая сборка"]
    lock = [s for s in good.parts if s not in {"RAM", "GPU"}]
    expected = []
    for ram, gpu in product(kb.by_kind("RAM"), kb.by_kind("GPU")):
        b = replace(good, parts={**good.parts, "RAM": ram.id, "GPU": gpu.id})
        r = validate(kb, b)
        if r.status == "pass":
            expected.append(r.total)
    report = search(kb, good, objective="cost", limit=1, locked=lock)
    assert report.complete
    assert report.plans[0].total == min(expected)


def test_impossible_budget_and_stopped_search_are_distinct(kb):
    impossible = search(kb, Build(budget=1))
    assert impossible.complete and not impossible.plans
    capped = search(kb, Build(budget=80000), max_nodes=1)
    assert not capped.complete
    assert any("оптимум" in s for s in capped.messages)


def test_unknown_candidates_never_labelled_confirmed(kb):
    original = DEMOS["Недостаточно данных"]
    strict = search(kb, original, locked=tuple(original.parts), allow_unknown=False)
    assert not strict.plans
    relaxed = search(kb, original, locked=tuple(original.parts), allow_unknown=True)
    assert relaxed.plans[0].status == "unknown"
    assert relaxed.plans[0].unknown


def test_unknown_prices_do_not_look_free(kb):
    kb.components["cpu_a5_6"].facts["price"] = None
    b = DEMOS["Совместимая сборка"]
    report = search(kb, b, locked=tuple(b.parts))
    assert not report.plans
    priced = replace(b, price_overrides={"cpu_a5_6": 19000})
    report = search(kb, priced, locked=tuple(b.parts))
    assert report.plans[0].total == 91000


def test_core_count_objective_is_not_a_price_alias(kb):
    report = search(kb, Build(budget=130000), objective="cores", limit=1)
    assert report.complete
    assert kb.components[report.plans[0].build.parts["CPU"]].get("coreCount") == 12
