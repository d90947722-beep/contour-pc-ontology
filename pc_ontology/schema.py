"""Build the OWL schema and reproducible demonstration knowledge base."""
from pathlib import Path
import types
from owlready2 import (World, Thing, ObjectProperty, DataProperty, FunctionalProperty,
                       AllDisjoint, AllDifferent, locstr, OneOf, And)
from .catalog_seed import VOCAB, META, SUPPORT, seed

BASE = "https://example.org/pc-ontology#"
ROOT = Path(__file__).resolve().parents[1]
OWL_PATH = ROOT / "ontology" / "components.owl"
KINDS = {"CPU": "Процессор", "Motherboard": "Материнская плата", "RAM": "Оперативная память",
         "GPU": "Видеокарта", "PSU": "Блок питания", "Case": "Корпус",
         "Storage": "Накопитель", "Cooler": "Кулер"}
OBJECTS = {
    "hasSocket": ("Component", "Socket", True),
    "supportsSocket": ("Cooler", "Socket", False),
    "supportsMemory": ("Component", "MemoryStandard", False),
    "hasMemoryStandard": ("RAM", "MemoryStandard", True),
    "hasBoardForm": ("Motherboard", "BoardFormFactor", True),
    "supportsBoardForm": ("Case", "BoardFormFactor", False),
    "hasPowerForm": ("PSU", "PowerFormFactor", True),
    "supportsPowerForm": ("Case", "PowerFormFactor", False),
    "supportsStorage": ("Motherboard", "StorageInterface", False),
    "hasStorageInterface": ("Storage", "StorageInterface", True),
    "hasMemoryForm": ("RAM", "MemoryFormFactor", True),
    "supportsMemoryForm": ("Motherboard", "MemoryFormFactor", False),
    "forCPU": ("CPUBoardSupport", "CPU", True),
    "forBoard": ("CPUBoardSupport", "Motherboard", True),
}
NUMBERS = ["price", "peakPowerW", "maxMemoryGB", "memorySlots", "biosRevision", "requiredEPS",
           "maxM2LengthMM", "capacityGB", "moduleCount", "lengthMM", "requiredPCIe8",
           "required12V2x6", "ratedPowerW", "availablePCIe8", "available12V2x6",
           "availableEPS", "availableSATA", "maxGPULengthMM", "maxCoolerHeightMM",
           "heightMM", "coolingCapacityW", "minBios"]
EXTRA_NUMBERS = ["tdpW", "coreCount", "threadCount", "gpuPowerW", "recommendedPSUW", "thicknessMM",
                 "maxGPUThicknessMM", "ramClearanceMM", "sataPortCount", "m2SlotCount", "gpuSlots", "maxPSULengthMM"]
EXTRA_BOOLS = ["hasIntegratedGraphics", "hasDisplayOutput", "unlimitedRAMClearance"]


