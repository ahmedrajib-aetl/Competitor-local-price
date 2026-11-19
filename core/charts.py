"""Plotly figure for the competitor price pages — one single day-wise chart.

Two presentation rules:

* no legend box — each competitor's name is printed at the end of its line;
* hovering a competitor shows that competitor's price for every product/origin
  on that date, not just the averaged line value.
"""

from __future__ import annotations

import html
from typing import Callable

import pandas as pd
import plotly.graph_objects as go

# Bright, distinguishable colours that read well on the dark theme.
PALETTE = [
    "#4f8cff", "#f5a623", "#27c281", "#f0516d", "#a78bfa",
    "#22d3ee", "#fb923c", "#34d399", "#e879f9", "#facc15",
    "#60a5fa", "#f472b6", "#2dd4bf", "#c084fc", "#fbbf24",
    "#4ade80", "#38bdf8", "#fb7185", "#a3e635", "#f97316",
]

AVERAGE_COLOUR = "#94a3b8"


def color_map(competitors: list[str]) -> dict[str, str]:
    return {
        name: PALETTE[index % len(PALETTE)]
        for index, name in enumerate(competitors)
    }


def _price_label(day: pd.DataFrame, product_order: dict[str, int],
                 multi_origin: bool, multi_category: bool) -> str:
    """One hover line per product/origin/category quoted on this date."""
    rows = (
        day.groupby(["Product", "Origin", "Category"], dropna=False)["Price"]
        .mean()
        .reset_index()
    )
    rows["_order"] = rows["Product"].map(product_order).fillna(999)
    rows = rows.sort_values(["_order", "Product", "Origin", "Category"])

    lines = []
    for _, row in rows.iterrows():
        parts = [str(row["Product"])]
        origin = str(row["Origin"])
        category = str(row["Category"])
        if multi_origin and origin not in {"", "—", "All"}:
            parts.append(origin)
        if multi_category and category not in {"", "All"}:
            parts.append(category)
        label = " · ".join(html.escape(part) for part in parts)
        lines.append(f"{label}: <b>{row['Price']:,.0f}</b>")
    return "<br>".join(lines)


def _add_end_labels(
    figure: go.Figure,
    labels: list[dict],
    y_lo: float,
    y_hi: float,
) -> None:
    """Print names just to the right of each line end, without overlapping text.

    Labels are first placed at the line's own y position, then pushed apart in
    *paper* coordinates (a fixed pixel gap), so the data scale is not distorted.
    A short connector joins each line end to its label.
    """
    if not labels:
        return

    y_span = max(y_hi - y_lo, 1e-9)
    ordered = sorted(labels, key=lambda item: item["y"])
    paper = [
        min(0.985, max(0.015, (item["y"] - y_lo) / y_span))
        for item in ordered
    ]

    # 14 px gap on a ~430 px plot area; convert to paper coordinates.
    gap = 14 / 430
    adjusted: list[float] = []
    previous = 0.0
    for position in paper:
        position = max(position, previous + gap)
        adjusted.append(position)
        previous = position

    # Keep the label stack centred on the original line ends.
    shift = (sum(adjusted) - sum(paper)) / len(paper)
    adjusted = [position - shift for position in adjusted]

    # Keep the whole stack inside the plotting area.
    if adjusted[0] < 0.025:
        correction = 0.025 - adjusted[0]
        adjusted = [position + correction for position in adjusted]
    if adjusted[-1] > 0.975:
        correction = adjusted[-1] - 0.975
        adjusted = [position - correction for position in adjusted]

    # Short connector from the actual line end to the moved label.
    for item, position in zip(ordered, adjusted):
        label_y = y_lo + position * y_span
        figure.add_trace(
            go.Scatter(
                x=[item["x"], item["label_x"]],
                y=[item["y"], label_y],
                mode="lines",
                line=dict(
                    color=item["color"],
                    width=0.8,
                    dash="dot" if item.get("average") else "solid",
                ),
                opacity=0.5,
                hoverinfo="skip",
                showlegend=False,
            )
        )

    # The names themselves.
    for item, position in zip(ordered, adjusted):
        figure.add_annotation(
            x=item["label_x"],
            y=position,
            xref="x",
            yref="paper",
            text=item["name"],
            showarrow=False,
            xanchor="left",
            yanchor="middle",
            font=dict(
                family="Inter, 'Segoe UI', system-ui, sans-serif",
                size=10,
                color=item["color"],
            ),
            bgcolor="rgba(10,18,32,0.70)",
            borderpad=1,
        )


