"""Explainable, three-valued validation over facts read from the OWL graph.

OWL's open-world semantics are retained for missing facts. Numerical constraints
and negative validation are implemented here, not misrepresented as OWL inference.
"""
from dataclasses import dataclass, field, asdict, replace
from math import ceil
from .schema import KINDS

SLOTS = tuple(KINDS)
STATUS_LABELS = {"pass": "Подтверждено", "fail": "Конфликт", "unknown": "Недостаточно данных"}
OVERHEAD_W = 60
POWER_MARGIN = 1.25


@dataclass
class Build:
    parts: dict = field(default_factory=dict)
    bios_revision: int | str | None = None
    budget: int | None = None
    price_overrides: dict = field(default_factory=dict)
    graphics_mode: str = "discrete"

    def __post_init__(self):
        if self.bios_revision is not None and not ((type(self.bios_revision) is int and self.bios_revision >= 0)
                or (isinstance(self.bios_revision, str) and 0 < len(self.bios_revision) <= 40)):
            raise ValueError("Некорректная ревизия BIOS.")
        if self.budget is not None and (type(self.budget) is not int or self.budget < 0):
            raise ValueError("Бюджет должен быть целым неотрицательным числом.")
        if set(self.parts) - set(SLOTS):
            raise ValueError("Неизвестные категории компонентов.")
        if not isinstance(self.price_overrides, dict) or any(not isinstance(k, str) or type(v) is not int or v < 0 for k, v in self.price_overrides.items()):
            raise ValueError("Цены должны быть целыми неотрицательными числами.")
        if self.graphics_mode not in ("discrete", "integrated"):
            raise ValueError("Неизвестный режим графики.")
        if self.graphics_mode == "integrated" and self.parts.get("GPU"):
            raise ValueError("В режиме встроенной графики уберите дискретную GPU из выбранного состава.")


def price_of(kb, build, id):
    return build.price_overrides.get(id, kb.components[id].get("price"))


@dataclass(frozen=True)
class Check:
    rule: str
    title: str
    status: str
    explanation: str
    participants: tuple
    evidence: tuple = ()


@dataclass
class Result:
    checks: list
    total: int
    estimated_power: int | None
    missing: list
    unknown_prices: list

    @property
    def status(self):
        if any(c.status == "fail" for c in self.checks):
            return "fail"
        if self.missing or any(c.status == "unknown" for c in self.checks):
            return "unknown"
        return "pass"

    def count(self, status):
        return sum(c.status == status for c in self.checks)