def extend_schema(onto):
    """Builds, assessments, evidence and source provenance, with OWL definitions."""
    with onto:
        for name in EXTRA_NUMBERS + EXTRA_BOOLS:
            if onto[name] is not None:
                continue
            prop = types.new_class(name, (DataProperty, FunctionalProperty))
            prop.domain, prop.range = [onto.Component], [bool if name in EXTRA_BOOLS else int]
        prop = types.new_class("supportedM2LengthsMM", (DataProperty,))
        prop.domain, prop.range = [onto.Motherboard], [int]
        for name in ["minBiosLabel", "supportStatus"]:
            prop = types.new_class(name, (DataProperty, FunctionalProperty))
            prop.domain, prop.range = [onto.CPUBoardSupport], [str]
        for name in ["Assembly", "Assessment", "Constraint", "SourceDocument", "FactAssertion"]:
            types.new_class(name, (Thing,))
        for name in ["PassedAssessment", "FailedAssessment", "UnknownAssessment"]:
            types.new_class(name, (onto.Assessment,))
        AllDisjoint([onto.PassedAssessment, onto.FailedAssessment, onto.UnknownAssessment])
        AllDisjoint([onto.Assembly, onto.Assessment, onto.Constraint, onto.SourceDocument,
                     onto.FactAssertion, onto.Component])
        relations = {
            "hasComponent": ("Assembly", "Component", False),
            "hasAssessment": ("Assembly", "Assessment", False),
            "assessesBuild": ("Assessment", "Assembly", True),
            "appliesConstraint": ("Assessment", "Constraint", True),
            "involvesComponent": ("Assessment", "Component", False),
            "usesFact": ("Assessment", "FactAssertion", False),
            "hasFact": ("Component", "FactAssertion", False),
            "factSubject": ("FactAssertion", "Component", True),
            "hasSource": ("Component", "SourceDocument", False),
            "factSource": ("FactAssertion", "SourceDocument", False),
            "supportSource": ("CPUBoardSupport", "SourceDocument", False),
            "usesSource": ("Assessment", "SourceDocument", False),
            "supportedCPUIDs": ("Cooler", "CPU", False),
        }
        for name, (domain, range_, single) in relations.items():
            prop = types.new_class(name, (ObjectProperty, FunctionalProperty) if single else (ObjectProperty,))
            prop.domain, prop.range = [onto[domain]], [onto[range_]]
        onto.hasAssessment.inverse_property = onto.assessesBuild
        onto.hasFact.inverse_property = onto.factSubject
        texts = {
            "sourceURL": "SourceDocument", "publisher": "SourceDocument", "checkedDate": "SourceDocument",
            "factProperty": "FactAssertion", "factValue": "FactAssertion", "evidenceKind": "FactAssertion",
            "assessmentMessage": "Assessment", "evidenceText": "Assessment", "ruleCode": "Constraint",
            "biosLabel": "Assembly", "graphicsMode": "Assembly", "createdAt": "Assembly", "selectionJSON": "Assembly",
        }
        for name, domain in texts.items():
            prop = types.new_class(name, (DataProperty, FunctionalProperty))
            prop.domain, prop.range = [onto[domain]], [str]
        for name in ["budgetAmount", "assessedTotal"]:
            prop = types.new_class(name, (DataProperty, FunctionalProperty))
            prop.domain, prop.range = [onto.Assembly], [int]
        full_discrete = And([onto.hasComponent.some(onto[k]) for k in KINDS])
        full_integrated = And([onto.hasComponent.some(onto[k]) for k in KINDS if k != "GPU"])
        full_integrated = full_integrated & onto.graphicsMode.value("integrated") & onto.hasComponent.some(
            onto.CPU & onto.hasIntegratedGraphics.value(True)) & onto.hasComponent.some(
            onto.Motherboard & onto.hasDisplayOutput.value(True))
        classes = {
            "PopulatedBuild": onto.Assembly & (full_discrete | full_integrated),
            "AssessedBuild": onto.Assembly & onto.hasAssessment.some(onto.Assessment),
            "ConflictedBuild": onto.Assembly & onto.hasAssessment.some(onto.FailedAssessment),
            "UncertainBuild": onto.Assembly & onto.hasAssessment.some(onto.UnknownAssessment),
            "EvidenceBackedComponent": onto.Component & onto.hasSource.some(onto.SourceDocument),
            "DualStandardCPU": onto.CPU & onto.supportsMemory.value(onto.DDR4) & onto.supportsMemory.value(onto.DDR5),
        }
        for name, definition in classes.items():
            cls = types.new_class(name, (onto.Component if name == "EvidenceBackedComponent" else onto.CPU if name == "DualStandardCPU" else onto.Assembly,))
            cls.equivalent_to = [definition]
        verified = types.new_class("VerifiedBuild", (onto.Assembly,))
        verified.equivalent_to = [onto.PopulatedBuild & onto.hasAssessment.some(onto.PassedAssessment)
                                  & onto.hasAssessment.only(onto.PassedAssessment)]
        for name, status in [("SupportedCPUBoardSupport", "supported"), ("UnsupportedCPUBoardSupport", "unsupported")]:
            cls = types.new_class(name, (onto.CPUBoardSupport,))
            cls.equivalent_to = [onto.CPUBoardSupport & onto.supportStatus.value(status)]
        AllDisjoint([onto.SupportedCPUBoardSupport, onto.UnsupportedCPUBoardSupport])
        for code in [f"R{i:02d}" for i in range(1, 30)] + ["D01"]:
            rule = onto.Constraint("rule_" + code)
            rule.ruleCode = code
        source = onto.SourceDocument("source_synthetic")
        source.label = [locstr("Синтетический набор версии 1", "ru")]
        source.publisher, source.checkedDate = "Автор учебного прототипа", "2026-10-28"
        for profile in onto.CPUBoardSupport.instances():
            profile.supportStatus, profile.supportSource = "supported", [source]
        negative = onto.CPUBoardSupport("support_explicit_negative_demo")
        negative.forCPU, negative.forBoard = onto.cpu_a4_6, onto.mb_a5
        negative.supportStatus, negative.supportSource = "unsupported", [source]
        negative.label = ["Учебный пример явного отрицательного сведения"]
        for component in onto.Component.instances():
            component.hasSource = [source]
            for name in NUMBERS + EXTRA_NUMBERS + EXTRA_BOOLS + list(OBJECTS):
                value = getattr(component, name)
                if value is None or value == []:
                    continue
                claim = onto.FactAssertion("fact_" + component.name + "_" + name)
                claim.factSubject = component
                claim.factProperty = name
                claim.factValue = str([v.name for v in value] if isinstance(value, list) else value.name if hasattr(value, "name") else value)
                claim.evidenceKind = "synthetic"
                claim.factSource = [source]


