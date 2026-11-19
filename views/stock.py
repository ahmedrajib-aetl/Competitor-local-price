"""Daily warehouse stock pages for Grain and Coal."""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

import config
from core import charts, source, stock, ui


def _top(cfg: config.SheetConfig, meta: dict, dataset: stock.StockDataset):
    latest = dataset.dates[-1]
    age_days = max(0, (date.today() - latest).days)
    tab_label = cfg.tab_name or "first tab"

    ui.stock_header(
        cfg, meta, dataset, latest, source.age_label(meta["fetched_at"])
    )

    source_col, refresh_col = st.columns([5, 1.2], vertical_alignment="center")
    with source_col:
        st.caption(
            f"Reading **{tab_label}** · newest date **{latest:%d %b %Y}** · "
            f"fetched {source.age_label(meta['fetched_at'])}"
        )
    with refresh_col:
        if st.button(
            "Refresh now",
            type="primary",
            width="stretch",
            key=f"{cfg.key}_refresh",
            help="Ignore the cache and download the stock sheet again.",
        ):
            source.clear_cache()
            st.rerun(scope="app")

    if not meta.get("live"):
        st.markdown(
            f"<div class='banner'><b>Snapshot mode.</b> Showing Master Data through "
            f"<b>{latest:%d %b %Y}</b>. {meta.get('note', '')}</div>",
            unsafe_allow_html=True,
        )
    elif age_days > config.STALE_AFTER_DAYS:
        st.markdown(
            f"<div class='banner'><b>The newest date in the sheet is "
            f"{latest:%d %b %Y} ({age_days} days ago).</b> Update the Master Data "
            "tab to show today's position.</div>",
            unsafe_allow_html=True,
        )

    return latest, age_days, tab_label


def _filters(cfg: config.SheetConfig, dataset: stock.StockDataset):
    date_key = f"{cfg.key}_date"
    search_key = f"{cfg.key}_search"
    group_key = f"{cfg.key}_group"
    item_key = f"{cfg.key}_item"
    plant_key = f"{cfg.key}_plant"
    warehouse_key = f"{cfg.key}_warehouse"

    dates = sorted(dataset.dates, reverse=True)
    labels = [day.strftime("%d %b %Y") for day in dates]
    if date_key in st.session_state and st.session_state[date_key] not in labels:
        st.session_state[date_key] = labels[0]

    with st.container(border=True):
        st.markdown(
            "<div class='filter-title'>Filters</div>"
            "<div class='filter-help'>The latest date is selected automatically. "
            "Every dropdown is searchable. An empty dropdown means <b>All</b>.</div>",
            unsafe_allow_html=True,
        )

        c1, c2, c3 = st.columns([1, 2.6, 0.8], vertical_alignment="bottom")
        with c1:
            selected_label = st.selectbox(
                "Date",
                labels,
                index=0,
                key=date_key,
            )
        with c2:
            search = st.text_input(
                "Search",
                key=search_key,
                placeholder="Item, code, warehouse or plant… press Enter",
            )
        with c3:
            def _reset() -> None:
                st.session_state[date_key] = labels[0]
                st.session_state[search_key] = ""
                st.session_state[group_key] = []
                st.session_state[item_key] = []
                st.session_state[plant_key] = []
                st.session_state[warehouse_key] = []

            st.button(
                "Reset",
                width="stretch",
                key=f"{cfg.key}_reset",
                on_click=_reset,
            )

        selected_date = dates[labels.index(selected_label)]

        show_plant = bool(dataset.plants)
        if show_plant:
            columns = st.columns(4, gap="small")
        else:
            columns = st.columns(3, gap="small")

        with columns[0]:
            groups = st.multiselect(
                dataset.group_label,
                dataset.groups,
                key=group_key,
                placeholder=f"All {dataset.group_label}s",
            )
        with columns[1]:
            items = st.multiselect(
                "Item Name",
                dataset.items,
                key=item_key,
                placeholder="All items",
            )
        if show_plant:
            with columns[2]:
                plants = st.multiselect(
                    "Plant",
                    dataset.plants,
                    key=plant_key,
                    placeholder="All plants",
                )
            warehouse_col = columns[3]
        else:
            plants = []
            warehouse_col = columns[2]
        with warehouse_col:
            warehouses = st.multiselect(
                "Warehouse",
                dataset.warehouses,
                key=warehouse_key,
                placeholder="All warehouses",
            )

    return {
        "selected_date": selected_date,
        "selected_label": selected_label,
        "search": search,
        "groups": groups,
        "items": items,
        "plants": plants,
        "warehouses": warehouses,
        "dates": dates,
    }