def validate(kb, build):
    parts = {}
    for kind, id in build.parts.items():
        if id is None:
            continue
        if id not in kb.components or kb.components[id].kind != kind:
            raise ValueError(f"Некорректный компонент для категории {kind}: {id}")
        parts[kind] = kb.components[id]
    checks = []

    def emit(rule, title, slots, values, predicate, success, failure):
        # An omitted component or fact never proves compatibility.
        missing_parts = [KINDS[s] for s in slots if s not in parts]
        evidence = tuple(f"{label}: {value if value is not None and value != [] else 'нет данных'}"
                         for label, value in values)
        unknown = missing_parts or any(v is None or v == [] for _, v in values)
        status = "unknown" if unknown else ("pass" if predicate() else "fail")
        message = ("Не выбраны: " + ", ".join(missing_parts) + "." if missing_parts
                   else "В онтологии отсутствуют сведения для этой проверки.") if unknown else (success if status == "pass" else failure)
        checks.append(Check(rule, title, status, message, slots, evidence))

    def fact(slot, name):
        return parts[slot].get(name) if slot in parts else None

    def compare(rule, title, slots, left_prop, right_prop, op, success, failure):
        a, b = fact(slots[0], left_prop), fact(slots[1], right_prop)
        emit(rule, title, slots, [(left_prop, a), (right_prop, b)], lambda: op(a, b), success, failure)

    compare("R01", "Сокет процессора и платы", ("CPU", "Motherboard"), "hasSocket", "hasSocket",
            lambda a, b: a == b, "Сокеты совпадают.", "Процессор и плата используют разные сокеты.")

    cpu, board = parts.get("CPU"), parts.get("Motherboard")
    support_key = (board.id, cpu.id) if cpu and board else None
    min_bios = kb.support.get(support_key)
    support_info = getattr(kb, "support_info", {}).get(support_key, {})
    support_status = support_info.get("status")
    real_min = support_info.get("minBiosLabel")
    bios_ok = None
    if real_min == "all":
        bios_ok = True
    elif real_min and build.bios_revision is not None:
        # Only equality or an explicitly documented sequence proves real firmware order.
        actual = str(build.bios_revision)
        sequence = support_info.get("biosSequence", [])
        if actual == real_min:
            bios_ok = True
        elif actual in sequence and real_min in sequence:
            bios_ok = sequence.index(actual) >= sequence.index(real_min)
    if support_status == "unsupported":
        checks.append(Check("R02", "Поддержка модели и версия BIOS", "fail", "В базе есть явное отрицательное свидетельство поддержки этой пары CPU/платы.", ("CPU", "Motherboard")))
    elif real_min:
        emit("R02", "Поддержка модели и версия BIOS", ("CPU", "Motherboard"),
             [("Минимальный BIOS", real_min), ("Проверенный порядок / совпадение версии", bios_ok)],
             lambda: bios_ok, "Поддержка CPU и условия BIOS подтверждены официальной таблицей.", "Установленная версия BIOS предшествует минимальной по проверенной последовательности.")
    else:
        if not isinstance(build.bios_revision, int):
            revision = None
        else:
            revision = build.bios_revision
        emit("R02", "Поддержка модели и версия BIOS", ("CPU", "Motherboard"),
             [("Минимальная ревизия BIOS из профиля поддержки", min_bios), ("Установленная ревизия BIOS", revision)],
             lambda: revision >= min_bios,
             "В онтологии есть профиль поддержки процессора; ревизия BIOS достаточна.",
             "Процессор поддерживается только с более новой ревизией BIOS. Требуется обновление.")
    for slot, rule in [("CPU", "R03"), ("Motherboard", "R04")]:
        compare(rule, "Стандарт памяти: " + KINDS[slot].lower(), ("RAM", slot),
                "hasMemoryStandard", "supportsMemory", lambda a, b: a in b,
                "Стандарт выбранной памяти поддерживается.", "Стандарт DDR выбранной памяти не поддерживается.")
    compare("R05", "Форм-фактор модулей памяти", ("RAM", "Motherboard"), "hasMemoryForm", "supportsMemoryForm",
            lambda a, b: a in b, "Форм-фактор модулей подходит.", "Форм-фактор модулей не подходит к слотам платы.")
    for slot, rule in [("CPU", "R06"), ("Motherboard", "R07")]:
        compare(rule, "Объём памяти: " + KINDS[slot].lower(), ("RAM", slot), "capacityGB", "maxMemoryGB",
                lambda a, b: a <= b, "Объём комплекта находится в пределах ограничения.", "Объём комплекта превышает поддерживаемый объём памяти.")
    compare("R08", "Количество модулей и слотов", ("RAM", "Motherboard"), "moduleCount", "memorySlots",
            lambda a, b: a <= b, "Для модулей достаточно слотов.", "Модулей памяти больше, чем слотов на плате.")
    compare("R09", "Плата и корпус", ("Motherboard", "Case"), "hasBoardForm", "supportsBoardForm",
            lambda a, b: a in b, "Корпус поддерживает форм-фактор платы.", "Корпус не поддерживает форм-фактор платы.")
    compare("R10", "Длина видеокарты", ("GPU", "Case"), "lengthMM", "maxGPULengthMM",
            lambda a, b: a <= b, "Видеокарта помещается по длине.", "Видеокарта длиннее допустимого размера корпуса.")
    compare("R11", "Крепление кулера", ("CPU", "Cooler"), "hasSocket", "supportsSocket",
            lambda a, b: a in b, "Кулер имеет крепление для сокета процессора.", "Кулер не поддерживает сокет процессора.")
    compare("R12", "Высота кулера", ("Cooler", "Case"), "heightMM", "maxCoolerHeightMM",
            lambda a, b: a <= b, "Кулер помещается по высоте.", "Высота кулера превышает ограничение корпуса.")
    cooler = parts.get("Cooler")
    if cooler and cooler.get("catalogKind") == "manufacturer":
        supported = cooler.get("supportedCPUIDs") or []
        confirmed = True if cpu and cpu.id in supported else None
        emit("R13", "Поддержка CPU производителем кулера", ("CPU", "Cooler"), [("supportedCPUIDs", confirmed)],
             lambda: True, "Производитель кулера явно подтверждает пригодность для этой модели CPU при указанных условиях крепления.", "")
    else:
        compare("R13", "Условная мощность охлаждения", ("CPU", "Cooler"), "peakPowerW", "coolingCapacityW",
                lambda a, b: a <= b, "Учебный порог мощности охлаждения соблюдён.",
                "Учебный порог мощности охлаждения ниже принятой пиковой мощности процессора.")
    compare("R14", "Форм-фактор блока питания", ("PSU", "Case"), "hasPowerForm", "supportsPowerForm",
            lambda a, b: a in b, "Корпус поддерживает форм-фактор блока питания.", "Блок питания не подходит по форм-фактору.")

    cpu_w, gpu_w = fact("CPU", "peakPowerW"), fact("GPU", "peakPowerW")
    if build.graphics_mode == "integrated" and "GPU" not in parts:
        gpu_w = 0
    power = ceil((cpu_w + gpu_w + OVERHEAD_W) * POWER_MARGIN) if cpu_w is not None and gpu_w is not None else None
    rated = fact("PSU", "ratedPowerW")
    emit("R15", "Расчёт мощности блока питания", ("CPU", "GPU", "PSU"),
         [("Расчёт с запасом, Вт", power), ("Номинал БП, Вт", rated)], lambda: rated >= power,
         "Мощности достаточно по учебной формуле: (пик CPU + пик GPU + 60 Вт) × 1,25 с округлением вверх.",
         "Мощности недостаточно по учебной формуле с запасом 25 %.")
    for rule, title, req, avail in [
        ("R16", "Разъёмы питания GPU: PCIe 8-pin", "requiredPCIe8", "availablePCIe8"),
        ("R17", "Разъёмы питания GPU: 12V-2x6", "required12V2x6", "available12V2x6"),
    ]:
        if fact("GPU", req) == 0 and "PSU" in parts:
            emit(rule, title, ("GPU", "PSU"), [(req, 0)], lambda: True, "Видеокарта не требует разъёмов этого типа.", "")
        else:
            compare(rule, title, ("GPU", "PSU"), req, avail, lambda a, b: a <= b,
                    "Прямых разъёмов нужного типа достаточно.", "Недостаточно прямых разъёмов нужного типа. Переходники модель не учитывает.")
    compare("R18", "Разъёмы питания платы: EPS", ("Motherboard", "PSU"), "requiredEPS", "availableEPS",
            lambda a, b: a <= b, "Разъёмов EPS достаточно.", "Недостаточно разъёмов EPS для платы.")
    compare("R19", "Интерфейс накопителя", ("Storage", "Motherboard"), "hasStorageInterface", "supportsStorage",
            lambda a, b: a in b, "Плата поддерживает интерфейс накопителя.", "Плата не поддерживает интерфейс накопителя.")
    interface = fact("Storage", "hasStorageInterface")
    if interface == "NVMe":
        compare("R20", "Длина M.2-накопителя", ("Storage", "Motherboard"), "lengthMM", "maxM2LengthMM",
                lambda a, b: a <= b, "Длина M.2 поддерживается платой в учебной модели.", "M.2-накопитель длиннее допустимого в учебной модели.")
    if interface == "SATA":
        sata = fact("PSU", "availableSATA")
        emit("R21", "Питание SATA-накопителя", ("Storage", "PSU"), [("Разъёмы SATA БП", sata)],
             lambda: sata >= 1, "Есть разъём питания SATA.", "Нет свободного разъёма питания SATA.")
    if build.graphics_mode == "integrated" and "GPU" not in parts:
        checks = [c for c in checks if c.rule not in {"R10", "R16", "R17"}]
        # Power calculation does not require a discrete GPU in this mode.
        checks = [replace(c, participants=("CPU", "PSU"), status="unknown" if power is None or rated is None else "pass" if rated >= power else "fail",
                          explanation="Расчёт без дискретной GPU: (пик CPU + 60 Вт) × 1,25." if power is not None and rated is not None else "Недостаточно данных о мощности CPU или БП.") if c.rule == "R15" else c for c in checks]
        for rule, slot, prop in [("R23", "CPU", "hasIntegratedGraphics"), ("R24", "Motherboard", "hasDisplayOutput")]:
            value = fact(slot, prop)
            emit(rule, "Встроенная графика" if slot == "CPU" else "Видеовыходы платы", (slot,), [(prop, value)],
                 lambda value=value: value is True, "Необходимая возможность подтверждена.", "Для работы без дискретной GPU необходима встроенная графика CPU и видеовыход платы.")
    real_build = any(c.get("catalogKind") == "manufacturer" for c in parts.values())
    lengths = fact("Motherboard", "supportedM2LengthsMM")
    if interface == "NVMe" and (lengths or real_build):
        actual_length = fact("Storage", "lengthMM")
        emit("R25", "Точное крепление M.2", ("Storage", "Motherboard"), [("Длина накопителя", actual_length), ("Поддерживаемые длины M.2", lengths)],
             lambda: actual_length in lengths, "Для длины накопителя указан поддерживаемый размер M.2.", "Для выбранной длины M.2 нет подходящего крепления в списке платы.")
    for rule, title, slots, left_prop, right_prop in [
        ("R26", "Толщина видеокарты", ("GPU", "Case"), "thicknessMM", "maxGPUThicknessMM"),
        ("R27", "Зазор кулера над памятью", ("RAM", "Cooler"), "heightMM", "ramClearanceMM"),
    ]:
        if rule == "R27" and fact("Cooler", "unlimitedRAMClearance") is True:
            emit(rule, title, ("RAM", "Cooler"), [("unlimitedRAMClearance", True)], lambda: True,
                 "Производитель заявляет отсутствие ограничения высоты памяти для указанной конфигурации кулера.", "")
            continue
        if (rule != "R26" or "GPU" in parts) and (real_build or fact(slots[0], left_prop) is not None or fact(slots[1], right_prop) is not None):
            compare(rule, title, slots, left_prop, right_prop, lambda a, b: a <= b,
                    "Габаритное ограничение соблюдено.", "Габаритное ограничение превышено.")
    if real_build:
        if "GPU" in parts:
            compare("R28", "Рекомендация производителя GPU по БП", ("GPU", "PSU"), "recommendedPSUW", "ratedPowerW",
                    lambda a, b: a <= b, "Номинал БП не ниже рекомендованного производителем GPU.",
                    "БП ниже рекомендации производителя GPU для его эталонной системы. Это отдельное ограничение прототипа, а не расчёт фактического потребления.")
        compare("R29", "Длина блока питания", ("PSU", "Case"), "lengthMM", "maxPSULengthMM", lambda a, b: a <= b,
                "Длина блока питания укладывается в ограничение корпуса при указанных условиях.", "Блок питания длиннее допустимого для выбранной конфигурации корпуса.")
    unknown_prices = [c.title for c in parts.values() if price_of(kb, build, c.id) is None]
    total = sum(price_of(kb, build, c.id) or 0 for c in parts.values())
    if build.budget is not None:
        emit("R22", "Учебный бюджет", tuple(parts), [("Сумма выбранных компонентов", None if unknown_prices else total),
             ("Бюджет", build.budget)], lambda: total <= build.budget,
             "Выбранные компоненты укладываются в бюджет; стоимость отсутствующих деталей не учтена.",
             "Сумма выбранных компонентов превышает бюджет.")
    if unknown_prices and build.budget is not None:
        checks.append(Check("D01", "Полнота цен", "unknown", "Нет цены: " + ", ".join(unknown_prices), tuple(parts)))
    return Result(checks, total, power, [s for s in SLOTS if s not in parts and not (s == "GPU" and build.graphics_mode == "integrated")], unknown_prices)


