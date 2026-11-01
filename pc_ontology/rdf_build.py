"""Export a configuration and its assessment as genuine RDF/OWL individuals."""
from datetime import datetime, timezone
import json
import tempfile
from pathlib import Path
from uuid import uuid4
from owlready2 import OneOf
from .knowledge import KnowledgeBase
from .engine import validate, export_build


def populate_build(kb, build, name=None):
    result = validate(kb, build)
    onto = kb.onto
    with onto:
        user_source = onto.SourceDocument("user_input_" + uuid4().hex)
        user_source.label = ["Параметры, введённые пользователем для этой конфигурации"]
        user_source.publisher = "Пользователь"
        user_source.checkedDate = datetime.now(timezone.utc).date().isoformat()
        user_price_claims = []
        for id, value in build.price_overrides.items():
            if id not in build.parts.values():
                continue
            claim = onto.FactAssertion("user_price_" + uuid4().hex)
            claim.factSubject, claim.factProperty, claim.factValue = onto[id], "effectivePrice", str(value)
            claim.evidenceKind, claim.factSource = "user_input", [user_source]
            user_price_claims.append(claim)
        assembly = onto.Assembly(name or "build_" + uuid4().hex)
        assembly.label = ["Конфигурация компьютера"]
        assembly.createdAt = datetime.now(timezone.utc).isoformat()
        assembly.selectionJSON = json.dumps(export_build(kb, build), ensure_ascii=False)
        assembly.graphicsMode = build.graphics_mode
        assembly.biosLabel = str(build.bios_revision) if build.bios_revision is not None else ""
        assembly.assessedTotal = result.total
        if build.budget is not None:
            assembly.budgetAmount = build.budget
        assembly.hasComponent = [onto[id] for id in build.parts.values() if id]
        # Local closure applies to this exported snapshot, not to the entire catalog.
        if assembly.hasComponent:
            assembly.is_a.append(onto.hasComponent.only(OneOf(assembly.hasComponent)))
        for check in result.checks:
            cls = {"pass": onto.PassedAssessment, "fail": onto.FailedAssessment,
                   "unknown": onto.UnknownAssessment}[check.status]
            assessment = cls(assembly.name + "_" + check.rule)
            assessment.assessesBuild = assembly
            assessment.appliesConstraint = onto["rule_" + check.rule]
            assessment.assessmentMessage = check.title + ": " + check.explanation
            assessment.evidenceText = "\n".join(check.evidence)
            assessment.involvesComponent = [onto[build.parts[s]] for s in check.participants if build.parts.get(s)]
            names = {line.split(":", 1)[0] for line in check.evidence}
            names.update({"R15": {"peakPowerW", "ratedPowerW"}, "R02": {"hasSocket"},
                          "R13": {"supportedCPUIDs", "peakPowerW", "coolingCapacityW"},
                          "R21": {"hasStorageInterface", "availableSATA"},
                          "R25": {"supportedM2LengthsMM", "lengthMM"}}.get(check.rule, set()))
            assessment.usesFact = [claim for obj in assessment.involvesComponent
                                   for claim in obj.hasFact if claim.factProperty in names and
                                   (claim.factProperty != "supportedCPUIDs" or claim.factValue == build.parts.get("CPU"))]
            if check.rule == "R22":
                assessment.usesFact = user_price_claims + [claim for obj in assembly.hasComponent
                    if obj.name not in build.price_overrides for claim in obj.hasFact if claim.factProperty == "price"]
                assessment.usesSource = [user_source]
            if check.rule == "R02":
                assessment.usesSource = [source for profile in onto.CPUBoardSupport.instances()
                                         if profile.forCPU == onto[build.parts.get("CPU", "")]
                                         and profile.forBoard == onto[build.parts.get("Motherboard", "")]
                                         for source in profile.supportSource]
                assessment.usesSource.append(user_source)
        if assembly.hasAssessment:
            assembly.is_a.append(onto.hasAssessment.only(OneOf(assembly.hasAssessment)))
    return assembly


def export_rdf(kb, build):
    """Export an isolated snapshot; never mutate the session knowledge base."""
    snapshot = KnowledgeBase(kb.path)
    try:
        populate_build(snapshot, build)
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "build.owl"
            snapshot.onto.save(file=str(target), format="rdfxml")
            return target.read_bytes()
    finally:
        snapshot.close()
