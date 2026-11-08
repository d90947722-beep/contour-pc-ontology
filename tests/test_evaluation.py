from pc_ontology.evaluation import scenarios
from pc_ontology.knowledge import KnowledgeBase
from pc_ontology.engine import validate


def test_declared_evaluation_scenarios():
    kb = KnowledgeBase()
    for id, title, build, expected in scenarios():
        assert validate(kb, build).status == expected, (id, title)
    kb.close()
