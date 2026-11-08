from dataclasses import replace
from pc_ontology.knowledge import KnowledgeBase
from pc_ontology.engine import DEMOS, REAL_DEMO
from pc_ontology.report import render_report


def test_report_has_composition_checks_and_escaped_user_title():
    kb = KnowledgeBase()
    report = render_report(kb, DEMOS["Совместимая сборка"], '<script>alert("bad")</script>')
    assert '<script>' not in report
    assert '&lt;script&gt;' in report
    assert '91 000 ₽' in report
    assert 'R01' in report and 'R22' in report
    assert 'Atlas A5' in report
    assert 'Распечатать / сохранить PDF' in report
    assert 'Учебная цена' in report
    kb.close()


def test_report_keeps_unknown_prices_and_sources_visible():
    kb = KnowledgeBase()
    report = render_report(kb, REAL_DEMO)
    assert 'Неполная сумма: от 0 ₽' in report
    assert 'Неизвестна' in report
    assert 'www.amd.com' in report
    assert 'www.asus.com' in report
    assert 'недостаточно' in report.lower() or 'требуют уточнения' in report.lower()
    priced = replace(REAL_DEMO, price_overrides={"real_cpu_7600": 15000})
    assert 'Цена пользователя' in render_report(kb, priced)
    kb.close()
