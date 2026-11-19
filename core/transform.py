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


# ===================================================================== long mode
# Coal Master Database: one row per importer / product / mine quote.  There are
# no competitor columns; the "competitor" is the Importers / Traders column.

_LONG_COLUMNS = {
    "Date": {"date"},
    "Location": {"location", "dumping point", "dumping location"},
    "Competitor": {
        "importers/ traders", "importers/traders", "importers / traders",
        "importer", "trader", "importers", "importer / trader",
    },
    "Origin": {"origin", "country of origin", "country"},
    "Grade": {"coal grade / cal (kcal)", "coal grade", "grade", "cal", "kcal"},
    "Mine": {"mine", "mine / grade", "mine/grade", "coal mine"},
    "Quantity": {"quantity (mt)", "quantity", "qty", "quantity mt"},
    "Price": {"sale / retail rate (bdt/mt)", "sale/retail rate", "rate",
              "sale rate", "retail rate", "price"},
    "Status": {"status"},
    "Remarks": {"remarks", "remark", "remarks "},
    "Vessel": {"vessel name", "vessel"},
    "VesselQty": {"vessel qty (mt)", "vessel qty", "vessel quantity"},
}


def _long_key(column: str) -> str | None:
    token = _norm(column)
    for canonical, names in _LONG_COLUMNS.items():
        if token in names:
            return canonical
    # Tolerant fallbacks for renamed headers.
    if "date" in token:
        return "Date"
    if "importer" in token or "trader" in token:
        return "Competitor"
    if "origin" in token or "country" in token:
        return "Origin"
    if "location" in token or "dumping point" in token:
        return "Location"
    if "grade" in token or token.endswith("kcal") or "cal (" in token:
        return "Grade"
    if token.startswith("mine"):
        return "Mine"
    if "quantity" in token:
        return "Quantity"
    if "vessel" in token and "qty" in token:
        return "VesselQty"
    if "vessel" in token:
        return "Vessel"
    if "sale" in token or "retail" in token or token == "price" or "rate" in token:
        return "Price"
    if "status" in token:
        return "Status"
    if "remark" in token:
        return "Remarks"
    return None


