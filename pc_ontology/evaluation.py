"""Reproducible scenario evaluation; not a real-world compatibility accuracy study."""
from dataclasses import replace
from pathlib import Path
import csv
import json
from .knowledge import KnowledgeBase
from .engine import Build, DEMOS, validate, STATUS_LABELS, export_build, REAL_DEMO
from .planner import search
from .rdf_build import export_rdf
from .schema import ROOT


def scenarios():
    good = DEMOS["Совместимая сборка"]
    rows = [("S01", "Полная корректная учебная сборка", good, "pass"),
            ("S02", "Набор конфликтов", DEMOS["Сборка с конфликтами"], "fail"),
            ("S03", "Неполные сведения", DEMOS["Недостаточно данных"], "unknown"),
            ("S04", "Пустая сборка", Build(), "unknown")]
    for id, title, slot, value, expected in [
        ("S05", "Неверный стандарт DDR", "RAM", "ram_d4_32", "fail"),
        ("S06", "Неверный форм-фактор DIMM", "RAM", "ram_so", "fail"),
        ("S07", "Корпус слишком мал", "Case", "case_mini", "fail"),
        ("S08", "Кулер для другого сокета", "Cooler", "cooler_a4", "fail"),
        ("S09", "Недостаточная мощность БП", "PSU", "psu_400", "fail"),
        ("S10", "Слишком длинный M.2", "Storage", "ssd_long", "fail"),
        ("S11", "Отсутствует GPU", "GPU", None, "unknown"),
        ("S12", "Неизвестны характеристики GPU", "GPU", "gpu_unknown", "unknown"),
    ]:
        rows.append((id, title, replace(good, parts={**good.parts, slot: value}), expected))
    rows += [("S13", "Точная граница бюджета", replace(good, budget=91000), "pass"),
             ("S14", "Бюджет на рубль меньше", replace(good, budget=90999), "fail"),
             ("S15", "Неизвестный BIOS", replace(good, bios_revision=None), "unknown"),
             ("S16", "Старый BIOS для CPU", replace(good, parts={**good.parts, "CPU": "cpu_a5_8"}, bios_revision=100), "fail")]
    real = Build(dict(CPU="real_cpu_7600", Motherboard="real_mb_b650_plus", RAM="real_ram_d5_32",
                      GPU="real_gpu_4060", PSU="real_psu_650", Case="real_case_pop",
                      Storage="real_ssd_980_1", Cooler="real_cooler_redux"), "0602")
    rows += [("R01", "Реальная сборка с неизвестным пиком мощности и толщиной", real, "unknown"),
             ("R02", "Реальная сборка с неверной DDR", replace(real, parts={**real.parts, "RAM": "real_ram_d4_16"}), "fail"),
             ("R03", "Реальная сборка с неизвестным BIOS", replace(real, bios_revision=None), "unknown"),
             ("R04", "Без GPU на CPU без встроенной графики", replace(real,
                 parts={**real.parts, "CPU": "real_cpu_5600", "GPU": None}, graphics_mode="integrated"), "fail")]
    return rows


def run(output=None):
    output = Path(output or ROOT / "docs" / "evaluation")
    output.mkdir(parents=True, exist_ok=True)
    kb = KnowledgeBase()
    try:
        rows = []
        for id, title, build, expected in scenarios():
            result = validate(kb, build)
            cpu = kb.components.get(build.parts.get("CPU"))
            board = kb.components.get(build.parts.get("Motherboard"))
            baseline = ("pass" if cpu.get("hasSocket") == board.get("hasSocket") else "fail") if cpu and board else "unknown"
            rows.append(dict(id=id, scenario=title, expected=expected, actual=result.status,
                             correct=result.status == expected, conflicts=result.count("fail"),
                             unknown=result.count("unknown"), passed=result.count("pass"),
                             socket_only_baseline=baseline, baseline_correct=baseline == expected))
        repair_start = replace(DEMOS["Совместимая сборка"], parts={**DEMOS["Совместимая сборка"].parts,
                                                              "RAM": "ram_d4_32", "PSU": "psu_400"})
        repair = search(kb, repair_start, repair=True, objective="changes", limit=1,
                        locked=[s for s in repair_start.parts if s not in {"RAM", "PSU"}])
        automatic = search(kb, Build(budget=80000), limit=1)
        matrix = {expected: {actual: 0 for actual in STATUS_LABELS} for expected in STATUS_LABELS}
        for row in rows:
            matrix[row["expected"]][row["actual"]] += 1
        report = dict(total=len(rows), correct=sum(r["correct"] for r in rows), confusion_matrix=matrix,
                      socket_only_baseline_correct=sum(r["baseline_correct"] for r in rows),
                      scope="Сконструированные сценарии, не независимая выборка реального рынка.",
                      automatic=dict(found=bool(automatic.plans), complete=automatic.complete, visited=automatic.visited, elapsed=automatic.elapsed,
                                     total=automatic.plans[0].total if automatic.plans else None),
                      repair=dict(found=bool(repair.plans), complete=repair.complete, visited=repair.visited, elapsed=repair.elapsed,
                                  changes=len(repair.plans[0].replacements) if repair.plans else None),
                      ontology=kb.stats(), scenarios=rows)
        (output / "results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        with (output / "scenarios.csv").open("w", encoding="utf-8-sig", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        example_dir = ROOT / "examples"
        for i, (_, build) in enumerate(DEMOS.items()):
            (example_dir / f"0{i+1}-build.owl").write_bytes(export_rdf(kb, build))
            (example_dir / f"0{i+1}-demo.json").write_text(json.dumps(export_build(kb, build), ensure_ascii=False, indent=2), encoding="utf-8")
        (example_dir / "04-real-build.owl").write_bytes(export_rdf(kb, REAL_DEMO))
        (example_dir / "04-real-demo.json").write_text(json.dumps(export_build(kb, REAL_DEMO), ensure_ascii=False, indent=2), encoding="utf-8")
        return report
    finally:
        kb.close()


if __name__ == "__main__":
    report = run()
    print(json.dumps({k: v for k, v in report.items() if k != "scenarios"}, ensure_ascii=True, indent=2))
