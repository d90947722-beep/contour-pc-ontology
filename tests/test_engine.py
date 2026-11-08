import json
import shutil
from dataclasses import replace
import pytest
from owlready2 import OwlReadyInconsistentOntologyError
from pc_ontology.engine import Build, DEMOS, validate, recommend, export_build, import_build
from pc_ontology.knowledge import KnowledgeBase, QUERIES
from pc_ontology.schema import generate


@pytest.fixture
def kb():
    base = KnowledgeBase()
    yield base
    base.close()


def change(build, slot, id, **kwargs):
    return replace(build, parts={**build.parts, slot: id}, **kwargs)


def check(kb, build, rule):
    return next(c for c in validate(kb, build).checks if c.rule == rule)


def test_three_demonstration_outcomes(kb):
    assert [validate(kb, b).status for b in DEMOS.values()] == ["pass", "fail", "unknown"]
    good = validate(kb, DEMOS["Совместимая сборка"])
    assert good.total == 91000
    assert good.estimated_power == 413  # ceil((100 + 170 + 60) * 1.25)


def test_empty_build_never_passes(kb):
    result = validate(kb, Build())
    assert result.status == "unknown"
    assert len(result.missing) == 8
    assert result.count("pass") == 0


def test_socket_match_does_not_prove_cpu_support(kb):
    build = change(DEMOS["Совместимая сборка"], "Motherboard", "mb_unknown", bios_revision=200)
    assert check(kb, build, "R01").status == "pass"
    assert check(kb, build, "R02").status == "unknown"


@pytest.mark.parametrize("bios,expected", [(100, "fail"), (200, "pass"), (None, "unknown")])
def test_bios_boundary(kb, bios, expected):
    build = change(DEMOS["Совместимая сборка"], "CPU", "cpu_a5_8", bios_revision=bios)
    assert check(kb, build, "R02").status == expected


@pytest.mark.parametrize("slot,id,rule", [
    ("RAM", "ram_d4_32", "R03"), ("RAM", "ram_d4_32", "R04"),
    ("RAM", "ram_so", "R05"), ("Case", "case_mini", "R09"),
    ("Case", "case_mini", "R10"), ("Cooler", "cooler_a4", "R11"),
    ("Case", "case_slim", "R12"), ("PSU", "psu_400", "R15"),
    ("GPU", "gpu_max", "R17"), ("Motherboard", "mb_i_d5", "R18"),
    ("Storage", "ssd_long", "R20"),
])
def test_detects_specific_conflicts(kb, slot, id, rule):
    assert check(kb, change(DEMOS["Совместимая сборка"], slot, id), rule).status == "fail"


def test_ram_slots_and_capacity(kb):
    build = change(DEMOS["Совместимая сборка"], "Motherboard", "mb_a5_itx", bios_revision=200)
    build = change(build, "RAM", "ram_d5_128")
    assert check(kb, build, "R08").status == "fail"
    assert check(kb, build, "R07").status == "fail"
    assert check(kb, build, "R06").status == "pass"


def test_unknown_gpu_is_not_zero_power_or_zero_connectors(kb):
    build = change(DEMOS["Совместимая сборка"], "GPU", "gpu_unknown")
    for rule in ["R10", "R15", "R16", "R17"]:
        assert check(kb, build, rule).status == "unknown"
    assert validate(kb, build).estimated_power is None


def test_zero_required_connectors_is_known(kb):
    build = change(DEMOS["Совместимая сборка"], "GPU", "gpu_eco")
    assert check(kb, build, "R16").status == "pass"
    assert check(kb, build, "R17").status == "pass"


def test_missing_gpu_cannot_be_confirmed(kb):
    result = validate(kb, change(DEMOS["Совместимая сборка"], "GPU", None))
    assert result.status == "unknown"
    assert "GPU" in result.missing


def test_power_boundary_and_cooling(kb):
    build = DEMOS["Совместимая сборка"]
    psu = kb.components["psu_550"]
    psu.facts["ratedPowerW"] = 413
    assert check(kb, build, "R15").status == "pass"
    psu.facts["ratedPowerW"] = 412
    assert check(kb, build, "R15").status == "fail"
    build = change(build, "CPU", "cpu_a5_8")
    build = change(build, "Cooler", "cooler_low")
    assert check(kb, build, "R13").status == "fail"


def test_sata_interface_and_power(kb):
    build = change(DEMOS["Совместимая сборка"], "Storage", "ssd_sata")
    assert check(kb, build, "R21").status == "pass"
    assert not any(c.rule == "R20" for c in validate(kb, build).checks)
    kb.components["psu_550"].facts["availableSATA"] = 0
    assert check(kb, build, "R21").status == "fail"
    build = change(build, "Motherboard", "mb_a5_itx")
    assert check(kb, build, "R19").status == "fail"


