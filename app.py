"""AEL Trading · Khatunganj Competitor Local Price dashboard.

Run locally:
    streamlit run app.py

Pages are generated from config.SHEETS, so adding a new sheet is a one-line
change in config.py.
"""

from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="AEL · Competitor Local Price",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

import config  # noqa: E402
from core import source, ui  # noqa: E402
from views import competitor  # noqa: E402


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

navigation = st.navigation(pages, position="sidebar")
navigation.run()

status = st.session_state.get("_status")
with st.sidebar:
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    if status:
        dot = "#27c281" if status["live"] else "#f5a623"
        label = "Live sheet" if status["live"] else "Snapshot"
        st.markdown(
            f"""
            <div class="sb-block">
              <div class="sb-title">{status['label']} data source</div>
              <div class="sb-row"><span>Status</span><span style="color:{dot};font-weight:700">{label}</span></div>
              <div class="sb-row"><span>Tab</span><span>{status.get('tab','—')}</span></div>
              <div class="sb-row"><span>Latest row</span><span style="color:{'#f5a623' if status.get('stale') else '#cbd5e1'};font-weight:600">{status.get('latest_label','—')}</span></div>
              <div class="sb-row"><span>Quotes</span><span>{status['rows']:,}</span></div>
              <div class="sb-row"><span>Products</span><span>{status['products']}</span></div>
              <div class="sb-row"><span>Competitors</span><span>{status['competitors']}</span></div>
              <div class="sb-row"><span>Unit</span><span>{status['unit']}</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if status.get("stale") and status["live"]:
            st.markdown(
                f"<div class='sb-note'>The connected tab is {status['age_days']} days "
                "behind. If you added newer rows in another tab or Google Sheet, this "
                "page cannot see them.</div>",
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
        st.rerun()

    if status:
        st.markdown(
            f"<div style='font-size:10.5px;color:#7d93b3;margin-top:8px'>"
            f"<a href='{status['url']}' target='_blank' style='color:#7fb0ff;text-decoration:none'>"
            "Open the source Google Sheet ↗</a></div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        "<div style='font-size:10px;color:#5f7695;line-height:1.5;margin-top:14px'>"
        "Sheet cached for 30 sec · page refreshes every 1 min."
        "</div>",
        unsafe_allow_html=True,
    )
