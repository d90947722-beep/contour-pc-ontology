from dataclasses import replace
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from pc_ontology.engine import DEMOS
from pc_ontology.knowledge import KnowledgeBase
from pc_ontology.report import render_report

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path, monkeypatch):
    monkeypatch.setenv("PC_ONTOLOGY_DATA_DIR", str(tmp_path / "data"))


def test_empty_build_shows_candidates_only_on_request():
    app = AppTest.from_file(str(ROOT / "cloud_app.py"), default_timeout=40).run()
    assert not app.exception
    assert app.metric[0].value == "0 / 8"
    assert not any(b.key and str(b.key).startswith("replace_") for b in app.button)
    app.checkbox(key="show_empty_recommendations").check().run()
    assert not app.exception
    assert any(b.key and str(b.key).startswith("replace_") for b in app.button)


@pytest.mark.parametrize("entry", ["app.py", "cloud_app.py"])
def test_guided_demo_repairs_only_memory_and_psu(entry):
    app = AppTest.from_file(str(ROOT / entry), default_timeout=40).run()
    app.button(key="demo_repair").click().run()
    assert not app.exception
    assert app.metric[3].value == "3 / 0"
    assert app.session_state["upgrade_targets"] == ["RAM", "PSU"]
    app.button(key="find_plans").click().run()
    assert not app.exception
    plans = app.session_state["search_result"][1].plans
    assert plans and len(plans[0].replacements) == 2
    assert {r["slot"] for r in plans[0].replacements} == {"RAM", "PSU"}
    app.button(key="apply_plan_0").click().run()
    assert not app.exception
    assert app.metric[3].value == "0 / 0"
    assert app.selectbox(key="part_RAM").value == "ram_d5_32"
    assert app.selectbox(key="part_PSU").value == "psu_550"


def test_changed_search_parameters_hide_plans_until_search_runs_again():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=40).run()
    app.button(key="find_plans").click().run()
    assert app.button(key="apply_plan_0")
    app.selectbox(key="plan_objective").select("cores").run()
    assert not app.exception
    assert not any(b.key == "apply_plan_0" for b in app.button)
    assert any("Предыдущие варианты скрыты" in msg.value for msg in app.info)
    app.button(key="find_plans").click().run()
    assert not app.exception
    assert app.button(key="apply_plan_0")
    assert not any("Предыдущие варианты скрыты" in msg.value for msg in app.info)


def test_budget_does_not_count_as_a_hardware_conflict_in_ui_or_report():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=40).run()
    app.number_input(key="budget_value").set_value(1).run()
    assert not app.exception
    assert app.metric[3].value == "0 / 0"
    assert any("Бюджет:" in msg.value for msg in app.warning)
    kb = KnowledgeBase()
    try:
        report = render_report(kb, replace(DEMOS["Совместимая сборка"], budget=1))
        assert 'class="pass">Совместимость: Подтверждено' in report
        assert 'Конфликтов совместимости: 0' in report
        assert 'Бюджет:' in report
        assert 'Версия 2.4' in report
    finally:
        kb.close()
