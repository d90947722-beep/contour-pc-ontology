# Проверенные источники реального каталога

Дата сверки: **28 октября 2026 года**. Каталог содержит **32 реальные модели**, по четыре на каждую из восьми категорий. В реестре `SOURCES` — **44 записи источников** (некоторые модели используют общий документ). Использованы страницы и документы самих производителей AMD, ASUS, Kingston, MSI, Fractal Design, Samsung и Noctua.

Это ограниченный снимок характеристик, а не полное утверждение о совместимости любых экземпляров. Официальные страницы предупреждают о смене спецификаций и региональных/комплектных различиях. Проверять точную ревизию товара всё равно необходимо.

## Как устроено происхождение фактов

В `pc_ontology/real_catalog.py` каждый компонент содержит `sources` и `factSources`. Связь `supportedCPUIDs` снабжена источником для каждого значения через ключ `supportedCPUIDs:<ID процессора>`. Таблица `SOURCES` хранит заголовок, издателя, URL и дату проверки. `REAL_SUPPORT` хранит источник каждой пары плата/процессор и минимальную **строковую метку BIOS**, а не искусственно назначенную установленную версию.

## Что намеренно неизвестно

- **Цены:** все `price=None`. Рыночные цены не собирались; бюджет можно считать только после ввода пользователем своих цен.
- **Пиковая мощность CPU:** TDP хранится в `tdpW`, а не в `peakPowerW`. Значение TDP не подменяет максимальное потребление.
- **Пиковая мощность GPU:** `gpuPowerW` хранит паспортное потребление производителя, не измеренный максимум. Для RTX 4060 страница указывает 115 или 120 Вт; единственное число намеренно не выбрано.
- **Мощность охлаждения:** NSPR Noctua не переводится в ватты. `coolingCapacityW` отсутствует. Для NH-U12S redux и NH-L9a-AM5 добавлены только явно подтверждённые пары с CPU из официального списка совместимости.
- **Установленная версия BIOS:** неизвестна. Наличие поддержки начиная с 2423/0602 не означает, что эта прошивка уже установлена на приобретаемой плате.
- **PCIe 16-pin GL:** один 16-pin указан производителем, но однозначный тип/ревизия 12VHPWR или 12V-2x6 не перенесён в `available12V2x6`. Для двух BN полная таблица кабелей не содержит 16-pin, поэтому число таких разъёмов равно нулю.
- **Высота RAM:** для DDR5 PDF указывает 34,9 мм. Для двух выбранных DDR4 PDF 4809941B и 4809947B указывают 34 мм в Features и размерном чертеже, с общим допуском ±0,12 мм. Чтобы не терять допуск и не подтверждать пограничный зазор округлением вниз, целочисленное `heightMM` всех четырёх комплектов оставлено неизвестным. Значение 34,1 мм из иных карточек в этот снимок не переносится.

## Условия интерпретации

- Все комплекты Kingston состоят из двух UDIMM. Профиль XMP и скорость JEDEC по умолчанию различаются; наличие нужного стандарта DDR не подтверждает разгон или QVL.
- Максимальный объём CPU взят из страницы AMD (128 ГБ), независимо от большего предела платы.
- `supportedM2LengthsMM` означает номинальные длины крепления M.2 в подходящем слоте, а не измерение длины всей платы SSD по механическому допуску. Для 980 PRO форм-фактор 2280 соответствует коду длины 80; физический максимум по PDF составляет 80,15 мм.
- Для PRIME B550M-A длина 110 поддерживается только одним из двух M.2-слотов. Наличие списка не доказывает пригодность любого выбранного слота. На PRIME B550-PLUS второй M.2 разделяет ресурсы с SATA6G_56; соответствующая оговорка есть в спецификации платы.
- Стандартные ATX-БП MSI имеют габариты 140 × 150 × 86 мм. Числа PCIe/EPS — разъёмы на стороне компонентов; это не число независимых кабелей.
- Для Meshify C текущая карточка Fractal указывает предел кулера **170 мм**. Старые описания могут отличаться; в набор не перенесено значение по памяти.
- Выбран North **Mesh FD-C-NOR1C-01 с боковым кронштейном в верхнем/среднем положении**: применён предел кулера **145 мм**. Без кронштейна допустимо 170 мм; модель не предполагает его снятие. GPU 355 мм допустим без переднего радиатора; наличие бокового кронштейна дополнительно влияет на ширину GPU, которая не проверена этим пределом длины. Предел БП 255 мм относится к одной корзине HDD; с двумя предел 155 мм. Расстановка корзин отдельно не моделируется.
- NH-U12S и NH-U14S в списках Noctua имеют отметку `upgrade-optional`; разные комплекты могут требовать монтажный набор. Поэтому безусловные `supportedCPUIDs` для них не заполнены. Поддерживаемые сокеты описывают текущую спецификацию с подходящим креплением.
- NH-U12S redux и NH-L9a-AM5 имеют прямое обещание отсутствия перекрытия RAM в разделах Features; для них указан `unlimitedRAMClearance=True`. Это ограниченный факт о перекрытии DIMM, а не обещание любой механической совместимости со всеми деталями.

