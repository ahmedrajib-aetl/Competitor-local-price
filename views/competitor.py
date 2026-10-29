"""The shared competitor-price page used by every sheet in config.SHEETS."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

import config
from core import charts, source, transform, ui


def _init_state(cfg: config.SheetConfig, dataset: transform.Dataset) -> None:
    product_key = f"{cfg.key}_product"
    category_key = f"{cfg.key}_category"

    if product_key not in st.session_state:
        if cfg.product_pills:
            st.session_state[product_key] = "All"
        else:
            st.session_state[product_key] = [transform.top_product(dataset)]
    elif cfg.product_pills and not isinstance(st.session_state[product_key], str):
        st.session_state[product_key] = "All"
    elif not cfg.product_pills:
        current = st.session_state.get(product_key) or []
        if isinstance(current, str):
            current = [current]
        st.session_state[product_key] = [
            product for product in current if product in dataset.products
        ]

    if len(dataset.categories) > 1:
        if category_key not in st.session_state or not isinstance(
            st.session_state[category_key], str
        ):
            st.session_state[category_key] = "All"


def _date_filter(cfg: config.SheetConfig, dataset: transform.Dataset) -> list[date]:
    """A single searchable dropdown: all dates, recent windows, latest, or a month."""
    all_dates = sorted({ts.date() for ts in dataset.long["Date"].unique()})
    latest = all_dates[-1]

    month_lookup: dict[str, tuple[int, int]] = {}
    for day in all_dates:
        month_lookup[day.strftime("%b %Y")] = (day.year, day.month)
    month_labels = sorted(
        month_lookup,
        key=lambda label: (month_lookup[label][0], month_lookup[label][1]),
        reverse=True,
    )

    options = [
        "All dates",
        "Last 7 days",
        "Last 30 days",
        "Last 90 days",
        "Latest date",
        *month_labels,
    ]

    choice_key = f"{cfg.key}_date_choice"
    if choice_key in st.session_state and st.session_state[choice_key] not in options:
        st.session_state[choice_key] = "All dates"

    choice = st.selectbox(
        "Date",
        options,
        index=0,
        key=choice_key,
        help="Pick the full history, a recent window, the latest report, or one month.",
    )

    if choice == "All dates":
        return all_dates
    if choice == "Latest date":
        return [latest]
    if choice.startswith("Last "):
        days = int(choice.split()[1])
        cutoff = latest - timedelta(days=days - 1)
        return [day for day in all_dates if cutoff <= day <= latest]

    year, month = month_lookup[choice]
    return [day for day in all_dates if day.year == year and day.month == month]


def _filters(
    cfg: config.SheetConfig,
    dataset: transform.Dataset,
) -> tuple[pd.DataFrame, dict]:
    product_key = f"{cfg.key}_product"
    origin_key = f"{cfg.key}_origin"
    category_key = f"{cfg.key}_category"
    competitor_key = f"{cfg.key}_competitor"

    with st.container(border=True):
        st.markdown(
            "<div class='filter-title'>Filters</div>"
            "<div class='filter-help'>Leave a dropdown empty to mean <b>All</b>. "
            "Every dropdown is searchable — type to filter its list.</div>",
            unsafe_allow_html=True,
        )

        if cfg.product_pills:
            search = st.text_input(
                "Search product",
                key=f"{cfg.key}_product_search",
                placeholder="Type to search, then press Enter…",
                label_visibility="collapsed",
            )
            needle = search.strip().casefold()
            options = [p for p in dataset.products if needle in p.casefold()] if needle else dataset.products
            if not options:
                options = dataset.products

            current = st.session_state.get(product_key)
            pill_options = ["All", *options]
            if current and current not in pill_options:
                pill_options.insert(1, current)

            selection = st.pills(
                "Product",
                pill_options,
                selection_mode="single",
                key=product_key,
            )
            selected_products = None if selection in (None, "All") else [selection]
        else:
            selected_products = st.multiselect(
                "Product",
                dataset.products,
                key=product_key,
                placeholder="All products",
            ) or None

        c1, c2, c3, c4 = st.columns([0.9, 1.0, 1.2, 1.3], gap="small")
        with c1:
            selected_origins = st.multiselect(
                "Origin",
                dataset.origins,
                key=origin_key,
                placeholder="All origins",
            )
        with c2:
            if len(dataset.categories) > 1:
                category_choice = st.pills(
                    "Price category",
                    ["All", *dataset.categories],
                    selection_mode="single",
                    key=category_key,
                )
                selected_categories = (
                    None if category_choice in (None, "All") else [category_choice]
                )
            else:
                selected_categories = []
                st.markdown(
                    f"<div style='font-size:9.5px;letter-spacing:.11em;text-transform:uppercase;"
                    f"color:#8fa3bf;font-weight:700;margin:2px 0 8px'>Price category</div>"
                    f"<div style='font-size:12.5px;color:#cbd5e1;padding:9px 11px;"
                    f"border:1px solid rgba(148,163,184,.16);border-radius:10px;"
                    f"background:#0b1628'>{dataset.categories[0]}</div>",
                    unsafe_allow_html=True,
                )
        with c3:
            selected_competitors = st.multiselect(
                "Competitor",
                dataset.competitors,
                key=competitor_key,
                placeholder="All competitors",
            )
        with c4:
            dates = _date_filter(cfg, dataset)

    frame = transform.apply_filters(
        dataset,
        dates=dates,
        products=selected_products,
        origins=selected_origins or None,
        categories=selected_categories or None,
        competitors=selected_competitors or None,
    )
    context = {
        "products": selected_products or dataset.products,
        "origins": selected_origins or dataset.origins,
        "categories": selected_categories or dataset.categories,
        "competitors": selected_competitors or dataset.competitors,
        "dates": dates,
    }
    return frame, context


def _download_button(label: str, frame: pd.DataFrame, filename: str, key: str) -> None:
    st.download_button(
        label,
        data=frame.to_csv(index=False).encode("utf-8-sig"),
        file_name=filename,
        mime="text/csv",
        key=key,
    )


def _render_body(cfg: config.SheetConfig) -> None:
    try:
        raw, meta = source.load_sheet(
            cfg.key, nonce=st.session_state.get(f"{cfg.key}_nonce", 0)
        )
    except Exception as exc:
        st.error(f"Could not load the {cfg.label} data source: {exc}")
        st.caption(
            "Check the Google Sheet sharing settings, or make sure the snapshot "
            "file exists in the data folder."
        )
        return

    try:
        dataset = transform.prepare(raw, cfg)
    except Exception as exc:
        st.error(f"Could not read this sheet: {exc}")
        st.caption(
            "Check that the tab still has Date, Product, Origin and Price Category "
            "columns, and that at least one competitor column contains prices."
        )
        return

    ui.header(cfg, meta, dataset, source.age_label(meta["fetched_at"]))

    latest_date = dataset.long["Date"].max().date()
    age_days = max(0, (date.today() - latest_date).days)
    tab_label = cfg.tab_name or "first tab"

    source_col, refresh_col = st.columns([5, 1.2], vertical_alignment="center")
    with source_col:
        st.caption(
            f"Reading **{tab_label}** · newest row **{latest_date:%d %b %Y}** · "
            f"fetched {source.age_label(meta['fetched_at'])}"
        )
    with refresh_col:
        if st.button(
            "Refresh now",
            type="primary",
            width="stretch",
            key=f"{cfg.key}_refresh_now",
            help="Ignore the cache and download the sheet again.",
        ):
            source.clear_cache()
            st.rerun(scope="app")

    if not meta.get("live"):
        error_text = str(meta.get("error", "")).lower()
        if "401" in error_text or "sign-in" in error_text:
            reason = (
                "Google returned HTTP 401 because this Google Sheet is private. "
                "Updates you make in the sheet will <b>not</b> appear here until it "
                "is shared as <b>Anyone with the link · Viewer</b> (or a service "
                "account is added)."
            )
        else:
            reason = meta.get("note", "")
        st.markdown(
            f"<div class='banner'><b>Snapshot mode.</b> Showing data through "
            f"<b>{latest_date:%d %b %Y}</b> ({age_days} days old). "
            f"{reason} "
            f"<a href='{cfg.sheet_url}' target='_blank' style='color:#ffd08a'>"
            "Open the sheet ↗</a></div>",
            unsafe_allow_html=True,
        )
    elif age_days > config.STALE_AFTER_DAYS:
        st.markdown(
            f"<div class='banner'><b>The connected tab is {age_days} days behind.</b> "
            f"No row newer than <b>{latest_date:%d %b %Y}</b> was found in "
            f"<b>{tab_label}</b>. The dashboard is reading this tab live — if you "
            "added newer rows, they are in a different tab or Google Sheet. "
            f"<a href='{cfg.sheet_url}' target='_blank' style='color:#ffd08a'>"
            "Open the connected sheet ↗</a></div>",
            unsafe_allow_html=True,
        )

    _init_state(cfg, dataset)
    frame, context = _filters(cfg, dataset)

    st.session_state["_status"] = {
        "key": cfg.key,
        "label": cfg.label,
        "live": bool(meta.get("live")),
        "source": meta.get("source", ""),
        "note": meta.get("note", ""),
        "fetched_at": meta.get("fetched_at"),
        "rows": len(dataset.long),
        "source_quotes": dataset.source_quotes,
        "collapsed": dataset.duplicates_collapsed,
        "products": len(dataset.products),
        "latest": latest_date.isoformat(),
        "latest_label": latest_date.strftime("%d %b %Y"),
        "age_days": age_days,
        "stale": age_days > config.STALE_AFTER_DAYS,
        "tab": tab_label,
        "competitors": len(dataset.competitors),
        "unit": cfg.unit,
        "url": cfg.sheet_url,
    }

    if frame.empty:
        ui.empty_state(
            "No prices match this filter. Widen the date range, pick another "
            "product/origin, or clear the competitor selection."
        )
        return

    stats = transform.kpis(frame)
    ui.kpi_cards(stats, dataset.unit)

    present_products = set(frame["Product"])
    selected_products = [
        product for product in dataset.products if product in present_products
    ]
    selected_origins = sorted(frame["Origin"].unique().tolist())
    selected_categories = sorted(frame["Category"].unique().tolist())

    if len(selected_products) > 1:
        scope = "All products"
    else:
        scope = selected_products[0]
    if len(selected_origins) == 1:
        scope += f" · {selected_origins[0]}"
    if len(selected_categories) == 1:
        scope += f" · {selected_categories[0]}"

    title_col, option_col = st.columns([4.2, 1], vertical_alignment="bottom")
    with title_col:
        ui.section(
            "Day-wise competitor price",
            f"{scope} · one line per competitor. The heavy line is {cfg.own_brand}; "
            "the grey dashed line is the market average.",
            hint="Click a legend item to hide/show · double-click to isolate",
        )
    with option_col:
        with st.popover("Chart options", width="stretch"):
            show_average = st.checkbox("Market average line", value=True, key=f"{cfg.key}_avg")
            markers = st.checkbox("Show data points", value=True, key=f"{cfg.key}_markers")

    figure = charts.price_trend(
        frame,
        competitors=[c for c in dataset.competitors if c in set(frame["Competitor"])],
        unit=dataset.unit,
        own_brand=cfg.own_brand,
        show_average=show_average,
        markers=markers,
    )
    st.plotly_chart(
        figure,
        width="stretch",
        config={
            "displaylogo": False,
            "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"],
        },
        key=f"{cfg.key}_trend",
    )

    if (
        len(selected_products) > 1
        or len(selected_origins) > 1
        or len(selected_categories) > 1
    ):
        st.caption(
            "One chart, one line per competitor. With several products, origins or "
            "price categories selected, each point is that competitor's average for "
            "the selected quotes — hover a point to see the product, quote count and "
            "source. Pick one product for an exact product-wise line."
        )

    quotes = transform.latest_quotes(frame)
    section_left, section_right = st.columns([4.2, 1], vertical_alignment="bottom")
    with section_left:
        ui.section(
            "Latest quotes",
            f"Competitors that quoted on {stats['latest'].strftime('%d %b %Y')}, "
            "cheapest first within each product / price category, with their own "
            "previous quote for comparison.",
        )
    with section_right:
        if not quotes.empty:
            _download_button(
                "Download latest",
                quotes,
                f"{cfg.key}_latest_{stats['latest'].date()}.csv",
                key=f"{cfg.key}_dl_latest",
            )
    ui.quote_table(quotes, dataset.unit)

    detail = transform.detail_rows(frame)
    matrix = transform.matrix(frame)

    with st.expander("Detailed data · day × competitor matrix and all rows"):
        st.markdown("**Day × competitor price matrix**")
        if matrix.empty:
            ui.empty_state("No rows for this filter.")
        else:
            matrix_view = matrix.copy()
            matrix_view["Date"] = pd.to_datetime(matrix_view["Date"]).dt.strftime("%Y-%m-%d")
            number_columns = {
                column: st.column_config.NumberColumn(format="%.0f")
                for column in matrix_view.columns
                if column in dataset.competitors
            }
            st.dataframe(
                matrix_view,
                width="stretch",
                hide_index=True,
                height=min(520, 120 + 35 * len(matrix_view)),
                column_config=number_columns,
            )
            _download_button(
                "Download matrix (CSV)",
                matrix_view,
                f"{cfg.key}_matrix_{stats['latest'].date()}.csv",
                key=f"{cfg.key}_dl_matrix",
            )

        st.markdown("**Every price behind the chart**")
        st.dataframe(
            detail,
            width="stretch",
            hide_index=True,
            height=380,
            column_config={
                "Price": st.column_config.NumberColumn(format="%.0f"),
            },
        )
        _download_button(
            "Download filtered rows (CSV)",
            detail,
            f"{cfg.key}_rows_{stats['latest'].date()}.csv",
            key=f"{cfg.key}_dl_rows",
        )

    ui.footer(cfg, meta)


def render(cfg: config.SheetConfig) -> None:
    st.session_state["_current_sheet"] = cfg.key

    @st.fragment(run_every=config.AUTO_REFRESH_SECONDS)
    def body() -> None:
        _render_body(cfg)

    body()
