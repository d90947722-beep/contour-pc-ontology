"""Readable standalone HTML report; all user/catalog text is escaped."""
from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo
from .engine import validate, price_of, STATUS_LABELS
from .schema import KINDS


def render_report(kb, build, title="Проверка сборки компьютера"):
    result = validate(kb, build)
    text = lambda value: escape(str(value), quote=True)
    money = lambda value: f"{value:,}".replace(",", " ") + " ₽"
    stamp = datetime.now(ZoneInfo("Europe/Moscow")).strftime("%d.%m.%Y %H:%M МСК")
    component_rows = []
    sources = {}
    for slot, label in KINDS.items():
        id = build.parts.get(slot)
        if not id:
            component_rows.append(f"<tr><td>{text(label)}</td><td>{'Не требуется: встроенная графика' if slot == 'GPU' and build.graphics_mode == 'integrated' else 'Не выбран'}</td><td>—</td></tr>")
            continue
        item = kb.components[id]
        price = price_of(kb, build, id)
        basis = "Цена пользователя" if id in build.price_overrides else "Учебная цена" if item.get("catalogKind") == "synthetic" else "Цена не задана"
        component_rows.append(f"<tr><td>{text(label)}</td><td>{text(item.title)}</td><td>{text(money(price)) if price is not None else 'Неизвестна'}<br><small>{basis}</small></td></tr>")
        for source in kb.onto[id].hasSource:
            if source.sourceURL and source.sourceURL.startswith(("https://", "http://")):
                sources[source.sourceURL] = (str(source.label.first() or source.name), source.checkedDate)
    check_rows = []
    for check in sorted(result.checks, key=lambda c: {"fail": 0, "unknown": 1, "pass": 2}[c.status]):
        evidence = "<br>".join(text(v) for v in check.evidence)
        check_rows.append(f"<tr><td>{text(check.rule)}</td><td><strong>{text(check.title)}</strong><br>{text(check.explanation)}<br><small>{evidence}</small></td><td class='{check.status}'>{text(STATUS_LABELS[check.status])}</td></tr>")
    sources_html = "".join(f"<li>{text(label)} — <a href='{text(url)}'>{text(url)}</a>; сверено {text(date or 'неизвестно')}</li>" for url, (label, date) in sorted(sources.items()))
    total = ("Неполная сумма: от " if result.unknown_prices else "Стоимость по заданным ценам: ") + money(result.total)
    scope = ("Каталог включает реальные модели с источниками. Неизвестные условия требуют уточнения. "
             "Учебные модели и их цены вымышлены. Этот результат относится только к реализованным правилам; "
             "он не заменяет проверку фактической прошивки, комплектации и условий установки.")
    return f"""<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{text(title)} · Контур</title><style>
body{{font:15px/1.5 Arial,sans-serif;color:#20332a;background:#f5f7f3;margin:0;overflow-wrap:anywhere}}main{{max-width:1000px;margin:30px auto;background:white;padding:36px}}h1{{font-size:30px}}h2{{margin-top:32px}}small,.muted{{color:#56675e}}table{{width:100%;border-collapse:collapse}}th,td{{padding:10px;border:1px solid #dbe3dc;vertical-align:top;text-align:left}}th{{background:#edf3ec}}.pass{{color:#176b43}}.fail{{color:#9a3628}}.unknown{{color:#805b12}}a{{overflow-wrap:anywhere;color:#176b57}}.banner{{padding:16px;background:#edf3ec;border-left:4px solid #176b57}}button{{padding:10px 18px;background:#176b57;color:white;border:0;border-radius:6px;cursor:pointer}}@media print{{body{{background:white;font-size:11px}}main{{max-width:none;margin:0;padding:0}}button{{display:none}}thead{{display:table-header-group}}tr{{break-inside:avoid}}@page{{margin:14mm}}}}
</style></head><body><main><button onclick="window.print()">Распечатать / сохранить PDF</button><p class="muted">КОНТУР · отчёт о проверке · {stamp}</p>
<h1>{text(title)}</h1><div class="banner"><strong class="{result.status}">{text(STATUS_LABELS[result.status])}</strong><br>{text(total)}</div>
<p>BIOS: {text(build.bios_revision if build.bios_revision is not None else 'неизвестен')}. Бюджет: {text(money(build.budget)) if build.budget is not None else 'не задан'}. Графика: {'встроенная' if build.graphics_mode == 'integrated' else 'дискретная'}.</p>
<p>{text(scope)}</p><h2>Состав</h2><table><thead><tr><th>Категория</th><th>Компонент</th><th>Стоимость</th></tr></thead><tbody>{''.join(component_rows)}</tbody></table>
<h2>Проверки</h2><p>Конфликтов: {result.count('fail')}; неизвестных условий: {result.count('unknown')}; подтверждений: {result.count('pass')}.</p>
<table><thead><tr><th>Правило</th><th>Объяснение и исходные значения</th><th>Результат</th></tr></thead><tbody>{''.join(check_rows)}</tbody></table>
<h2>Источники реальных характеристик</h2>{'<ul>'+sources_html+'</ul>' if sources_html else '<p>В этой сборке использован только учебный каталог.</p>'}
<p class="muted">Числовые проверки выполнены правилами Python над фактами OWL. Данный HTML-отчёт не является результатом отдельного запуска HermiT. Для формальной модели используйте экспорт OWL.</p>
</main></body></html>"""