def recommend(kb, build, slot):
    """Evaluate only constraints affected by the replaced slot; keep other conflicts visible separately."""
    if slot not in SLOTS:
        raise ValueError("Неизвестная категория.")
    rows = []
    for candidate in kb.by_kind(slot):
        revision = candidate.get("biosRevision") if slot == "Motherboard" else build.bios_revision
        trial = replace(build, parts={**build.parts, slot: candidate.id}, bios_revision=revision)
        result = validate(kb, trial)
        relevant = [c for c in result.checks if slot in c.participants]
        failures = [c for c in relevant if c.status == "fail"]
        unknown = [c for c in relevant if c.status == "unknown"]
        status = "fail" if failures else ("unknown" if unknown else "pass")
        rows.append({"component": candidate, "status": status, "checks": relevant,
                     "reasons": failures or unknown, "total": result.total, "bios_revision": revision})
    return sorted(rows, key=lambda r: ({"pass": 0, "unknown": 1, "fail": 2}[r["status"]],
                                       r["component"].get("price") or 0))


def export_build(kb, build):
    result = validate(kb, build)
    return {"format": "pc-ontology-build", "version": 2,
            "notice": "Статус относится только к правилам прототипа. Цены пользователя не являются рыночной котировкой.",
            "parts": build.parts, "bios_revision": build.bios_revision, "budget": build.budget,
            "price_overrides": build.price_overrides, "graphics_mode": build.graphics_mode,
            "names": {s: kb.components[id].title for s, id in build.parts.items() if id},
            "result": {"status": result.status, "total": result.total,
                       "estimated_power": result.estimated_power, "missing": result.missing,
                       "checks": [asdict(c) for c in result.checks]}}


