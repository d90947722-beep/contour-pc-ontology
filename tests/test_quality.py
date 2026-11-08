from datetime import date
from rdflib import Graph, Namespace, Literal, URIRef
import pytest
from pc_ontology.quality import audit, read_graph, provenance_coverage, review_sources
from pc_ontology.schema import OWL_PATH, BASE
from pc_ontology.knowledge import KnowledgeBase
from pc_ontology.engine import Build, DEMOS
from pc_ontology.rdf_build import export_rdf

PC = Namespace(BASE)
XSD_STRING = URIRef("http://www.w3.org/2001/XMLSchema#string")


def test_catalog_conforms_and_all_real_values_have_evidence():
    report = audit(today=date(2026, 10, 28))
    assert report.conforms
    assert not report.findings
    assert len(report.coverage) == 32
    assert all(row["Записанных значений"] == row["Значений с источником"] for row in report.coverage)
    assert all(row["Состояние"] == "Дата сверки актуальна" for row in report.source_reviews)
    Graph().parse(data=report.validation_turtle, format="turtle")


def test_missing_socket_and_negative_power_are_formal_violations():
    graph = read_graph()
    graph.remove((PC.real_cpu_7600, PC.hasSocket, None))
    graph.set((PC.psu_550, PC.ratedPowerW, Literal(-1)))
    original = len(graph)
    report = audit(graph)
    assert not report.conforms
    assert any(r["ID"] == "real_cpu_7600" and r["Свойство"] == "hasSocket" for r in report.findings)
    assert any(r["ID"] == "psu_550" and r["Свойство"] == "ratedPowerW" for r in report.findings)
    assert len(graph) == original  # Validation never expands caller-owned graph.


def test_manufacturer_fact_without_url_is_rejected():
    graph = read_graph()
    graph.remove((PC.src_cpu_7600, PC.sourceURL, None))
    report = audit(graph)
    assert not report.conforms
    assert any("URL" in row["Причина"] for row in report.findings)


def test_optional_unknown_values_and_partial_build_are_valid_snapshots():
    kb = KnowledgeBase()
    data = export_rdf(kb, Build())
    report = audit(data)
    assert report.conforms, report.validation_text
    kb.close()


def test_coverage_detects_missing_per_cpu_evidence():
    graph = read_graph()
    claim = PC.fact_real_cooler_redux_supportedCPUIDs_real_cpu_7600
    graph.remove((claim, None, None))
    row = next(r for r in provenance_coverage(graph) if r["id"] == "real_cooler_redux")
    assert row["Значений с источником"] < row["Записанных значений"]
    assert "supportedCPUIDs" in row["Без подтверждающей записи"]


def test_dates_distinguish_future_stale_and_invalid():
    graph = read_graph()
    graph.set((PC.src_cpu_7600, PC.checkedDate, Literal("2026-99-01", datatype=XSD_STRING)))
    graph.set((PC.src_cpu_5600, PC.checkedDate, Literal("2027-01-01", datatype=XSD_STRING)))
    graph.set((PC.src_cpu_7700, PC.checkedDate, Literal("2020-01-01", datatype=XSD_STRING)))
    states = {r["Состояние"] for r in review_sources(graph, today=date(2026, 10, 28))}
    assert {"Дата в будущем", "Стоит перепроверить", "Некорректная или отсутствующая дата"} <= states
