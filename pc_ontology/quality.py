"""Formal SHACL validation, provenance coverage and source-date review.

These checks assess the recorded knowledge graph, not physical compatibility.
Unknown optional hardware values are reported separately from shape violations.
"""
from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import warnings
from rdflib import Graph, Namespace, RDF, RDFS, URIRef
from pyshacl import validate as validate_shacl
from .schema import ROOT, OWL_PATH, BASE, OBJECTS, NUMBERS, EXTRA_NUMBERS, EXTRA_BOOLS

PC = Namespace(BASE)
SH = Namespace("http://www.w3.org/ns/shacl#")
SHAPES_PATH = ROOT / "ontology" / "quality-shapes.ttl"


@dataclass
class QualityReport:
    conforms: bool
    findings: list
    validation_text: str
    validation_turtle: str
    coverage: list = field(default_factory=list)
    source_reviews: list = field(default_factory=list)

    def to_dict(self):
        return {key: value for key, value in asdict(self).items() if key not in {"validation_text", "validation_turtle"}}


def read_graph(source=OWL_PATH):
    if isinstance(source, Graph):
        # pySHACL may expand the graph; retain isolation even for caller-owned graphs.
        result = Graph()
        for prefix, namespace in source.namespaces():
            result.bind(prefix, namespace)
        for triple in source:
            result.add(triple)
        return result
    if isinstance(source, bytes):
        return Graph().parse(data=source, format="xml")
    return Graph().parse(str(Path(source)), format="xml")


def node_label(graph, node):
    return str(graph.value(node, RDFS.label) or str(node).rsplit("#", 1)[-1])


def provenance_coverage(graph):
    """Coverage is evidence availability, never a score of truth or reliability."""
    properties = {PC[name] for name in list(OBJECTS) + NUMBERS + EXTRA_NUMBERS + EXTRA_BOOLS +
                  ["supportedM2LengthsMM", "supportedCPUIDs"]}
    rows = []
    for component, kind in graph.subject_objects(PC.catalogKind):
        if str(kind) != "manufacturer":
            continue
        claims = list(graph.subjects(PC.factSubject, component))
        observed, supported, missing = 0, 0, []
        for prop, value in graph.predicate_objects(component):
            if prop not in properties:
                continue
            observed += 1
            name = str(prop).rsplit("#", 1)[-1]
            candidates = [claim for claim in claims if str(graph.value(claim, PC.factProperty)) == name]
            if name == "supportedCPUIDs":
                target = str(value).rsplit("#", 1)[-1]
                candidates = [c for c in candidates if str(graph.value(c, PC.factValue)) == target]
            with_sources = [claim for claim in candidates if any(graph.value(source, PC.sourceURL)
                            for source in graph.objects(claim, PC.factSource))]
            if with_sources:
                supported += 1
            else:
                missing.append(name + (" → " + node_label(graph, value) if isinstance(value, URIRef) else ""))
        rows.append({"id": str(component).rsplit("#", 1)[-1], "Компонент": node_label(graph, component),
                     "Записанных значений": observed, "Значений с источником": supported,
                     "Без подтверждающей записи": "; ".join(sorted(missing))})
    return sorted(rows, key=lambda row: row["Компонент"])


def review_sources(graph, today=None, stale_days=180):
    today = today or datetime.now(ZoneInfo("Europe/Moscow")).date()
    rows = []
    for source in graph.subjects(RDF.type, PC.SourceDocument):
        raw = str(graph.value(source, PC.checkedDate) or "")
        url = str(graph.value(source, PC.sourceURL) or "")
        try:
            checked = date.fromisoformat(raw)
            age = (today - checked).days
            state = "Дата в будущем" if age < 0 else "Стоит перепроверить" if age > stale_days else "Дата сверки актуальна"
        except ValueError:
            state, age = "Некорректная или отсутствующая дата", None
        rows.append({"Источник": node_label(graph, source), "URL": url, "Проверено": raw,
                     "Дней с проверки": age, "Состояние": state})
    return sorted(rows, key=lambda r: (r["Состояние"] == "Дата сверки актуальна", r["Источник"]))


def audit(source=OWL_PATH, *, today=None, shapes_path=SHAPES_PATH):
    graph = read_graph(source)
    original = read_graph(graph)
    # pySHACL 0.40 uses two Dataset aliases deprecated by RDFLib 7.6.
    # Filter only those third-party notices, not SHACL findings or other warnings.
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=r"Dataset\.default_context is deprecated.*", category=DeprecationWarning, module=r"rdflib\.graph")
        warnings.filterwarnings("ignore", message=r"Dataset\.identifier is deprecated.*", category=DeprecationWarning, module=r"rdflib\.graph")
        conforms, result_graph, text = validate_shacl(graph, shacl_graph=str(shapes_path),
            inference="rdfs", abort_on_first=False, allow_warnings=False, allow_infos=False,
            do_owl_imports=False, advanced=False, js=False)
    findings = []
    for node in result_graph.subjects(RDF.type, SH.ValidationResult):
        focus = result_graph.value(node, SH.focusNode)
        path = result_graph.value(node, SH.resultPath)
        messages = list(result_graph.objects(node, SH.resultMessage))
        message = next((str(v) for v in messages if getattr(v, "language", None) == "ru"),
                       "; ".join(str(v) for v in messages))
        findings.append({"Уровень": str(result_graph.value(node, SH.resultSeverity)).rsplit("#", 1)[-1],
                         "Объект": node_label(original, focus), "ID": str(focus).rsplit("#", 1)[-1],
                         "Свойство": str(path).rsplit("#", 1)[-1] if isinstance(path, URIRef) else "Набор связанных свойств",
                         "Причина": message})
    return QualityReport(bool(conforms), sorted(findings, key=lambda r: (r["ID"], r["Свойство"], r["Причина"])),
                         str(text), result_graph.serialize(format="turtle"),
                         provenance_coverage(original), review_sources(original, today=today))


if __name__ == "__main__":
    import json
    report = audit()
    target = ROOT / "docs" / "quality"
    target.mkdir(parents=True, exist_ok=True)
    (target / "catalog-quality.json").write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    (target / "shacl-report.ttl").write_text(report.validation_turtle, encoding="utf-8")
    print(f"SHACL conforms: {report.conforms}; findings: {len(report.findings)}; real components: {len(report.coverage)}")