def _clean_label(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).replace("\n", " ").replace("\r", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return "" if text.lower() in {"nan", "none", "nat"} else text


@dataclass
class LongDataset:
    long: pd.DataFrame
    competitors: list[str]
    locations: list[str]
    origins: list[str]
    mines: list[str]
    remarks: list[str]
    unit: str
    unit_short: str
    source_quotes: int = 0
    rows: int = 0

    @property
    def products(self) -> list[str]:
        return []


def prepare_long(raw: pd.DataFrame, cfg: config.SheetConfig) -> LongDataset:
    """Clean the Coal Master Database (one quote per row)."""
    if raw is None or raw.empty:
        raise ValueError("The Master Database is empty.")

    frame = raw.copy()
    frame.columns = [str(c).replace("\n", " ").strip() for c in frame.columns]

    rename: dict[str, str] = {}
    for column in frame.columns:
        key = _long_key(column)
        if key and key not in rename.values():
            rename[column] = key
    frame = frame.rename(columns=rename)

    if "Date" not in frame.columns or "Competitor" not in frame.columns:
        raise ValueError(
            "The Master Database needs a Date column and an Importers / Traders "
            f"column. Found: {', '.join(map(str, frame.columns))}"
        )

    for column in ("Location", "Origin", "Mine", "Grade", "Quantity", "Price",
                   "Status", "Remarks", "Vessel", "VesselQty"):
        if column not in frame.columns:
            frame[column] = ""

    frame["Date"] = _to_date(frame["Date"])
    frame["Competitor"] = frame["Competitor"].map(_clean_label)
    frame["Location"] = frame["Location"].map(_clean_label)
    frame["Origin"] = frame["Origin"].map(_clean_label).map(_smart_title)
    frame["Mine"] = frame["Mine"].map(_clean_label)
    frame["Grade"] = frame["Grade"].map(_clean_label)
    frame["Status"] = frame["Status"].map(_clean_label)
    frame["Remarks"] = frame["Remarks"].map(_clean_label)
    frame["Vessel"] = frame["Vessel"].map(_clean_label)
    frame["Quantity"] = _to_number(frame["Quantity"])
    frame["Price"] = _to_number(frame["Price"])

    for source, target in cfg.aliases.items():
        frame["Competitor"] = frame["Competitor"].replace(source, target)

    frame = frame.dropna(subset=["Date"])
    frame = frame[frame["Competitor"].ne("") & frame["Competitor"].str.lower().ne("nan")]
    frame = frame[frame["Competitor"].ne("Importers/ Traders")]
    # A zero / negative rate is a not-yet-quoted vessel row, not a real price.
    frame["Price"] = frame["Price"].where(frame["Price"] > 0)
    frame["Quantity"] = frame["Quantity"].where(frame["Quantity"] >= 0)
    frame = frame.reset_index(drop=True)

    if frame.empty:
        raise ValueError("No dated importer rows were found in the Master Database.")

    def unique(column: str) -> list[str]:
        values = frame[column].dropna().map(lambda v: _clean_label(v))
        return sorted({value for value in values if value}, key=str.casefold)

    return LongDataset(
        long=frame,
        competitors=unique("Competitor"),
        locations=unique("Location"),
        origins=unique("Origin"),
        mines=unique("Mine"),
        remarks=unique("Remarks"),
        unit=cfg.unit,
        unit_short=cfg.unit_short,
        source_quotes=int(frame["Price"].notna().sum()),
        rows=len(frame),
    )


def filter_long(
    dataset: LongDataset,
    *,
    dates: list | None = None,
    locations: list[str] | None = None,
    competitors: list[str] | None = None,
    origins: list[str] | None = None,
    mines: list[str] | None = None,
    remarks: list[str] | None = None,
) -> pd.DataFrame:
    frame = dataset.long
    if dates:
        frame = frame[frame["Date"].isin(pd.to_datetime(list(dates)))]
    if locations:
        frame = frame[frame["Location"].isin(locations)]
    if competitors:
        frame = frame[frame["Competitor"].isin(competitors)]
    if origins:
        frame = frame[frame["Origin"].isin(origins)]
    if mines:
        frame = frame[frame["Mine"].isin(mines)]
    if remarks:
        frame = frame[frame["Remarks"].isin(remarks)]
    return frame.copy()


def long_summary(frame: pd.DataFrame) -> tuple[pd.DataFrame, object, dict]:
    """Origin-wise quantity and average rate for the latest date in the filter."""
    if frame.empty:
        return pd.DataFrame(), None, {}
    latest = frame["Date"].max()
    today = frame[frame["Date"] == latest].copy()
    if today.empty:
        return pd.DataFrame(), latest, {}
    today["Origin"] = today["Origin"].replace("", "Unknown")

    rows = (
        today.groupby("Origin", dropna=False)
        .agg(
            Quantity=("Quantity", "sum"),
            AverageRate=("Price", "mean"),
            Lines=("Date", "size"),
        )
        .reset_index()
    )
    rows = rows.sort_values("Origin", key=lambda series: series.str.casefold())
    total = {
        "Origin": "Grand Total",
        "Quantity": today["Quantity"].sum(),
        "AverageRate": today["Price"].mean(),
        "Lines": len(today),
    }
    return rows, latest, total


def latest_long_quotes(frame: pd.DataFrame) -> pd.DataFrame:
    """One row per importer/trader on the latest date in the filter."""
    if frame.empty:
        return pd.DataFrame()
    latest = frame["Date"].max()
    today = frame[(frame["Date"] == latest) & frame["Price"].notna()].copy()
    if today.empty:
        return pd.DataFrame()

    quotes = (
        today.groupby("Competitor")
        .agg(
            Price=("Price", "mean"),
            Quantity=("Quantity", "sum"),
            Quotes=("Price", "size"),
            Min=("Price", "min"),
            Max=("Price", "max"),
        )
        .reset_index()
    )

    def meta_for(day: pd.DataFrame) -> str:
        parts: list[str] = []
        for _, row in day.drop_duplicates(["Origin", "Mine"]).iterrows():
            label = row["Origin"] or "Unknown"
            if row["Mine"]:
                label += " · " + row["Mine"]
            if label not in parts:
                parts.append(label)
        if len(parts) > 2:
            return " | ".join(parts[:2]) + f" +{len(parts) - 2} more"
        return " | ".join(parts)

    by_competitor = today.groupby("Competitor")
    meta = by_competitor.apply(meta_for, include_groups=False)
    quotes["Meta"] = quotes["Competitor"].map(meta)

    history = frame[(frame["Date"] < latest) & frame["Price"].notna()]
    if history.empty:
        quotes["Prev"] = pd.NA
    else:
        previous = (
            history.groupby(["Competitor", "Date"])["Price"].mean().reset_index()
            .sort_values("Date").groupby("Competitor").tail(1)
            .rename(columns={"Price": "Prev"})
        )
        quotes = quotes.merge(previous[["Competitor", "Prev"]], on="Competitor", how="left")

    quotes["Change"] = quotes["Price"] - quotes["Prev"]
    quotes["ChangePct"] = quotes["Change"] / quotes["Prev"] * 100
    quotes["VsMarket"] = quotes["Price"] - quotes["Price"].mean()
    quotes["LatestDate"] = latest
    return quotes.sort_values("Price").reset_index(drop=True)


def long_matrix(frame: pd.DataFrame) -> pd.DataFrame:
    data = frame.dropna(subset=["Price"])
    if data.empty:
        return pd.DataFrame()
    table = (
        data.pivot_table(index="Date", columns="Competitor", values="Price", aggfunc="mean")
        .reset_index()
    )
    table.columns.name = None
    return table


def long_detail(frame: pd.DataFrame) -> pd.DataFrame:
    columns = ["Date", "Location", "Competitor", "Origin", "Mine", "Grade",
               "Quantity", "Price", "Status", "Remarks"]
    table = frame[columns].copy()
    table = table.sort_values(["Date", "Competitor"], ascending=[False, True])
    table["Date"] = table["Date"].dt.strftime("%Y-%m-%d")
    return table.rename(
        columns={
            "Competitor": "Importers / Traders",
            "Price": "Sale / Retail Rate (BDT/MT)",
            "Quantity": "Quantity (MT)",
            "Mine": "Mine / Grade",
        }
    )
