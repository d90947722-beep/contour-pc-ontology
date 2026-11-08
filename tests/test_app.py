from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app.py"


@pytest.fixture(autouse=True)
def isolated_user_data(tmp_path, monkeypatch):
    monkeypatch.setenv("PC_ONTOLOGY_DATA_DIR", str(tmp_path / "data"))


def test_app_scenarios_and_replacement():
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not app.exception
    assert app.metric[1].value == "91 000 ₽"
    app.button(key="demo_1").click().run()
    assert not app.exception
    assert "Есть несовместимые компоненты" in " ".join(x.value for x in app.markdown)
    app.button(key="demo_2").click().run()
    assert not app.exception
    assert "Нужны дополнительные сведения" in " ".join(x.value for x in app.markdown)
    app.button(key="demo_0").click().run()
    app.selectbox(key="part_RAM").select("ram_d4_32").run()
    assert not app.exception
    assert "Есть несовместимые компоненты" in " ".join(x.value for x in app.markdown)
    app.selectbox(key="recommend_slot").select("RAM").run()
    app.button(key="replace_ram_d5_32").click().run()
    assert not app.exception
    assert app.selectbox(key="part_RAM").value == "ram_d5_32"
    assert "Сборка прошла проверки" in " ".join(x.value for x in app.markdown)


def test_board_change_resets_bios_and_invalid_input_is_explained():
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.selectbox(key="part_Motherboard").select("mb_unknown").run()
    assert not app.exception
    assert app.text_input(key="bios_text").value == ""
    app.text_input(key="bios_text").set_value("abc").run()
    assert not app.exception
    assert any("ревизию BIOS" in x.value for x in app.error)


def test_real_catalog_and_string_bios():
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.radio(key="catalog_mode").set_value("manufacturer").run()
    assert not app.exception
    app.selectbox(key="part_CPU").select("real_cpu_7600").run()
    app.selectbox(key="part_Motherboard").select("real_mb_b650_plus").run()
    app.text_input(key="bios_text").set_value("0602").run()
    assert not app.exception
    assert app.text_input(key="bios_text").value == "0602"
    assert not app.error


def test_auto_search_and_apply():
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.button(key="find_plans").click().run()
    assert not app.exception
    assert app.button(key="apply_plan_0")
    app.button(key="apply_plan_0").click().run()
    assert not app.exception
    assert app.metric[1].value == "52 000 ₽"
    assert "Сборка прошла проверки" in " ".join(x.value for x in app.markdown)


def test_library_save_restore_and_archive():
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.text_input(key="new_build_title").set_value("Мой учебный ПК")
    next(b for b in app.button if b.label == "Сохранить в мои сборки").click().run()
    assert not app.exception
    assert app.selectbox(key="saved_build_id")
    app.checkbox(key="preview_saved_report").check().run()
    assert not app.exception
    app.selectbox(key="part_RAM").select("ram_d4_32").run()
    app.button(key="open_saved").click().run()
    assert app.selectbox(key="part_RAM").value == "ram_d5_32"
    app.button(key="archive_saved").click().run()
    assert not app.exception
    assert app.button(key="restore_saved")
    app.button(key="restore_saved").click().run()
    assert app.button(key="open_saved")
    assert not app.exception


def test_draft_survives_new_browser_session():
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.selectbox(key="part_RAM").select("ram_d5_64").run()
    second = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not second.exception
    assert second.selectbox(key="part_RAM").value == "ram_d5_64"


def test_saved_prices_survive_catalog_switch():
    from pc_ontology.storage import Store
    Store().update_prices({"real_cpu_7600": 19001})
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.button(key="demo_real").click().run()
    assert not app.exception
    assert app.session_state["price_overrides"]["real_cpu_7600"] == 19001
    app.button(key="demo_0").click().run()
    app.button(key="demo_real").click().run()
    assert app.session_state["price_overrides"]["real_cpu_7600"] == 19001


def test_library_comparison_and_update():
    from pc_ontology.storage import Store
    from pc_ontology.knowledge import KnowledgeBase
    from pc_ontology.engine import DEMOS, export_build
    kb = KnowledgeBase()
    store = Store()
    one = store.save_build("Первая", export_build(kb, DEMOS["Совместимая сборка"]))
    two = store.save_build("Вторая", export_build(kb, DEMOS["Сборка с конфликтами"]))
    kb.close()
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.multiselect(key="compare_build_ids").set_value([one, two]).run()
    assert not app.exception
    app.selectbox(key="saved_build_id").select(two).run()
    app.button(key="update_saved").click().run()
    assert not app.exception
    assert Store().load_build(two)["payload"]["parts"]["CPU"] == "cpu_a5_6"


def test_invalid_draft_is_kept_and_library_still_works():
    from pc_ontology.storage import Store
    store = Store()
    with store.connection() as conn:
        conn.execute("INSERT INTO settings VALUES('draft',?,?)", ('broken JSON', '2026-10-28T12:00:00+00:00'))
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not app.exception
    assert any("не перезаписан" in warning.value for warning in app.warning)
    with store.connection() as conn:
        assert conn.execute("SELECT value FROM settings WHERE key='draft'").fetchone()[0] == 'broken JSON'


def test_quality_audit_and_actionable_real_clarifications():
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.button(key="audit_quality").click().run()
    assert not app.exception
    assert any("SHACL-ограничениям" in message.value for message in app.success)
    app.button(key="demo_real").click().run()
    assert not app.exception
    assert app.download_button(key="download_clarifications")
    report = app.session_state["quality_result"][1]
    assert report.conforms and len(report.coverage) == 32


def test_actual_graph_explorer_switches_resource_groups():
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.selectbox(key="explorer_group").select("SourceDocument").run()
    app.select_slider(key="graph_depth").set_value(2).run()
    app.checkbox(key="graph_literals").check().run()
    assert not app.exception
    app.selectbox(key="explorer_group").select("FactAssertion").run()
    assert not app.exception
