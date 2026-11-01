"""Run: python -m streamlit run app.py"""
import json
from dataclasses import replace
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import sqlite3
import hashlib
import streamlit as st
from pc_ontology.knowledge import KnowledgeBase, QUERIES
from pc_ontology.schema import KINDS, OWL_PATH
from pc_ontology.engine import (Build, SLOTS, DEMOS, STATUS_LABELS, validate,
                                recommend, export_build, import_build, price_of, REAL_DEMO)
from pc_ontology.rdf_build import export_rdf, populate_build
from pc_ontology.planner import search as search_builds
from pc_ontology.storage import Store
from pc_ontology.report import render_report
from pc_ontology.quality import audit, SHAPES_PATH
from pc_ontology.clarifications import requests as clarification_requests, checklist_markdown
from pc_ontology.explorer import neighborhood, label as entity_label

st.set_page_config(page_title="Контур · подбор комплектующих", page_icon="◈", layout="wide")
public_demo = bool(globals().get("PUBLIC_DEMO", False))
st.markdown("""<style>
.block-container {max-width:1500px;padding-top:4.4rem;padding-bottom:3rem}
h1 {font-weight:650!important;letter-spacing:-1.4px;font-size:2.65rem!important}
h2,h3 {letter-spacing:-.4px}
[data-testid="stMetric"] {background:white;border:1px solid #dce5dc;padding:16px 22px;border-radius:12px}
[data-testid="stMetricLabel"] {color:#577065}
[data-testid="stMetricLabel"] p {white-space:normal!important}
[data-testid="stSidebar"] {border-right:1px solid #dce5dc}
[data-testid="stTabs"] button {font-size:15px}
.brand {font-size:13px;letter-spacing:2px;color:#176b57;font-weight:700;margin-bottom:14px}
.lead {font-size:17px;color:#58695f;max-width:820px;margin-bottom:26px}
.statusbox {padding:22px 24px;border-radius:14px;border:1px solid;margin:4px 0 16px}
.statusbox.good {background:#eaf5ed;border-color:#bad9c2;color:#235c37}
.statusbox.bad {background:#fff0eb;border-color:#efc2b3;color:#8a3924}
.statusbox.wait {background:#fff7e6;border-color:#ead5a4;color:#7d601f}
.statusbox strong {font-size:21px;display:block;margin-bottom:6px}
.smallnote {color:#68796e;font-size:13px}
@media(max-width:1050px) {
  [data-testid="stHorizontalBlock"] {flex-wrap:wrap!important}
  [data-testid="stColumn"] {min-width:min(100%,300px)!important;flex:1 1 300px!important}
  [data-testid="stMetricValue"] {font-size:1.8rem!important}
  h1 {font-size:2.1rem!important}
}
</style>""", unsafe_allow_html=True)

if not OWL_PATH.exists():
    st.error("Не найден ontology/components.owl. Восстановите файл командой python -m pc_ontology.schema.")
    st.stop()
kb = KnowledgeBase()
storage_error = None
try:
    if public_demo:
        if "_public_store" not in st.session_state:
            st.session_state._public_store = Store(":memory:")
        store = st.session_state._public_store
    else:
        store = Store()
    saved_prices = {id: value for id, value in store.prices().items() if id in kb.components}
except (sqlite3.Error, OSError, ValueError) as exc:
    store, saved_prices = None, {}
    storage_error = str(exc)


def notify(message):
    st.session_state.notice = message


def local_date(value):
    return datetime.fromisoformat(value).astimezone(ZoneInfo("Europe/Moscow")).strftime("%d.%m.%Y %H:%M")


def money(n):
    return f"{n:,}".replace(",", " ") + " ₽"


def apply(build):
    for slot in SLOTS:
        st.session_state["part_" + slot] = build.parts.get(slot)
    st.session_state.bios_text = "" if build.bios_revision is None else str(build.bios_revision)
    st.session_state.budget_enabled = build.budget is not None
    st.session_state.budget_value = build.budget if build.budget is not None else 110000
    st.session_state.price_overrides = build.price_overrides.copy()
    st.session_state.graphics_mode = build.graphics_mode
    kinds = {kb.components[id].get("catalogKind") for id in build.parts.values() if id}
    if kinds:
        st.session_state.catalog_mode = "manufacturer" if kinds == {"manufacturer"} else "synthetic"


def catalog_changed():
    selected = st.session_state.catalog_mode
    apply(Build(price_overrides=saved_prices))
    st.session_state.catalog_mode = selected


def graphics_changed():
    if st.session_state.graphics_mode == "integrated":
        st.session_state.part_GPU = None


def board_changed():
    id = st.session_state.get("part_Motherboard")
    revision = kb.components[id].get("biosRevision") if id else None
    st.session_state.bios_text = "" if revision is None else str(revision)


if "part_CPU" not in st.session_state:
    initial = None
    if store:
        try:
            raw_draft = store.load_draft()
            if raw_draft:
                initial = import_build(kb, raw_draft)
                notify("Восстановлена последняя конфигурация с этого компьютера.")
        except (ValueError, TypeError, sqlite3.Error) as exc:
            st.session_state.draft_recovery_error = str(exc)
    apply(initial if initial is not None else replace(DEMOS["Совместимая сборка"], price_overrides=saved_prices))
if "pending_build" in st.session_state:
    apply(st.session_state.pop("pending_build"))
st.session_state.setdefault("catalog_mode", "synthetic")