## Профили поддержки CPU и BIOS

| Плата | CPU | Минимальный BIOS | Источник |
|---|---|---|---|
| ASUS PRIME B550-PLUS | AMD Ryzen 5 5600 | 2423 | [ASUS](https://www.asus.com/motherboards-components/motherboards/prime/prime-b550-plus/helpdesk_cpu?model2Name=PRIME-B550-PLUS) |
| ASUS PRIME B550-PLUS | AMD Ryzen 7 5700X | 2423 | [ASUS](https://www.asus.com/motherboards-components/motherboards/prime/prime-b550-plus/helpdesk_cpu?model2Name=PRIME-B550-PLUS) |
| ASUS TUF GAMING B550-PLUS | AMD Ryzen 5 5600 | 2423 | [ASUS](https://www.asus.com/us/supportonly/tuf%20gaming%20b550-plus/helpdesk_cpu/) |
| ASUS TUF GAMING B550-PLUS | AMD Ryzen 7 5700X | 2423 | [ASUS](https://www.asus.com/us/supportonly/tuf%20gaming%20b550-plus/helpdesk_cpu/) |
| ASUS PRIME B550M-A | AMD Ryzen 5 5600 | 2423 | [ASUS](https://www.asus.com/motherboards-components/motherboards/prime/prime-b550m-a/helpdesk_cpu?model2Name=PRIME-B550M-A) |
| ASUS PRIME B550M-A | AMD Ryzen 7 5700X | 2423 | [ASUS](https://www.asus.com/motherboards-components/motherboards/prime/prime-b550m-a/helpdesk_cpu?model2Name=PRIME-B550M-A) |
| ASUS PRIME B650-PLUS | AMD Ryzen 5 7600 | 0602 | [ASUS](https://www.asus.com/de/motherboards-components/motherboards/prime/prime-b650-plus/helpdesk_cpu/?model2Name=PRIME-B650-PLUS) |
| ASUS PRIME B650-PLUS | AMD Ryzen 7 7700 | 0602 | [ASUS](https://www.asus.com/de/motherboards-components/motherboards/prime/prime-b650-plus/helpdesk_cpu/?model2Name=PRIME-B650-PLUS) |

Метки сравниваются только в пределах конкретной платы и по явно заданным проверенным сведениям. Лексикографическое сравнение строк не используется. В этом снимке нет собственных утверждений о порядке всех опубликованных версий.

## Каталог и использованные документы

### Процессоры

- **AMD Ryzen 5 5600** — [AMD: спецификация](https://www.amd.com/en/support/downloads/drivers.html/processors/ryzen/ryzen-5000-series/amd-ryzen-5-5600.html).
- **AMD Ryzen 7 5700X** — [AMD: спецификация](https://www.amd.com/en/support/downloads/drivers.html/processors/ryzen/ryzen-5000-series/amd-ryzen-7-5700x.html).
- **AMD Ryzen 5 7600** — [AMD: спецификация](https://www.amd.com/en/products/processors/desktops/ryzen/7000-series/amd-ryzen-5-7600.html).
- **AMD Ryzen 7 7700** — [AMD: спецификация](https://www.amd.com/en/products/processors/desktops/ryzen/7000-series/amd-ryzen-7-7700.html).

### Материнские платы

- **ASUS PRIME B550-PLUS** — [ASUS: спецификация](https://www.asus.com/motherboards-components/motherboards/prime/prime-b550-plus/techspec/).
- **ASUS TUF GAMING B550-PLUS** — [ASUS: спецификация](https://www.asus.com/motherboards-components/motherboards/tuf-gaming/tuf-gaming-b550-plus/techspec/).
- **ASUS PRIME B550M-A** — [ASUS: спецификация](https://www.asus.com/motherboards-components/motherboards/prime/prime-b550m-a/techspec/).
- **ASUS PRIME B650-PLUS** — [ASUS: спецификация](https://www.asus.com/motherboards-components/motherboards/prime/prime-b650-plus/techspec/).

### Память

- **Kingston FURY Beast KF432C16BBK2/16 · 16 ГБ** — [Kingston: спецификация](https://www.kingston.com/datasheets/KF432C16BBK2_16.pdf).
- **Kingston FURY Beast KF432C16BBK2/32 · 32 ГБ** — [Kingston: спецификация](https://www.kingston.com/datasheets/KF432C16BBK2_32.pdf).
- **Kingston FURY Beast KF552C40BBK2-32 · 32 ГБ** — [Kingston: спецификация](https://www.kingston.com/datasheets/KF552C40BBK2-32.pdf).
- **Kingston FURY Beast KF552C40BBK2-64 · 64 ГБ** — [Kingston: спецификация](https://www.kingston.com/datasheets/KF552C40BBK2-64.pdf).

### Видеокарты

- **MSI GeForce RTX 3060 VENTUS 2X 12G OC** — [MSI: спецификация](https://us.msi.com/Graphics-Card/GeForce-RTX-3060-VENTUS-2X-12G-OC/Specification).
- **MSI GeForce RTX 4060 VENTUS 2X BLACK 8G OC** — [MSI: спецификация](https://uk.msi.com/Graphics-Card/GeForce-RTX-4060-VENTUS-2X-BLACK-8G-OC/Specification).
- **MSI GeForce RTX 4060 Ti VENTUS 2X BLACK 8G OC** — [MSI: спецификация](https://storage-asset.msi.com/datasheet/vga/global/GeForce-RTX-4060-Ti-VENTUS-2X-BLACK-8G-OC.pdf).
- **MSI GeForce RTX 4070 VENTUS 2X 12G OC** — [MSI: спецификация](https://www.msi.com/Graphics-Card/GeForce-RTX-4070-VENTUS-2X-12G-OC/Specification).

### Блоки питания

- **MSI MAG A550BN** — [MSI: спецификация](https://www.msi.com/Power-Supply/MAG-A550BN/Specification).
- **MSI MAG A650BN** — [MSI: спецификация](https://www.msi.com/Power-Supply/MAG-A650BN/Specification).
- **MSI MAG A750GL PCIE5** — [MSI: спецификация](https://www.msi.com/Power-Supply/MAG-A750GL-PCIE5/Specification).
- **MSI MAG A850GL PCIE5** — [MSI: спецификация](https://www.msi.com/Power-Supply/MAG-A850GL-PCIE5/Specification).

### Корпуса

- **Fractal Design Pop Air RGB Orange Core · FD-C-POR1A-05** — [Fractal Design: спецификация](https://www.fractal-design.com/products/cases/pop-series/pop-air/pop-air-rgb-orange-core-tg-clear-tint/).
- **Fractal Design Meshify C · FD-CA-MESH-C-BKO** — [Fractal Design: спецификация](https://www.fractal-design.com/products/cases/meshify-series/meshify-c/meshify-c/).
- **Fractal Design Focus 2 Black Solid · FD-C-FOC2A-07** — [Fractal Design: спецификация](https://www.fractal-design.com/products/cases/focus-series/focus-2/focus-2-black-solid/).
- **Fractal Design North Charcoal Black Mesh · FD-C-NOR1C-01** — [Fractal Design: спецификация](https://www.fractal-design.com/products/cases/north-series/north/north-charcoal-black/).

### Накопители

- **Samsung 870 EVO 1 ТБ · MZ-77E1T0BW** — [Samsung: спецификация](https://download.semiconductor.samsung.com/resources/data-sheet/Samsung_SSD_870_EVO_Data_Sheet_Rev1.1_230509.pdf).
- **Samsung 870 EVO 2 ТБ · MZ-77E2T0BW** — [Samsung: спецификация](https://download.semiconductor.samsung.com/resources/data-sheet/Samsung_SSD_870_EVO_Data_Sheet_Rev1.1_230509.pdf).
- **Samsung 980 PRO 1 ТБ · MZ-V8P1T0BW** — [Samsung: спецификация](https://download.semiconductor.samsung.com/resources/data-sheet/Samsung-NVMe-SSD-980-PRO-Data-Sheet_Rev.2.1_230509.pdf).
- **Samsung 980 PRO 2 ТБ · MZ-V8P2T0BW** — [Samsung: спецификация](https://download.semiconductor.samsung.com/resources/data-sheet/Samsung-NVMe-SSD-980-PRO-Data-Sheet_Rev.2.1_230509.pdf).

### Кулеры

- **Noctua NH-U12S redux** — [Noctua: спецификация](https://www.noctua.at/en/products/nh-u12s-redux/specifications).
- **Noctua NH-U12S** — [Noctua: спецификация](https://www.noctua.at/en/products/nh-u12s/specifications).
- **Noctua NH-U14S** — [Noctua: спецификация](https://www.noctua.at/en/products/nh-u14s/specifications).
- **Noctua NH-L9a-AM5** — [Noctua: спецификация](https://www.noctua.at/en/products/nh-l9a-am5/specifications).

## Полный реестр источников

- `src_cpu_5600` — [AMD Ryzen 5 5600 — Specifications](https://www.amd.com/en/support/downloads/drivers.html/processors/ryzen/ryzen-5000-series/amd-ryzen-5-5600.html); AMD; проверено 2026-10-28.
- `src_cpu_5700x` — [AMD Ryzen 7 5700X — Specifications](https://www.amd.com/en/support/downloads/drivers.html/processors/ryzen/ryzen-5000-series/amd-ryzen-7-5700x.html); AMD; проверено 2026-10-28.
- `src_cpu_7600` — [AMD Ryzen 5 7600 — Specifications](https://www.amd.com/en/products/processors/desktops/ryzen/7000-series/amd-ryzen-5-7600.html); AMD; проверено 2026-10-28.
- `src_cpu_7700` — [AMD Ryzen 7 7700 — Specifications](https://www.amd.com/en/products/processors/desktops/ryzen/7000-series/amd-ryzen-7-7700.html); AMD; проверено 2026-10-28.
- `src_mb_b550_plus` — [ASUS PRIME B550-PLUS — Tech Specs](https://www.asus.com/motherboards-components/motherboards/prime/prime-b550-plus/techspec/); ASUS; проверено 2026-10-28.
- `src_support_b550_plus` — [ASUS PRIME B550-PLUS — CPU support](https://www.asus.com/motherboards-components/motherboards/prime/prime-b550-plus/helpdesk_cpu?model2Name=PRIME-B550-PLUS); ASUS; проверено 2026-10-28.
- `src_mb_tuf_b550` — [ASUS TUF GAMING B550-PLUS — Tech Specs](https://www.asus.com/motherboards-components/motherboards/tuf-gaming/tuf-gaming-b550-plus/techspec/); ASUS; проверено 2026-10-28.
- `src_support_tuf_b550` — [ASUS TUF GAMING B550-PLUS — CPU support](https://www.asus.com/us/supportonly/tuf%20gaming%20b550-plus/helpdesk_cpu/); ASUS; проверено 2026-10-28.
- `src_mb_b550m_a` — [ASUS PRIME B550M-A — Tech Specs](https://www.asus.com/motherboards-components/motherboards/prime/prime-b550m-a/techspec/); ASUS; проверено 2026-10-28.
- `src_support_b550m_a` — [ASUS PRIME B550M-A — CPU support](https://www.asus.com/motherboards-components/motherboards/prime/prime-b550m-a/helpdesk_cpu?model2Name=PRIME-B550M-A); ASUS; проверено 2026-10-28.
- `src_mb_b650_plus` — [ASUS PRIME B650-PLUS — Tech Specs](https://www.asus.com/motherboards-components/motherboards/prime/prime-b650-plus/techspec/); ASUS; проверено 2026-10-28.
- `src_support_b650_plus` — [ASUS PRIME B650-PLUS — CPU support](https://www.asus.com/de/motherboards-components/motherboards/prime/prime-b650-plus/helpdesk_cpu/?model2Name=PRIME-B650-PLUS); ASUS; проверено 2026-10-28.
- `src_ram_d4_16` — [KF432C16BBK2/16 — Memory Module Specifications](https://www.kingston.com/datasheets/KF432C16BBK2_16.pdf); Kingston; проверено 2026-10-28.
- `src_ram_d4_32` — [KF432C16BBK2/32 — Memory Module Specifications](https://www.kingston.com/datasheets/KF432C16BBK2_32.pdf); Kingston; проверено 2026-10-28.
- `src_ram_d5_32` — [KF552C40BBK2-32 — Memory Module Specifications](https://www.kingston.com/datasheets/KF552C40BBK2-32.pdf); Kingston; проверено 2026-10-28.
- `src_ram_d5_64` — [KF552C40BBK2-64 — Memory Module Specifications](https://www.kingston.com/datasheets/KF552C40BBK2-64.pdf); Kingston; проверено 2026-10-28.
- `src_gpu_3060` — [MSI GeForce RTX 3060 VENTUS 2X 12G OC — Specifications](https://us.msi.com/Graphics-Card/GeForce-RTX-3060-VENTUS-2X-12G-OC/Specification); MSI; проверено 2026-10-28.
- `src_gpu_4060` — [MSI GeForce RTX 4060 VENTUS 2X BLACK 8G OC — Specifications](https://uk.msi.com/Graphics-Card/GeForce-RTX-4060-VENTUS-2X-BLACK-8G-OC/Specification); MSI; проверено 2026-10-28.
- `src_gpu_4060ti` — [MSI GeForce RTX 4060 Ti VENTUS 2X BLACK 8G OC — Specifications](https://storage-asset.msi.com/datasheet/vga/global/GeForce-RTX-4060-Ti-VENTUS-2X-BLACK-8G-OC.pdf); MSI; проверено 2026-10-28.
- `src_gpu_4070` — [MSI GeForce RTX 4070 VENTUS 2X 12G OC — Specifications](https://www.msi.com/Graphics-Card/GeForce-RTX-4070-VENTUS-2X-12G-OC/Specification); MSI; проверено 2026-10-28.
- `src_psu_550` — [MSI MAG A550BN — Specifications](https://www.msi.com/Power-Supply/MAG-A550BN/Specification); MSI; проверено 2026-10-28.
- `src_psu_550_manual` — [MSI MAG A550BN — manufacturer datasheet/manual](https://storage-asset.msi.com/datasheet/power-supply/in/MAG-A550BN.pdf); MSI; проверено 2026-10-28.
- `src_psu_650` — [MSI MAG A650BN — Specifications](https://www.msi.com/Power-Supply/MAG-A650BN/Specification); MSI; проверено 2026-10-28.
- `src_psu_650_manual` — [MSI MAG A650BN — manufacturer datasheet/manual](https://storage-asset.msi.com/datasheet/power-supply/in/MAG-A650BN.pdf); MSI; проверено 2026-10-28.
- `src_psu_750` — [MSI MAG A750GL PCIE5 — Specifications](https://www.msi.com/Power-Supply/MAG-A750GL-PCIE5/Specification); MSI; проверено 2026-10-28.
- `src_psu_750_manual` — [MSI MAG A750GL PCIE5 — manufacturer datasheet/manual](https://download.msi.com/archive/mnu_exe/psu/MAGA850GL_A750GLPCIE5A650GL.pdf); MSI; проверено 2026-10-28.
- `src_psu_850` — [MSI MAG A850GL PCIE5 — Specifications](https://www.msi.com/Power-Supply/MAG-A850GL-PCIE5/Specification); MSI; проверено 2026-10-28.
- `src_psu_850_manual` — [MSI MAG A850GL PCIE5 — manufacturer datasheet/manual](https://download.msi.com/archive/mnu_exe/psu/MAGA850GL_A750GLPCIE5A650GL.pdf); MSI; проверено 2026-10-28.
- `src_case_pop` — [Fractal Design Pop Air RGB Orange Core · FD-C-POR1A-05 — Compatibility](https://www.fractal-design.com/products/cases/pop-series/pop-air/pop-air-rgb-orange-core-tg-clear-tint/); Fractal Design; проверено 2026-10-28.
- `src_case_meshify` — [Fractal Design Meshify C · FD-CA-MESH-C-BKO — Compatibility](https://www.fractal-design.com/products/cases/meshify-series/meshify-c/meshify-c/); Fractal Design; проверено 2026-10-28.
- `src_case_focus` — [Fractal Design Focus 2 Black Solid · FD-C-FOC2A-07 — Compatibility](https://www.fractal-design.com/products/cases/focus-series/focus-2/focus-2-black-solid/); Fractal Design; проверено 2026-10-28.
- `src_case_north` — [Fractal Design North Charcoal Black Mesh · FD-C-NOR1C-01 — Compatibility](https://www.fractal-design.com/products/cases/north-series/north/north-charcoal-black/); Fractal Design; проверено 2026-10-28.
- `src_ssd_870` — [Samsung SSD 870 EVO — Data Sheet Rev.1.1](https://download.semiconductor.samsung.com/resources/data-sheet/Samsung_SSD_870_EVO_Data_Sheet_Rev1.1_230509.pdf); Samsung; проверено 2026-10-28.
- `src_ssd_980` — [Samsung NVMe SSD 980 PRO — Data Sheet Rev.2.1](https://download.semiconductor.samsung.com/resources/data-sheet/Samsung-NVMe-SSD-980-PRO-Data-Sheet_Rev.2.1_230509.pdf); Samsung; проверено 2026-10-28.
- `src_noctua_amd-ryzen-5-5600` — [amd-ryzen-5-5600 — CPU compatibility](https://www.noctua.at/en/compatibility/by-components/cpus/amd-ryzen-5-5600); Noctua; проверено 2026-10-28.
- `src_noctua_amd-ryzen-7-5700x` — [amd-ryzen-7-5700x — CPU compatibility](https://www.noctua.at/en/compatibility/by-components/cpus/amd-ryzen-7-5700x); Noctua; проверено 2026-10-28.
- `src_noctua_amd-ryzen-5-7600` — [amd-ryzen-5-7600 — CPU compatibility](https://www.noctua.at/en/compatibility/by-components/cpus/amd-ryzen-5-7600); Noctua; проверено 2026-10-28.
- `src_noctua_amd-ryzen-7-7700` — [amd-ryzen-7-7700 — CPU compatibility](https://www.noctua.at/en/compatibility/by-components/cpus/amd-ryzen-7-7700); Noctua; проверено 2026-10-28.
- `src_cooler_redux` — [Noctua NH-U12S redux — Specifications](https://www.noctua.at/en/products/nh-u12s-redux/specifications); Noctua; проверено 2026-10-28.
- `src_cooler_redux_features` — [Noctua NH-U12S redux — RAM compatibility](https://www.noctua.at/en/products/nh-u12s-redux/features); Noctua; проверено 2026-10-28.
- `src_cooler_u12s` — [Noctua NH-U12S — Specifications](https://www.noctua.at/en/products/nh-u12s/specifications); Noctua; проверено 2026-10-28.
- `src_cooler_u14s` — [Noctua NH-U14S — Specifications](https://www.noctua.at/en/products/nh-u14s/specifications); Noctua; проверено 2026-10-28.
- `src_cooler_l9a` — [Noctua NH-L9a-AM5 — Specifications](https://www.noctua.at/en/products/nh-l9a-am5/specifications); Noctua; проверено 2026-10-28.
- `src_cooler_l9a_features` — [Noctua NH-L9a-AM5 — RAM compatibility](https://www.noctua.at/en/products/nh-l9a-am5/features); Noctua; проверено 2026-10-28.


## Повторная сверка габаритных ограничений

- M.2: PRIME B550-PLUS и TUF GAMING B550-PLUS поддерживают 2242/2260/2280/22110 в обоих M-key слотах; PRIME B550M-A — 22110 только в M.2_1; PRIME B650-PLUS с выбранными Ryzen 7000 — 2242/2260/2280/22110 в обоих слотах. Следовательно, объединённый список [42,60,80,110] для одного накопителя корректен у всех четырёх плат; он не заменяет проверку конкретного слота.
- [Fractal Pop Air FAQ](https://support.fractal-design.com/support/solutions/articles/4000184330-pop-air-silent): БП170 мм, кулер170 мм. [Product Sheet Pop Air](https://www.fractal-design.com/app/uploads/2022/06/Pop-Air-RGB-Pop-Air_Product-Sheet_EN.pdf) уточняет GPU405 мм с передним вентилятором.
- [Fractal Focus 2 FAQ](https://support.fractal-design.com/support/solutions/articles/4000186456-focus-2): БП250 мм максимум,175 мм рекомендовано для кабелей; кулер170 мм. [Product Sheet Focus 2](https://www.fractal-design.com/app/uploads/2022/08/Focus-2-Focus-2-RGB-_Product-Sheet_EN.pdf): GPU405 мм с передним вентилятором.
- [North FAQ](https://support.fractal-design.com/support/solutions/articles/4000189455-north): кулер170 мм без бокового кронштейна и145 мм при его верхнем/среднем положении.
- [North GPU compatibility](https://support.fractal-design.com/support/solutions/articles/4000189454-north-%20compatibilit%C3%A9%20GPU): передний радиатор сокращает предел длины, а боковой кронштейн может влиять на ширину видеокарты. Ограничение ширины нельзя подменять ограничением длины.
- [North PSU compatibility](https://support.fractal-design.com/support/solutions/articles/4000189451-north-psu-compatibility):255 мм при одной корзине HDD,155 мм при двух.

Дополнительные ссылки этого раздела использованы для перекрёстной проверки условий. Базовые44 записи происхождения фактов в онтологии сохранены.