def _render_body(cfg: config.SheetConfig) -> None:
    try:
        raw, meta = source.load_sheet(
            cfg.key, nonce=st.session_state.get(f"{cfg.key}_nonce", 0)
        )
    except Exception as exc:
        st.error(f"Could not load the {cfg.label} source: {exc}")
        return

    try:
        dataset = stock.prepare_stock(raw, cfg)
    except Exception as exc:
        st.error(f"Could not read Master Data: {exc}")
        st.caption(
            "Check that the tab has Date, Product/SBU, Item Name, Warehouse, Qty "
            "and Value columns."
        )
        return

    latest, age_days, tab_label = _top(cfg, meta, dataset)
    ctx = _filters(cfg, dataset)
    selected_date = ctx["selected_date"]

    today = stock.filter_stock(
        dataset,
        selected_date,
        groups=ctx["groups"],
        items=ctx["items"],
        plants=ctx["plants"],
        warehouses=ctx["warehouses"],
        search=ctx["search"],
    )

    previous_dates = [day for day in dataset.dates if day < selected_date]
    previous_date = max(previous_dates) if previous_dates else None
    previous = (
        stock.filter_stock(
            dataset,
            previous_date,
            groups=ctx["groups"],
            items=ctx["items"],
            plants=ctx["plants"],
            warehouses=ctx["warehouses"],
            search=ctx["search"],
        )
        if previous_date
        else pd.DataFrame()
    )

    k = stock.stock_kpis(today, previous)

    st.session_state["_status"] = {
        "mode": "stock",
        "key": cfg.key,
        "label": cfg.label,
        "live": bool(meta.get("live")),
        "source": meta.get("source", ""),
        "note": meta.get("note", ""),
        "fetched_at": meta.get("fetched_at"),
        "rows": dataset.rows,
        "rows_shown": k["rows"],
        "selected_label": ctx["selected_label"],
        "dates_stored": len(dataset.dates),
        "items": k["items"],
        "warehouses": k["warehouses"],
        "plants": k["plants"],
        "groups": k["groups"],
        "unit": "MT · BDT",
        "url": cfg.sheet_url,
        "tab": tab_label,
        "latest": latest.isoformat(),
        "latest_label": latest.strftime("%d %b %Y"),
        "age_days": age_days,
        "stale": age_days > config.STALE_AFTER_DAYS,
        "collapsed": 0,
    }

    ui.stock_kpis(
        k,
        selected_date,
        previous_date.strftime("%d %b") if previous_date else "",
        dataset.group_label,
    )

    if today.empty:
        ui.empty_state(
            "No stock rows match this filter. Change the date or clear a "
            "product / item / plant / warehouse filter."
        )
        return

    dimensions = [
        (dataset.group_label, "Group"),
        ("Item Name", "Item"),
    ]
    if dataset.plants:
        dimensions.append(("Plant", "Plant"))
    dimensions.append(("Warehouse", "Warehouse"))

    tab_labels = [label for label, _ in dimensions] + ["Overall table"]
    tabs = st.tabs(tab_labels)

    for tab, (label, dimension) in zip(tabs[:-1], dimensions):
        with tab:
            summary = stock.stock_summary(today, dimension)
            if summary.empty:
                ui.empty_state("No rows for this dimension.")
                continue

            top = 3 if dimension in {"Group", "Plant"} else 5
            left, right = st.columns(2, gap="small")
            with left:
                st.plotly_chart(
                    charts.stock_bar(
                        summary,
                        dimension,
                        "Quantity",
                        title=f"{label} · quantity",
                        unit=dataset.unit,
                        color="#4f8cff",
                        label_formatter=ui.fmt_qty,
                        top=top,
                    ),
                    width="stretch",
                    config={"displayModeBar": False},
                    key=f"{cfg.key}_bar_q_{dimension}",
                )
            with right:
                st.plotly_chart(
                    charts.stock_bar(
                        summary,
                        dimension,
                        "Value",
                        title=f"{label} · value",
                        unit="BDT",
                        color="#22d3ee",
                        label_formatter=ui.fmt_bdt,
                        top=top,
                    ),
                    width="stretch",
                    config={"displayModeBar": False},
                    key=f"{cfg.key}_bar_v_{dimension}",
                )

            ui.stock_table(summary, dimension, label, dataset.unit)

    with tabs[-1]:
        detail = stock.stock_detail(today, dataset.group_label)
        ui.stock_overall_table(detail, dataset.group_label, dataset.unit)
        st.download_button(
            "Download stock table (CSV)",
            data=detail.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"{cfg.key}_{selected_date.strftime('%Y-%m-%d')}.csv",
            mime="text/csv",
            key=f"{cfg.key}_download",
        )

    ui.footer(cfg, meta)


def render(cfg: config.SheetConfig) -> None:
    st.session_state["_current_sheet"] = cfg.key

    @st.fragment(run_every=config.AUTO_REFRESH_SECONDS)
    def body() -> None:
        _render_body(cfg)

    body()
