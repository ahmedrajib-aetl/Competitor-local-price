"""AEL Trading · Market & Stock dashboard (V2).

V1 price pages remain exactly as before; stock pages are additive.

Run locally:
    streamlit run app.py
"""

from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="AEL · Market & Stock",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

import config  # noqa: E402
from core import source, ui  # noqa: E402
from views import competitor, stock as stock_view  # noqa: E402


ui.inject_css()

with st.sidebar:
    st.markdown(
        """
        <div class="sb-brand">
          <div class="sb-logo">AEL</div>
          <div>
            <div class="sb-name">Competitor Price</div>
            <div class="sb-sub">Khatunganj · daily</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

pages = [
    st.Page(
        lambda sheet=sheet: competitor.render(sheet),
        title=sheet.label,
        icon=sheet.icon,
        url_path=sheet.key,
        default=(index == 0),
    )
    for index, sheet in enumerate(config.SHEETS)
]
pages += [
    st.Page(
        lambda sheet=sheet: stock_view.render(sheet),
        title=sheet.label,
        icon=sheet.icon,
        url_path=sheet.key.replace("_", "-"),
        default=False,
    )
    for sheet in config.STOCKS
]

navigation = st.navigation(pages, position="sidebar")
navigation.run()

status = st.session_state.get("_status")
with st.sidebar:
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    if status:
        dot = "#27c281" if status["live"] else "#f5a623"
        label = "Live" if status["live"] else "Snapshot"
        if status.get("mode") == "stock":
            row_label = "Rows"
            metric_rows = (
                f"<div class='sb-row'><span>Selected date</span><span>{status.get('selected_label','—')}</span></div>"
                f"<div class='sb-row'><span>Rows shown</span><span>{status.get('rows_shown', 0)}</span></div>"
                f"<div class='sb-row'><span>Dates stored</span><span>{status.get('dates_stored', 0)}</span></div>"
                f"<div class='sb-row'><span>Items</span><span>{status.get('items', 0)}</span></div>"
                f"<div class='sb-row'><span>Warehouses</span><span>{status.get('warehouses', 0)}</span></div>"
                f"<div class='sb-row'><span>Plants</span><span>{status.get('plants', 0)}</span></div>"
            )
        elif status.get("mode") == "long":
            row_label = "Rows"
            metric_rows = (
                f"<div class='sb-row'><span>Locations</span><span>{status.get('locations', 0)}</span></div>"
                f"<div class='sb-row'><span>Origins</span><span>{status.get('origins', 0)}</span></div>"
                f"<div class='sb-row'><span>Mines</span><span>{status.get('mines', 0)}</span></div>"
                f"<div class='sb-row'><span>Importers</span><span>{status.get('importers', 0)}</span></div>"
            )
        else:
            row_label = "Quotes"
            metric_rows = (
                f"<div class='sb-row'><span>Products</span><span>{status['products']}</span></div>"
                f"<div class='sb-row'><span>Competitors</span><span>{status['competitors']}</span></div>"
            )
        st.markdown(
            f"""
            <div class="sb-block">
              <div class="sb-title">{status['label']} data source</div>
              <div class="sb-row"><span>Status</span><span style="color:{dot};font-weight:700">{label}</span></div>
              <div class="sb-row"><span>Tab</span><span>{status.get('tab','—')}</span></div>
              <div class="sb-row"><span>Latest row</span><span style="color:{'#f5a623' if status.get('stale') else '#cbd5e1'};font-weight:600">{status.get('latest_label','—')}</span></div>
              <div class="sb-row"><span>{row_label}</span><span>{status['rows']:,}</span></div>
              {metric_rows}
              <div class="sb-row"><span>Unit</span><span>{status['unit']}</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if status.get("stale") and status["live"]:
            if status.get("mode") == "stock":
                stale_note = (
                    f"The newest date in the Master Data is "
                    f"{status.get('latest_label','—')} ({status.get('age_days', 0)} "
                    "days ago). Update the sheet to show today's position."
                )
            else:
                stale_note = (
                    f"The connected tab is {status['age_days']} days behind. If you "
                    "added newer rows in another tab or file, this page cannot see them."
                )
            st.markdown(
                f"<div class='sb-note'>{stale_note}</div>",
                unsafe_allow_html=True,
            )
        if status.get("collapsed"):
            st.markdown(
                f"<div class='sb-note' style='color:#8fa3bf'>Data check: "
                f"{status['collapsed']} duplicate quote(s) collapsed — the bottom-most "
                "entry in the sheet wins for the same competitor/date.</div>",
                unsafe_allow_html=True,
            )
        if not status["live"] and status.get("note"):
            st.markdown(
                f"<div class='sb-note'>{status['note']}</div>",
                unsafe_allow_html=True,
            )
    else:
        st.caption("No data loaded yet.")

    if st.button("Refresh now", type="primary", width="stretch", key="sb_refresh"):
        source.clear_cache()
        st.rerun()

    if st.button("Reset filters", width="stretch", key="sb_reset"):
        current = st.session_state.get("_current_sheet")
        if current:
            for key in list(st.session_state.keys()):
                if key.startswith(f"{current}_"):
                    del st.session_state[key]
            if status and status.get("mode") == "stock":
                st.session_state[f"{current}_date"] = status.get("latest_label")
                st.session_state[f"{current}_search"] = ""
                st.session_state[f"{current}_group"] = []
                st.session_state[f"{current}_item"] = []
                st.session_state[f"{current}_plant"] = []
                st.session_state[f"{current}_warehouse"] = []
        st.rerun()

    if status:
        st.markdown(
            f"<div style='font-size:10.5px;color:#7d93b3;margin-top:8px'>"
            f"<a href='{status['url']}' target='_blank' style='color:#7fb0ff;text-decoration:none'>"
            "Open the source file ↗</a></div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        "<div style='font-size:10px;color:#5f7695;line-height:1.5;margin-top:14px'>"
        "Source cached for 1 hour · page auto-refreshes every 1 hour."
        "</div>",
        unsafe_allow_html=True,
    )
