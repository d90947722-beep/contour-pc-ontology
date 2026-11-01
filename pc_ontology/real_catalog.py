"""Small manufacturer-sourced catalog checked on 2026-10-28.

No market prices, peak-power estimates or invented cooler wattage are included.
Facts are a dated snapshot. Each fact has provenance; omitted values are unknown.
"""

CHECKED_DATE = "2026-10-28"
SOURCES = {}
REAL_ITEMS = []
REAL_SUPPORT = []


def _source(id, publisher, title, url):
    SOURCES[id] = dict(title=title, url=url, checkedDate=CHECKED_DATE, publisher=publisher)
    return id


def _item(id, kind, title, source, *, notes="", extra_sources=(), fact_sources=None, **facts):
    provenance = {key: source for key, value in facts.items() if value is not None}
    provenance.update(fact_sources or {})
    item = dict(id=id, kind=kind, title=title, price=None, catalogKind="manufacturer",
                sources=list(dict.fromkeys([source, *extra_sources, *provenance.values()])),
                factSources=provenance, assumptions={},
                sourceNote=f"Характеристики производителя; проверено {CHECKED_DATE}. Цена не задана. " + notes,
                **facts)
    REAL_ITEMS.append(item)
    return item


for id, name, slug, socket, memory, cores, threads, integrated in [
    ("real_cpu_5600", "AMD Ryzen 5 5600", "amd-ryzen-5-5600", "AM4", "DDR4", 6, 12, False),
    ("real_cpu_5700x", "AMD Ryzen 7 5700X", "amd-ryzen-7-5700x", "AM4", "DDR4", 8, 16, False),
    ("real_cpu_7600", "AMD Ryzen 5 7600", "amd-ryzen-5-7600", "AM5", "DDR5", 6, 12, True),
    ("real_cpu_7700", "AMD Ryzen 7 7700", "amd-ryzen-7-7700", "AM5", "DDR5", 8, 16, True),
]:
    url = (f"https://www.amd.com/en/support/downloads/drivers.html/processors/ryzen/ryzen-5000-series/{slug}.html"
           if socket == "AM4" else f"https://www.amd.com/en/products/processors/desktops/ryzen/7000-series/{slug}.html")
    source = _source("src_" + id[5:], "AMD", name + " — Specifications", url)
    _item(id, "CPU", name, source, hasSocket=socket, supportsMemory=[memory], maxMemoryGB=128,
          tdpW=65, coreCount=cores, threadCount=threads, hasIntegratedGraphics=integrated,
          notes="TDP не является максимальным потреблением: peakPowerW неизвестно.")


for id, title, family, slug, socket, memory, form, capacity, bios, cpu_source_url in [
    ("real_mb_b550_plus", "ASUS PRIME B550-PLUS", "prime", "prime-b550-plus", "AM4", "DDR4", "ATX", 128,
     "2423", "https://www.asus.com/motherboards-components/motherboards/prime/prime-b550-plus/helpdesk_cpu?model2Name=PRIME-B550-PLUS"),
    ("real_mb_tuf_b550", "ASUS TUF GAMING B550-PLUS", "tuf-gaming", "tuf-gaming-b550-plus", "AM4", "DDR4", "ATX", 128,
     "2423", "https://www.asus.com/us/supportonly/tuf%20gaming%20b550-plus/helpdesk_cpu/"),
    ("real_mb_b550m_a", "ASUS PRIME B550M-A", "prime", "prime-b550m-a", "AM4", "DDR4", "mATX", 128,
     "2423", "https://www.asus.com/motherboards-components/motherboards/prime/prime-b550m-a/helpdesk_cpu?model2Name=PRIME-B550M-A"),
    ("real_mb_b650_plus", "ASUS PRIME B650-PLUS", "prime", "prime-b650-plus", "AM5", "DDR5", "ATX", 192,
     "0602", "https://www.asus.com/de/motherboards-components/motherboards/prime/prime-b650-plus/helpdesk_cpu/?model2Name=PRIME-B650-PLUS"),
]:
    source = _source("src_" + id[5:], "ASUS", title + " — Tech Specs",
                     f"https://www.asus.com/motherboards-components/motherboards/{family}/{slug}/techspec/")
    support_source = _source("src_support_" + id[8:], "ASUS", title + " — CPU support", cpu_source_url)
    _item(id, "Motherboard", title, source, hasSocket=socket, supportsMemory=[memory],
          hasBoardForm=form, supportsMemoryForm=["UDIMM"], memorySlots=4, maxMemoryGB=capacity,
          requiredEPS=1, supportsStorage=["NVMe", "SATA"], maxM2LengthMM=110,
          supportedM2LengthsMM=[42, 60, 80, 110], hasDisplayOutput=True, m2SlotCount=2,
          sataPortCount=6 if id in ("real_mb_b550_plus", "real_mb_tuf_b550") else 4,
          notes="Установленная версия BIOS неизвестна: минимальная версия поддержки не означает версию прошивки конкретного экземпляра. "
                "Длины M.2 указаны для доступного подходящего слота; распределение по слотам проверяется отдельно.",
          extra_sources=[support_source])
    cpus = ["real_cpu_5600", "real_cpu_5700x"] if socket == "AM4" else ["real_cpu_7600", "real_cpu_7700"]
    for cpu in cpus:
        REAL_SUPPORT.append(dict(board=id, cpu=cpu, minBiosLabel=bios, source=support_source, status="supported"))