def price_trend(
    frame: pd.DataFrame,
    competitors: list[str],
    unit: str,
    *,
    own_brand: str = "AEL",
    product_order: list[str] | None = None,
    show_average: bool = True,
    markers: bool = True,
    hover_builder: Callable[[pd.DataFrame], str] | None = None,
) -> go.Figure:
    """One line per competitor across every selected product / origin / category.

    A competitor can quote several products on the same day.  To keep one line,
    each date is that competitor's mean for the selected quotes.  Hovering the
    line lists every product/origin/category price behind that mean.
    """
    colours = color_map(competitors)
    multi_origin = frame["Origin"].nunique() > 1 if "Origin" in frame.columns else False
    multi_category = frame["Category"].nunique() > 1 if "Category" in frame.columns else False

    if product_order is None:
        product_order = (
            sorted(frame["Product"].unique().tolist())
            if "Product" in frame.columns
            else []
        )
    else:
        product_order = [p for p in product_order if p in set(frame["Product"])]
        product_order += [
            p for p in frame["Product"].unique() if p not in set(product_order)
        ]
    order_map = {product: index for index, product in enumerate(product_order)}

    figure = go.Figure()
    end_labels: list[dict] = []

    for competitor in competitors:
        subset = frame[frame["Competitor"] == competitor]
        if subset.empty:
            continue

        grouped = (
            subset.groupby("Date", as_index=False)["Price"]
            .agg(Price="mean", Quotes="size")
            .sort_values("Date")
        )

        breakdowns = {
            date: (
                hover_builder(day)
                if hover_builder is not None
                else _price_label(day, order_map, multi_origin, multi_category)
            )
            for date, day in subset.groupby("Date")
        }
        hover = []
        for _, row in grouped.iterrows():
            quotes = int(row["Quotes"])
            quote_text = f"{quotes} quote{'s' if quotes != 1 else ''}"
            hover.append(
                f"{quote_text}<br><br>{breakdowns.get(row['Date'], '')}"
            )

        colour = colours.get(competitor, "#94a3b8")
        safe_name = html.escape(competitor)
        figure.add_trace(
            go.Scatter(
                x=grouped["Date"],
                y=grouped["Price"],
                mode="lines+markers" if markers else "lines",
                name=competitor,
                showlegend=False,
                line=dict(
                    color=colour,
                    width=3.2 if competitor == own_brand else 2.0,
                ),
                marker=dict(
                    color=colour,
                    size=4.5,
                    line=dict(width=0),
                ),
                text=hover,
                hovertemplate=(
                    f"<b>{safe_name}</b> · %{{x|%d %b %Y}}"
                    f"<br>Average <b>%{{y:,.0f}}</b> {unit}"
                    "<br>%{text}<extra></extra>"
                ),
                connectgaps=False,
            )
        )

        last = grouped.iloc[-1]
        end_labels.append(
            {
                "name": competitor,
                "x": last["Date"],
                "y": float(last["Price"]),
                "color": colour,
                "average": False,
            }
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
                showlegend=False,
                line=dict(color=AVERAGE_COLOUR, width=1.5, dash="dash"),
                hovertemplate=(
                    "<b>Market average</b> · %{x|%d %b %Y}"
                    f"<br>Average <b>%{{y:,.0f}}</b> {unit}<extra></extra>"
                ),
            )
        )
        last = average.iloc[-1]
        end_labels.append(
            {
                "name": "Market average",
                "x": last["Date"],
                "y": float(last["Price"]),
                "color": AVERAGE_COLOUR,
                "average": True,
            }
        )

    # Reserve a clean column on the right for the direct labels.
    x_min = frame["Date"].min()
    x_max = frame["Date"].max()
    span_days = max((x_max - x_min).days, 1)
    right_pad_days = max(2.0, span_days * 0.20)
    x_lo = x_min - pd.Timedelta(days=max(1.0, span_days * 0.02))
    x_hi = x_max + pd.Timedelta(days=right_pad_days)

    # Each name sits just after its own line end; the gap is tiny so the
    # connector is a short elbow rather than a line across the chart.
    label_offset_days = max(0.5, span_days * 0.006)
    for item in end_labels:
        item["label_x"] = item["x"] + pd.Timedelta(days=label_offset_days)

    y_min = float(frame["Price"].min())
    y_max = float(frame["Price"].max())
    y_span = max(y_max - y_min, 1.0)
    y_lo = y_min - y_span * 0.05
    y_hi = y_max + y_span * 0.05

    _add_end_labels(figure, end_labels, y_lo, y_hi)

    figure.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            family="Inter, 'Segoe UI', system-ui, -apple-system, sans-serif",
            color="#cbd5e1",
            size=12,
        ),
        height=500,
        margin=dict(l=12, r=18, t=18, b=8),
        hovermode="closest",
        showlegend=False,
    )
    figure.update_xaxes(
        range=[x_lo, x_hi],
        showgrid=True,
        gridcolor="rgba(148,163,184,0.12)",
        zeroline=False,
        tickformat="%d %b",
        tickfont=dict(size=10.5, color="#8fa3bf"),
        linecolor="rgba(148,163,184,0.2)",
    )
    figure.update_yaxes(
        range=[y_lo, y_hi],
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

def stock_bar(
    summary: pd.DataFrame,
    dimension: str,
    measure: str,
    *,
    title: str,
    unit: str,
    color: str,
    label_formatter: Callable[[float], str] | None = None,
    top: int = 5,
) -> go.Figure:
    """Horizontal bar chart for a stock dimension (quantity or value)."""
    data = summary[summary[measure].notna()].copy()
    data = data.sort_values(measure, ascending=True).tail(top)
    formatter = label_formatter or (lambda value: f"{value:,.0f}")
    labels = [formatter(float(value)) for value in data[measure]]
    names = [str(value) for value in data[dimension]]

    figure = go.Figure(
        go.Bar(
            x=data[measure],
            y=names,
            orientation="h",
            marker=dict(color=color),
            text=labels,
            textposition="outside",
            cliponaxis=False,
            textfont=dict(size=10.5, color="#dbe6f5"),
            hovertemplate=(
                "<b>%{y}</b><br>%{x:,.3f} " + unit + "<extra></extra>"
            ),
        )
    )
    figure.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        title=dict(text=title, font=dict(size=13, color="#cbd5e1"), x=0),
        height=380,
        margin=dict(l=10, r=58, t=34, b=8),
        font=dict(
            family="Inter, 'Segoe UI', system-ui, sans-serif",
            color="#cbd5e1",
            size=11,
        ),
        showlegend=False,
        bargap=0.35,
    )
    figure.update_xaxes(visible=False)
    figure.update_yaxes(
        showgrid=False,
        tickfont=dict(size=11, color="#cbd5e1"),
        linecolor="rgba(148,163,184,0.2)",
    )
    return figure
