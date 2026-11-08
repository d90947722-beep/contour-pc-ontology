"""Bounded branch-and-bound search over exactly the same validation rules as the UI.

Returned feasible solutions are always revalidated in full. A search cap is
reported explicitly; a partial search never claims global optimality.
"""
from dataclasses import dataclass, field, replace
from time import monotonic
from .engine import Build, validate, price_of

ORDER = ("CPU", "Motherboard", "RAM", "Cooler", "GPU", "PSU", "Case", "Storage")


@dataclass
class Plan:
    build: Build
    status: str
    total: int
    replacements: list
    resolved: list
    unknown: list
    score: tuple


@dataclass
class SearchResult:
    plans: list = field(default_factory=list)
    visited: int = 0
    complete: bool = True
    messages: list = field(default_factory=list)
    elapsed: float = 0


def search(kb, original=None, *, catalog="synthetic", repair=False, objective="cost",
           allow_unknown=False, limit=3, max_nodes=50000, timeout=12, locked=(),
           must_change=(), replacement_budget=None):
    if objective not in {"cost", "purchases", "changes", "cores", "memory"}:
        raise ValueError("Неизвестная цель поиска.")
    original = original or Build()
    validate(kb, original)
    if set(locked) - set(ORDER):
        raise ValueError("Неизвестная фиксируемая категория.")
    if set(must_change) - set(ORDER) or set(must_change) & set(locked):
        raise ValueError("Категории для замены должны быть известны и не зафиксированы.")
    if replacement_budget is not None and (type(replacement_budget) is not int or replacement_budget < 0):
        raise ValueError("Бюджет покупок должен быть целым неотрицательным числом.")
    if original.graphics_mode == "integrated" and "GPU" in must_change:
        raise ValueError("Для замены видеокарты выберите дискретную графику.")
    started = monotonic()
    report = SearchResult()
    slots = [s for s in ORDER if not (s == "GPU" and original.graphics_mode == "integrated")]
    domains = {}
    for slot in slots:
        all_items = kb.by_kind(slot)
        items = [c for c in all_items if c.get("catalogKind") == catalog]
        if slot in locked:
            items = [c for c in items if original.parts.get(slot) == c.id]
        if slot in must_change:
            items = [c for c in items if original.parts.get(slot) != c.id]
        if replacement_budget is not None or objective == "purchases":
            items = [c for c in items if c.id == original.parts.get(slot) or price_of(kb, original, c.id) is not None]
        # A numeric budget/cost objective cannot be evaluated without supplied prices.
        if original.budget is not None or objective == "cost":
            items = [c for c in items if price_of(kb, original, c.id) is not None]
        items.sort(key=lambda c: (repair and c.id != original.parts.get(slot),
                                  price_of(kb, original, c.id) is None,
                                  price_of(kb, original, c.id) or 0, c.id))
        domains[slot] = items
    empty = [s for s in slots if not domains[s]]
    if empty:
        report.messages.append("Нет допустимых кандидатов (проверьте цены и фиксацию): " + ", ".join(empty))
        return report
    original_result = validate(kb, original)
    baseline_failed = {c.rule for c in original_result.checks if c.status == "fail"}
    best = []

    def objective_score(trial, result):
        changes = sum(original.parts.get(s) != trial.parts.get(s) for s in slots)
        cores = kb.components[trial.parts["CPU"]].get("coreCount") or 0
        memory = kb.components[trial.parts["RAM"]].get("capacityGB") or 0
        numeric_cost = result.total if not result.unknown_prices else float("inf")
        purchases = sum(price_of(kb, trial, id) for slot, id in trial.parts.items()
                        if original.parts.get(slot) != id) if objective == "purchases" else 0
        # Unknown solutions never outrank confirmed solutions for a claimed optimum.
        quality = 0 if result.status == "pass" else 1
        if objective == "changes":
            return quality, changes, numeric_cost
        if objective == "purchases":
            return quality, purchases, changes
        if objective == "cores":
            return quality, -cores, numeric_cost, changes
        if objective == "memory":
            return quality, -memory, numeric_cost, changes
        return quality, numeric_cost, changes

    def walk(index, chosen, current_cost, changed, bios):
        if report.visited >= max_nodes or monotonic() - started >= timeout:
            report.complete = False
            return
        report.visited += 1
        trial = replace(original, parts=chosen.copy(), bios_revision=bios)
        partial = validate(kb, trial)
        if replacement_budget is not None or objective == "purchases":
            purchases = sum(price_of(kb, original, id) for slot, id in chosen.items()
                            if original.parts.get(slot) != id)
            if replacement_budget is not None and purchases > replacement_budget:
                return
        if any(c.status == "fail" for c in partial.checks):
            return
        # An unknown test with all its participants selected cannot be repaired by
        # adding unrelated slots. Missing-part unknowns remain eligible for search.
        if not allow_unknown and any(c.status == "unknown" and c.participants
                and all(s in chosen for s in c.participants) for c in partial.checks):
            return
        if original.budget is not None:
            lower_cost = current_cost + sum(min(price_of(kb, original, c.id) for c in domains[s]) for s in slots[index:])
            if lower_cost > original.budget:
                return
        if len(best) == limit and best[-1].status == "pass":
            if objective == "changes" and changed > best[-1].score[1]:
                return
            if objective == "cost":
                lower_cost = current_cost + sum(min(price_of(kb, original, c.id) for c in domains[s]) for s in slots[index:])
                if lower_cost > best[-1].total:
                    return
            if objective == "purchases":
                lower_purchases = purchases + sum(min(0 if c.id == original.parts.get(s)
                    else price_of(kb, original, c.id) for c in domains[s]) for s in slots[index:])
                if lower_purchases > best[-1].score[1]:
                    return
        if index == len(slots):
            if partial.status == "fail" or (partial.status != "pass" and not allow_unknown):
                return
            replacements = [{"slot": s, "old": original.parts.get(s), "new": chosen.get(s)}
                            for s in slots if original.parts.get(s) != chosen.get(s)]
            final_failed = {c.rule for c in partial.checks if c.status == "fail"}
            plan = Plan(trial, partial.status, partial.total, replacements,
                        sorted(baseline_failed - final_failed),
                        [c.title for c in partial.checks if c.status == "unknown"], objective_score(trial, partial))
            best.append(plan)
            best.sort(key=lambda p: (p.score, tuple(p.build.parts.get(s, "") for s in slots)))
            del best[limit:]
            return
        slot = slots[index]
        for component in domains[slot]:
            chosen[slot] = component.id
            new_bios = bios
            if slot == "Motherboard" and component.id != original.parts.get(slot):
                new_bios = component.get("biosRevision")  # Unknown for physical real boards.
            cost = price_of(kb, original, component.id) or 0
            walk(index + 1, chosen, current_cost + cost,
                 changed + (component.id != original.parts.get(slot)), new_bios)
            chosen.pop(slot)
            if not report.complete:
                return

    walk(0, {}, 0, 0, original.bios_revision)
    report.plans, report.elapsed = best, round(monotonic() - started, 3)
    if not report.complete:
        report.messages.append("Достигнут предел времени/числа узлов. Это найденные варианты; глобальный оптимум не доказан.")
    if not best:
        report.messages.append("В проверенной области поиска сборки не найдены. Уточните данные, бюджет или фиксированные компоненты.")
    return report