for id, part, memory, capacity, height in [
    ("real_ram_d4_16", "KF432C16BBK2/16", "DDR4", 16, None),
    ("real_ram_d4_32", "KF432C16BBK2/32", "DDR4", 32, None),
    ("real_ram_d5_32", "KF552C40BBK2-32", "DDR5", 32, None),
    ("real_ram_d5_64", "KF552C40BBK2-64", "DDR5", 64, None),
]:
    source = _source("src_" + id[5:], "Kingston", part + " — Memory Module Specifications",
                     "https://www.kingston.com/datasheets/" + part.replace("/", "_") + ".pdf")
    _item(id, "RAM", f"Kingston FURY Beast {part} · {capacity} ГБ", source,
          hasMemoryStandard=memory, capacityGB=capacity, moduleCount=2, hasMemoryForm="UDIMM", heightMM=height,
          notes=("Высота DDR5 по PDF — 34,9 мм; целочисленное heightMM оставлено неизвестным без округления. " if memory == "DDR5" else
                 "В использованных PDF DDR4 указана номинальная высота 34 мм и общий допуск ±0,12 мм. heightMM оставлено неизвестным для проверки точного зазора без округления допуска вниз. ") +
                "DDR4-3200 и DDR5-5200 — профили XMP; частота по умолчанию отличается. Проверка типа DDR не подтверждает XMP/QVL.")


for id, title, source_url, length, thickness, watts, recommended, capacity in [
    ("real_gpu_3060", "MSI GeForce RTX 3060 VENTUS 2X 12G OC",
     "https://us.msi.com/Graphics-Card/GeForce-RTX-3060-VENTUS-2X-12G-OC/Specification", 235, 42, 170, 550, 12),
    ("real_gpu_4060", "MSI GeForce RTX 4060 VENTUS 2X BLACK 8G OC",
     "https://uk.msi.com/Graphics-Card/GeForce-RTX-4060-VENTUS-2X-BLACK-8G-OC/Specification", 199, 41, None, 550, 8),
    ("real_gpu_4060ti", "MSI GeForce RTX 4060 Ti VENTUS 2X BLACK 8G OC",
     "https://storage-asset.msi.com/datasheet/vga/global/GeForce-RTX-4060-Ti-VENTUS-2X-BLACK-8G-OC.pdf", 199, 42, 160, 550, 8),
    ("real_gpu_4070", "MSI GeForce RTX 4070 VENTUS 2X 12G OC",
     "https://www.msi.com/Graphics-Card/GeForce-RTX-4070-VENTUS-2X-12G-OC/Specification", 242, 43, 200, 650, 12),
]:
    source = _source("src_" + id[5:], "MSI", title + " — Specifications", source_url)
    _item(id, "GPU", title, source, lengthMM=length, thicknessMM=thickness,
          requiredPCIe8=1, required12V2x6=0, gpuPowerW=watts, recommendedPSUW=recommended, capacityGB=capacity,
          notes=("Производитель указывает потребление 115 или 120 Вт без однозначного значения для экземпляра; gpuPowerW не заполнено. "
                 if id == "real_gpu_4060" else "Паспортное потребление GPU не приравнивается к измеренному пику. ") +
                "Рекомендация по БП относится к системе производителя и является отдельной проверкой.")