def details(check):
    icon = {"pass": "✓", "fail": "×", "unknown": "?"}[check.status]
    with st.expander(f"{icon}  {check.title} · {check.rule}"):
        st.write(check.explanation)
        for line in check.evidence:
            st.caption(line)


with st.sidebar:
    st.markdown("### ◈ Контур")
    st.caption("Лаборатория совместимости ПК")
    st.divider()
    st.markdown("**Готовые сценарии**")
    for demo_index, (name, demo) in enumerate(DEMOS.items()):
        if st.button(name, key=f"demo_{demo_index}", width="stretch"):
            apply(replace(demo, price_overrides=saved_prices))
    if st.button("Пример с реальными моделями", key="demo_real", width="stretch",
                 help="Версия BIOS и цены неизвестны. Нажмите, чтобы посмотреть подтверждённые сведения и недостающие условия."):
        apply(replace(REAL_DEMO, price_overrides=saved_prices))
    if st.button("Очистить сборку", width="stretch"):
        apply(Build(price_overrides=saved_prices))
    st.divider()
    st.radio("Каталог для выбора", ["synthetic", "manufacturer"], key="catalog_mode", on_change=catalog_changed,
             format_func=lambda x: "Учебный" if x == "synthetic" else "Реальные модели")
    st.radio("Графика", ["discrete", "integrated"], key="graphics_mode", on_change=graphics_changed,
             format_func=lambda x: "Дискретная видеокарта" if x == "discrete" else "Встроенная графика CPU")
    st.markdown("**Параметры сборки**")
    st.toggle("Учитывать бюджет", key="budget_enabled")
    budget_value = st.number_input("Бюджет, ₽", min_value=0, step=5000, key="budget_value",
                                   disabled=not st.session_state.budget_enabled)
    bios = st.text_input("Установленная ревизия BIOS", key="bios_text", placeholder="Пусто — неизвестна", max_chars=40,
                         help="Учебные платы: 100 или 200. Реальные: точная строка версии, например 2423 или 0602. Неизвестные версии не сравниваются по алфавиту.")
    st.caption("При смене платы подставляется ревизия из её карточки. Можно уточнить её вручную.")
    st.divider()
    uploaded = st.file_uploader("Открыть сохранённую сборку", type=["json"])
    if uploaded and st.button("Загрузить сборку", width="stretch"):
        try:
            if uploaded.size > 1_000_000:
                raise ValueError("Размер файла не должен превышать 1 МБ.")
            loaded = import_build(kb, json.loads(uploaded.getvalue()))
            st.session_state.pending_build = loaded
            st.rerun()
        except (ValueError, TypeError) as exc:
            st.error(str(exc))
    st.caption("Учебный проект · версия 2.2")

st.markdown('<div class="brand">КОНТУР / БАЗА ЗНАНИЙ О КОМПЛЕКТУЮЩИХ</div>', unsafe_allow_html=True)
st.title("Каждая деталь на своём месте.")
st.markdown('<div class="lead">Соберите конфигурацию, проверьте ограничения и узнайте, почему компоненты подходят друг другу.</div>', unsafe_allow_html=True)
st.caption("Учебный каталог содержит вымышленные модели. Реальные модели снабжены источниками производителей. Цены для них вводятся вами; неизвестные сведения требуют уточнения.")
if public_demo:
    st.info("Публичная демонстрация: сборки и цены доступны только в вашем текущем сеансе. После обновления страницы или разрыва соединения они могут исчезнуть. Скачайте сборку в JSON, чтобы сохранить её надолго.")
if "notice" in st.session_state:
    st.success(st.session_state.pop("notice"))
if storage_error:
    st.warning("Не удалось открыть локальные сохранения. Проверки и экспорт в файлы доступны.")
    with st.expander("Сведения о проблеме с сохранениями"):
        st.code(storage_error)

selected_board = st.session_state.get("part_Motherboard")
bios_is_synthetic = kb.components[selected_board].get("catalogKind") == "synthetic" if selected_board else st.session_state.catalog_mode == "synthetic"
if bios_is_synthetic and bios.strip() and (not bios.strip().isascii() or not bios.strip().isdigit()):
    st.error("Укажите целую неотрицательную ревизию BIOS или оставьте поле пустым.")
    kb.close()
    st.stop()
build = Build({s: st.session_state.get("part_" + s) for s in SLOTS},
              (int(bios) if bios_is_synthetic else bios.strip()) if bios.strip() else None,
              int(budget_value) if st.session_state.budget_enabled else None,
              st.session_state.price_overrides, st.session_state.graphics_mode)
result = validate(kb, build)
payload = export_build(kb, build)
draft_saved = False
if store and not st.session_state.get("draft_recovery_error"):
    try:
        store.save_draft(payload)
        draft_saved = True
    except (sqlite3.Error, OSError, ValueError):
        st.warning("Не удалось сохранить черновик. Скачайте JSON, чтобы сохранить текущую конфигурацию.")
elif store and st.session_state.get("draft_recovery_error"):
    st.warning("Предыдущий черновик не удалось восстановить; он не перезаписан. Именованные сборки доступны во вкладке «Мои сборки».")
    if st.button("Использовать текущую конфигурацию как новый черновик"):
        store.save_draft(payload)
        st.session_state.pop("draft_recovery_error", None)
        st.rerun()
