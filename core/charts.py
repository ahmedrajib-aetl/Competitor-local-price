"""Plotly figure for the competitor price pages — one single day-wise chart."""

from __future__ import annotations

import html

import pandas as pd
import plotly.graph_objects as go

# Bright, distinguishable colours that read well on the dark theme.
PALETTE = [
    "#4f8cff", "#f5a623", "#27c281", "#f0516d", "#a78bfa",
    "#22d3ee", "#fb923c", "#34d399", "#e879f9", "#facc15",
    "#60a5fa", "#f472b6", "#2dd4bf", "#c084fc", "#fbbf24",
    "#4ade80", "#38bdf8", "#fb7185", "#a3e635", "#f97316",
]


def color_map(competitors: list[str]) -> dict[str, str]:
    return {
        name: PALETTE[index % len(PALETTE)]
        for index, name in enumerate(competitors)
    }


def _short(values, limit: int = 58) -> str:
    text = ", ".join(sorted({str(value) for value in values if str(value)}))
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def price_trend(
    frame: pd.DataFrame,
    competitors: list[str],
    unit: str,
    *,
    own_brand: str = "AEL",
    show_average: bool = True,
    markers: bool = True,
) -> go.Figure:
    """One line per competitor across every selected product / origin / category.

    A competitor can quote several products on the same day.  To keep a single
    line, each date is the mean of that competitor's quotes inside the current
    filter.  The hover text says how many quotes were averaged and which
    products/origins they came from.
    """
    colours = color_map(competitors)
    single_product = frame["Product"].nunique() == 1
    single_origin = frame["Origin"].nunique() == 1
    single_category = frame["Category"].nunique() == 1

    product_label = frame["Product"].iloc[0] if single_product else ""
    origin_label = frame["Origin"].iloc[0] if single_origin else ""
    category_label = frame["Category"].iloc[0] if single_category else ""

    figure = go.Figure()

    for competitor in competitors:
        subset = frame[frame["Competitor"] == competitor]
        if subset.empty:
            continue

        grouped = (
            subset.groupby("Date", as_index=False)
            .agg(
                Price=("Price", "mean"),
                Quotes=("Price", "size"),
                Products=("Product", lambda values: _short(values)),
                Origins=("Origin", lambda values: _short(values)),
                Categories=("Category", lambda values: _short(values)),
            )
            .sort_values("Date")
        )

        hover = []
        for _, row in grouped.iterrows():
            scope = [
                product_label or row["Products"],
                origin_label or row["Origins"],
                category_label or row["Categories"],
            ]
            scope_text = " · ".join(html.escape(str(bit)) for bit in scope if bit)
            quotes = int(row["Quotes"])
            quote_text = f"{quotes} quote{'s' if quotes != 1 else ''}"
            hover.append(f"{scope_text}<br>{quote_text}")

        safe_name = html.escape(competitor)
        figure.add_trace(
            go.Scatter(
                x=grouped["Date"],
                y=grouped["Price"],
                mode="lines+markers" if markers else "lines",
                name=competitor,
                line=dict(
                    color=colours.get(competitor, "#94a3b8"),
                    width=3.2 if competitor == own_brand else 2.0,
                ),
                marker=dict(
                    color=colours.get(competitor, "#94a3b8"),
                    size=4.5,
                    line=dict(width=0),
                ),
                text=hover,
                hovertemplate=(
                    f"<b>{safe_name}</b><br>%{{x|%d %b %Y}}"
                    f"<br><b>%{{y:,.0f}}</b> {unit}"
                    "<br>%{text}<extra></extra>"
                ),
                connectgaps=False,
            )
        )

    if show_average and not frame.empty:
        average = (
            frame.groupby("Date", as_index=False)["Price"].mean().sort_values("Date")
        )
        figure.add_trace(
            go.Scatter(
                x=average["Date"],
                y=average["Price"],
                mode="lines",
                name="Market average",
                legendrank=1000,
                line=dict(color="#94a3b8", width=1.5, dash="dash"),
                hovertemplate=(
                    "<b>Market average</b><br>%{x|%d %b %Y}"
                    f"<br>%{{y:,.0f}} {unit}<extra></extra>"
                ),
            )
        )

    figure.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            family="Inter, 'Segoe UI', system-ui, -apple-system, sans-serif",
            color="#cbd5e1",
            size=12,
        ),
        height=520,
        margin=dict(l=12, r=14, t=18, b=8),
        hovermode="closest",
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.16,
            x=0,
            font=dict(size=10.5, color="#cbd5e1"),
            bgcolor="rgba(0,0,0,0)",
            itemclick="toggle",
            itemdoubleclick="toggleothers",
            traceorder="normal",
        ),
        legend_title_text="",
    )
    figure.update_xaxes(
        showgrid=True,
        gridcolor="rgba(148,163,184,0.12)",
        zeroline=False,
        tickformat="%d %b",
        tickfont=dict(size=10.5, color="#8fa3bf"),
        linecolor="rgba(148,163,184,0.2)",
    )
    figure.update_yaxes(
        showgrid=True,
        gridcolor="rgba(148,163,184,0.12)",
        zeroline=False,
        tickformat=",.0f",
        title_text=unit,
        title_font=dict(size=10, color="#8fa3bf"),
        tickfont=dict(size=10.5, color="#8fa3bf"),
        linecolor="rgba(148,163,184,0.2)",
    )
    return figure