for id, title, watts, pcie8, eps, sata, source_url, second_url in [
    ("real_psu_550", "MSI MAG A550BN", 550, 2, 1, 5,
     "https://www.msi.com/Power-Supply/MAG-A550BN/Specification",
     "https://storage-asset.msi.com/datasheet/power-supply/in/MAG-A550BN.pdf"),
    ("real_psu_650", "MSI MAG A650BN", 650, 2, 1, 5,
     "https://www.msi.com/Power-Supply/MAG-A650BN/Specification",
     "https://storage-asset.msi.com/datasheet/power-supply/in/MAG-A650BN.pdf"),
    ("real_psu_750", "MSI MAG A750GL PCIE5", 750, 3, 2, 8,
     "https://www.msi.com/Power-Supply/MAG-A750GL-PCIE5/Specification",
     "https://download.msi.com/archive/mnu_exe/psu/MAGA850GL_A750GLPCIE5A650GL.pdf"),
    ("real_psu_850", "MSI MAG A850GL PCIE5", 850, 4, 2, 8,
     "https://www.msi.com/Power-Supply/MAG-A850GL-PCIE5/Specification",
     "https://download.msi.com/archive/mnu_exe/psu/MAGA850GL_A750GLPCIE5A650GL.pdf"),
]:
    source = _source("src_" + id[5:], "MSI", title + " — Specifications", source_url)
    second = _source("src_" + id[5:] + "_manual", "MSI", title + " — manufacturer datasheet/manual", second_url)
    _item(id, "PSU", title, source, ratedPowerW=watts, hasPowerForm="PSU_ATX", availablePCIe8=pcie8,
          availableEPS=eps, availableSATA=sata, lengthMM=140,
          available12V2x6=0 if watts in (550, 650) else None,
          extra_sources=[second], fact_sources={"hasPowerForm": second},
          notes=("В источнике есть один PCIe 16-pin, но тип 12VHPWR/12V-2x6 и ревизия комплекта требуют уточнения: available12V2x6 неизвестно. "
                 if watts >= 750 else "") +
                "Числа PCIe/EPS — разъёмы на стороне компонентов, не число кабелей. Для GL использована таблица 3/4 PCIe 6+2; ревизию нужно сверить с комплектом.")


for id, title, url, gpu, cooler, psu, notes in [
    ("real_case_pop", "Fractal Design Pop Air RGB Orange Core · FD-C-POR1A-05",
     "https://www.fractal-design.com/products/cases/pop-series/pop-air/pop-air-rgb-orange-core-tg-clear-tint/", 405, 170, 170,
     "GPU 405 мм со штатным передним вентилятором, без переднего радиатора. БП максимум 170 мм."),
    ("real_case_meshify", "Fractal Design Meshify C · FD-CA-MESH-C-BKO",
     "https://www.fractal-design.com/products/cases/meshify-series/meshify-c/meshify-c/", 315, 170, 175,
     "Использован лимит GPU со штатным передним вентилятором. Значение высоты кулера 170 мм взято из текущей карточки производителя."),
    ("real_case_focus", "Fractal Design Focus 2 Black Solid · FD-C-FOC2A-07",
     "https://www.fractal-design.com/products/cases/focus-series/focus-2/focus-2-black-solid/", 405, 170, 250,
     "GPU 405 мм со штатным передним вентилятором, без переднего радиатора. БП максимум 250 мм; производитель рекомендует 175 мм для удобства кабелей."),
    ("real_case_north", "Fractal Design North Charcoal Black Mesh · FD-C-NOR1C-01",
     "https://www.fractal-design.com/products/cases/north-series/north/north-charcoal-black/", 355, 145, 255,
     "Выбрана Mesh-конфигурация с боковым кронштейном в верхнем/среднем положении: кулер максимум 145 мм. GPU до 355 мм без переднего радиатора; ширина GPU может дополнительно ограничиваться боковым кронштейном и здесь не подтверждена. БП до 255 мм при одной корзине HDD; при двух предел 155 мм."),
]:
    source = _source("src_" + id[5:], "Fractal Design", title + " — Compatibility", url)
    _item(id, "Case", title, source, supportsBoardForm=["ATX", "mATX", "ITX"], supportsPowerForm=["PSU_ATX"],
          maxGPULengthMM=gpu, maxCoolerHeightMM=cooler, maxPSULengthMM=psu, notes=notes)


source_870 = _source("src_ssd_870", "Samsung", "Samsung SSD 870 EVO — Data Sheet Rev.1.1",
    "https://download.semiconductor.samsung.com/resources/data-sheet/Samsung_SSD_870_EVO_Data_Sheet_Rev1.1_230509.pdf")