def import_build(kb, data):
    if not isinstance(data, dict) or data.get("format") != "pc-ontology-build" or data.get("version") not in (1, 2):
        raise ValueError("Ожидается файл сборки pc-ontology-build версии 1 или 2.")
    parts = data.get("parts")
    if not isinstance(parts, dict) or any(not isinstance(v, (str, type(None))) for v in parts.values()):
        raise ValueError("Некорректный список компонентов.")
    if data["version"] == 1 and data.get("bios_revision") is not None and type(data["bios_revision"]) is not int:
        raise ValueError("Формат версии 1 требует целочисленную ревизию BIOS.")
    build = Build(parts, data.get("bios_revision"), data.get("budget"), data.get("price_overrides", {}), data.get("graphics_mode", "discrete"))
    validate(kb, build)  # Never trust the saved result: recompute from this knowledge base.
    return build


DEMOS = {
    "Совместимая сборка": Build(dict(CPU="cpu_a5_6", Motherboard="mb_a5", RAM="ram_d5_32", GPU="gpu_mid",
                                  PSU="psu_550", Case="case_tower", Storage="ssd_nvme_1", Cooler="cooler_tower"), 200, 110000),
    "Сборка с конфликтами": Build(dict(CPU="cpu_a5_8", Motherboard="mb_a4_m", RAM="ram_d5_128", GPU="gpu_max",
                                      PSU="psu_400", Case="case_mini", Storage="ssd_long", Cooler="cooler_a4"), 100, 100000),
    "Недостаточно данных": Build(dict(CPU="cpu_a5_6", Motherboard="mb_unknown", RAM="ram_d5_32", GPU="gpu_unknown",
                                     PSU="psu_550", Case="case_tower", Storage="ssd_nvme_1", Cooler="cooler_tower"), None, 110000),
}

REAL_DEMO = Build(dict(CPU="real_cpu_7600", Motherboard="real_mb_b650_plus", RAM="real_ram_d5_32",
                       GPU="real_gpu_4060", PSU="real_psu_650", Case="real_case_pop",
                       Storage="real_ssd_980_1", Cooler="real_cooler_redux"))
