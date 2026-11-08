from dataclasses import replace
import pytest
from pc_ontology.engine import DEMOS, REAL_DEMO, Build
from pc_ontology.knowledge import KnowledgeBase
from pc_ontology.clarifications import requests, checklist_markdown


@pytest.fixture
def kb():
    value = KnowledgeBase()
    yield value
    value.close()


def test_confirmed_build_has_no_clarifications(kb):
    assert requests(kb, DEMOS["Совместимая сборка"]) == []


def test_real_build_requests_bios_and_peak_without_fabricating_values(kb):
    result = requests(kb, REAL_DEMO)
    fields = [row["Свойство"] for row in result]
    assert fields.count("peakPowerW") == 2
    assert "bios_revision" in fields
    assert "maxGPUThicknessMM" in fields
    assert all("price" != field for field in fields)  # No budget constraint.
    assert any("TDP" in row["Что сделать"] for row in result)
    assert "# Что уточнить" in checklist_markdown(result)


def test_empty_build_has_eight_selections_not_spurious_hardware_requests(kb):
    items = requests(kb, Build())
    assert len(items) == 8
    assert all(row["Свойство"] == "selection" for row in items)


def test_price_requests_are_deduplicated_between_budget_rules(kb):
    items = requests(kb, replace(REAL_DEMO, budget=100000))
    prices = [row for row in items if row["Свойство"] == "price"]
    assert len(prices) == 8
    assert all(set(row["Правила"]) == {"R22", "D01"} for row in prices)


def test_confirmed_conflicts_are_not_relabelled_as_unknown(kb):
    bad = replace(DEMOS["Совместимая сборка"], parts={**DEMOS["Совместимая сборка"].parts, "RAM": "ram_d4_32"})
    assert requests(kb, bad) == []
