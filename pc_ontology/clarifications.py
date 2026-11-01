"""Turn unknown validation results into a deduplicated, actionable checklist."""
from .engine import validate, price_of
from .schema import KINDS

FIELDS = {
    "R01": [("CPU", "hasSocket"), ("Motherboard", "hasSocket")],
    "R03": [("RAM", "hasMemoryStandard"), ("CPU", "supportsMemory")],
    "R04": [("RAM", "hasMemoryStandard"), ("Motherboard", "supportsMemory")],
    "R05": [("RAM", "hasMemoryForm"), ("Motherboard", "supportsMemoryForm")],
    "R06": [("RAM", "capacityGB"), ("CPU", "maxMemoryGB")],
    "R07": [("RAM", "capacityGB"), ("Motherboard", "maxMemoryGB")],
    "R08": [("RAM", "moduleCount"), ("Motherboard", "memorySlots")],
    "R09": [("Motherboard", "hasBoardForm"), ("Case", "supportsBoardForm")],
    "R10": [("GPU", "lengthMM"), ("Case", "maxGPULengthMM")],
    "R11": [("CPU", "hasSocket"), ("Cooler", "supportsSocket")],
    "R12": [("Cooler", "heightMM"), ("Case", "maxCoolerHeightMM")],
    "R13": [("CPU", "peakPowerW"), ("Cooler", "coolingCapacityW")],
    "R14": [("PSU", "hasPowerForm"), ("Case", "supportsPowerForm")],
    "R15": [("CPU", "peakPowerW"), ("GPU", "peakPowerW"), ("PSU", "ratedPowerW")],
    "R16": [("GPU", "requiredPCIe8"), ("PSU", "availablePCIe8")],
    "R17": [("GPU", "required12V2x6"), ("PSU", "available12V2x6")],
    "R18": [("Motherboard", "requiredEPS"), ("PSU", "availableEPS")],
    "R19": [("Storage", "hasStorageInterface"), ("Motherboard", "supportsStorage")],
    "R20": [("Storage", "lengthMM"), ("Motherboard", "maxM2LengthMM")],
    "R21": [("PSU", "availableSATA")],
    "R23": [("CPU", "hasIntegratedGraphics")], "R24": [("Motherboard", "hasDisplayOutput")],
    "R25": [("Storage", "lengthMM"), ("Motherboard", "supportedM2LengthsMM")],
    "R26": [("GPU", "thicknessMM"), ("Case", "maxGPUThicknessMM")],
    "R27": [("RAM", "heightMM"), ("Cooler", "ramClearanceMM")],
    "R28": [("GPU", "recommendedPSUW"), ("PSU", "ratedPowerW")],
    "R29": [("PSU", "lengthMM"), ("Case", "maxPSULengthMM")],
}
LABELS = {
    "hasSocket": "Сокет", "hasMemoryStandard": "Стандарт DDR", "supportsMemory": "Поддерживаемые стандарты памяти",
    "hasMemoryForm": "Форм-фактор памяти", "supportsMemoryForm": "Поддерживаемые форм-факторы памяти",
    "capacityGB": "Объём, ГБ", "maxMemoryGB": "Максимальный объём памяти, ГБ",
    "moduleCount": "Число модулей", "memorySlots": "Число слотов памяти",
    "hasBoardForm": "Форм-фактор платы", "supportsBoardForm": "Форм-факторы плат для корпуса",
    "lengthMM": "Длина, мм", "heightMM": "Высота, мм", "thicknessMM": "Толщина видеокарты, мм",
    "maxGPULengthMM": "Допустимая длина GPU, мм", "maxGPUThicknessMM": "Допустимая толщина GPU, мм",
    "supportsSocket": "Поддерживаемые крепления кулера", "maxCoolerHeightMM": "Допустимая высота кулера, мм",
    "peakPowerW": "Пиковое потребление, Вт", "coolingCapacityW": "Условная мощность охлаждения, Вт",
    "hasPowerForm": "Форм-фактор БП", "supportsPowerForm": "Форм-факторы БП для корпуса",
    "ratedPowerW": "Номинальная мощность БП, Вт", "recommendedPSUW": "Рекомендация GPU по БП, Вт",
    "requiredPCIe8": "Требуемые разъёмы PCIe 8-pin", "availablePCIe8": "Доступные разъёмы PCIe 8-pin",
    "required12V2x6": "Требуемые разъёмы 12V-2x6", "available12V2x6": "Доступные разъёмы 12V-2x6",
    "requiredEPS": "Требуемые разъёмы EPS", "availableEPS": "Доступные разъёмы EPS",
    "availableSATA": "Доступные разъёмы питания SATA", "hasStorageInterface": "Интерфейс накопителя",
    "supportsStorage": "Поддерживаемые интерфейсы накопителей", "maxM2LengthMM": "Максимальная длина M.2, мм",
    "supportedM2LengthsMM": "Точные номинальные длины крепления M.2", "hasIntegratedGraphics": "Наличие встроенной графики CPU",
    "hasDisplayOutput": "Наличие видеовыходов платы", "ramClearanceMM": "Зазор кулера над памятью, мм",
    "maxPSULengthMM": "Допустимая длина БП, мм", "supportedCPUIDs": "Поддержка выбранной модели CPU кулером",
    "bios_revision": "Установленная версия BIOS", "CPUBoardSupport": "Профиль поддержки CPU и платы",
    "price": "Цена пользователя",
}