stats = kb.stats()
m1, m2, m3, m4 = st.columns(4)
required_count = 7 if build.graphics_mode == "integrated" else 8
m1.metric("Выбрано компонентов", f"{required_count - len(result.missing)} / {required_count}")
m2.metric("Стоимость по заданным ценам", ("от " if result.unknown_prices else "") + money(result.total))
m3.metric("Расчётный минимум БП", f"{result.estimated_power} Вт" if result.estimated_power is not None else "Нет данных")
m4.metric("Конфликты / нет данных", f"{result.count('fail')} / {result.count('unknown')}")
st.write("")
builder, library, planning, catalog, ontology, quality, about = st.tabs(["Конфигуратор", "Мои сборки", "Автоподбор и исправление", "Каталог", "Онтология и вывод", "Качество данных", "О проекте"], key="workspace_tabs")

with builder:
    left, right = st.columns([1.12, 1], gap="large")
    with left:
        st.subheader("Ваша конфигурация")
        st.caption("Проверки обновляются после каждого выбора. Цена указана за компонент или комплект памяти.")
        cols = st.columns(2)
        for i, (slot, label) in enumerate(KINDS.items()):
            if slot == "GPU" and build.graphics_mode == "integrated":
                continue
            options = [None] + [c.id for c in kb.by_kind(slot) if c.get("catalogKind") == st.session_state.catalog_mode or c.id == build.parts.get(slot)]
            with cols[i % 2]:
                st.selectbox(label, options, key="part_" + slot,
                             on_change=board_changed if slot == "Motherboard" else None,
                             format_func=lambda id: "Не выбрано" if id is None else kb.components[id].title)
                selected = st.session_state["part_" + slot]
                st.caption(money(price_of(kb, build, selected)) if selected and price_of(kb, build, selected) is not None else "Цена не задана")
        # Selectboxes update session_state before rerunning, so build/result above already match the selection.
        st.download_button("Сохранить сборку и объяснения", json.dumps(export_build(kb, build), ensure_ascii=False, indent=2),
                           file_name="pc-build.json", mime="application/json", width="stretch")
        st.download_button("Скачать сборку с проверками в OWL", export_rdf(kb, build),
                           file_name="pc-build.owl", mime="application/rdf+xml", width="stretch")
        st.download_button("Отчёт для печати", render_report(kb, build), file_name="pc-build-report.html",
                           mime="text/html", width="stretch")
        st.caption(("Черновик хранится только в вашем текущем сеансе. Скачайте JSON для длительного хранения." if public_demo else "Последняя конфигурация сохранена на этом компьютере. Для сохранения под названием откройте «Мои сборки».") if draft_saved else "Скачайте JSON, чтобы сохранить текущую конфигурацию; черновик сейчас недоступен.")
    with right:
        st.subheader("Результат проверки")
        heading = {"pass": "Сборка прошла проверки", "fail": "Есть несовместимые компоненты", "unknown": "Нужны дополнительные сведения"}[result.status]
        subtitle = {"pass": "Все применимые правила прототипа выполнены.", "fail": "Откройте конфликт, чтобы увидеть причину и исходные характеристики.",
                    "unknown": "Выберите недостающие компоненты или уточните неизвестные характеристики."}[result.status]
        style = {"pass": "good", "fail": "bad", "unknown": "wait"}[result.status]
        st.markdown(f'<div class="statusbox {style}"><strong>{heading}</strong>{subtitle}</div>', unsafe_allow_html=True)
        if result.missing:
            st.info("Не выбраны: " + ", ".join(KINDS[s].lower() for s in result.missing))
        shown = st.radio("Показать проверки", ["Проблемы", "Все"], horizontal=True, label_visibility="collapsed")
        checks = [c for c in result.checks if shown == "Все" or c.status != "pass"]
        if not checks:
            st.success(f"Подтверждено проверок: {result.count('pass')}. Можно перейти к подбору альтернатив.")
        with st.container(height=400, border=False):
            for check in sorted(checks, key=lambda c: {"fail": 0, "unknown": 1, "pass": 2}[c.status]):
                details(check)
        unknown_items = clarification_requests(kb, build)
        if unknown_items:
            with st.expander(f"Что именно нужно уточнить · {len(unknown_items)}"):
                for item in unknown_items:
                    st.markdown(f"**{item['Компонент']} — {item['Сведения']}**")
                    st.write(item["Что сделать"])
                    st.caption("Связанные проверки: " + ", ".join(item["Правила"]))
                st.download_button("Скачать список уточнений", checklist_markdown(unknown_items),
                                   file_name="clarifications.md", mime="text/markdown", key="download_clarifications")
    st.divider()
    st.subheader("Подобрать замену")
    st.caption("Оценка учитывает правила, затрагивающие выбранную категорию, и общий бюджет. Другие конфликты сборки могут сохраниться.")
    r1, r2 = st.columns([1, 2])
    with r1:
        slot = st.selectbox("Категория для подбора", [s for s in KINDS if not (s == "GPU" and build.graphics_mode == "integrated")], format_func=KINDS.get, key="recommend_slot")
    with r2:
        statuses = st.multiselect("Какие варианты показать", ["pass", "unknown", "fail"], default=["pass", "unknown"],
                                 format_func=STATUS_LABELS.get)
    candidates = [r for r in recommend(kb, build, slot) if r["status"] in statuses and r["component"].get("catalogKind") == st.session_state.catalog_mode]
    if not candidates:
        st.info("Вариантов с выбранным статусом нет. Покажите конфликты, чтобы увидеть причины, или измените остальные компоненты.")
    for row in candidates:
        candidate = row["component"]
        with st.container(border=True):
            a, b, c = st.columns([3, 1.1, 1])
            with a:
                st.markdown("**" + candidate.title + "**")
                st.caption(STATUS_LABELS[row["status"]])
                if row["reasons"]:
                    st.write(" · ".join(x.title for x in row["reasons"]))
                else:
                    st.write(f"Подтверждено связанных проверок: {len(row['checks'])}.")
                if slot == "Motherboard":
                    st.caption("Ревизия BIOS для новой платы: " + str(row["bios_revision"] or "неизвестна — проверьте перед использованием"))
            b.markdown("**" + (money(price_of(kb, build, candidate.id)) if price_of(kb, build, candidate.id) is not None else "Нет цены") + "**")
            trial_build = replace(build, parts={**build.parts, slot: candidate.id}, bios_revision=row["bios_revision"])
            trial_unknown_prices = validate(kb, trial_build).unknown_prices
            b.caption("Вся сборка: " + ("от " if trial_unknown_prices else "") + money(row["total"]))
            if c.button("Выбрать", key="replace_" + candidate.id, width="stretch"):
                st.session_state.pending_build = replace(build, parts={**build.parts, slot: candidate.id}, bios_revision=row["bios_revision"])
                st.rerun()
            with st.expander("Почему этот статус"):
                for check in row["checks"]:
                    st.write(f"**{check.rule} · {STATUS_LABELS[check.status]} · {check.title}**")
                    st.caption(check.explanation + " " + "; ".join(check.evidence))

