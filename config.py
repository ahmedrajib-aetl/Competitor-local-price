"""Configuration for the Khatunganj competitor price dashboard.

Everything that changes when a new sheet is added lives here.  A page is
generated automatically for every SheetConfig in ``SHEETS``.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ------------------------------------------------------------------ behaviour
# How long a downloaded source is reused before it is downloaded again.
# 3600 = one hour. "Refresh now" always bypasses this.
CACHE_TTL_SECONDS = 3600

# The page quietly refreshes itself on this interval (seconds).
# 3600 = once an hour.
AUTO_REFRESH_SECONDS = 3600

REQUEST_TIMEOUT_SECONDS = 45

# Show a prominent warning when the newest row in the connected tab is older
# than this many days.  It usually means the sheet was updated in another tab.
STALE_AFTER_DAYS = 2


@dataclass(frozen=True)
class SheetConfig:
    """One dashboard page backed by one Google Sheet tab."""

    key: str                       # short id, also used for URL + widget keys
    label: str                     # sidebar / page name
    title: str                     # big heading
    subtitle: str
    icon: str
    sheet_id: str
    tab_name: str | None           # Excel tab name (used for the xlsx export)
    gid: int | None                # tab id (used for the lighter CSV export)
    unit: str                      # e.g. "BDT/MT"
    unit_short: str                # e.g. "MT"
    snapshot: str                  # bundled fallback CSV, relative to this repo
    source_note: str
    product_pills: bool = True     # True = button style, False = dropdown
    own_brand: str = "AEL"         # thicker line for our own company
    title_products: bool = False   # tidy ALL-CAPS product names (coal)
    mode: str = "wide"             # "wide" = competitor columns, "long" = one row per quote
    source_type: str = "sheets"    # "sheets" = native Google Sheet, "drive" = uploaded xlsx
    source_url: str | None = None  # optional custom link shown in the app
    aliases: dict[str, str] = field(default_factory=dict)

    @property
    def sheet_url(self) -> str:
        return self.source_url or f"https://docs.google.com/spreadsheets/d/{self.sheet_id}/edit"


# ---------------------------------------------------------------------- pages
COAL = SheetConfig(
    key="coal",
    label="Coal",
    title="Coal — Market Database",
    subtitle="Khatunganj coal market · BDT per metric ton · location, importer, origin & mine",
    icon="⛏️",
    sheet_id="1EQBuUlDPQS3fPP5yOTfWe-R9JPml1kT0",
    tab_name="Master Database",
    gid=None,
    unit="BDT/MT",
    unit_short="MT",
    snapshot="data/coal_snapshot.csv",
    source_note="Coal Market Database · Master Database",
    product_pills=False,
    own_brand="",
    title_products=False,
    mode="long",
    source_type="drive",
    source_url="https://docs.google.com/spreadsheets/d/1EQBuUlDPQS3fPP5yOTfWe-R9JPml1kT0/edit?usp=sharing&rtpof=true&sd=true",
    aliases={
        "Sheikh Bhorthers": "Sheikh Brothers",
    },
)

GRAIN = SheetConfig(
    key="grain",
    label="Grain",
    title="Grain — Competitor Local Price",
    subtitle="Khatunganj daily retail price · BDT per maund · wheat, lentils, chickpeas, yellowpeas, canola",
    icon="🌾",
    sheet_id="1nJ1VUWi7c_k_2_qOoiOUjGxBE67dIiFztzYDjhl5j-4",
    tab_name="Khatunganj",
    gid=None,
    unit="BDT/mound",
    unit_short="mound",
    snapshot="data/grain_snapshot.csv",
    source_note="Khatunganj competitor local price · daily collection",
    product_pills=True,
    aliases={
        "Noapara group": "Noapara Group",
        "Bishwas": "Bishwas",
        "Consortium (Saroda, Payel, King)": "Consortium",
        "SS Enterprise": "SS Enterprise",
    },
)

# ----------------------------------------------------------------- stock pages
GRAIN_STOCK = SheetConfig(
    key="grain_stock",
    label="Grain Stock",
    title="Grain — Daily Stock Report",
    subtitle="Grain stock by product, item, plant and warehouse · quantity in MT and value in BDT",
    icon="📦",
    sheet_id="1a2zNQH_9xPKaE_D7eH67LDb-BoHnlD4A3aoL65FYb34",
    tab_name="Master Data",
    gid=None,
    unit="MT",
    unit_short="MT",
    snapshot="data/grain_stock_snapshot.csv",
    source_note="AEL Daily Stock Report · Master Data",
    product_pills=False,
    own_brand="",
    mode="stock",
)

COAL_STOCK = SheetConfig(
    key="coal_stock",
    label="Coal Stock",
    title="Coal — Daily Stock Report",
    subtitle="Coal stock by SBU, warehouse and item · physical quantity in MT and value in BDT",
    icon="📦",
    sheet_id="1sTYUr8gksQx_zu8hPAtwykMr2aU93g-Wh7-asI0yQfg",
    tab_name="Master Data",
    gid=None,
    unit="MT",
    unit_short="MT",
    snapshot="data/coal_stock_snapshot.csv",
    source_note="AEL Daily Stock Report · Master Data",
    product_pills=False,
    own_brand="",
    mode="stock",
)

# Add another SheetConfig here later (e.g. rice, sugar) and a third page will
# appear automatically — no other code changes needed.
SHEETS: list[SheetConfig] = [COAL, GRAIN]
STOCKS: list[SheetConfig] = [GRAIN_STOCK, COAL_STOCK]


def get_sheet(key: str) -> SheetConfig:
    for sheet in [*SHEETS, *STOCKS]:
        if sheet.key == key:
            return sheet
    raise KeyError(f"Unknown sheet: {key}")