source_980 = _source("src_ssd_980", "Samsung", "Samsung NVMe SSD 980 PRO — Data Sheet Rev.2.1",
    "https://download.semiconductor.samsung.com/resources/data-sheet/Samsung-NVMe-SSD-980-PRO-Data-Sheet_Rev.2.1_230509.pdf")
for id, title, capacity in [("real_ssd_870_1", "Samsung 870 EVO 1 ТБ · MZ-77E1T0BW", 1000),
                            ("real_ssd_870_2", "Samsung 870 EVO 2 ТБ · MZ-77E2T0BW", 2000)]:
    _item(id, "Storage", title, source_870, hasStorageInterface="SATA", capacityGB=capacity,
          notes="Накопитель 2,5 дюйма. Проверка питания SATA не подтверждает наличие крепления и кабеля данных.")
for id, title, capacity in [("real_ssd_980_1", "Samsung 980 PRO 1 ТБ · MZ-V8P1T0BW", 1000),
                            ("real_ssd_980_2", "Samsung 980 PRO 2 ТБ · MZ-V8P2T0BW", 2000)]:
    _item(id, "Storage", title, source_980, hasStorageInterface="NVMe", capacityGB=capacity, lengthMM=80,
          notes="Версия без радиатора. lengthMM=80 — номинальная длина типоразмера M.2 2280; габарит по допуску 80,15 мм не используется как код крепления.")


cooler_rows = [
    ("real_cooler_redux", "Noctua NH-U12S redux", "nh-u12s-redux", 158, ["AM4", "AM5", "LGA1700"]),
    ("real_cooler_u12s", "Noctua NH-U12S", "nh-u12s", 158, ["AM4", "AM5", "LGA1700"]),
    ("real_cooler_u14s", "Noctua NH-U14S", "nh-u14s", 165, ["AM4", "AM5", "LGA1700"]),
    ("real_cooler_l9a", "Noctua NH-L9a-AM5", "nh-l9a-am5", 37, ["AM5"]),
]
for cpu_slug in ["amd-ryzen-5-5600", "amd-ryzen-7-5700x", "amd-ryzen-5-7600", "amd-ryzen-7-7700"]:
    _source("src_noctua_" + cpu_slug, "Noctua", cpu_slug + " — CPU compatibility",
            "https://www.noctua.at/en/compatibility/by-components/cpus/" + cpu_slug)
for id, title, slug, height, sockets in cooler_rows:
    source = _source("src_" + id[5:], "Noctua", title + " — Specifications",
                     f"https://www.noctua.at/en/products/{slug}/specifications")
    supported = (["real_cpu_5600", "real_cpu_5700x", "real_cpu_7600", "real_cpu_7700"] if id == "real_cooler_redux"
                 else ["real_cpu_7600", "real_cpu_7700"] if id == "real_cooler_l9a" else [])
    per_cpu_source = {"real_cpu_5600": "src_noctua_amd-ryzen-5-5600",
                      "real_cpu_5700x": "src_noctua_amd-ryzen-7-5700x",
                      "real_cpu_7600": "src_noctua_amd-ryzen-5-7600",
                      "real_cpu_7700": "src_noctua_amd-ryzen-7-7700"}
    item = _item(id, "Cooler", title, source, supportsSocket=sockets, heightMM=height,
                 supportedCPUIDs=supported,
                 extra_sources=[per_cpu_source[cpu] for cpu in supported],
                 notes="Ваттный coolingCapacityW не задан: NSPR не является ваттами. " +
                 ("Официальный список помечает крепление и тепловую пригодность для перечисленных CPU; проверка платы и корпуса остаётся отдельной."
                  if supported else "В списке Noctua старые комплекты имеют upgrade-optional. Наличие нужного крепления следует сверять; безусловная связь с CPU не утверждена."))
    if supported:
        # A multi-valued relationship has one evidence source for EACH value.
        item["factSources"].pop("supportedCPUIDs", None)
        for cpu in supported:
            item["factSources"]["supportedCPUIDs:" + cpu] = per_cpu_source[cpu]
    if id in ("real_cooler_redux", "real_cooler_l9a"):
        clearance_source = _source("src_" + id[5:] + "_features", "Noctua", title + " — RAM compatibility",
                                   f"https://www.noctua.at/en/products/{slug}/features")
        item["unlimitedRAMClearance"] = True
        item["sources"].append(clearance_source)
        item["factSources"]["unlimitedRAMClearance"] = clearance_source


assert len(REAL_ITEMS) == 32
assert len({item["id"] for item in REAL_ITEMS}) == 32