def test_pcie8_and_psu_form(kb):
    build = change(DEMOS["Совместимая сборка"], "GPU", "gpu_plus")
    build = change(build, "PSU", "psu_400")
    assert check(kb, build, "R16").status == "fail"
    build = change(build, "Case", "case_mini")
    assert check(kb, build, "R14").status == "fail"


def test_budget_boundary(kb):
    good = DEMOS["Совместимая сборка"]
    assert check(kb, replace(good, budget=91000), "R22").status == "pass"
    assert check(kb, replace(good, budget=90999), "R22").status == "fail"
    assert check(kb, replace(good, budget=0), "R22").status == "fail"


def test_recommendations_validate_trial_and_respect_budget(kb):
    build = change(DEMOS["Совместимая сборка"], "RAM", "ram_d4_32")
    rows = recommend(kb, build, "RAM")
    assert any(r["component"].id == "ram_d5_32" and r["status"] == "pass" for r in rows)
    assert next(r for r in rows if r["component"].id == "ram_d4_32")["status"] == "fail"
    expensive = next(r for r in rows if r["component"].id == "ram_d5_128")
    assert any(c.rule == "R22" and c.status == "fail" for c in expensive["checks"])


def test_recommendation_does_not_hide_existing_unrelated_conflict(kb):
    build = change(DEMOS["Совместимая сборка"], "RAM", "ram_d4_16")
    rows = recommend(kb, build, "GPU")
    good = next(r for r in rows if r["component"].id == "gpu_mid")
    assert good["status"] == "pass"
    assert validate(kb, build).status == "fail"


def test_board_recommendation_uses_its_own_bios(kb):
    build = change(DEMOS["Совместимая сборка"], "CPU", "cpu_a5_8", bios_revision=999)
    mini = next(r for r in recommend(kb, build, "Motherboard") if r["component"].id == "mb_a5_itx")
    assert mini["bios_revision"] == 100
    assert any(c.rule == "R02" and c.status == "fail" for c in mini["checks"])


def test_serialization_recomputes_saved_result(kb):
    data = json.loads(json.dumps(export_build(kb, DEMOS["Совместимая сборка"])))
    data["result"]["status"] = "fail"
    restored = import_build(kb, data)
    assert validate(kb, restored).status == "pass"


@pytest.mark.parametrize("data", [[], {}, {"format": "pc-ontology-build", "version": 1, "parts": {"CPU": "psu_550"}},
    {"format": "pc-ontology-build", "version": 1, "parts": {"CPU": "missing"}},
    {"format": "pc-ontology-build", "version": 1, "parts": {"other": "gpu_mid"}},
    {"format": "pc-ontology-build", "version": 1, "parts": {}, "bios_revision": "abc"}])
def test_invalid_import(kb, data):
    with pytest.raises(ValueError):
        import_build(kb, data)


def test_all_sparql_queries_execute(kb):
    assert [len(kb.query(name)) for name in QUERIES] == [5, 20, 4, 1, 25]


def test_owl_is_runtime_source(tmp_path):
    path = generate(tmp_path / "test.owl")
    kb = KnowledgeBase(path)
    kb.onto.ram_d5_32.capacityGB = 999
    kb.onto.save(file=str(path))
    kb.close()
    reloaded = KnowledgeBase(path)
    assert reloaded.components["ram_d5_32"].get("capacityGB") == 999
    assert check(reloaded, DEMOS["Совместимая сборка"], "R07").status == "fail"
    reloaded.close()


@pytest.mark.skipif(shutil.which("java") is None, reason="Java is not installed")
def test_actual_hermit_classification(kb):
    assert kb.onto.DDR5Board not in kb.onto.mb_a5.is_a
    inferred = kb.reason()
    assert sum(row["Выведенный класс"] in {"DDR4Board", "DDR5Board", "AM4CPU", "AM5CPU", "LGA1700CPU"} for row in inferred) == 21
    assert kb.onto.DDR5Board in kb.onto.mb_a5.INDIRECT_is_a
    assert kb.onto.AM5CPU in kb.onto.cpu_a5_6.INDIRECT_is_a
    assert not list(kb.world.inconsistent_classes())


@pytest.mark.skipif(shutil.which("java") is None, reason="Java is not installed")
def test_disjoint_classes_reject_invalid_ontology(kb):
    kb.onto.cpu_a5_6.is_a.append(kb.onto.Motherboard)
    with pytest.raises(OwlReadyInconsistentOntologyError):
        kb.reason()
