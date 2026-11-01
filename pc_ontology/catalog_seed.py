"""Synthetic fixtures. These are NOT specifications of commercial products."""

META = {
    "kind": "synthetic",
    "description": "Учебные модели. Все характеристики, цены и сведения о BIOS вымышлены.",
    "currency": "RUB",
}

# Relations refer to named OWL individuals, not free-text values.
VOCAB = {
    "Socket": {"AM4": "AM4", "AM5": "AM5", "LGA1700": "LGA1700"},
    "MemoryStandard": {"DDR4": "DDR4", "DDR5": "DDR5"},
    "BoardFormFactor": {"ATX": "ATX", "mATX": "Micro-ATX", "ITX": "Mini-ITX"},
    "PowerFormFactor": {"PSU_ATX": "ATX", "SFX": "SFX"},
    "StorageInterface": {"NVMe": "M.2 NVMe / PCIe", "SATA": "SATA"},
    "MemoryFormFactor": {"UDIMM": "UDIMM", "SODIMM": "SO-DIMM"},
}


def seed():
    items = []

    def add(id, kind, title, price, **facts):
        items.append(dict(id=id, kind=kind, title=title, price=price, **facts))

    # Power is an assumed peak draw for the demo, NOT TDP.
    for id, title, socket, mem, price, power, cap in [
        ("cpu_a4_6", "Atlas A4 · 6 ядер", "AM4", ["DDR4"], 11000, 90, 128),
        ("cpu_a4_8", "Atlas A4 · 8 ядер", "AM4", ["DDR4"], 17000, 140, 128),
        ("cpu_a5_6", "Atlas A5 · 6 ядер", "AM5", ["DDR5"], 19000, 100, 192),
        ("cpu_a5_8", "Atlas A5 · 8 ядер", "AM5", ["DDR5"], 28000, 160, 192),
        ("cpu_i5", "Vector I · 6 ядер", "LGA1700", ["DDR4", "DDR5"], 18000, 130, 128),
        ("cpu_i7", "Vector I · 12 ядер", "LGA1700", ["DDR4", "DDR5"], 30000, 220, 192),
    ]:
        add(id, "CPU", title, price, hasSocket=socket, supportsMemory=mem,
            peakPowerW=power, maxMemoryGB=cap,
            coreCount={"cpu_a4_6":6,"cpu_a4_8":8,"cpu_a5_6":6,"cpu_a5_8":8,"cpu_i5":6,"cpu_i7":12}[id],
            hasIntegratedGraphics=socket != "AM4")

    for id, title, socket, mem, form, price, slots, cap, bios, eps, storage in [
        ("mb_a4", "Terra A4 Standard", "AM4", "DDR4", "ATX", 9000, 4, 128, 200, 1, ["NVMe", "SATA"]),
        ("mb_a4_m", "Terra A4 Compact", "AM4", "DDR4", "mATX", 7000, 2, 64, 100, 1, ["NVMe", "SATA"]),
        ("mb_a5", "Terra A5 Standard", "AM5", "DDR5", "ATX", 15000, 4, 192, 200, 1, ["NVMe", "SATA"]),
        ("mb_a5_itx", "Terra A5 Mini", "AM5", "DDR5", "ITX", 18000, 2, 96, 100, 1, ["NVMe"]),
        ("mb_i_d4", "Vector Board D4", "LGA1700", "DDR4", "ATX", 12000, 4, 128, 100, 1, ["NVMe", "SATA"]),
        ("mb_i_d5", "Vector Board D5", "LGA1700", "DDR5", "ATX", 16000, 4, 192, 200, 2, ["NVMe", "SATA"]),
        ("mb_unknown", "Terra A5 · неполные данные", "AM5", "DDR5", "mATX", 10000, 2, 96, None, 1, ["NVMe", "SATA"]),
    ]:
        add(id, "Motherboard", title, price, hasSocket=socket, supportsMemory=[mem],
            hasBoardForm=form, supportsMemoryForm=["UDIMM"], memorySlots=slots,
            maxMemoryGB=cap, biosRevision=bios, requiredEPS=eps, supportsStorage=storage,
            maxM2LengthMM=80, hasDisplayOutput=True)

    for id, title, mem, cap, modules, form, price in [
        ("ram_d4_16", "Pulse DDR4 · 16 ГБ (2×8)", "DDR4", 16, 2, "UDIMM", 4000),
        ("ram_d4_32", "Pulse DDR4 · 32 ГБ (2×16)", "DDR4", 32, 2, "UDIMM", 6500),
        ("ram_d5_32", "Pulse DDR5 · 32 ГБ (2×16)", "DDR5", 32, 2, "UDIMM", 9000),
        ("ram_d5_64", "Pulse DDR5 · 64 ГБ (2×32)", "DDR5", 64, 2, "UDIMM", 17000),
        ("ram_d5_128", "Pulse DDR5 · 128 ГБ (4×32)", "DDR5", 128, 4, "UDIMM", 32000),
        ("ram_so", "Pulse Mobile DDR5 · 32 ГБ", "DDR5", 32, 2, "SODIMM", 8500),
    ]:
        add(id, "RAM", title, price, hasMemoryStandard=mem, capacityGB=cap,
            moduleCount=modules, hasMemoryForm=form)

    for id, title, price, power, length, p8, p12 in [
        ("gpu_eco", "Prism Eco · 6 ГБ", 15000, 70, 180, 0, 0),
        ("gpu_mid", "Prism Core · 8 ГБ", 27000, 170, 245, 1, 0),
        ("gpu_plus", "Prism Plus · 12 ГБ", 42000, 240, 300, 2, 0),
        ("gpu_max", "Prism Max · 16 ГБ", 65000, 350, 340, 0, 1),
        ("gpu_unknown", "Prism Prototype · неполные данные", 20000, None, None, None, None),
    ]:
        add(id, "GPU", title, price, peakPowerW=power, lengthMM=length,
            requiredPCIe8=p8, required12V2x6=p12)

    for id, title, price, watts, form, p8, p12, eps, sata in [
        ("psu_400", "Volt 400", 3500, 400, "PSU_ATX", 1, 0, 1, 2),
        ("psu_550", "Volt 550", 5000, 550, "PSU_ATX", 2, 0, 1, 3),
        ("psu_750", "Volt 750", 8000, 750, "PSU_ATX", 3, 1, 2, 4),
        ("psu_1000", "Volt 1000", 12000, 1000, "PSU_ATX", 4, 1, 2, 6),
        ("psu_sfx", "Volt SFX 650", 10000, 650, "SFX", 2, 0, 1, 2),
    ]:
        add(id, "PSU", title, price, ratedPowerW=watts, hasPowerForm=form,
            availablePCIe8=p8, available12V2x6=p12, availableEPS=eps, availableSATA=sata)

    for id, title, price, forms, psu, gpu, cooler in [
        ("case_tower", "Frame Tower", 6000, ["ATX", "mATX", "ITX"], ["PSU_ATX"], 360, 170),
        ("case_compact", "Frame Compact", 4500, ["mATX", "ITX"], ["PSU_ATX"], 280, 155),
        ("case_mini", "Frame Mini", 7000, ["ITX"], ["SFX"], 210, 70),
        ("case_air", "Frame Air", 8500, ["ATX", "mATX", "ITX"], ["PSU_ATX", "SFX"], 400, 185),
        ("case_slim", "Frame Slim", 5000, ["mATX", "ITX"], ["PSU_ATX"], 250, 90),
    ]:
        add(id, "Case", title, price, supportsBoardForm=forms, supportsPowerForm=psu,
            maxGPULengthMM=gpu, maxCoolerHeightMM=cooler)

    for id, title, price, interface, length, cap in [
        ("ssd_nvme_1", "Orbit NVMe · 1 ТБ", 6000, "NVMe", 80, 1000),
        ("ssd_nvme_2", "Orbit NVMe · 2 ТБ", 11000, "NVMe", 80, 2000),
        ("ssd_sata", "Orbit SATA · 1 ТБ", 5000, "SATA", None, 1000),
        ("ssd_long", "Orbit NVMe Long · 2 ТБ", 10000, "NVMe", 110, 2000),
    ]:
        add(id, "Storage", title, price, hasStorageInterface=interface, lengthMM=length, capacityGB=cap)

    for id, title, price, sockets, height, capacity in [
        ("cooler_low", "Breeze Low", 2500, ["AM4", "AM5", "LGA1700"], 65, 110),
        ("cooler_tower", "Breeze Tower", 4000, ["AM4", "AM5", "LGA1700"], 155, 190),
        ("cooler_pro", "Breeze Pro", 6500, ["AM4", "AM5", "LGA1700"], 175, 260),
        ("cooler_a4", "Breeze A4", 2000, ["AM4"], 140, 150),
    ]:
        add(id, "Cooler", title, price, supportsSocket=sockets, heightMM=height, coolingCapacityW=capacity)
    return items


# minBios is an ordinal revision within one fictional board family.
SUPPORT = [
    ("mb_a4", "cpu_a4_6", 100), ("mb_a4", "cpu_a4_8", 200),
    ("mb_a4_m", "cpu_a4_6", 100), ("mb_a4_m", "cpu_a4_8", 200),
    ("mb_a5", "cpu_a5_6", 100), ("mb_a5", "cpu_a5_8", 200),
    ("mb_a5_itx", "cpu_a5_6", 100), ("mb_a5_itx", "cpu_a5_8", 200),
    ("mb_i_d4", "cpu_i5", 100), ("mb_i_d4", "cpu_i7", 200),
    ("mb_i_d5", "cpu_i5", 100), ("mb_i_d5", "cpu_i7", 200),
]