with library:
    st.subheader("Мои сборки")
    st.write("Сохраняйте и сравнивайте варианты в текущем сеансе. Другие посетители не видят эти сборки. Для длительного хранения скачайте JSON из конфигуратора." if public_demo else "Сохраняйте варианты под названиями, возвращайтесь к ним и сравнивайте состав. Всё хранится на этом компьютере. Именованная сборка меняется только после явного обновления.")
    if store is None:
        st.info("Локальная библиотека недоступна. Сборку можно скачать в JSON из конфигуратора.")
    else:
        records = store.list_builds()
        labels = {row["id"]: row["title"] + " · " + local_date(row["updated_at"]) for row in records}
        with st.form("save_library_form", clear_on_submit=True):
            title = st.text_input("Название новой сборки", max_chars=100, placeholder="Например, ПК для учёбы", key="new_build_title")
            notes = st.text_area("Заметка", max_chars=4000, placeholder="Что важно в этой конфигурации", key="new_build_notes")
            if st.form_submit_button("Сохранить в мои сборки", type="primary"):
                try:
                    store.save_build(title, payload, notes)
                    notify("Сборка сохранена в текущем сеансе." if public_demo else "Сборка сохранена на этом компьютере.")
                    st.rerun()
                except (ValueError, sqlite3.Error, OSError) as exc:
                    st.error(str(exc))
        if records:
            chosen = st.selectbox("Сохранённая сборка", list(labels), format_func=labels.get, key="saved_build_id")
            record = store.load_build(chosen)
            try:
                saved = import_build(kb, record["payload"])
                saved_result = validate(kb, saved)
                st.write(f"**{record['title']}** · {STATUS_LABELS[saved_result.status]}")
                if record["notes"]:
                    st.write(record["notes"])
                st.caption("Проверки пересчитаны по текущей онтологии. При открытии восстанавливаются цены, записанные в этой сборке.")
                c1, c2, c3 = st.columns(3)
                if c1.button("Открыть сборку", key="open_saved", width="stretch"):
                    st.session_state.pending_build = saved
                    notify("Сохранённая сборка открыта. Её состав — во вкладке «Конфигуратор».")
                    st.rerun()
                if c2.button("Обновить текущим составом", key="update_saved", width="stretch",
                              help="Заменить состав выбранной именованной сборки текущей конфигурацией. Название и заметка сохранятся."):
                    store.save_build(record["title"], payload, record["notes"], id=chosen)
                    notify("Состав выбранной сборки обновлён.")
                    st.rerun()
                if c3.button("В архив", key="archive_saved", width="stretch"):
                    store.archive(chosen)
                    notify("Сборка перемещена в архив. Её можно восстановить ниже.")
                    st.rerun()
                st.download_button("Отчёт сохранённой сборки", render_report(kb, saved, record["title"]),
                                   file_name="saved-build-report.html", mime="text/html")
                if st.checkbox("Показать отчёт прямо здесь", key="preview_saved_report"):
                    st.iframe(render_report(kb, saved, record["title"]), height=700,
                              alt="Отчёт: состав сохранённой сборки, результаты проверок и источники")
            except (ValueError, TypeError) as exc:
                st.warning("Сборку нельзя открыть с текущим каталогом: " + str(exc))
                st.download_button("Скачать исходный JSON", json.dumps(record["payload"], ensure_ascii=False, indent=2),
                                   file_name="saved-build-original.json", mime="application/json")
        else:
            st.info("Пока нет именованных сборок. Задайте название и сохраните текущую конфигурацию.")
        if len(records) >= 2:
            compare_ids = st.multiselect("Сравнить сборки", list(labels), format_func=labels.get, max_selections=3, key="compare_build_ids")
            if len(compare_ids) >= 2:
                comparison = []
                selected = []
                for id in compare_ids:
                    row = store.load_build(id)
                    try:
                        value = import_build(kb, row["payload"])
                        checked = validate(kb, value)
                        selected.append((labels[id] + " · " + id[:4], value, checked))
                    except (ValueError, TypeError):
                        st.warning("Пропущена несовместимая с каталогом запись: " + row["title"])
                for slot, label in KINDS.items():
                    comparison.append({"Параметр": label, **{name: kb.components[value.parts[slot]].title if value.parts.get(slot)
                        else "Встроенная графика" if slot == "GPU" and value.graphics_mode == "integrated" else "Не выбран" for name, value, _ in selected}})
                comparison += [
                    {"Параметр": "Стоимость", **{name: ("от " if checked.unknown_prices else "") + money(checked.total) for name, _, checked in selected}},
                    {"Параметр": "Результат", **{name: STATUS_LABELS[checked.status] for name, _, checked in selected}},
                    {"Параметр": "Конфликты / неизвестные", **{name: f"{checked.count('fail')} / {checked.count('unknown')}" for name, _, checked in selected}},
                ]
                st.dataframe(comparison, hide_index=True, width="stretch")
        archived = store.list_builds(archived=True)
        if archived:
            with st.expander(f"Архив · {len(archived)}"):
                archived_labels = {r["id"]: r["title"] + " · " + local_date(r["updated_at"]) for r in archived}
                recover = st.selectbox("Сборка в архиве", list(archived_labels), format_func=archived_labels.get, key="archived_build_id")
                if st.button("Восстановить из архива", key="restore_saved"):
                    store.archive(recover, archived=False)
                    notify("Сборка восстановлена.")
                    st.rerun()

