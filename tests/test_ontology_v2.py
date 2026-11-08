from owlready2 import World
from pc_ontology.knowledge import KnowledgeBase
from pc_ontology.engine import DEMOS, Build
from pc_ontology.rdf_build import populate_build, export_rdf
from pc_ontology.schema import BASE
from dataclasses import replace


def test_builds_are_inferred_from_assessments():
    kb = KnowledgeBase()
    for i, build in enumerate(DEMOS.values()):
        populate_build(kb, build, f"example_{i}")
    populate_build(kb, Build(), "empty")
    kb.reason()
    assert kb.onto.VerifiedBuild in kb.onto.example_0.INDIRECT_is_a
    assert kb.onto.ConflictedBuild in kb.onto.example_1.INDIRECT_is_a
    assert kb.onto.VerifiedBuild not in kb.onto.example_1.INDIRECT_is_a
    assert kb.onto.UncertainBuild in kb.onto.example_2.INDIRECT_is_a
    assert kb.onto.PopulatedBuild not in kb.onto.empty.INDIRECT_is_a
    assert kb.onto.VerifiedBuild not in kb.onto.empty.INDIRECT_is_a
    kb.close()


def test_export_has_evidence_without_mutating_catalog(tmp_path):
    kb = KnowledgeBase()
    original_count = len(list(kb.onto.individuals()))
    data = export_rdf(kb, DEMOS["Совместимая сборка"])
    path = tmp_path / "build.owl"
    path.write_bytes(data)
    snapshot = KnowledgeBase(path)
    builds = list(snapshot.onto.Assembly.instances())
    assert len(builds) == 1
    assert len(builds[0].hasComponent) == 8
    assert len(builds[0].hasAssessment) == 21
    socket_check = next(c for c in builds[0].hasAssessment if c.appliesConstraint.ruleCode == "R01")
    assert {f.factProperty for f in socket_check.usesFact} == {"hasSocket"}
    assert len(socket_check.usesFact) == 2
    assert len(list(kb.onto.individuals())) == original_count
    snapshot.close()
    kb.close()


def test_integrated_build_classification_and_price_provenance(tmp_path):
    kb = KnowledgeBase()
    good = DEMOS["Совместимая сборка"]
    integrated = replace(good, parts={**good.parts, "GPU": None}, graphics_mode="integrated",
                         price_overrides={"cpu_a5_6": 12345})
    assembly = populate_build(kb, integrated, "integrated_example")
    kb.reason()
    assert kb.onto.VerifiedBuild in assembly.INDIRECT_is_a
    price_check = next(a for a in assembly.hasAssessment if a.appliesConstraint.ruleCode == "R22")
    overrides = [claim for claim in price_check.usesFact if claim.evidenceKind == "user_input"]
    assert len(overrides) == 1
    assert overrides[0].factValue == "12345"
    assert overrides[0].factSource[0].publisher == "Пользователь"
    assert kb.onto.cpu_a5_6.price == 19000  # Catalog price was not overwritten.
    kb.close()
