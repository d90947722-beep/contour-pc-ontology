from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
from pc_ontology.storage import Store

APP = Path(__file__).resolve().parents[1] / "cloud_app.py"


def test_memory_stores_do_not_share_prices_or_saved_builds():
    one, two = Store(":memory:"), Store(":memory:")
    payload = {"format": "pc-ontology-build"}
    saved_id = one.save_build("Private build", payload)
    one.update_prices({"cpu": 1234})
    one.save_draft(payload)
    assert two.list_builds() == []
    assert two.prices() == {}
    assert two.load_draft() is None
    with pytest.raises(KeyError):
        two.load_build(saved_id)
    with pytest.raises(KeyError):
        two.archive(saved_id)


def test_public_sessions_are_isolated_and_reruns_keep_current_library(tmp_path, monkeypatch):
    monkeypatch.setenv("PC_ONTOLOGY_DATA_DIR", str(tmp_path / "data"))
    first = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not first.exception
    first.button(key="demo_0").click().run()
    first.text_input(key="new_build_title").set_value("Visitor A")
    next(b for b in first.button if b.label == "Сохранить в мои сборки").click().run()
    assert not first.exception
    assert first.selectbox(key="saved_build_id")
    first.selectbox(key="part_RAM").select("ram_d5_64").run()
    assert first.selectbox(key="saved_build_id")
    second = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not second.exception
    assert not any(b.key == "saved_build_id" for b in second.selectbox)
    assert second.selectbox(key="part_RAM").value is None
    assert second.radio(key="catalog_mode").value == "manufacturer"
    assert not (tmp_path / "data" / "contour.sqlite3").exists()
