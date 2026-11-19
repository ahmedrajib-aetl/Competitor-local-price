"""The shared competitor-price page used by every sheet in config.SHEETS."""

from __future__ import annotations

import html
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


def _top(cfg: config.SheetConfig, meta: dict, dataset) -> tuple[date, int, str]:
    """Header, source status and freshness warnings shared by both modes."""
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
            help="Ignore the cache and download the source again.",
        ):
            source.clear_cache()
            st.rerun(scope="app")

    if not meta.get("live"):
        error_text = str(meta.get("error", "")).lower()
        if "401" in error_text or "sign-in" in error_text:
            reason = (
                "The source is private, so updates you make there will <b>not</b> "
                "appear here until it is shared as <b>Anyone with the link · "
                "Viewer</b> (or a service account is added)."
            )
        else:
            reason = meta.get("note", "")
        st.markdown(
            f"<div class='banner'><b>Snapshot mode.</b> Showing data through "
            f"<b>{latest_date:%d %b %Y}</b> ({age_days} days old). "
            f"{reason} "
            f"<a href='{cfg.sheet_url}' target='_blank' style='color:#ffd08a'>"
            "Open the source ↗</a></div>",
            unsafe_allow_html=True,
        )
    elif age_days > config.STALE_AFTER_DAYS:
        st.markdown(
            f"<div class='banner'><b>The connected tab is {age_days} days behind.</b> "
            f"No row newer than <b>{latest_date:%d %b %Y}</b> was found in "
            f"<b>{tab_label}</b>. The dashboard is reading it live — if you added "
            "newer rows, they are in a different tab or file. "
            f"<a href='{cfg.sheet_url}' target='_blank' style='color:#ffd08a'>"
            "Open the connected source ↗</a></div>",
            unsafe_allow_html=True,
        )

    return latest_date, age_days, tab_label


def _render_body(cfg: config.SheetConfig) -> None:
    try:
        raw, meta = source.load_sheet(
            cfg.key, nonce=st.session_state.get(f"{cfg.key}_nonce", 0)
        )
    except Exception as exc:
        st.error(f"Could not load the {cfg.label} data source: {exc}")
        st.caption(
            "Check the source sharing settings, or make sure the snapshot "
            "file exists in the data folder."
        )
        return

    if cfg.mode == "long":
        _render_long(cfg, raw, meta)
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

    latest_date, age_days, tab_label = _top(cfg, meta, dataset)

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
            hint="Names are at the line ends · hover a line for product-wise prices",
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
        product_order=dataset.products,
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
            "the selected quotes — hover a point to see every product/origin price "
            "behind it. Pick one product for an exact product-wise line."
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



# ===================================================================== long mode
def _filters_long(
    cfg: config.SheetConfig,
    dataset: transform.LongDataset,
) -> tuple[pd.DataFrame, dict]:
    location_key = f"{cfg.key}_location"
    importer_key = f"{cfg.key}_importer"
    origin_key = f"{cfg.key}_origin"
    mine_key = f"{cfg.key}_mine"
    remarks_key = f"{cfg.key}_remarks"

    with st.container(border=True):
        st.markdown(
            "<div class='filter-title'>Filters</div>"
            "<div class='filter-help'>Leave a dropdown empty to mean <b>All</b>. "
            "Every dropdown is searchable — type to filter its list.</div>",
            unsafe_allow_html=True,
        )

        c1, c2, c3 = st.columns(3, gap="small")
        with c1:
            locations = st.multiselect(
                "Location", dataset.locations, key=location_key,
                placeholder="All locations",
            )
        with c2:
            competitors = st.multiselect(
                "Importers / Traders", dataset.competitors, key=importer_key,
                placeholder="All importers / traders",
            )
        with c3:
            origins = st.multiselect(
                "Origin", dataset.origins, key=origin_key,
                placeholder="All origins",
            )

        c4, c5, c6 = st.columns(3, gap="small")
        with c4:
            mines = st.multiselect(
                "Mine", dataset.mines, key=mine_key,
                placeholder="All mines",
            )
        with c5:
            remarks = st.multiselect(
                "Remarks", dataset.remarks, key=remarks_key,
                placeholder="All remarks",
            )
        with c6:
            dates = _date_filter(cfg, dataset)

    frame = transform.filter_long(
        dataset,
        dates=dates,
        locations=locations or None,
        competitors=competitors or None,
        origins=origins or None,
        mines=mines or None,
        remarks=remarks or None,
    )
    context = {
        "locations": locations,
        "competitors": competitors,
        "origins": origins,
        "mines": mines,
        "remarks": remarks,
        "dates": dates,
    }
    return frame, context


