from dataclasses import replace
import pytest
from streamlit.testing.v1 import AppTest
from pathlib import Path
from pc_ontology.engine import DEMOS, Build
from pc_ontology.knowledge import KnowledgeBase
from pc_ontology.planner import search
from pc_ontology.purchase import assessment, replacement_impact, shopping_cost


@pytest.fixture
def kb():
    value = KnowledgeBase()
    yield value
    value.close()


def test_budget_excess_is_separate_from_hardware_compatibility(kb):
    b = replace(DEMOS['Совместимая сборка'], budget=1)
    review = assessment(kb, b)
    assert review['status'] == 'pass'
    assert any(c.status == 'fail' for c in review['budget'])


def test_partial_selection_never_looks_compatible(kb):
    review = assessment(kb, Build({'CPU': 'cpu_a5_6'}))
    assert review['status'] == 'unknown'
    assert len(review['missing']) == 7
    assert not review['conflicts']
    assert not review['unknown']  # completion checklist owns missing-part checks


def test_impact_does_not_hide_other_conflicts(kb):
    b = replace(DEMOS['Совместимая сборка'], parts={**DEMOS['Совместимая сборка'].parts, 'RAM':'ram_d4_32', 'PSU':'psu_400'})
    impact = replacement_impact(kb,b,'RAM','ram_d5_32',b.bios_revision)
    assert impact['resolved'] and impact['conflicts'] > 0


def test_upgrade_budget_only_counts_purchases_and_requires_actual_change(kb):
    b = replace(DEMOS['Совместимая сборка'], budget=None)
    locked=[s for s in b.parts if s != 'RAM']
    # Prices for already owned parts can be absent.
    for slot in locked:
        kb.components[b.parts[slot]].facts['price'] = None
    report=search(kb,b,repair=True,objective='changes',locked=locked,must_change=['RAM'],replacement_budget=50000)
    assert report.plans
    for plan in report.plans:
        assert plan.build.parts['RAM'] != b.parts['RAM']
        cost, unknown=shopping_cost(kb,b,plan.build)
        assert cost <= 50000 and not unknown
    assert not search(kb,b,objective='changes',locked=locked,must_change=['RAM'],replacement_budget=0).plans
    with pytest.raises(ValueError):
        search(kb,b,locked=['RAM'],must_change=['RAM'])


def test_three_customer_workflows_and_price_input(tmp_path, monkeypatch):
    monkeypatch.setenv('PC_ONTOLOGY_DATA_DIR',str(tmp_path))
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'cloud_app.py'),default_timeout=40).run()
    assert not app.exception
    assert app.radio(key='catalog_mode').value == 'manufacturer'
    app.button(key='demo_0').click().run()
    app.radio(key='customer_workflow').set_value('Обновить компьютер').run()
    assert app.button(key='find_plans').disabled
    app.multiselect(key='upgrade_targets').set_value(['RAM']).run()
    app.checkbox(key='upgrade_budget_enabled').check().run()
    assert not app.exception
    app.button(key='find_plans').click().run()
    assert not app.exception
    assert app.session_state['search_result'][1].plans
    assert all(p.build.parts['RAM'] != 'ram_d5_32' for p in app.session_state['search_result'][1].plans)
    app.radio(key='customer_workflow').set_value('Собрать с нуля').run()
    app.button(key='find_plans').click().run()
    assert not app.exception
    assert app.session_state['search_result'][1].plans


def test_purchase_objective_ignores_owned_prices_and_matches_exhaustive_cost(kb):
    b = replace(DEMOS['Совместимая сборка'], budget=None)
    locked = [slot for slot in b.parts if slot != 'RAM']
    for slot in locked:
        kb.components[b.parts[slot]].facts['price'] = None
    from pc_ontology.engine import validate
    expected = []
    for candidate in kb.by_kind('RAM'):
        if candidate.get('catalogKind') == 'synthetic' and candidate.id != b.parts['RAM']:
            trial = replace(b, parts={**b.parts, 'RAM': candidate.id})
            if validate(kb, trial).status == 'pass':
                expected.append(shopping_cost(kb, b, trial)[0])
    report = search(kb, b, repair=True, objective='purchases', locked=locked,
                    must_change=['RAM'], limit=1)
    assert report.complete and report.plans
    assert report.plans[0].score[1] == min(expected)
    assert shopping_cost(kb, b, report.plans[0].build)[0] == min(expected)


def test_inline_prices_persist_and_refresh_after_loading_build(tmp_path, monkeypatch):
    monkeypatch.setenv('PC_ONTOLOGY_DATA_DIR', str(tmp_path))
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/'cloud_app.py'), default_timeout=40).run()
    app.button(key='demo_real').click().run()
    app.number_input(key='purchase_price_real_cpu_7600').set_value(23000)
    next(b for b in app.button if b.label == 'Применить цены').click().run()
    assert not app.exception
    assert app.session_state['price_overrides']['real_cpu_7600'] == 23000
    assert app.session_state['_public_store'].prices()['real_cpu_7600'] == 23000
    # Loading a snapshot with another price must also refresh the price editor.
    from pc_ontology.engine import REAL_DEMO
    app.session_state['pending_build'] = replace(REAL_DEMO, price_overrides={'real_cpu_7600': 24000})
    app.run()
    assert not app.exception
    assert app.number_input(key='purchase_price_real_cpu_7600').value == 24000