with planning:
    st.subheader("Полная сборка и план исправлений")
    st.write("Поиск перебирает сочетания из выбранного каталога и проверяет их теми же правилами, что конфигуратор. Можно сохранить нужные детали и выбрать цель поиска.")
    mode = st.radio("Задача", ["Новая сборка", "Исправить текущую"], horizontal=True)
    objective = st.selectbox("Что важнее", ["cost", "changes", "cores", "memory"] if mode == "Исправить текущую" else ["cost", "cores", "memory"],
        format_func={"cost": "Минимальная стоимость", "changes": "Минимальное число замен", "cores": "Больше ядер CPU", "memory": "Больше оперативной памяти"}.get)
    st.caption("Число ядер и объём памяти — отдельные критерии. Они не заменяют измерения производительности в играх или приложениях.")
    locked = st.multiselect("Сохранить выбранные компоненты", [s for s in SLOTS if build.parts.get(s)], format_func=KINDS.get)
    provisional = st.checkbox("Показать также варианты с неподтверждёнными условиями", value=False)
    st.caption("Для реального каталога это может понадобиться: TDP не подменяется пиковым потреблением, а неизвестный BIOS и габариты не считаются подтверждёнными.")
    signature = json.dumps([export_build(kb, build), mode, objective, locked, provisional, st.session_state.catalog_mode], sort_keys=True, ensure_ascii=False)
    if st.button("Найти варианты", type="primary", key="find_plans"):
        with st.spinner("Проверяю сочетания компонентов…"):
            original = build if mode == "Исправить текущую" else replace(build, parts={s: build.parts[s] for s in locked}, bios_revision=build.bios_revision if "Motherboard" in locked else None)
            report = search_builds(kb, original, catalog=st.session_state.catalog_mode,
                                   repair=mode == "Исправить текущую", objective=objective,
                                   locked=locked, allow_unknown=provisional)
        st.session_state.search_result = (signature, report)
    stored = st.session_state.get("search_result")
    if stored and stored[0] == signature:
        report = stored[1]
        for message in report.messages:
            st.info(message)
        if report.plans and report.complete:
            st.success("Поиск завершён в выбранном каталоге с заданными ограничениями.")
        for i, plan in enumerate(report.plans):
            with st.container(border=True):
                plan_result = validate(kb, plan.build)
                plan_price = ("от " if plan_result.unknown_prices else "") + money(plan.total)
                st.markdown(f"**Вариант {i+1} · {plan_price} · {STATUS_LABELS[plan.status]}**")
                if plan_result.unknown_prices:
                    st.caption("Не заданы цены: " + ", ".join(plan_result.unknown_prices))
                if plan.status == "unknown":
                    st.warning("Этот вариант требует уточнения: " + "; ".join(plan.unknown))
                st.dataframe([{"Категория": KINDS[s], "Компонент": kb.components[id].title,
                               "Цена, ₽": price_of(kb, plan.build, id)} for s, id in plan.build.parts.items() if id],
                             hide_index=True, width="stretch")
                if mode == "Исправить текущую":
                    st.write(f"Замен: {len(plan.replacements)}. Устранённые конфликты: {', '.join(plan.resolved) or 'нет исходных конфликтов'}.")
                    for change in plan.replacements:
                        old = kb.components[change["old"]].title if change["old"] else "не выбрано"
                        st.caption(f"{KINDS[change['slot']]}: {old} → {kb.components[change['new']].title}")
                    if not result.unknown_prices and not validate(kb, plan.build).unknown_prices:
                        delta = plan.total - result.total
                        st.write("Изменение стоимости: " + ("+" if delta >= 0 else "−") + money(abs(delta)))
                if st.button("Применить вариант", key=f"apply_plan_{i}"):
                    st.session_state.pending_build = plan.build
                    st.rerun()
                st.download_button("Скачать вариант JSON", json.dumps(export_build(kb, plan.build), ensure_ascii=False, indent=2),
                                   file_name=f"plan-{i+1}.json", mime="application/json", key=f"download_plan_{i}")
        with st.expander("Как выполнен поиск"):
            st.write(f"Проверено узлов: {report.visited}. Время: {report.elapsed} с. Полный обход с отсечениями: {'да' if report.complete else 'нет'}.")
            st.write("Подтверждённые варианты имеют приоритет перед неизвестными. Глобальный оптимум заявляется только в пределах заданного каталога и ограничений при завершённом поиске.")

