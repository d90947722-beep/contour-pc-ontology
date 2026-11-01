"""Bounded neighborhoods of real OWL individuals; diagrams and RDF share triples."""
from dataclasses import dataclass
import json
import textwrap
from rdflib import Graph, Literal, URIRef, RDF
from .schema import BASE

PROVENANCE = {"hasFact", "factSubject", "factSource", "usesFact"}


def label(obj):
    return str(obj.label.first() or obj.name)


@dataclass
class Neighborhood:
    dot: str
    rows: list
    turtle: str
    node_count: int
    edge_count: int
    truncated: bool


def neighborhood(kb, id, *, depth=1, include_literals=False, include_provenance=False, max_nodes=45):
    if depth not in (1, 2) or type(max_nodes) is not int or max_nodes < 2:
        raise ValueError("Глубина должна быть 1 или 2, предел узлов — не меньше двух.")
    root = kb.onto[id]
    if root is None or not hasattr(root, "get_properties"):
        raise ValueError("Неизвестный объект онтологии.")
    known = {root.iri: (label(root), "resource")}
    frontier = [root]
    seen, edges, rows = set(), {}, {}
    graph = Graph()
    graph.bind("pc", BASE)
    truncated = False
    quote = lambda value: json.dumps(str(value), ensure_ascii=False)

    def add(subject, prop_iri, prop_label, obj, kind="object"):
        nonlocal truncated
        s = subject.iri
        target = obj.iri if hasattr(obj, "iri") else "literal:" + repr((type(obj).__name__, str(obj), getattr(obj, "lang", None)))
        additions = set([s, target]) - set(known)
        if len(known) + len(additions) > max_nodes:
            truncated = True
            return False
        known[s] = (label(subject), "resource")
        known[target] = (label(obj), "class" if kind == "type" else "resource") if hasattr(obj, "iri") else (str(obj), "literal")
        edge = (s, prop_iri, target)
        edges[edge] = prop_label
        rows[edge] = {"Из": label(subject), "Связь": prop_label, "В": known[target][0],
                      "ID источника": subject.name, "ID цели": obj.name if hasattr(obj, "iri") else "Литерал", "Тип": kind}
        term = URIRef(obj.iri) if hasattr(obj, "iri") else Literal(str(obj), lang=obj.lang) if getattr(obj, "lang", None) else Literal(obj)
        graph.add((URIRef(s), URIRef(prop_iri), term))
        return True

    for _ in range(depth):
        next_frontier = {}
        for current in sorted(frontier, key=lambda x: x.name):
            if current.iri in seen:
                continue
            seen.add(current.iri)
            for cls in current.is_a:
                if hasattr(cls, "iri"):
                    add(current, str(RDF.type), "rdf:type", cls, "type")
            for prop in sorted(current.get_properties(), key=lambda p: p.name):
                if prop.name in PROVENANCE and not include_provenance:
                    continue
                for obj in sorted(prop[current], key=str):
                    if hasattr(obj, "iri"):
                        if add(current, prop.iri, prop.name, obj):
                            next_frontier[obj.iri] = obj
                    elif include_literals and prop.name not in {"selectionJSON", "evidenceText"}:
                        add(current, prop.iri, prop.name, obj, "literal")
            inverses = [(s, p) for s, p in current.get_inverse_properties() if hasattr(s, "iri") and hasattr(p, "iri")]
            for subject, prop in sorted(inverses, key=lambda pair: (pair[1].name, pair[0].name)):
                if prop.name in PROVENANCE and not include_provenance:
                    continue
                if add(subject, prop.iri, prop.name, current):
                    next_frontier[subject.iri] = subject
        frontier = [obj for obj in next_frontier.values() if obj.iri not in seen]
    dot = ['digraph G {', 'graph [rankdir=LR bgcolor="transparent"];',
           'node [shape=box style="rounded,filled" fontname="Arial" fontsize=11];',
           'edge [fontname="Arial" fontsize=9 color="#88a293"];']
    for iri, (title, kind) in sorted(known.items()):
        color = "#176b57" if iri == root.iri else "#fff3d9" if kind == "literal" else "#e9edf6" if kind == "class" else "#edf3ec"
        font = "white" if iri == root.iri else "#20352b"
        shown_title = title if len(title) <= 120 else title[:117] + "…"
        shown_title = "\n".join(textwrap.wrap(shown_title, width=32))
        dot.append(f"{quote(iri)} [label={quote(shown_title)} fillcolor={quote(color)} fontcolor={quote(font)}];")
    for (subject, _, obj), prop_label in sorted(edges.items()):
        dot.append(f"{quote(subject)} -> {quote(obj)} [label={quote(prop_label)}];")
    dot.append("}")
    return Neighborhood("\n".join(dot), [rows[key] for key in sorted(rows)], graph.serialize(format="turtle"),
                        len(known), len(edges), truncated)
