"""Warehouse stock data for the Grain and Coal stock pages.

Both source sheets use a `Master Data` tab with one row per item/warehouse:

* Grain: Date, Product (Bulk), Item Name, Code, UOM, Qty, Value, Plant, Warehouse
* Coal:  Date, SBU, Warehouse, Item Name, Code, Physical Qty (MT) 4th lot, Value(BDT)

The stock pages only use this tab.  Older dated tabs in the workbooks are
snapshots/backups and are intentionally ignored.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

import config
from core.transform import _smart_title, _to_date, _to_number


def _norm(value: object) -> str:
    text = str(value).replace("\n", " ").replace("\r", " ").replace("\xa0", " ")
    return " ".join(text.split()).strip().lower()


def _label(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).replace("\n", " ").replace("\r", " ").strip()
    text = " ".join(text.split())
    return "" if text.lower() in {"nan", "none", "nat"} else text


def _column(columns: list[str], exact: tuple[str, ...], contains: tuple[str, ...] = ()) -> str | None:
    for column in columns:
        if _norm(column) in exact:
            return column
    for column in columns:
        token = _norm(column)
        if any(part in token for part in contains):
            return column
    return None


@dataclass
class StockDataset:
    frame: pd.DataFrame
    group_label: str
    groups: list[str]
    items: list[str]
    warehouses: list[str]
    plants: list[str]
    dates: list
    rows: int
    unit: str


def prepare_stock(raw: pd.DataFrame, cfg: config.SheetConfig) -> StockDataset:
    if raw is None or raw.empty:
        raise ValueError("The Master Data tab is empty.")

    frame = raw.copy()
    frame.columns = [str(c).replace("\n", " ").strip() for c in frame.columns]
    columns = list(frame.columns)

    date_col = _column(columns, ("date",), ())
    group_col = _column(columns, ("product (bulk)", "sbu", "product"), ("product (bulk)", "sbu"))
    item_col = _column(columns, ("item name", "item"), ())
    code_col = _column(columns, ("code",), ())
    warehouse_col = _column(columns, ("warehouse",), ())
    plant_col = _column(columns, ("plant",), ())
    qty_col = _column(
        columns,
        ("qty", "quantity (mt)", "physical qty (mt) 4th lot"),
        ("physical qty", "qty"),
    )
    value_col = _column(columns, ("value", "value(bdt)"), ("value",))
    uom_col = _column(columns, ("uom",), ())

    if not date_col or not qty_col or not value_col:
        raise ValueError(
            "Master Data needs Date, qty and value columns. "
            f"Found: {', '.join(map(str, columns))}"
        )

    group_label = "SBU" if group_col and _norm(group_col) == "sbu" else "Product"

    out = pd.DataFrame(
        {
            "Date": _to_date(frame[date_col]),
            "Group": frame[group_col].map(_label) if group_col else "",
            "Item": frame[item_col].map(_label) if item_col else "",
            "Code": frame[code_col].map(_label) if code_col else "",
            "Warehouse": frame[warehouse_col].map(_label) if warehouse_col else "",
            "Plant": frame[plant_col].map(_label) if plant_col else "",
            "Quantity": _to_number(frame[qty_col]),
            "Value": _to_number(frame[value_col]),
            "UOM": frame[uom_col].map(_label) if uom_col else cfg.unit,
        }
    )

    out = out.dropna(subset=["Date"])
    out = out[
        out["Group"].ne("")
        | out["Item"].ne("")
        | out["Warehouse"].ne("")
    ]
    out["UOM"] = out["UOM"].replace("", cfg.unit)
    out = out.reset_index(drop=True)

    if out.empty:
        raise ValueError("No dated stock rows were found in Master Data.")

    def unique(column: str) -> list[str]:
        return sorted(
            {value for value in out[column] if value},
            key=str.casefold,
        )

    return StockDataset(
        frame=out,
        group_label=group_label,
        groups=unique("Group"),
        items=unique("Item"),
        warehouses=unique("Warehouse"),
        plants=unique("Plant"),
        dates=sorted(out["Date"].dt.date.unique().tolist()),
        rows=len(out),
        unit=cfg.unit,
    )


def filter_stock(
    dataset: StockDataset,
    selected_date,
    *,
    groups: list[str] | None = None,
    items: list[str] | None = None,
    plants: list[str] | None = None,
    warehouses: list[str] | None = None,
    search: str = "",
) -> pd.DataFrame:
    frame = dataset.frame[dataset.frame["Date"] == pd.Timestamp(selected_date)].copy()
    if groups:
        frame = frame[frame["Group"].isin(groups)]
    if items:
        frame = frame[frame["Item"].isin(items)]
    if plants:
        frame = frame[frame["Plant"].isin(plants)]
    if warehouses:
        frame = frame[frame["Warehouse"].isin(warehouses)]

    needle = search.strip().casefold()
    if needle:
        mask = pd.Series(False, index=frame.index)
        for column in ("Group", "Item", "Code", "Warehouse", "Plant"):
            mask |= frame[column].astype(str).str.casefold().str.contains(needle, regex=False)
        frame = frame[mask]

    return frame.copy()


def stock_kpis(today: pd.DataFrame, previous: pd.DataFrame) -> dict:
    quantity = float(today["Quantity"].sum())
    value = float(today["Value"].sum())

    def delta(current: float, old: float) -> float | None:
        if not old:
            return None
        return (current - old) / old * 100

    previous_qty = float(previous["Quantity"].sum()) if not previous.empty else 0.0
    previous_value = float(previous["Value"].sum()) if not previous.empty else 0.0

    return {
        "quantity": quantity,
        "value": value,
        "items": int(today["Item"].replace("", pd.NA).nunique()),
        "warehouses": int(today["Warehouse"].replace("", pd.NA).nunique()),
        "plants": int(today["Plant"].replace("", pd.NA).nunique()),
        "groups": int(today["Group"].replace("", pd.NA).nunique()),
        "rows": int(len(today)),
        "average": value / quantity if quantity else float("nan"),
        "previous_quantity": previous_qty,
        "previous_value": previous_value,
        "quantity_delta": delta(quantity, previous_qty),
        "value_delta": delta(value, previous_value),
    }


def stock_summary(frame: pd.DataFrame, dimension: str) -> pd.DataFrame:
    data = frame.copy()
    if dimension == "Item":
        data = data[data["Item"].ne("")]
    elif dimension == "Plant":
        data = data[data["Plant"].ne("")]
    elif dimension == "Warehouse":
        data = data[data["Warehouse"].ne("")]
    else:
        data = data[data["Group"].ne("")]

    if data.empty:
        return pd.DataFrame(columns=[dimension, "Quantity", "Value", "AvgRate", "QtyShare", "ValueShare", "Rows"])

    grouped = (
        data.groupby(dimension, dropna=False)
        .agg(
            Quantity=("Quantity", "sum"),
            Value=("Value", "sum"),
            Rows=("Date", "size"),
        )
        .reset_index()
    )
    total_qty = grouped["Quantity"].sum()
    total_value = grouped["Value"].sum()
    grouped["AvgRate"] = grouped.apply(
        lambda row: row["Value"] / row["Quantity"] if row["Quantity"] else float("nan"),
        axis=1,
    )
    grouped["QtyShare"] = grouped["Quantity"] / total_qty * 100 if total_qty else 0.0
    grouped["ValueShare"] = grouped["Value"] / total_value * 100 if total_value else 0.0
    return grouped.sort_values("Quantity", ascending=False).reset_index(drop=True)


def stock_detail(frame: pd.DataFrame, group_label: str) -> pd.DataFrame:
    table = frame[["Group", "Item", "Code", "Plant", "Warehouse", "Quantity", "Value"]].copy()
    total_qty = table["Quantity"].sum()
    total_value = table["Value"].sum()
    table["AvgRate"] = table.apply(
        lambda row: row["Value"] / row["Quantity"] if row["Quantity"] else float("nan"),
        axis=1,
    )
    table["QtyShare"] = table["Quantity"] / total_qty * 100 if total_qty else 0.0
    table["ValueShare"] = table["Value"] / total_value * 100 if total_value else 0.0
    table = table.rename(columns={"Group": group_label})
    return table.sort_values("Quantity", ascending=False).reset_index(drop=True)
