from rdflib import Graph, Namespace
import pytest
from pc_ontology.knowledge import KnowledgeBase
from pc_ontology.explorer import neighborhood
from pc_ontology.schema import BASE


@pytest.fixture
def kb():
    value = KnowledgeBase()
    yield value
    value.close()


def test_graph_uses_real_subject_object_relations(kb):
    graph = neighborhood(kb, "real_cpu_7600")
    pc = Namespace(BASE)
    rdf = Graph().parse(data=graph.turtle, format="turtle")
    assert (pc.real_cpu_7600, pc.hasSocket, pc.AM5) in rdf
    assert (pc.real_cpu_7600, pc.supportsMemory, pc.DDR5) in rdf
    assert (pc.real_support_06, pc.forCPU, pc.real_cpu_7600) in rdf
    assert 'hasSocket' in graph.dot
    assert not any(row['Связь'] == 'factSubject' for row in graph.rows)


def test_provenance_toggle_and_bounded_two_hop_graph(kb):
    simple = neighborhood(kb, "real_cpu_7600")
    detailed = neighborhood(kb, "real_cpu_7600", include_provenance=True, include_literals=True)
    assert detailed.edge_count > simple.edge_count
    assert any(row['Связь'] == 'factSubject' for row in detailed.rows)
    assert any(row['Связь'] == 'coreCount' for row in detailed.rows)
    bounded = neighborhood(kb, "real_cpu_7600", depth=2, include_provenance=True, include_literals=True, max_nodes=12)
    assert bounded.node_count <= 12
    assert bounded.truncated
    assert Graph().parse(data=bounded.turtle, format="turtle")


def test_class_restrictions_do_not_break_two_hop_neighborhood(kb):
    graph = neighborhood(kb, "AM5", depth=2)
    assert graph.node_count > 1
    assert 'AM5' in graph.dot


def test_unknown_root_is_rejected(kb):
    with pytest.raises(ValueError):
        neighborhood(kb, "does_not_exist")