def requests(kb, build):
    result = validate(kb, build)
    pending = {}

    def add(slot, field, rule, instruction, sources=()):
        id = build.parts.get(slot)
        key = (slot, field)
        if key not in pending:
            pending[key] = {"Категория": KINDS[slot], "Компонент": kb.components[id].title if id else "Не выбран",
                            "Сведения": LABELS.get(field, field), "Свойство": field, "Правила": [],
                            "Что сделать": instruction, "Источники": list(sources)}
        if rule not in pending[key]["Правила"]:
            pending[key]["Правила"].append(rule)

    def sources_for(id):
        return list(dict.fromkeys(s.sourceURL for s in kb.onto[id].hasSource if s.sourceURL))

    for slot in result.missing:
        add(slot, "selection", "Состав", "Выберите компонент во вкладке «Конфигуратор».")
    for check in result.checks:
        if check.status != "unknown" or any(not build.parts.get(slot) for slot in check.participants):
            continue
        if check.rule in {"R22", "D01"}:
            for slot, id in build.parts.items():
                if id and price_of(kb, build, id) is None:
                    add(slot, "price", check.rule, "Укажите свою цену в каталоге и нажмите «Сохранить цены». Цена производителя здесь не предполагается.")
            continue
        if check.rule == "R02":
            cpu, board = build.parts.get("CPU"), build.parts.get("Motherboard")
            profile = kb.support_info.get((board, cpu))
            if not profile or (not profile.get("minBiosLabel") and (board, cpu) not in kb.support):
                add("Motherboard", "CPUBoardSupport", check.rule,
                    "Найдите точную модель CPU в официальной таблице поддержки этой платы. Совпадение сокета само по себе недостаточно.", sources_for(board))
            else:
                add("Motherboard", "bios_revision", check.rule,
                    "Проверьте установленную версию в настройках BIOS/UEFI. Для реальных строковых версий нужен подтверждённый минимум или порядок версий; порядок по названию не угадывается.", sources_for(board))
            continue
        cooler_id = build.parts.get("Cooler")
        if check.rule == "R13" and cooler_id and kb.components[cooler_id].get("catalogKind") == "manufacturer":
            add("Cooler", "supportedCPUIDs", check.rule,
                "Уточните поддержку конкретного CPU и наличие нужного монтажного комплекта. Отсутствие пары в базе не является доказательством несовместимости.", sources_for(cooler_id))
            continue
        found = False
        for slot, field in FIELDS.get(check.rule, []):
            id = build.parts.get(slot)
            if not id:
                continue
            value = kb.components[id].get(field)
            if value is None or value == []:
                note = "Найдите точное значение и условия для своей модели/ревизии в документации производителя; не переносите его с похожей модели."
                if field == "peakPowerW":
                    note = "Уточните максимальное потребление для выбранного режима работы. TDP и паспортное среднее потребление не подменяются измеренным пиком."
                elif field == "maxGPUThicknessMM":
                    note = "Уточните допустимую толщину GPU при выбранных вентиляторах, радиаторах и кронштейнах корпуса. Допустимая длина не доказывает допустимую толщину."
                elif field in {"heightMM", "ramClearanceMM"}:
                    note = "Сопоставьте размеры с учётом допусков, положения вентилятора и перекрытия DIMM. Не округляйте габарит вниз для подтверждения зазора."
                add(slot, field, check.rule, note, sources_for(id))
                found = True
        if not found and check.rule not in FIELDS:
            slot = check.participants[0] if check.participants else "CPU"
            add(slot, check.rule, check.rule, check.explanation)
    return list(pending.values())


def checklist_markdown(items):
    lines = ["# Что уточнить для проверки сборки", "", "Неизвестные сведения не считаются ни подтверждением, ни конфликтом.", ""]
    for item in items:
        lines += [f"- [ ] {item['Компонент']} — {item['Сведения']} ({', '.join(item['Правила'])})", f"  {item['Что сделать']}"]
        lines.extend(f"  Источник для проверки: {url}" for url in item["Источники"])
        lines.append("")
    if not items:
        lines.append("Нет неизвестных проверок. Подтверждённые конфликты, если они есть, исправляются отдельно.")
    return "\n".join(lines)
