"""Customer-facing assessment without changing the underlying validation rules."""
from dataclasses import replace
from .engine import validate, price_of
from .schema import KINDS

FINANCIAL_RULES = {"R22", "D01"}


def assessment(kb, build):
    result = validate(kb, build)
    physical = [c for c in result.checks if c.rule not in FINANCIAL_RULES]
    # Checks involving unselected parts belong to the completion checklist.
    actionable = [c for c in physical if all(build.parts.get(s) for s in c.participants)]
    conflicts = [c for c in actionable if c.status == "fail"]
    unknown = [c for c in actionable if c.status == "unknown"]
    status = "fail" if conflicts else "unknown" if result.missing or unknown else "pass"
    return {"status": status, "conflicts": conflicts, "unknown": unknown,
            "passed": [c for c in actionable if c.status == "pass"],
            "missing": result.missing,
            "budget": [c for c in result.checks if c.rule in FINANCIAL_RULES]}


def replacement_impact(kb, build, slot, candidate_id, bios_revision):
    trial = replace(build, parts={**build.parts, slot: candidate_id}, bios_revision=bios_revision)
    before, after = assessment(kb, build), assessment(kb, trial)
    failed_after = {c.rule for c in after["conflicts"]}
    resolved = [c.title for c in before["conflicts"] if c.rule not in failed_after
                and any(p.rule == c.rule for p in after["passed"])]
    old_id = build.parts.get(slot)
    old = price_of(kb, build, old_id) if old_id else 0
    new = price_of(kb, trial, candidate_id)
    return {"resolved": resolved, "conflicts": len(after["conflicts"]),
            "unknown": len(after["unknown"]), "missing": len(after["missing"]),
            "delta": new - old if old is not None and new is not None else None}


def shopping_cost(kb, original, trial):
    """Only purchases count; no assumed resale value of owned parts."""
    changed = [id for slot, id in trial.parts.items() if id and original.parts.get(slot) != id]
    unknown = [kb.components[id].title for id in changed if price_of(kb, trial, id) is None]
    return sum(price_of(kb, trial, id) or 0 for id in changed), unknown


def checklist(kb, build):
    review = assessment(kb, build)
    lines = ["# Проверка сборки перед покупкой", "", "## Состав"]
    for slot, label in KINDS.items():
        id = build.parts.get(slot)
        lines.append(f"- {label}: {kb.components[id].title if id else 'Не выбран'}")
    for title, key in [("Конфликты", "conflicts"), ("Нужно уточнить", "unknown"), ("Бюджет", "budget")]:
        lines += ["", "## " + title]
        lines += [f"- {c.title}: {c.explanation}" for c in review[key]] or ["- Нет замечаний в этой группе."]
    if review["missing"]:
        lines += ["", "Не выбраны: " + ", ".join(KINDS[s] for s in review["missing"])]
    lines += ["", "Проверены только условия, представленные в каталоге. Неизвестные сведения не подтверждают совместимость."]
    return "\n".join(lines)
