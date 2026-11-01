"""Read facts and relationships from OWL; no parallel runtime catalog."""
from dataclasses import dataclass
from pathlib import Path
import owlready2.reasoning
from owlready2 import World, sync_reasoner
from .schema import BASE, OWL_PATH, KINDS, OBJECTS, NUMBERS, EXTRA_NUMBERS, EXTRA_BOOLS


@dataclass(frozen=True)
class Component:
    id: str
    kind: str
    title: str
    facts: dict

    def get(self, name):
        return self.facts.get(name)


QUERIES = {
    "Платы с DDR5": """PREFIX pc: <https://example.org/pc-ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?board ?title WHERE {
  ?board a pc:Motherboard ; pc:supportsMemory pc:DDR5 ; rdfs:label ?title .
} ORDER BY ?title""",
    "Поддержка процессоров и BIOS": """PREFIX pc: <https://example.org/pc-ontology#>
SELECT ?board ?cpu ?minimumBIOS WHERE {
  ?support a pc:CPUBoardSupport ; pc:forBoard ?board ;
           pc:forCPU ?cpu .
  { ?support pc:minBios ?minimumBIOS } UNION { ?support pc:minBiosLabel ?minimumBIOS }
} ORDER BY ?board ?cpu""",
    "Процессоры с сокетом AM5": """PREFIX pc: <https://example.org/pc-ontology#>
SELECT ?cpu ?socket WHERE {
  ?cpu a pc:CPU ; pc:hasSocket ?socket . FILTER (?socket = pc:AM5)
} ORDER BY ?cpu""",
    "Явные отрицательные сведения": """PREFIX pc: <https://example.org/pc-ontology#>
SELECT ?board ?cpu WHERE {
  ?profile a pc:CPUBoardSupport ; pc:forBoard ?board ; pc:forCPU ?cpu ; pc:supportStatus "unsupported" .
} ORDER BY ?board ?cpu""",
    "Источники отдельных утверждений": """PREFIX pc: <https://example.org/pc-ontology#>
SELECT ?component ?property ?value ?url WHERE {
  ?claim a pc:FactAssertion ; pc:factSubject ?component ; pc:factProperty ?property ;
         pc:factValue ?value ; pc:factSource ?source .
  ?source pc:sourceURL ?url .
} ORDER BY ?component ?property LIMIT 25""",
}
QUERY_COLUMNS = {
    "Платы с DDR5": ["ID платы", "Название"],
    "Поддержка процессоров и BIOS": ["ID платы", "ID процессора", "Минимальная ревизия BIOS"],
    "Процессоры с сокетом AM5": ["ID процессора", "Сокет"],
    "Явные отрицательные сведения": ["ID платы", "ID процессора"],
    "Источники отдельных утверждений": ["Компонент", "Свойство", "Значение", "URL"],
}


class KnowledgeBase:
    def __init__(self, path=OWL_PATH):
        self.path = Path(path).resolve()
        self.world = World()
        with self.path.open("rb") as source:
            self.onto = self.world.get_ontology(BASE).load(fileobj=source)
        self.components = {}
        for kind in KINDS:
            for obj in self.onto[kind].instances():
                facts = {name: getattr(obj, name) for name in NUMBERS + EXTRA_NUMBERS + EXTRA_BOOLS}
                facts["supportedM2LengthsMM"] = list(obj.supportedM2LengthsMM)
                for name, (_, _, single) in OBJECTS.items():
                    value = getattr(obj, name)
                    facts[name] = (value.name if value else None) if single else [v.name for v in value]
                facts["sourceNote"] = obj.sourceNote
                facts["catalogKind"] = obj.catalogKind
                facts["supportedCPUIDs"] = [o.name for o in obj.supportedCPUIDs]
                self.components[obj.name] = Component(obj.name, kind, str(obj.label.first() or obj.name), facts)
        # Query an n-ary OWL relationship rather than consulting the seed file.
        rows = self.world.sparql("""PREFIX pc: <https://example.org/pc-ontology#>
            SELECT ?board ?cpu ?bios WHERE {
              ?s a pc:CPUBoardSupport ; pc:forBoard ?board ; pc:forCPU ?cpu ; pc:minBios ?bios .
            }""")
        self.support = {(board.name, cpu.name): bios for board, cpu, bios in rows}
        self.support_info = {(profile.forBoard.name, profile.forCPU.name):
                             {"status": profile.supportStatus, "minBiosLabel": profile.minBiosLabel}
                             for profile in self.onto.CPUBoardSupport.instances() if profile.forBoard and profile.forCPU}

    def provenance(self, id):
        obj = self.onto[id]
        return [{"Свойство": f.factProperty, "Значение": f.factValue, "Тип сведений": f.evidenceKind,
                 "Источник": "; ".join(s.sourceURL or str(s.label.first()) for s in f.factSource),
                 "Проверено": "; ".join(s.checkedDate or "" for s in f.factSource)} for f in obj.hasFact]

    def by_kind(self, kind):
        return sorted((c for c in self.components.values() if c.kind == kind),
                      key=lambda c: (c.get("price") is None, c.get("price") or 0, c.title))

    def query(self, name):
        return [dict(zip(QUERY_COLUMNS[name],
                         [v.name if hasattr(v, "name") else v for v in row]))
                for row in self.world.sparql(QUERIES[name])]

    def reason(self):
        # The isolated world is essential: inference must not affect other sessions.
        targets = list(self.onto.Component.instances()) + list(self.onto.Assembly.instances()) + list(self.onto.CPUBoardSupport.instances())
        before = {o.name: {c.name for c in o.INDIRECT_is_a if hasattr(c, "name")} for o in targets}
        owlready2.reasoning.JAVA_MEMORY = 512
        with self.onto:
            sync_reasoner([self.onto], infer_property_values=True, debug=0)
        inferred = []
        names = {"DDR4Board", "DDR5Board", "AM4CPU", "AM5CPU", "LGA1700CPU", "EvidenceBackedComponent",
                 "DualStandardCPU", "PopulatedBuild", "AssessedBuild", "ConflictedBuild", "UncertainBuild", "VerifiedBuild",
                 "SupportedCPUBoardSupport", "UnsupportedCPUBoardSupport"}
        for obj in targets:
            ancestors = {cls.name for cls in obj.INDIRECT_is_a if hasattr(cls, "name")}
            for name in sorted(ancestors & names):
                if name not in before[obj.name]:
                    inferred.append({"Объект": str(obj.label.first() or obj.name), "Выведенный класс": name})
        return inferred

    def stats(self):
        return {"classes": len(list(self.onto.classes())),
                "object_properties": len(list(self.onto.object_properties())),
                "data_properties": len(list(self.onto.data_properties())),
                "individuals": len(list(self.onto.individuals())),
                "components": len(self.components), "support_profiles": len(self.support_info),
                "manufacturer_components": sum(c.get("catalogKind") == "manufacturer" for c in self.components.values()),
                "sources": len(list(self.onto.SourceDocument.instances())),
                "facts": len(list(self.onto.FactAssertion.instances()))}

    def close(self):
        self.world.close()
