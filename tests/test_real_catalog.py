from dataclasses import replace
import pytest
from pc_ontology.engine import Build, validate, export_build, import_build
from pc_ontology.knowledge import KnowledgeBase
from pc_ontology.real_catalog import REAL_ITEMS, REAL_SUPPORT, SOURCES


@pytest.fixture
def kb():
    value = KnowledgeBase()
    yield value
    value.close()


def real_build():
    return Build(dict(CPU="real_cpu_7600", Motherboard="real_mb_b650_plus", RAM="real_ram_d5_32",
                      GPU="real_gpu_4060", PSU="real_psu_650", Case="real_case_pop",
                      Storage="real_ssd_980_1", Cooler="real_cooler_redux"), "0602")


def by_rule(kb, build, rule):
    return next(c for c in validate(kb, build).checks if c.rule == rule)


def test_real_facts_have_per_property_provenance(kb):
    assert len(REAL_ITEMS) == 32
    assert len(REAL_SUPPORT) == 8
    for item in REAL_ITEMS:
        obj = kb.onto[item["id"]]
        assert obj.catalogKind == "manufacturer"
        assert obj.price is None
        assert obj.hasSource
        assert obj.hasFact
        for claim in obj.hasFact:
            assert claim.factSource
            assert all(s.sourceURL.startswith("https://") and s.checkedDate == "2026-10-28" for s in claim.factSource)
    assert kb.components["real_cpu_7600"].get("tdpW") == 65
    assert kb.components["real_cpu_7600"].get("peakPowerW") is None


def test_real_bios_exact_label_and_unknown_order(kb):
    build = real_build()
    assert by_rule(kb, build, "R02").status == "pass"
    assert by_rule(kb, replace(build, bios_revision="9999"), "R02").status == "unknown"
    assert by_rule(kb, replace(build, bios_revision=None), "R02").status == "unknown"
    key = ("real_mb_b650_plus", "real_cpu_7600")
    kb.support_info[key]["status"] = "unsupported"
    assert by_rule(kb, build, "R02").status == "fail"


def test_no_tdp_to_peak_or_cooler_wattage_substitution(kb):
    build = real_build()
    assert by_rule(kb, build, "R15").status == "unknown"
    assert by_rule(kb, build, "R13").status == "pass"
    assert by_rule(kb, build, "R27").status == "pass"
    assert validate(kb, build).status == "unknown"


def test_extended_geometry_and_psu_rules(kb):
    build = real_build()
    assert by_rule(kb, build, "R25").status == "pass"
    assert by_rule(kb, build, "R26").status == "unknown"
    assert by_rule(kb, build, "R28").status == "pass"
    assert by_rule(kb, build, "R29").status == "pass"
    kb.components["real_mb_b650_plus"].facts["supportedM2LengthsMM"] = [42, 60]
    assert by_rule(kb, build, "R25").status == "fail"
    kb.components["real_case_pop"].facts["maxGPUThicknessMM"] = 40
    assert by_rule(kb, build, "R26").status == "fail"


def test_unused_gpu_connector_needs_no_availability_fact(kb):
    build = replace(real_build(), parts={**real_build().parts, "PSU": "real_psu_750"})
    assert kb.components["real_psu_750"].get("available12V2x6") is None
    assert by_rule(kb, build, "R17").status == "pass"


def test_integrated_graphics_requires_cpu_and_board(kb):
    build = real_build()
    build = replace(build, parts={**build.parts, "GPU": None}, graphics_mode="integrated")
    result = validate(kb, build)
    assert not result.missing
    assert by_rule(kb, build, "R23").status == "pass"
    assert by_rule(kb, build, "R24").status == "pass"
    assert not any(c.rule in {"R10", "R16", "R17", "R26", "R28"} for c in result.checks)
    build = replace(build, parts={**build.parts, "CPU": "real_cpu_5600"})
    assert by_rule(kb, build, "R23").status == "fail"


def test_user_prices_are_separate_from_manufacturer_facts(kb):
    build = real_build()
    priced = replace(build, budget=100000, price_overrides={id: 5000 for id in build.parts.values()})
    assert validate(kb, priced).total == 40000
    assert by_rule(kb, priced, "R22").status == "pass"
    assert all(kb.components[id].get("price") is None for id in build.parts.values())
    assert import_build(kb, export_build(kb, priced)) == priced