def _long_hover(day: pd.DataFrame) -> str:
    """Origin + mine/grade + rate for one importer on one date."""
    rows = (
        day.groupby(["Origin", "Mine", "Grade"], dropna=False)
        .agg(Price=("Price", "mean"), Quantity=("Quantity", "sum"))
        .reset_index()
    )
    rows["Origin"] = rows["Origin"].replace("", "Unknown")
    rows["Mine"] = rows["Mine"].fillna("").astype(str).str.strip()
    rows["Grade"] = rows["Grade"].fillna("").astype(str).str.strip()
    rows = rows.sort_values(
        ["Origin", "Mine", "Grade"],
        key=lambda series: series.astype(str).str.casefold(),
    )

    lines = []
    for _, row in rows.iterrows():
        if pd.isna(row["Price"]):
            continue
        parts = [str(row["Origin"] or "Unknown")]
        mine = str(row["Mine"] or "").strip()
        grade = str(row["Grade"] or "").strip()
        if mine:
            parts.append(mine)
        elif grade:
            parts.append(grade)
        label = " · ".join(html.escape(part) for part in parts if part)
        lines.append(f"{label} — Rate: <b>{row['Price']:,.0f}</b>")
    return "<br>".join(lines)


def _render_long(
    cfg: config.SheetConfig,
    raw: pd.DataFrame,
    meta: dict,
) -> None:
    try:
        dataset = transform.prepare_long(raw, cfg)
    except Exception as exc:
        st.error(f"Could not read the Master Database: {exc}")
        st.caption(
            "Check that the Master Database tab still has Date, Importers / Traders, "
            "Origin, Mine, Quantity (MT) and Sale / Retail Rate (BDT/MT) columns."
        )
        return

    latest_date, age_days, tab_label = _top(cfg, meta, dataset)
    frame, context = _filters_long(cfg, dataset)

    st.session_state["_status"] = {
        "mode": "long",
        "key": cfg.key,
        "label": cfg.label,
        "live": bool(meta.get("live")),
        "source": meta.get("source", ""),
        "note": meta.get("note", ""),
        "fetched_at": meta.get("fetched_at"),
        "rows": len(dataset.long),
        "source_quotes": dataset.source_quotes,
        "collapsed": 0,
        "products": 0,
        "competitors": len(dataset.competitors),
        "importers": len(dataset.competitors),
        "locations": len(dataset.locations),
        "origins": len(dataset.origins),
        "mines": len(dataset.mines),
        "unit": cfg.unit,
        "url": cfg.sheet_url,
        "tab": tab_label,
        "latest": latest_date.isoformat(),
        "latest_label": latest_date.strftime("%d %b %Y"),
        "age_days": age_days,
        "stale": age_days > config.STALE_AFTER_DAYS,
    }

    if frame.empty:
        ui.empty_state(
            "No rows match this filter. Widen the date range or clear a location, "
            "importer, origin, mine or remarks filter."
        )
        return

    summary, summary_date, total = transform.long_summary(frame)
    if summary.empty:
        ui.empty_state("No rows on the latest date for this filter.")
        return

    # ---------------------------------------------------------- origin summary
    summary_view = summary.copy()
    summary_view.insert(1, "Date", summary_date)
    total_row = pd.DataFrame(
        [{
            "Origin": "Grand Total",
            "Date": summary_date,
            "Quantity": total.get("Quantity"),
            "AverageRate": total.get("AverageRate"),
            "Lines": total.get("Lines"),
        }]
    )
    summary_view = pd.concat([summary_view, total_row], ignore_index=True)

    summary_download = summary_view[["Origin", "Date", "Quantity", "AverageRate"]].copy()
    summary_download["Date"] = pd.to_datetime(summary_download["Date"]).dt.strftime("%d-%b-%Y")
    summary_download = summary_download.rename(
        columns={
            "Origin": "Country of Origin",
            "Quantity": "Dumping Quantity (MT)",
            "AverageRate": "Average Sale / Retail Rate (BDT/MT)",
        }
    )

    summary_left, summary_right = st.columns([4.2, 1], vertical_alignment="bottom")
    with summary_left:
        ui.section(
            "Latest date — origin summary",
            f"{summary_date:%d-%b-%Y} · dumping quantity and average sale rate",
            hint="Latest date only · follows every filter",
        )
    with summary_right:
        st.download_button(
            "Download summary",
            data=summary_download.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"{cfg.key}_summary_{summary_date.strftime('%Y-%m-%d')}.csv",
            mime="text/csv",
            key=f"{cfg.key}_dl_summary",
        )
    ui.origin_summary_table(summary, total, summary_date, dataset.unit)

    # ------------------------------------------------------------------- chart
    chart_frame = frame[frame["Price"].notna()].copy()
    if chart_frame.empty:
        ui.empty_state("No sale rates in this filter — quantity rows exist but no rate.")
    else:
        if len(context["locations"]) == 1:
            scope_bits = [context["locations"][0]]
        elif len(context["locations"]) > 1:
            scope_bits = [f"{len(context['locations'])} locations"]
        else:
            scope_bits = ["All locations"]

        if len(context["origins"]) == 1:
            scope_bits.append(context["origins"][0])
        elif len(context["origins"]) > 1:
            scope_bits.append(f"{len(context['origins'])} origins")

        if len(context["mines"]) == 1:
            scope_bits.append(context["mines"][0])
        if len(context["remarks"]) == 1:
            scope_bits.append(context["remarks"][0])
        scope = " · ".join(scope_bits)

        title_col, option_col = st.columns([4.2, 1], vertical_alignment="bottom")
        with title_col:
            ui.section(
                "Day-wise sale rate",
                f"{scope} · one line per importer / trader. Hover a line for "
                "origin & mine rates.",
                hint="Names are at the line ends · hover for origin/mine prices",
            )
        with option_col:
            with st.popover("Chart options", width="stretch"):
                show_average = st.checkbox(
                    "Market average line", value=True, key=f"{cfg.key}_avg"
                )
                markers = st.checkbox(
                    "Show data points", value=True, key=f"{cfg.key}_markers"
                )
                trim_outliers = st.checkbox(
                    "Trim extreme outliers",
                    value=True,
                    key=f"{cfg.key}_trim",
                    help="Keeps the chart readable. Summary and tables still include "
                    "every row.",
                )

        removed = 0
        if trim_outliers and len(chart_frame) > 8:
            q05, q95 = chart_frame["Price"].quantile([0.05, 0.95])
            lower, upper = q05 * 0.5, q95 * 1.25
            keep = chart_frame["Price"].between(lower, upper)
            removed = int((~keep).sum())
            chart_frame = chart_frame[keep].copy()

        if chart_frame.empty:
            ui.empty_state("No sale rates in the normal price range for this filter.")
        else:
            competitors = [
                name for name in dataset.competitors
                if name in set(chart_frame["Competitor"])
            ]
            figure = charts.price_trend(
                chart_frame,
                competitors=competitors,
                unit=dataset.unit,
                own_brand=cfg.own_brand,
                show_average=show_average,
                markers=markers,
                hover_builder=_long_hover,
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
            if chart_frame.groupby(["Date", "Competitor"]).size().max() > 1:
                st.caption(
                    "Each point is the importer's average rate for the selected rows; "
                    "hover the line to see every origin / mine rate behind it."
                )
            if removed:
                st.caption(
                    f"Chart excludes {removed} extreme quote(s) outside the normal "
                    "price range. The summary and tables above still include every "
                    "row. Untick “Trim extreme outliers” to see them."
                )

    # ---------------------------------------------------------- latest quotes
    quotes = transform.latest_long_quotes(frame)
    quote_left, quote_right = st.columns([4.2, 1], vertical_alignment="bottom")
    with quote_left:
        ui.section(
            "Latest quotes",
            "Importers / traders that quoted on "
            f"{summary_date.strftime('%d %b %Y')}, cheapest first.",
        )
    with quote_right:
        if not quotes.empty:
            _download_button(
                "Download latest",
                quotes,
                f"{cfg.key}_latest_{summary_date.strftime('%Y-%m-%d')}.csv",
                key=f"{cfg.key}_dl_latest",
            )
    ui.quote_table(quotes, dataset.unit, name_header="Importer / Trader")

    # --------------------------------------------------------------- details
    matrix = transform.long_matrix(frame)
    detail = transform.long_detail(frame)

    with st.expander("Detailed data · day × importer matrix and all rows"):
        st.markdown("**Day × importer average sale rate**")
        if matrix.empty:
            ui.empty_state("No rates for this filter.")
        else:
            matrix_view = matrix.copy()
            matrix_view["Date"] = pd.to_datetime(matrix_view["Date"]).dt.strftime("%Y-%m-%d")
            number_columns = {
                column: st.column_config.NumberColumn(format="%.0f")
                for column in matrix_view.columns
                if column != "Date"
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
                f"{cfg.key}_matrix_{summary_date.strftime('%Y-%m-%d')}.csv",
                key=f"{cfg.key}_dl_matrix",
            )

        st.markdown("**Every row behind the chart**")
        st.dataframe(
            detail,
            width="stretch",
            hide_index=True,
            height=400,
            column_config={
                "Quantity (MT)": st.column_config.NumberColumn(format="%.0f"),
                "Sale / Retail Rate (BDT/MT)": st.column_config.NumberColumn(format="%.0f"),
            },
        )
        _download_button(
            "Download filtered rows (CSV)",
            detail,
            f"{cfg.key}_rows_{summary_date.strftime('%Y-%m-%d')}.csv",
            key=f"{cfg.key}_dl_rows",
        )

    ui.footer(cfg, meta)


def render(cfg: config.SheetConfig) -> None:
    st.session_state["_current_sheet"] = cfg.key

    @st.fragment(run_every=config.AUTO_REFRESH_SECONDS)
    def body() -> None:
        _render_body(cfg)

    body()