with catalog:
    st.subheader("Каталог и происхождение сведений")
    a, b = st.columns([1, 2])
    category = a.selectbox("Тип компонента", ["Все"] + list(KINDS), format_func=lambda x: KINDS.get(x, x))
    search = b.text_input("Поиск по названию", placeholder="Например, DDR5 или Terra")
    components = [c for c in kb.components.values() if c.get("catalogKind") == st.session_state.catalog_mode and (category == "Все" or c.kind == category) and search.casefold() in c.title.casefold()]
    st.caption(f"Найдено: {len(components)}. Источник фактов — ontology/components.owl.")
    st.dataframe([{"Название": c.title, "Категория": KINDS[c.kind], "Цена, ₽": price_of(kb, build, c.id), "ID": c.id} for c in components],
                 hide_index=True, width="stretch")
    if components:
        selected_id = st.selectbox("Карточка компонента", [c.id for c in components], format_func=lambda x: kb.components[x].title)
        item = kb.components[selected_id]
        rows = [{"Свойство онтологии": name, "Значение": ", ".join(map(str, value)) if isinstance(value, list) else str(value)}
                for name, value in item.facts.items() if value is not None and value != [] and name != "sourceNote"]
        st.dataframe(rows, hide_index=True, width="stretch")
        st.caption(item.get("sourceNote"))
        with st.expander("Источники отдельных характеристик"):
            st.dataframe(kb.provenance(selected_id), hide_index=True, width="stretch")
            for source in kb.onto[selected_id].hasSource:
                if source.sourceURL and source.sourceURL.startswith(("https://", "http://")):
                    st.link_button(str(source.label.first() or source.name), source.sourceURL)
    st.markdown("#### Ваши цены")
    st.caption("Это ваши предложения или плановые оценки, а не автоматически полученные цены магазинов. Пустая цена остаётся неизвестной; 0 означает явно заданную нулевую стоимость.")
    with st.form("prices_form"):
        price_rows = [{"ID": c.id, "Компонент": c.title, "Цена, ₽": price_of(kb, build, c.id)}
                      for c in kb.components.values() if c.get("catalogKind") == st.session_state.catalog_mode]
        edited = st.data_editor(price_rows, disabled=["ID", "Компонент"], hide_index=True, width="stretch",
                                column_config={"Цена, ₽": st.column_config.NumberColumn(min_value=0, step=100, format="%d")})
        if st.form_submit_button("Сохранить цены"):
            try:
                overrides = {**build.price_overrides}
                updates = {}
                for row in edited:
                    value = row["Цена, ₽"]
                    if value is None:
                        overrides.pop(row["ID"], None)
                        updates[row["ID"]] = None
                    else:
                        if value < 0 or int(value) != value:
                            raise ValueError("Цена должна быть целым неотрицательным числом.")
                        overrides[row["ID"]] = int(value)
                        updates[row["ID"]] = int(value)
                if store:
                    store.update_prices(updates)
                    notify("Цены сохранены в текущем сеансе." if public_demo else "Цены сохранены на этом компьютере.")
                else:
                    notify("Цены применены только к текущему сеансу. Сохранение на компьютере недоступно.")
                st.session_state.pending_build = replace(build, price_overrides=overrides)
                st.rerun()
            except (ValueError, TypeError, sqlite3.Error, OSError) as exc:
                st.error(str(exc))