def add_real_catalog(onto):
    from .real_catalog import REAL_ITEMS, REAL_SUPPORT, SOURCES
    with onto:
        for id, info in SOURCES.items():
            source = onto.SourceDocument(id)
            source.label = [info["title"]]
            source.sourceURL, source.publisher, source.checkedDate = info["url"], info["publisher"], info["checkedDate"]
        for item in REAL_ITEMS:
            obj = onto[item["kind"]](item["id"])
            obj.label = [item["title"]]
        for item in REAL_ITEMS:
            obj = onto[item["id"]]
            obj.catalogKind = "manufacturer"
            obj.sourceNote = item["sourceNote"]
            obj.hasSource = [onto[id] for id in item["sources"]]
            facts = {k: v for k, v in item.items() if k not in {"id", "kind", "title", "catalogKind", "sourceNote", "sources", "factSources", "assumptions"} and v is not None and v != []}
            for name, value in facts.items():
                if name in OBJECTS:
                    value = [onto[v] for v in value] if isinstance(value, list) else onto[value]
                elif name == "supportedCPUIDs":
                    value = [onto[v] for v in value]
                elif name not in NUMBERS + EXTRA_NUMBERS + EXTRA_BOOLS + ["supportedM2LengthsMM"]:
                    raise ValueError(f"Unknown real catalog property {name}")
                setattr(obj, name, value)
            for key, source_id in item["factSources"].items():
                name, _, target = key.partition(":")
                value = target if target else item.get(name)
                if value is None or value == []:
                    continue
                claim = onto.FactAssertion("fact_" + obj.name + "_" + key.replace(":", "_"))
                claim.factSubject, claim.factProperty, claim.factValue = obj, name, str(value)
                claim.evidenceKind = "manufacturer"
                claim.factSource = [onto[source_id]]
        for i, profile in enumerate(REAL_SUPPORT):
            obj = onto.CPUBoardSupport(f"real_support_{i:02d}")
            obj.forCPU, obj.forBoard = onto[profile["cpu"]], onto[profile["board"]]
            obj.minBiosLabel, obj.supportStatus = profile["minBiosLabel"], profile["status"]
            obj.supportSource = [onto[profile["source"]]]


def generate(path=OWL_PATH):
    world = World()
    onto = world.get_ontology(BASE)
    with onto:
        component = types.new_class("Component", (Thing,))
        component.label = [locstr("Комплектующее", "ru")]
        for name, label in KINDS.items():
            cls = types.new_class(name, (component,))
            cls.label = [locstr(label, "ru")]
        for name in VOCAB:
            types.new_class(name, (Thing,))
        types.new_class("CPUBoardSupport", (Thing,))
        AllDisjoint([onto[name] for name in KINDS])
        AllDisjoint([component, onto.CPUBoardSupport] + [onto[name] for name in VOCAB])
        for name, (domain, range_, functional) in OBJECTS.items():
            parents = (ObjectProperty, FunctionalProperty) if functional else (ObjectProperty,)
            prop = types.new_class(name, parents)
            prop.domain = [onto[domain]]
            prop.range = [onto[range_]]
        for name in NUMBERS:
            prop = types.new_class(name, (DataProperty, FunctionalProperty))
            prop.range = [int]
            prop.domain = [onto.CPUBoardSupport if name == "minBios" else component]
        for name in EXTRA_NUMBERS + EXTRA_BOOLS:
            prop = types.new_class(name, (DataProperty, FunctionalProperty))
            prop.range = [bool if name in EXTRA_BOOLS else int]
            prop.domain = [component]
        for name in ["sourceNote", "catalogKind"]:
            prop = types.new_class(name, (DataProperty, FunctionalProperty))
            prop.range = [str]
            prop.domain = [component]
        for class_name, individuals in VOCAB.items():
            values = []
            for name, label in individuals.items():
                individual = onto[class_name](name)
                individual.label = [label]
                values.append(individual)
            AllDifferent(values)
        for name, standard in [("DDR4Board", "DDR4"), ("DDR5Board", "DDR5")]:
            cls = types.new_class(name, (onto.Motherboard,))
            cls.equivalent_to = [onto.Motherboard & onto.supportsMemory.value(onto[standard])]
        for name, socket in [("AM4CPU", "AM4"), ("AM5CPU", "AM5"), ("LGA1700CPU", "LGA1700")]:
            cls = types.new_class(name, (onto.CPU,))
            cls.equivalent_to = [onto.CPU & onto.hasSocket.value(onto[socket])]
        for item in seed():
            obj = onto[item["kind"]](item["id"])
            obj.label = [locstr(item["title"], "ru")]
            obj.sourceNote = META["description"]
            obj.catalogKind = META["kind"]
            for name, value in item.items():
                if name in ("id", "kind", "title") or value is None:
                    continue
                if name in OBJECTS:
                    value = [onto[v] for v in value] if isinstance(value, list) else onto[value]
                setattr(obj, name, value)
        for i, (board, cpu, bios) in enumerate(SUPPORT):
            obj = onto.CPUBoardSupport(f"support_{i:02d}")
            obj.forCPU, obj.forBoard, obj.minBios = onto[cpu], onto[board], bios
        extend_schema(onto)
        add_real_catalog(onto)
        onto.metadata.comment.append(locstr(META["description"], "ru"))
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    onto.save(file=str(path), format="rdfxml")
    world.close()
    return path


if __name__ == "__main__":
    print(generate())
