"""Shared visual language: CSS, page header, KPI cards and tables."""

from __future__ import annotations

import html
from datetime import datetime

import pandas as pd
import streamlit as st

import config


CSS = """
<style>
:root {
  --cph-bg: #0a1220;
  --cph-panel: #101b2d;
  --cph-panel-2: #0d1728;
  --cph-line: rgba(148, 163, 184, .16);
  --cph-text: #e6edf7;
  --cph-muted: #8fa3bf;
  --cph-accent: #4f8cff;
  --cph-good: #27c281;
  --cph-bad: #f0516d;
  --cph-warn: #f5a623;
}

html, body, [class*="css"] {
  font-family: Inter, "Segoe UI", system-ui, -apple-system, sans-serif;
}
.stApp {
  background:
    radial-gradient(1100px 520px at 18% -12%, rgba(79,140,255,.11), transparent 58%),
    radial-gradient(900px 480px at 100% 0%, rgba(39,194,129,.06), transparent 55%),
    var(--cph-bg);
}
.block-container { padding-top: 1.15rem; padding-bottom: 3rem; max-width: 1560px; }
header[data-testid="stHeader"] { background: transparent; }
#MainMenu, footer { visibility: hidden; }

/* ------------------------------------------------------------- side bar */
section[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0c1729 0%, #0a1322 100%);
  border-right: 1px solid var(--cph-line);
}
section[data-testid="stSidebar"] .block-container { padding-top: 1.2rem; }
.sb-brand { display:flex; gap:11px; align-items:center; margin:2px 0 6px; }
.sb-logo {
  width:38px; height:38px; border-radius:11px; display:grid; place-items:center;
  background:linear-gradient(135deg,#4f8cff,#22d3ee); color:#06101f;
  font-weight:800; font-size:11px; letter-spacing:.04em;
}
.sb-name { font-weight:750; font-size:14px; color:var(--cph-text); line-height:1.15; }
.sb-sub { font-size:10.5px; color:var(--cph-muted); letter-spacing:.09em; text-transform:uppercase; }
.sb-block {
  border:1px solid var(--cph-line); border-radius:12px; padding:11px 12px;
  background:rgba(16,27,45,.65); margin:10px 0;
}
.sb-title { font-size:9.5px; letter-spacing:.12em; text-transform:uppercase; color:var(--cph-muted); font-weight:700; margin-bottom:7px; }
.sb-row { display:flex; justify-content:space-between; gap:8px; font-size:11.5px; padding:3px 0; color:#cbd5e1; }
.sb-row span:first-child { color:var(--cph-muted); }
.sb-note { font-size:10.5px; line-height:1.45; color:#f5b95e; margin-top:8px; }

/* --------------------------------------------------------------- header */
.cph-head { padding: 4px 0 14px; animation: cph-fade .35s ease both; }
.cph-head-top { display:flex; align-items:flex-start; justify-content:space-between; gap:24px; flex-wrap:wrap; }
.cph-brand { display:flex; gap:15px; align-items:flex-start; }
.cph-logo {
  width:46px; height:46px; border-radius:13px; display:grid; place-items:center;
  background:linear-gradient(135deg,#4f8cff,#22d3ee); color:#06101f;
  font-weight:850; font-size:12px; letter-spacing:.05em; margin-top:3px;
  box-shadow:0 8px 26px rgba(79,140,255,.28);
}
.cph-kicker { font-size:10px; letter-spacing:.18em; text-transform:uppercase; color:#7d93b3; font-weight:700; }
.cph-head h1 { font-size:31px; line-height:1.12; margin:5px 0 6px; color:#f3f7ff; font-weight:800; letter-spacing:-.02em; }
.cph-head h1 em { font-style:normal; color:var(--cph-accent); }
.cph-sub { font-size:12.5px; color:var(--cph-muted); margin:0; max-width:880px; line-height:1.5; }
.cph-chips { display:flex; gap:7px; flex-wrap:wrap; justify-content:flex-end; padding-top:6px; }
.chip {
  display:inline-flex; align-items:center; gap:6px; padding:4px 11px;
  border-radius:999px; border:1px solid var(--cph-line);
  background:rgba(16,27,45,.8); color:#b9c7da; font-size:10.5px; font-weight:600;
  white-space:nowrap;
}
.chip .dot { width:6px; height:6px; border-radius:50%; background:var(--cph-good); box-shadow:0 0 0 3px rgba(39,194,129,.16); }
.chip.live { color:#9ff0cd; border-color:rgba(39,194,129,.35); background:rgba(39,194,129,.1); }
.chip.snapshot { color:#ffd08a; border-color:rgba(245,166,35,.35); background:rgba(245,166,35,.1); }
.chip.snapshot .dot { background:var(--cph-warn); box-shadow:0 0 0 3px rgba(245,166,35,.16); }
.cph-rule { height:1px; background:linear-gradient(90deg, rgba(79,140,255,.65), rgba(34,211,238,.18), transparent 75%); margin-top:16px; }

/* --------------------------------------------------------------- KPI row */
.kpi-grid { display:grid; grid-template-columns:repeat(4, minmax(0,1fr)); gap:11px; margin:2px 0 20px; }
.kpi {
  border:1px solid var(--cph-line); border-radius:15px; padding:14px 16px 13px;
  background:linear-gradient(155deg, rgba(20,33,54,.92), rgba(13,23,40,.92));
  position:relative; overflow:hidden; animation:cph-fade .4s ease both;
}
.kpi:before { content:""; position:absolute; left:0; top:0; bottom:0; width:3px; background:var(--cph-accent); opacity:.75; }
.kpi.good:before { background:var(--cph-good); }
.kpi.bad:before { background:var(--cph-bad); }
.kpi.warn:before { background:var(--cph-warn); }
.k-label { font-size:9.5px; letter-spacing:.13em; text-transform:uppercase; color:#8fa3bf; font-weight:750; }
.k-value { font-size:25px; font-weight:800; color:#f3f7ff; margin:7px 0 3px; line-height:1.05; letter-spacing:-.02em; }
.k-value small { font-size:11px; font-weight:600; color:#8fa3bf; letter-spacing:0; margin-left:4px; }
.k-sub { font-size:10.5px; color:#8fa3bf; line-height:1.35; }
.k-sub .up { color:#fb7185; font-weight:700; }
.k-sub .down { color:#34d399; font-weight:700; }

/* --------------------------------------------------------------- section */
.sec { display:flex; align-items:flex-end; justify-content:space-between; gap:16px; margin:6px 0 10px; flex-wrap:wrap; }
.sec h2 { font-size:15.5px; margin:0; color:#eaf1fb; font-weight:750; letter-spacing:-.01em; }
.sec p { font-size:11.5px; color:var(--cph-muted); margin:3px 0 0; line-height:1.45; }
.sec .hint { font-size:10.5px; color:#7d93b3; }

/* ------------------------------------------------------------- filter box */
div[data-testid="stVerticalBlockBorderWrapper"] {
  background:rgba(16,27,45,.62);
  border:1px solid var(--cph-line) !important;
  border-radius:16px;
}
div[data-testid="stVerticalBlockBorderWrapper"] > div { padding: .35rem .55rem .15rem; }
.filter-title { font-size:9.5px; letter-spacing:.16em; text-transform:uppercase; color:#7d93b3; font-weight:750; margin:0 0 2px; }
.filter-help { font-size:10.5px; color:#7d93b3; margin:-2px 0 6px; }

/* ------------------------------------------------------------- widgets */
div[data-baseweb="select"] > div {
  background:#0b1628 !important; border-color:rgba(148,163,184,.22) !important;
  border-radius:10px !important; min-height:40px;
}
div[data-baseweb="select"] span { font-size:12.5px; }
div[data-baseweb="tag"] {
  background:rgba(79,140,255,.16) !important; border:1px solid rgba(79,140,255,.35) !important;
  border-radius:7px !important;
}
div[data-baseweb="tag"] span { color:#cfe0ff !important; font-size:11px !important; }
div[data-testid="stDateInput"] input { font-size:12.5px; }
div[data-testid="stTextInput"] input {
  background:#0b1628; border-radius:10px; font-size:12.5px;
}
.stSelectbox label, .stMultiSelect label, .stDateInput label, .stTextInput label, .stPills label,
label[data-testid="stWidgetLabel"] p {
  font-size:9.5px !important; letter-spacing:.11em; text-transform:uppercase;
  color:#8fa3bf !important; font-weight:700 !important;
}
label[data-testid="stWidgetLabel"] p { margin:0 !important; }
div[data-testid="stPills"] button,
button[data-variant="pills"] {
  border-radius:999px !important; border:1px solid rgba(148,163,184,.22) !important;
  background:rgba(11,22,40,.65) !important; color:#c3d0e2 !important;
  font-size:11.5px !important; padding:5px 12px !important; min-height:40px;
}
div[data-testid="stPills"] button:hover,
button[data-variant="pills"]:hover { border-color:rgba(79,140,255,.55) !important; color:#eaf1fb !important; }
div[data-testid="stPills"] button[kind="pillsActive"], div[data-testid="stPills"] button[aria-checked="true"],
button[data-variant="pills"][aria-checked="true"] {
  background:rgba(39,194,129,.16) !important; border-color:rgba(39,194,129,.55) !important; color:#9ff0cd !important;
}
div[data-testid="stBaseButton-secondary"] {
  border-radius:9px !important; border:1px solid rgba(148,163,184,.22) !important;
  background:rgba(11,22,40,.65) !important; color:#c3d0e2 !important; font-size:11.5px !important;
}
div[data-testid="stBaseButton-secondary"]:hover { border-color:rgba(79,140,255,.55) !important; color:#fff !important; }
div[data-testid="stBaseButton-primary"] { border-radius:9px !important; font-weight:700 !important; }

/* tabs */
div[data-baseweb="tab-list"] { gap:4px; background:transparent; border-bottom:1px solid var(--cph-line); }
button[data-baseweb="tab"] { font-size:12px !important; color:#93a7c3 !important; padding:7px 12px !important; }
button[data-baseweb="tab"][aria-selected="true"] { color:#dbe9ff !important; }
div[data-baseweb="tab-highlight"] { background:var(--cph-accent); }

/* --------------------------------------------------------------- table */
.qt-wrap { border:1px solid var(--cph-line); border-radius:14px; overflow:auto; max-height:560px; background:rgba(13,23,40,.7); }
table.qt { width:100%; border-collapse:separate; border-spacing:0; font-size:12.5px; min-width:720px; }
table.qt thead th {
  position:sticky; top:0; z-index:2; background:#101c2f; color:#8fa3bf;
  font-size:9.5px; letter-spacing:.09em; text-transform:uppercase; font-weight:750;
  text-align:left; padding:10px 12px; border-bottom:1px solid var(--cph-line); white-space:nowrap;
}
table.qt thead th.num { text-align:right; }
table.qt tbody td { padding:9px 12px; border-bottom:1px solid rgba(148,163,184,.09); color:#d7e2f1; vertical-align:middle; }
table.qt tbody tr:last-child td { border-bottom:none; }
table.qt tbody tr:hover td { background:rgba(79,140,255,.055); }
table.qt td.num { text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }
table.qt td.rank { color:#6f86a6; font-size:11px; width:36px; }
table.qt tr.low td { background:rgba(39,194,129,.055); }
table.qt tr.low td:first-child { box-shadow:inset 3px 0 0 var(--cph-good); }
table.qt .who { font-weight:700; color:#eef4fd; }
table.qt .meta { display:block; font-size:10px; color:#7d93b3; margin-top:2px; font-weight:500; }
table.qt .pos { color:#fb7185; font-weight:650; }
table.qt .neg { color:#34d399; font-weight:650; }
table.qt .flat { color:#7d93b3; }
table.qt .price { font-weight:800; color:#f3f7ff; font-size:13.5px; }
.badge {
  display:inline-block; font-size:8.5px; letter-spacing:.08em; font-weight:800;
  padding:2px 6px; border-radius:5px; margin-left:6px; vertical-align:1px;
}
.badge.low { background:rgba(39,194,129,.15); color:#54dda6; border:1px solid rgba(39,194,129,.3); }
.badge.high { background:rgba(240,81,109,.13); color:#ff8ca1; border:1px solid rgba(240,81,109,.28); }
.qt-note { font-size:10.5px; color:#7d93b3; margin-top:7px; }

.empty {
  border:1px dashed rgba(148,163,184,.3); border-radius:14px; padding:36px 20px;
  text-align:center; color:#8fa3bf; font-size:13px; background:rgba(16,27,45,.4);
}
.banner {
  border:1px solid rgba(245,166,35,.3); border-radius:12px; padding:10px 14px;
  background:rgba(245,166,35,.08); color:#e8c58b; font-size:11.5px;
  line-height:1.5; margin:0 0 14px;
}
.banner b { color:#ffd08a; }
.foot { margin-top:26px; padding-top:14px; border-top:1px solid var(--cph-line); color:#6f86a6; font-size:10.5px; line-height:1.6; }
.foot b { color:#93a7c3; }

@keyframes cph-fade { from { opacity:0; transform:translateY(4px);} to { opacity:1; transform:none;} }
@media (max-width: 1100px) { .kpi-grid { grid-template-columns:repeat(2, minmax(0,1fr)); } .cph-head h1 { font-size:26px; } }
@media (max-width: 640px) { .kpi-grid { grid-template-columns:1fr; } .cph-head h1 { font-size:23px; } }
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def _esc(value: object) -> str:
    return html.escape(str(value))


def fmt_int(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{value:,.0f}"


def fmt_signed(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{value:+,.0f}"


def header(cfg: config.SheetConfig, meta: dict, dataset, updated: str) -> None:
    live = bool(meta.get("live"))
    status_class = "live" if live else "snapshot"
    status_text = "LIVE SHEET" if live else "SNAPSHOT"
    parts = cfg.title.split("—", 1)
    if len(parts) == 2:
        heading = f"{_esc(parts[0].strip())} — <em>{_esc(parts[1].strip())}</em>"
    else:
        heading = _esc(cfg.title)
    st.markdown(
        f"""
        <div class="cph-head">
          <div class="cph-head-top">
            <div class="cph-brand">
              <div class="cph-logo">AEL</div>
              <div>
                <div class="cph-kicker">AEL Trading · Khatunganj market intelligence</div>
                <h1>{heading}</h1>
                <p class="cph-sub">{_esc(cfg.subtitle)}</p>
              </div>
            </div>
            <div class="cph-chips">
              <span class="chip {status_class}"><span class="dot"></span>{status_text}</span>
              <span class="chip">{_esc(cfg.unit)}</span>
              <span class="chip">{len(dataset.competitors)} competitors</span>
              <span class="chip">Data to {dataset.long["Date"].max():%d %b %Y}</span>
              <span class="chip">Fetched {_esc(updated)}</span>
            </div>
          </div>
          <div class="cph-rule"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def kpi_cards(k: dict, unit: str) -> None:
    latest = k["latest"]
    change = k["change"]
    change_pct = k["change_pct"]

    if change is None:
        change_value = "—"
        change_sub = "No earlier quote in this range"
        change_class = ""
    else:
        change_value = f"{change:+,.0f}"
        arrow = "▲" if change > 0 else ("▼" if change < 0 else "•")
        css = "up" if change > 0 else ("down" if change < 0 else "")
        pct = f"{change_pct:+.1f}%" if change_pct is not None else ""
        change_sub = (
            f"<span class='{css}'>{arrow} {pct}</span> vs previous report "
            f"({_esc(k['previous_date'].strftime('%d %b'))})"
        )
        change_class = "bad" if change > 0 else ("good" if change < 0 else "")

    st.markdown(
        f"""
        <div class="kpi-grid">
          <div class="kpi">
            <div class="k-label">Latest report</div>
            <div class="k-value">{_esc(latest.strftime('%d %b %Y'))}</div>
            <div class="k-sub">{k['days']} reporting day{'s' if k['days'] != 1 else ''} in the selected range</div>
          </div>
          <div class="kpi">
            <div class="k-label">Market average</div>
            <div class="k-value">{fmt_int(k['average'])}<small>{_esc(unit)}</small></div>
            <div class="k-sub">quoted range {fmt_int(k['low'])} – {fmt_int(k['high'])}</div>
          </div>
          <div class="kpi {change_class}">
            <div class="k-label">Change vs previous</div>
            <div class="k-value">{change_value}<small>{_esc(unit)}</small></div>
            <div class="k-sub">{change_sub}</div>
          </div>
          <div class="kpi">
            <div class="k-label">Competitors quoting</div>
            <div class="k-value">{k['competitors']}</div>
            <div class="k-sub">{k['observations']} quotes on the latest date</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section(title: str, sub: str = "", hint: str = "") -> None:
    right = f"<div class='hint'>{_esc(hint)}</div>" if hint else ""
    sub_html = f"<p>{sub}</p>" if sub else ""
    st.markdown(
        f"<div class='sec'><div><h2>{_esc(title)}</h2>{sub_html}</div>{right}</div>",
        unsafe_allow_html=True,
    )


def empty_state(message: str) -> None:
    st.markdown(f"<div class='empty'>{_esc(message)}</div>", unsafe_allow_html=True)


def quote_table(quotes: pd.DataFrame, unit: str) -> None:
    if quotes.empty:
        empty_state("No competitor quoted on the latest date for this filter.")
        return

    grouping_cols = [column for column in ("Product", "Category") if column in quotes.columns]
    has_product = "Product" in grouping_cols
    lowest: dict[tuple, float] = {}
    highest: dict[tuple, float] = {}
    if grouping_cols:
        for key, group in quotes.groupby(grouping_cols):
            key = key if isinstance(key, tuple) else (key,)
            lowest[key] = float(group["Price"].min())
            highest[key] = float(group["Price"].max())
    else:
        lowest[()] = float(quotes["Price"].min())
        highest[()] = float(quotes["Price"].max())

    rows = []
    previous_key = None
    rank = 0
    for _, row in quotes.iterrows():
        key = tuple(row.get(column, "") for column in grouping_cols)
        if key != previous_key:
            rank = 0
            previous_key = key
        rank += 1

        product = row.get("Product", "")
        price = float(row["Price"])
        prev = row.get("Prev")
        change = row.get("Change")
        pct = row.get("ChangePct")

        prev_text = fmt_int(prev) if pd.notna(prev) else "—"
        if pd.notna(change):
            direction = "pos" if change > 0 else ("neg" if change < 0 else "flat")
            arrow = "▲" if change > 0 else ("▼" if change < 0 else "•")
            change_text = f"<span class='{direction}'>{arrow} {abs(change):,.0f}</span>"
            pct_text = f"<span class='{direction}'>{pct:+.1f}%</span>" if pd.notna(pct) else "—"
        else:
            change_text = "<span class='flat'>—</span>"
            pct_text = "<span class='flat'>—</span>"

        vs_market = row.get("VsMarket")
        if pd.notna(vs_market):
            direction = "pos" if vs_market > 0 else ("neg" if vs_market < 0 else "flat")
            vs_text = f"<span class='{direction}'>{vs_market:+,.0f}</span>"
        else:
            vs_text = "<span class='flat'>—</span>"

        badge = ""
        if price == lowest.get(key):
            badge = "<span class='badge low'>LOWEST</span>"
        elif price == highest.get(key):
            badge = "<span class='badge high'>HIGHEST</span>"

        meta_bits = [
            str(row.get("Origin", "") or ""),
            str(row.get("Category", "") or ""),
        ]
        meta = " · ".join(bit for bit in meta_bits if bit and bit != "All")
        meta_html = f"<span class='meta'>{_esc(meta)}</span>" if meta else ""

        product_cell = f"<td>{_esc(product)}</td>" if has_product else ""
        rows.append(
            f"<tr class='{'low' if price == lowest.get(key) else ''}'>"
            f"<td class='rank'>{rank:02d}</td>"
            f"{product_cell}"
            f"<td><span class='who'>{_esc(row['Competitor'])}</span>{badge}{meta_html}</td>"
            f"<td class='num price'>{fmt_int(price)}</td>"
            f"<td class='num'>{prev_text}</td>"
            f"<td class='num'>{change_text}</td>"
            f"<td class='num'>{pct_text}</td>"
            f"<td class='num'>{int(row['Quotes'])}</td>"
            f"<td class='num'>{fmt_int(row['Min'])} – {fmt_int(row['Max'])}</td>"
            f"<td class='num'>{vs_text}</td>"
            "</tr>"
        )

    product_header = "<th>Product</th>" if has_product else ""
    st.markdown(
        f"""
        <div class="qt-wrap">
          <table class="qt">
            <thead>
              <tr>
                <th>#</th>{product_header}<th>Competitor</th><th class="num">Latest ({_esc(unit)})</th><th class="num">Previous</th><th class="num">Δ</th><th class="num">Δ %</th><th class="num">Quotes</th><th class="num">Min – Max</th><th class="num">vs Market</th>
              </tr>
            </thead>
            <tbody>{''.join(rows)}</tbody>
          </table>
        </div>
        <div class="qt-note">Ranked cheapest first. Latest is the most recent reporting date; Δ compares
        each competitor with its own previous quote. Quotes and Min–Max cover the selected date range.
        “vs Market” is the difference from the average of the latest quotes. Green = cheaper than market /
        price fell; red = dearer than market / price rose.</div>
        """,
        unsafe_allow_html=True,
    )


def footer(cfg: config.SheetConfig, meta: dict) -> None:
    source = _esc(meta.get("source", ""))
    note = _esc(meta.get("note", ""))
    error = _esc(meta.get("error", ""))
    extra = f"<br><span style='color:#f5b95e'>{note}</span>" if note else ""
    if error and meta.get("live"):
        extra += f"<br><span style='color:#7d93b3'>Fallback detail: {error}</span>"
    st.markdown(
        f"""
        <div class="foot">
          <b>Source:</b> <a href="{cfg.sheet_url}" target="_blank" style="color:#7fb0ff;text-decoration:none">{_esc(cfg.source_note)}</a> ·
          {source} · unit {_esc(cfg.unit)} · prices are as reported by the market, not adjusted.
          {extra}
          <br>Built for AEL Trading, Khatunganj. All figures update automatically when the
          Google Sheet changes — use <b>Refresh now</b> in the header or sidebar to pull immediately.
        </div>
        """,
        unsafe_allow_html=True,
    )
