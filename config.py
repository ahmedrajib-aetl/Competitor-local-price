"""Configuration for the Khatunganj competitor price dashboard.

Everything that changes when a new sheet is added lives here.  A page is
generated automatically for every SheetConfig in ``SHEETS``.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ------------------------------------------------------------------ behaviour
# How long a downloaded sheet is reused before Google is asked again.  Keep this
# short: the dashboard is meant to show the market as it is now.
CACHE_TTL_SECONDS = 30

# The page quietly refreshes itself on this interval (seconds).  Set to None to
# disable the automatic refresh entirely.
AUTO_REFRESH_SECONDS = 60

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
    aliases: dict[str, str] = field(default_factory=dict)

    @property
    def sheet_url(self) -> str:
        return f"https://docs.google.com/spreadsheets/d/{self.sheet_id}/edit"


# ---------------------------------------------------------------------- pages
COAL = SheetConfig(
    key="coal",
    label="Coal",
    title="Coal — Competitor Local Price",
    subtitle="Khatunganj daily retail price · BDT per metric ton · coal grades by origin",
    icon="⛏️",
    sheet_id="1RMKAzbjWvWm0KmDIyM_cR_N0OvHhECTZZPyT-4Hx4Jg",
    tab_name="COAL APPX PRICE",
    gid=1780791072,
    unit="BDT/MT",
    unit_short="MT",
    snapshot="data/coal_snapshot.csv",
    source_note="Coal Appx Price · Khatunganj daily collection",
    product_pills=True,
    own_brand="Akij Bongo Traders",
    title_products=True,
    aliases={
        "Akij_Bongo Traders Ltd.": "Akij Bongo Traders",
        "Akij Bongo Traders Ltd.": "Akij Bongo Traders",
        "NABIL GRP": "Nabil Group",
        "SHAHARA": "Shahara",
        "NOAPARA": "Noapara",
        "SHEIKH": "Sheikh",
        "SABISA": "Sabisa",
        "ABUL KHAIR": "Abul Khair",
        "TST/JHM": "TST / JHM",
        "SARKER": "Sarker",
        "SOINIK": "Soinik",
        "BASHUNDHARA": "Bashundhara",
        "CROWN": "Crown",
        "Meghna Group": "Meghna Group",
        "FAKR UDDIN": "Fakr Uddin",
        "FALAL UDDIN": "Falal Uddin",
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

# Add another SheetConfig here later (e.g. rice, sugar) and a third page will
# appear automatically — no other code changes needed.
SHEETS: list[SheetConfig] = [COAL, GRAIN]


def get_sheet(key: str) -> SheetConfig:
    for sheet in SHEETS:
        if sheet.key == key:
            return sheet
    raise KeyError(f"Unknown sheet: {key}")