with ontology:
    st.subheader("От фактов к объяснимому решению")
    st.write("OWL хранит компоненты, профили поддержки, источники, отдельные утверждения и результаты проверок сборки. HermiT выводит классы по логическим определениям; числовые ограничения проверяются правилами Python.")
    st.caption(f"Классов: {stats['classes']} · объектных свойств: {stats['object_properties']} · свойств данных: {stats['data_properties']} · экземпляров: {stats['individuals']} · профилей поддержки CPU: {stats['support_profiles']}")
    st.caption(f"Реальных компонентов: {stats['manufacturer_components']} · документов-источников: {stats['sources']} · отдельных утверждений о свойствах: {stats['facts']}")
    st.graphviz_chart('''digraph {
      graph [rankdir=LR bgcolor="transparent" fontname="Arial"];
      node [shape=box style="rounded,filled" fillcolor="#edf1eb" color="#b5c9bc" fontname="Arial"];
      edge [color="#7e9c8a" fontname="Arial" fontsize=10];
      CPU [label="Процессор"]; Board [label="Материнская плата"]; Socket [label="Сокет"];
      RAM [label="Память"]; DDR [label="Стандарт DDR"]; Support [label="Профиль поддержки CPU"];
      GPU [label="Видеокарта"]; Case [label="Корпус"]; PSU [label="Блок питания"];
      Build [label="Сборка"]; Assessment [label="Результат проверки"]; Rule [label="Ограничение"];
      Fact [label="Утверждение о свойстве"]; Source [label="Источник / дата / URL"];
      CPU -> Socket [label="имеет"]; Board -> Socket [label="имеет"];
      CPU -> DDR [label="поддерживает"]; Board -> DDR [label="поддерживает"]; RAM -> DDR [label="имеет стандарт"];
      Support -> CPU [label="forCPU"]; Support -> Board [label="forBoard / minBios"];
      GPU -> Case [label="проверка длины" style=dashed]; PSU -> GPU [label="проверка питания" style=dashed];
      Build -> CPU [label="hasComponent"]; Build -> Assessment [label="hasAssessment"];
      Assessment -> Rule [label="appliesConstraint"]; Assessment -> Fact [label="usesFact"];
      Fact -> CPU [label="factSubject"]; Fact -> Source [label="factSource"];
    }''')
    st.caption("Сплошные линии — отношения OWL. Пунктир — прикладные проверки Python, а не утверждённые отношения онтологии.")
    st.download_button("Скачать онтологию для Protégé", OWL_PATH.read_bytes(), file_name="components.owl", mime="application/rdf+xml")
    st.markdown("#### Исследовать реальные связи")
    st.write("Выберите объект и глубину просмотра. Граф строится по его отношениям в загруженной OWL-онтологии, включая входящие связи; это не статическая картинка.")
    group = st.selectbox("Какие объекты исследовать", ["Component", "CPUBoardSupport", "SourceDocument", "FactAssertion"],
                        format_func={"Component": "Комплектующие", "CPUBoardSupport": "Профили поддержки CPU", "SourceDocument": "Источники", "FactAssertion": "Утверждения о свойствах"}.get, key="explorer_group")
    individuals = sorted(kb.onto[group].instances(), key=lambda obj: (entity_label(obj), obj.name))
    entity_labels = {obj.name: entity_label(obj) + " · " + obj.name for obj in individuals}
    root_id = st.selectbox("Объект графа", [obj.name for obj in individuals],
                           format_func=entity_labels.get, key="explorer_root_" + group)
    g1, g2, g3 = st.columns(3)
    graph_depth = g1.select_slider("Число переходов", [1, 2], key="graph_depth")
    include_values = g2.checkbox("Показать значения свойств", key="graph_literals")
    provenance = g3.checkbox("Показать происхождение", value=group in {"SourceDocument", "FactAssertion"}, key="graph_provenance_" + group)
    fragment = neighborhood(kb, root_id, depth=graph_depth, include_literals=include_values, include_provenance=provenance)
    st.graphviz_chart(fragment.dot)
    st.caption(f"Узлов: {fragment.node_count}; связей: {fragment.edge_count}. Показаны записанные отношения, а не результат отдельного запуска HermiT. Длинные подписи в диаграмме сокращены; таблица содержит полные значения.")
    if fragment.truncated:
        st.info("Фрагмент ограничен 45 узлами. Уменьшите глубину или отключите происхождение, чтобы сосредоточиться на нужных связях.")
    with st.expander("Связи в таблице"):
        st.dataframe(fragment.rows, hide_index=True, width="stretch")
    st.download_button("Скачать фрагмент графа RDF", fragment.turtle, file_name="ontology-fragment.ttl", mime="text/turtle")
    st.markdown("#### Запросы SPARQL")
    query_name = st.selectbox("Запрос к базе знаний", list(QUERIES))
    st.code(QUERIES[query_name], language="sparql")
    st.dataframe(kb.query(query_name), hide_index=True, width="stretch")
    st.markdown("#### Логический вывод HermiT")
    st.write("HermiT классифицирует платы по стандартам памяти, CPU по сокетам, компоненты с источниками и текущую сборку. ConflictedBuild выводится при наличии отрицательной проверки, а VerifiedBuild — при полном составе и замкнутом наборе только успешных проверок.")
    st.caption("Нужна установленная Java в PATH. Вывод выполняется в отдельной копии базы и не изменяет файл OWL.")
    if st.button("Проверить согласованность и вывести классы", type="primary"):
        reasoning_kb = KnowledgeBase()
        try:
            with st.spinner("HermiT проверяет онтологию…"):
                populate_build(reasoning_kb, build, "current_build")
                inferred = reasoning_kb.reason()
            st.success(f"Онтология согласована. Найдено новых классификаций: {len(inferred)}.")
            st.dataframe(inferred, hide_index=True, width="stretch")
        except Exception as exc:
            st.error("Логический вывод не завершён. Проверьте установку Java и согласованность OWL. Проверки сборки работают отдельно.")
            with st.expander("Диагностика"):
                st.code(str(exc))
        finally:
            reasoning_kb.close()

