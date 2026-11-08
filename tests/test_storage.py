import json
import sqlite3
from dataclasses import replace
import pytest
from pc_ontology.storage import Store
from pc_ontology.knowledge import KnowledgeBase
from pc_ontology.engine import DEMOS, export_build, import_build


@pytest.fixture
def payload():
    kb = KnowledgeBase()
    data = export_build(kb, DEMOS["Совместимая сборка"])
    kb.close()
    return json.loads(json.dumps(data))


def test_library_survives_reopening_and_archive_is_reversible(tmp_path, payload):
    path = tmp_path / "user.sqlite3"
    store = Store(path)
    id = store.save_build("Сборка '); DROP TABLE builds; --", payload, "Заметка")
    reopened = Store(path)
    assert len(reopened.list_builds()) == 1
    assert reopened.load_build(id)["payload"] == payload
    reopened.archive(id)
    assert not reopened.list_builds()
    assert len(reopened.list_builds(archived=True)) == 1
    reopened.archive(id, False)
    assert len(reopened.list_builds()) == 1


def test_update_preserves_id_and_creation_time(tmp_path, payload):
    store = Store(tmp_path / "user.sqlite3")
    id = store.save_build("Исходная", payload)
    original = store.load_build(id)
    changed = {**payload, "budget": 90000}
    store.save_build("Новая", changed, id=id)
    record = store.load_build(id)
    assert record["created_at"] == original["created_at"]
    assert record["payload"]["budget"] == 90000
    assert len(store.list_builds()) == 1
    with pytest.raises(KeyError):
        store.save_build("Неверная", payload, id="missing")


def test_draft_roundtrip_and_unchanged_write_is_skipped(tmp_path, payload):
    path = tmp_path / "user.sqlite3"
    store = Store(path)
    assert store.load_draft() is None
    assert store.save_draft(payload)
    assert not store.save_draft(payload)
    assert Store(path).load_draft() == payload


def test_prices_zero_clear_and_atomic_validation(tmp_path):
    store = Store(tmp_path / "user.sqlite3")
    store.update_prices({"cpu": 0, "ram": 7000})
    assert store.prices() == {"cpu": 0, "ram": 7000}
    with pytest.raises(ValueError):
        store.update_prices({"ram": 10000, "cpu": -1})
    assert store.prices()["ram"] == 7000
    store.update_prices({"cpu": None})
    assert store.prices() == {"ram": 7000}
    assert Store(store.path).prices() == {"ram": 7000}


@pytest.mark.parametrize("value", [True, 2.5, "12000", -100, 1_000_000_001])
def test_invalid_price_values_are_rejected(tmp_path, value):
    store = Store(tmp_path / "user.sqlite3")
    with pytest.raises(ValueError):
        store.update_prices({"cpu": value})
    assert not store.prices()


@pytest.mark.parametrize("title", ["", "  ", "X" * 101, None])
def test_bad_titles_are_rejected(tmp_path, payload, title):
    store = Store(tmp_path / "user.sqlite3")
    with pytest.raises(ValueError):
        store.save_build(title, payload)
    assert not store.list_builds()


def test_corrupted_database_is_not_replaced(tmp_path):
    path = tmp_path / "bad.sqlite3"
    content = b"This is not a SQLite database. Keep these bytes."
    path.write_bytes(content)
    with pytest.raises(sqlite3.DatabaseError):
        Store(path)
    assert path.read_bytes() == content


def test_more_recent_schema_is_not_modified(tmp_path):
    path = tmp_path / "newer.sqlite3"
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA user_version=2")
    with pytest.raises(ValueError):
        Store(path)
    with sqlite3.connect(path) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 2
