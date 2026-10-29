"""Turn the raw sheet grid into a clean, filterable price dataset.

The sheet layout can change: a competitor column may be added, a tab renamed,
or a unit changed from rate/mound to rate/MT.  Fixed columns are found by name,
everything else that holds prices becomes a competitor automatically.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

import config

FIXED_NAMES = {
    "date": "Date",
    "product": "Product",
    "origin": "Origin",
    "category": "Category",
}

_FIXED_TOKENS = {
    "date": {"date", "dates", "report date", "reporting date", "day"},
    "product": {"product", "prouct", "products", "commodity", "item", "grade"},
    "origin": {"origin", "origins", "country", "source"},
    "category": {
        "price category", "category", "price cat", "price type", "type",
        "packing",
    },
}

_IGNORE = {
    "sl", "s.l", "sl no", "sl. no", "serial", "serial no", "note", "notes",
    "remark", "remarks", "comment", "comments", "unit", "month", "week",
    "average", "avg", "market average", "open market",
}

_UNIT_SUFFIX = re.compile(
    r"\s*[\(\[]\s*(?:rate|price)?\s*[/\-]?\s*"
    r"(?:mt|m\.?t\.?|mound|maund|ton|tonne|kg)\s*"
    r"(?:[/\-]\s*(?:mound|maund|mt|ton|kg))?\s*[\)\]]\s*$",
    re.IGNORECASE,
)


def _norm(value: object) -> str:
    text = str(value).replace("\ufeff", "").replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip().lower()


def _smart_title(text: str) -> str:
    """Title-case a label while keeping short acronyms (UAE, USA, MGI)."""
    words = []
    for word in str(text).split():
        if word.isupper() and (len(word) <= 4 or word in {"UAE", "USA", "UK", "EU"}):
            words.append(word)
        else:
            words.append(word[:1].upper() + word[1:].lower())
    return " ".join(words)


_PRODUCT_ACRONYMS = {
    "BBE", "KPC", "CWRS2", "AKC", "AEL", "MGI", "KBC", "PRAN",
    "SS", "TST", "JHM",
}


def _title_product(text: str) -> str:
    """Coal sheet names are ALL CAPS: make them readable, keep grade acronyms."""
    words = []
    for word in str(text).split():
        if word.isupper() and word in _PRODUCT_ACRONYMS:
            words.append(word)
        else:
            words.append(word[:1].upper() + word[1:].lower())
    return " ".join(words)


def _clean_competitor(name: str, cfg: config.SheetConfig) -> str:
    text = str(name).replace("\n", " ").replace("\r", " ")
    text = _UNIT_SUFFIX.sub("", text)
    text = re.sub(r"\s+", " ", text).strip(" -_")
    text = text.replace("_", " ").strip()

    for key, value in cfg.aliases.items():
        if text.casefold() == key.casefold():
            return value
    return text


def _fixed_column(column: str) -> str | None:
    token = _norm(column)
    for key, tokens in _FIXED_TOKENS.items():
        if token in tokens:
            return FIXED_NAMES[key]
    # Be tolerant of renamed / extended headers ("Product Name", "Origin Country").
    if "date" in token or token in {"day", "reporting period"}:
        return FIXED_NAMES["date"]
    if "product" in token or "prouct" in token or token in {"item", "commodity", "grade"}:
        return FIXED_NAMES["product"]
    if "origin" in token or "country" in token:
        return FIXED_NAMES["origin"]
    if "category" in token or "price type" in token or token == "type":
        return FIXED_NAMES["category"]
    return None


def _to_number(series: pd.Series) -> pd.Series:
    text = (
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("\u00a0", " ", regex=False)
        .str.strip()
    )
    text = text.mask(text.isin(["", "-", "–", "—", "nan", "None", "N/A", "NA", "#DIV/0!"]))
    return pd.to_numeric(text, errors="coerce")


def _to_date(series: pd.Series) -> pd.Series:
    if pd.api.types.is_datetime64_any_dtype(series):
        return pd.to_datetime(series, errors="coerce").dt.normalize()

    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.notna().sum() >= max(1, int(0.8 * len(series))):
        # Excel serial dates (rare after the export, but cheap to support).
        return pd.to_datetime(
            numeric, unit="D", origin="1899-12-30", errors="coerce"
        ).dt.normalize()

    text = series.astype(str).str.strip()
    parsed = pd.to_datetime(text, errors="coerce", dayfirst=False)
    return parsed.dt.normalize()


@dataclass
class Dataset:
    long: pd.DataFrame
    wide: pd.DataFrame
    competitors: list[str]
    products: list[str]
    origins: list[str]
    categories: list[str]
    unit: str
    unit_short: str
    source_quotes: int = 0
    duplicates_collapsed: int = 0


_PRODUCT_ORDER = ("wheat", "lentil", "chickpea", "yellowpea", "canola", "coal")


def _product_sort_key(name: str) -> tuple[int, str]:
    lowered = str(name).casefold()
    for index, token in enumerate(_PRODUCT_ORDER):
        if token in lowered:
            return (index, lowered)
    return (len(_PRODUCT_ORDER), lowered)


def prepare(raw: pd.DataFrame, cfg: config.SheetConfig) -> Dataset:
    if raw is None or raw.empty:
        raise ValueError("The sheet is empty.")

    frame = raw.copy()
    frame.columns = [str(c).replace("\n", " ").strip() for c in frame.columns]

    # Map the four fixed columns.  Unknown extra columns stay as candidate
    # competitor columns and are validated numerically below.
    rename: dict[str, str] = {}
    for column in frame.columns:
        fixed = _fixed_column(column)
        if fixed and fixed not in rename.values():
            rename[column] = fixed
    frame = frame.rename(columns=rename)

    if "Date" not in frame.columns or "Product" not in frame.columns:
        raise ValueError(
            "The sheet needs at least a Date column and a Product column. "
            f"Found: {', '.join(map(str, frame.columns))}"
        )

    if "Origin" not in frame.columns:
        frame["Origin"] = "—"
    if "Category" not in frame.columns:
        frame["Category"] = "All"

    frame["Date"] = _to_date(frame["Date"])
    frame["Product"] = frame["Product"].astype(str).str.replace("\n", " ", regex=False).str.strip()
    frame["Origin"] = frame["Origin"].astype(str).str.replace("\n", " ", regex=False).str.strip()
    frame["Category"] = frame["Category"].astype(str).str.replace("\n", " ", regex=False).str.strip()

    frame = frame.dropna(subset=["Date"])
    frame = frame[frame["Product"].ne("") & frame["Product"].ne("nan")]
    if cfg.title_products:
        frame["Product"] = frame["Product"].map(_title_product)
    frame["Origin"] = frame["Origin"].replace({"": "—", "nan": "—"})
    frame["Origin"] = frame["Origin"].map(_smart_title)
    frame["Category"] = frame["Category"].replace({"": "All", "nan": "All"})
    frame["Category"] = frame["Category"].map(
        lambda value: _smart_title(value) if value != "—" else value
    )

    competitor_columns: list[tuple[str, str]] = []
    used_names: set[str] = set()
    for column in frame.columns:
        if column in FIXED_NAMES.values():
            continue
        token = _norm(column)
        if not token or token.startswith("unnamed") or token in _IGNORE:
            continue
        if token in {"date", "product", "origin", "category"}:
            continue

        name = _clean_competitor(column, cfg)
        if not name:
            continue
        if name in used_names:
            suffix = 2
            while f"{name} ({suffix})" in used_names:
                suffix += 1
            name = f"{name} ({suffix})"
        used_names.add(name)

        frame[column] = _to_number(frame[column])
        if frame[column].notna().any():
            competitor_columns.append((column, name))

    if not competitor_columns:
        raise ValueError("No price columns were found in this sheet.")

    # Keep the sheet's row order so duplicate rows are resolved deterministically:
    # the bottom-most (most recently appended) quote wins for that competitor.
    frame = frame.reset_index(drop=True)
    frame["_row"] = range(len(frame))

    wide = frame[["Date", "Product", "Origin", "Category", "_row"]].copy()
    for column, name in competitor_columns:
        wide[name] = frame[column]

    competitors = [name for _, name in competitor_columns]
    wide = wide.dropna(subset=competitors, how="all").reset_index(drop=True)
    source_quotes = int((wide[competitors] > 0).sum().sum())

    long = wide.melt(
        id_vars=["Date", "Product", "Origin", "Category", "_row"],
        value_vars=competitors,
        var_name="Competitor",
        value_name="Price",
    )
    long = long.dropna(subset=["Price"])
    long = long[long["Price"] > 0]
    long = long.sort_values(["Date", "_row"])
    long = long.drop_duplicates(
        subset=["Date", "Product", "Origin", "Category", "Competitor"],
        keep="last",
    ).reset_index(drop=True)
    long = long.drop(columns="_row")
    wide = wide.drop(columns="_row")

    if long.empty:
        raise ValueError("The sheet has dates and products, but no valid prices.")

    present = set(long["Competitor"])
    competitors = [name for name in competitors if name in present]

    products = sorted(long["Product"].unique().tolist(), key=_product_sort_key)

    return Dataset(
        long=long,
        wide=wide,
        competitors=competitors,
        products=products,
        origins=sorted(long["Origin"].unique().tolist()),
        categories=sorted(long["Category"].unique().tolist()),
        unit=cfg.unit,
        unit_short=cfg.unit_short,
        source_quotes=source_quotes,
        duplicates_collapsed=max(0, source_quotes - len(long)),
    )


# ------------------------------------------------------------------- filtering
def apply_filters(
    dataset: Dataset,
    *,
    dates: list | None = None,
    products: list[str] | None = None,
    origins: list[str] | None = None,
    categories: list[str] | None = None,
    competitors: list[str] | None = None,
) -> pd.DataFrame:
    frame = dataset.long
    if dates:
        frame = frame[frame["Date"].isin(pd.to_datetime(list(dates)))]
    if products:
        frame = frame[frame["Product"].isin(products)]
    if origins:
        frame = frame[frame["Origin"].isin(origins)]
    if categories:
        frame = frame[frame["Category"].isin(categories)]
    if competitors:
        frame = frame[frame["Competitor"].isin(competitors)]
    return frame.copy()


def date_bounds(dataset: Dataset) -> tuple:
    return dataset.long["Date"].min(), dataset.long["Date"].max()


def top_product(dataset: Dataset) -> str:
    """The product with the most quotes recently — a useful opening view."""
    latest = dataset.long["Date"].max()
    recent = dataset.long[dataset.long["Date"] >= latest - pd.Timedelta(days=45)]
    if recent.empty:
        recent = dataset.long
    counts = recent.groupby("Product")["Price"].count()
    return str(counts.idxmax()) if not counts.empty else dataset.products[0]


# ------------------------------------------------------------------ summaries
def kpis(frame: pd.DataFrame) -> dict:
    latest = frame["Date"].max()
    today = frame[frame["Date"] == latest]
    average = float(today["Price"].mean())
    low = float(today["Price"].min())
    high = float(today["Price"].max())

    previous_dates = frame.loc[frame["Date"] < latest, "Date"]
    previous_average = None
    previous_date = None
    change = None
    change_pct = None
    if not previous_dates.empty:
        previous_date = previous_dates.max()
        previous_average = float(frame.loc[frame["Date"] == previous_date, "Price"].mean())
        change = average - previous_average
        change_pct = (change / previous_average * 100) if previous_average else None

    return {
        "latest": latest,
        "average": average,
        "low": low,
        "high": high,
        "previous_average": previous_average,
        "previous_date": previous_date,
        "change": change,
        "change_pct": change_pct,
        "competitors": int(today["Competitor"].nunique()),
        "observations": int(len(today)),
        "days": int(frame["Date"].nunique()),
    }


def daily_average(frame: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        frame.groupby("Date")["Price"]
        .agg(["mean", "min", "max", "count"])
        .reset_index()
        .rename(columns={"mean": "Average", "min": "Low", "max": "High", "count": "Quotes"})
    )
    return grouped


def latest_quotes(frame: pd.DataFrame) -> pd.DataFrame:
    """One row per competitor for the most recent reporting date.

    ``Prev`` is that competitor's own previous quote, which may be on an older
    date than the latest report.
    """
    if frame.empty:
        return pd.DataFrame()

    latest = frame["Date"].max()
    today = frame[frame["Date"] == latest]
    if today.empty:
        return pd.DataFrame()

    groups = []
    if today["Product"].nunique() > 1:
        groups.append("Product")
    if today["Category"].nunique() > 1:
        groups.append("Category")

    latest_rows = (
        today.groupby(groups + ["Competitor"], dropna=False)
        .agg(
            Price=("Price", "mean"),
            Origin=("Origin", lambda values: ", ".join(sorted(set(values)))),
        )
        .reset_index()
    )
    if "Category" not in groups:
        categories = (
            today.groupby(groups + ["Competitor"], dropna=False)["Category"]
            .agg(lambda values: ", ".join(sorted(set(values))))
            .reset_index()
        )
        latest_rows = latest_rows.merge(
            categories, on=groups + ["Competitor"], how="left"
        )
    latest_rows["LatestDate"] = latest

    history = frame[frame["Date"] < latest]
    if history.empty:
        latest_rows["Prev"] = pd.NA
    else:
        previous = (
            history.groupby(groups + ["Competitor", "Date"], dropna=False)["Price"]
            .mean()
            .reset_index()
            .sort_values("Date")
            .groupby(groups + ["Competitor"], dropna=False)
            .tail(1)
        )
        previous = previous.rename(columns={"Price": "Prev"})
        latest_rows = latest_rows.merge(
            previous[groups + ["Competitor", "Prev"]],
            on=groups + ["Competitor"],
            how="left",
        )

    stats = (
        frame.groupby(groups + ["Competitor"], dropna=False)["Price"]
        .agg(Quotes="count", Min="min", Max="max")
        .reset_index()
    )
    latest_rows = latest_rows.merge(stats, on=groups + ["Competitor"], how="left")

    latest_rows["Change"] = latest_rows["Price"] - latest_rows["Prev"]
    latest_rows["ChangePct"] = latest_rows["Change"] / latest_rows["Prev"] * 100

    if groups:
        market = latest_rows.groupby(groups)["Price"].transform("mean")
    else:
        market = pd.Series(latest_rows["Price"].mean(), index=latest_rows.index)
    latest_rows["VsMarket"] = latest_rows["Price"] - market

    sort_cols = groups + ["Price"]
    latest_rows = latest_rows.sort_values(sort_cols, ascending=[True] * len(groups) + [True])
    return latest_rows.reset_index(drop=True)


def matrix(frame: pd.DataFrame) -> pd.DataFrame:
    """Date × competitor table, the shape most people recognise from the sheet."""
    if frame.empty:
        return pd.DataFrame()

    index = ["Date"]
    if frame["Product"].nunique() > 1:
        index.append("Product")
    if frame["Origin"].nunique() > 1:
        index.append("Origin")
    if frame["Category"].nunique() > 1:
        index.append("Category")

    table = (
        frame.pivot_table(
            index=index,
            columns="Competitor",
            values="Price",
            aggfunc="mean",
        )
        .reset_index()
        .sort_values(index)
    )
    table.columns.name = None
    return table


def detail_rows(frame: pd.DataFrame) -> pd.DataFrame:
    table = frame[["Date", "Product", "Origin", "Category", "Competitor", "Price"]].copy()
    table = table.sort_values(["Date", "Product", "Competitor"], ascending=[False, True, True])
    table["Date"] = table["Date"].dt.strftime("%Y-%m-%d")
    return table