with quality:
    st.subheader("Качество базы знаний")
    st.write("SHACL проверяет, как записаны данные: обязательные поля, типы и диапазоны значений, ссылки на источники и структуру результатов. Это отдельная проверка, которая не доказывает физическую совместимость сборки.")
    scope = st.radio("Что проверить", ["Каталог", "Текущую сборку вместе с каталогом"], horizontal=True, key="quality_scope")
    today_text = datetime.now(ZoneInfo("Europe/Moscow")).date().isoformat()
    signature_data = OWL_PATH.read_bytes() + SHAPES_PATH.read_bytes() + today_text.encode() + scope.encode()
    if scope != "Каталог":
        signature_data += json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()
    quality_signature = hashlib.sha256(signature_data).hexdigest()
    if st.button("Проверить качество данных", type="primary", key="audit_quality"):
        with st.spinner("Проверяю формальные ограничения и происхождение сведений…"):
            source = OWL_PATH if scope == "Каталог" else export_rdf(kb, build)
            checked_quality = audit(source)
        st.session_state.quality_result = (quality_signature, checked_quality)
    cached_quality = st.session_state.get("quality_result")
    if cached_quality and cached_quality[0] == quality_signature:
        checked_quality = cached_quality[1]
        total_values = sum(row["Записанных значений"] for row in checked_quality.coverage)
        sourced_values = sum(row["Значений с источником"] for row in checked_quality.coverage)
        review_count = sum(row["Состояние"] != "Дата сверки актуальна" for row in checked_quality.source_reviews)
        q1, q2, q3 = st.columns(3)
        q1.metric("Нарушения SHACL", len(checked_quality.findings))
        q2.metric("Значения с записью источника", f"{sourced_values} / {total_values}")
        q3.metric("Источники для пересмотра", review_count)
        if checked_quality.conforms:
            st.success("Структура проверенного снимка соответствует заданным SHACL-ограничениям.")
        else:
            st.error("Обнаружены нарушения формальных ограничений. Проверьте указанные объекты и свойства.")
            st.dataframe(checked_quality.findings, hide_index=True, width="stretch")
        st.caption("Покрытие источниками означает наличие записи происхождения, а не оценку истинности характеристики. Даты и ссылки берутся из базы; сайт производителя при этой проверке не запрашивается. Порог пересмотра источника — 180 дней, это политика прототипа.")
        with st.expander("Происхождение значений реальных моделей"):
            st.dataframe(checked_quality.coverage, hide_index=True, width="stretch")
        with st.expander("Даты проверки источников"):
            st.dataframe(checked_quality.source_reviews, hide_index=True, width="stretch")
        st.download_button("Скачать отчёт качества JSON", json.dumps(checked_quality.to_dict(), ensure_ascii=False, indent=2),
                           file_name="quality-report.json", mime="application/json")
        st.download_button("Скачать формальный отчёт SHACL", checked_quality.validation_turtle,
                           file_name="shacl-report.ttl", mime="text/turtle")
    elif cached_quality:
        st.info("Проверяемый снимок изменился. Запустите проверку снова, чтобы обновить результат.")
    else:
        st.info("Нажмите «Проверить качество данных», чтобы получить формальный отчёт.")
    st.download_button("Скачать SHACL-ограничения", SHAPES_PATH.read_text(encoding="utf-8"),
                       file_name="quality-shapes.ttl", mime="text/turtle")
    st.markdown("#### Что уточнить для текущей сборки")
    requests = clarification_requests(kb, build)
    if requests:
        st.dataframe([{**row, "Правила": ", ".join(row["Правила"]), "Источники": "; ".join(row["Источники"])} for row in requests],
                     hide_index=True, width="stretch")
        st.download_button("Скачать план уточнения данных", checklist_markdown(requests),
                           file_name="data-clarifications.md", mime="text/markdown")
    else:
        st.success("Неизвестных проверок в текущей сборке нет. Подтверждённые конфликты, если они есть, исправляются отдельно.")

with about:
    if public_demo:
        st.caption("В публичной демонстрации библиотека, цены и черновик хранятся только в текущем сеансе. Постоянные локальные сохранения, описанные ниже, доступны в настольном варианте проекта.")
    st.subheader("Разработка онтологии для интеллектуального подбора компьютерных комплектующих")
    st.write("Цель — представить знания о компонентах ПК и их ограничениях в формальной модели и использовать её для объяснимой проверки и подбора компонентов.")
    st.markdown("""
**Версия 2.2**

- 42 учебных и 32 реальных компонента с источниками и датой проверки. Факты производителя отделены от цен пользователя.
- В OWL представлены сборки, ограничения, результаты проверок и использованные утверждения. Сборку с объяснениями можно скачать и открыть в Protégé.
- HermiT выводит классы компонентов и сборок. Python проверяет числовые ограничения и формирует рекомендации.
- Поиск полной конфигурации и плана замены нескольких деталей: стоимость, число замен, число ядер или объём памяти. Есть фиксация выбранных деталей.
- Дополнительные проверки встроенной графики, точного размера M.2, толщины GPU, зазора над RAM, рекомендаций производителя GPU и длины БП.
- Локальная библиотека именованных сборок, сравнение вариантов и восстанавливаемый архив. Цены и последний черновик сохраняются между сеансами. Доступен печатный отчёт с объяснениями и источниками.
- SHACL-проверка качества базы, просмотр реальных связей OWL с экспортом RDF и адресный список недостающих сведений для сборки. Неизвестные необязательные измерения отделены от ошибок структуры.

**Как интерпретировать результат**

Нет сведений — значит «недостаточно данных». TDP не заменяет пиковое потребление, NSPR кулера не переводится в ватты. Неизвестные цены не считаются нулевыми. BIOS реальных плат подтверждается по точной метке из таблицы; порядок произвольных строк не угадывается.

Реальные конфигурации могут требовать уточнения мощности или механических условий. Режим поиска с неподтверждёнными условиями показывает их явно. При прерывании поиска глобальная оптимальность не заявляется.

**Границы модели**

Один компонент каждой категории, память — комплект; GPU можно исключить при встроенной графике. Пока нет проверки QVL/XMP, разводки PCIe и одновременного использования нескольких накопителей, полного пространственного моделирования, переходников питания и реальных тестов производительности. Размеры и ограничения действуют при условиях, записанных в источниках.

**Для защиты:** покажите конфликт памяти, поиск исправлений, автоматическую сборку, источник реальной характеристики и вывод класса текущей сборки. В папке docs находятся описание модели, источники и воспроизводимая оценка сценариев.
""")
    evaluation_path = Path(__file__).parent / "docs" / "evaluation" / "results.json"
    if evaluation_path.exists():
        assessment = json.loads(evaluation_path.read_text(encoding="utf-8"))
        st.info(f"Оценка сконструированных сценариев: {assessment['correct']} из {assessment['total']} ожидаемых исходов. Это проверка сценариев, а не оценка точности на реальном рынке.")

kb.close()
