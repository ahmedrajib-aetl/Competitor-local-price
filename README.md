# AEL Trading — Market & Stock Dashboard

Four pages in one app:

| Page | Source | Unit | Status |
|---|---|---|---|
| **Coal** | `Master Database` tab of the Coal Market Database (Google Drive `.xlsx`) | BDT/MT | Live |
| **Grain** | `Khatunganj` tab of the grain Google Sheet | BDT/mound | Snapshot until the sheet is shared (see below) |
| **Grain Stock** | `Master Data` tab of the Grain stock workbook | MT · BDT | Live |
| **Coal Stock** | `Master Data` tab of the Coal stock workbook | MT · BDT | Live |

The two price pages are the original V1 dashboard and are unchanged. The stock
pages are additive. A page is generated automatically for every `SheetConfig`
in `config.SHEETS` (price) or `config.STOCKS` (stock).

---

## What it does

- **Filters with search everywhere**
  - **Date dropdown**: all dates, last 7 / 30 / 90 days, the latest report, or a
    specific month.
  - **Coal filters**: Location, Importers / Traders, Origin, Mine, Remarks — all
    searchable dropdowns.
  - **Grain filters**: Product buttons with **All** and search, Origin, Price
    category buttons **All / Bag / Lighter**, and Competitor.
  - An empty dropdown means **All**.
  - **Stock pages**: Date (latest by default), Search, and Product/SBU, Item Name,
    Plant (Grain only) and Warehouse dropdowns.
- **Coal latest-date origin summary**: Country of Origin, Date, Dumping Quantity
  (MT), Average Sale / Retail Rate and a Grand Total. It always uses the newest
  date inside the current filter, so it moves to 16 Nov automatically when the
  Master Database gets a 16 Nov row.
- **Grain Stock / Coal Stock**: the latest date in `Master Data` is selected
  automatically; KPIs show total quantity, total value, items, warehouses,
  plants and average rate (with deltas vs the previous date). Tabs show
  quantity/value charts and tables for product/SBU, item, plant (Grain) and
  warehouse, plus an overall stock table and CSV download.
- **One single day-wise chart**
  - **Coal**: one line per importer / trader; names sit at the line ends. Hover
    a line to see that importer's price for every **Origin + Mine/Grade** (e.g.
    `South Africa · SA RB2 5700 Kcal — 19,500`).
  - **Grain**: one line per competitor; hover shows every product / origin /
    category price behind the average.
  - No legend box. Labels are collision-spaced and colour-matched to the lines;
    the grey dashed line is the market average.
- **Latest quotes table**: cheapest first, previous quote, change, % change,
  number of quotes, min–max, and the gap to the market average. Coal adds the
  origin / mine under each importer.
- **Detail exports**: day × competitor/importer matrix, all filtered rows, the
  latest quotes and the coal origin summary — each downloadable as CSV.
- **Live updates**: the source is read again after 1 hour; the page refreshes
  itself every hour. **Refresh now** in the header or sidebar forces an
  immediate pull and clears the cache. Every response is cache-busted.
- **Two data shapes**: Grain uses competitor columns (wide); Coal uses one row
  per quote in the Master Database (long). Both auto-detect their columns.

---

## Run locally

```powershell
cd competitor-price-dashboard
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Or double-click `run.bat`. The first run creates a local `.venv` and installs the
dependencies (a few minutes); later runs start immediately. `run.bat` also stops
any older dashboard still holding port 8501, so the browser always opens the
current version.

The app opens at <http://localhost:8501>. Pages:

- `/` — Coal price (V1)
- `/grain` — Grain price (V1)
- `/grain-stock` — Grain warehouse stock
- `/coal-stock` — Coal warehouse stock

The stock pages read only the `Master Data` tab of their stock workbook; older
dated tabs in the workbook are ignored.

---

## Make the Grain sheet live (important)

The Grain Google Sheet is currently **private** — Google returns a sign-in page,
so the dashboard shows the bundled snapshot (data to 14 Oct 2026). Choose one of
these two fixes:

### Option A — share the sheet (fastest)

In the Grain Google Sheet: **Share → General access → Anyone with the link →
Viewer**. Nothing else is needed; the dashboard will switch to live data on the
next refresh. This is fine if the sheet contains only market prices.

### Option B — service account (keeps the sheet private)

1. Create a Google Cloud project and enable the **Google Sheets API** and
   **Google Drive API**.
2. Create a **service account**, then create a **JSON key** for it.
3. Share the Grain Google Sheet with the service account's `client_email` as
   **Viewer**.
4. Add the key to Streamlit secrets (locally in
   `.streamlit/secrets.toml`, on Streamlit Cloud in **App settings → Secrets**):

```toml
[gcp_service_account]
type = "service_account"
project_id = "your-project"
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "dashboard-reader@your-project.iam.gserviceaccount.com"
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
```

The app tries the public export first, then this service account, then the local
snapshot. The sidebar tells you which mode is active.

---

## Publish to Streamlit Community Cloud

1. Push this folder to a GitHub repository. Do **not** commit
   `.streamlit/secrets.toml`.
2. Go to <https://share.streamlit.io> → **New app** → choose the repo/branch and
   set **Main file path** to `competitor-price-dashboard/app.py` (or `app.py` if
   the repo root is this folder).
3. If you use Option B, paste the `[gcp_service_account]` block into
   **Advanced settings → Secrets**.
4. Deploy. The app reads the live sources on every refresh.

`requirements.txt` is already pinned to the libraries Streamlit Cloud needs.

---

## Add another sheet later (rice, sugar, …)

1. Put a fallback copy in `data/` (CSV with the header in the first row).
2. Add a `SheetConfig` in `config.py`:

```python
RICE = SheetConfig(
    key="rice",
    label="Rice",
    title="Rice — Competitor Local Price",
    subtitle="Khatunganj daily retail price · BDT per maund",
    icon="🍚",
    sheet_id="THE_GOOGLE_SHEET_ID",
    tab_name="Khatunganj",          # or None to use the first tab
    gid=None,                       # or the tab gid for a faster CSV read
    unit="BDT/mound",
    unit_short="mound",
    snapshot="data/rice_snapshot.csv",
    source_note="Rice competitor local price",
    mode="wide",                    # "wide" = competitor columns; "long" = one row per quote
    source_type="sheets",           # "sheets" = Google Sheet; "drive" = uploaded .xlsx
    product_pills=True,
    own_brand="AEL",
    aliases={"Some Sheet Spelling": "Nice Name"},
)
SHEETS.append(RICE)
```

A new page and sidebar item appear automatically. Use `mode="long"` for a
Master-Database-style sheet with Importers/Traders, Origin, Mine, Quantity and
Rate columns. For a warehouse stock page, append a similar config to `STOCKS`
with `mode="stock"` and `tab_name="Master Data"`.

### Current sheet layouts

The dashboard reads each source's real headers, not a hard-coded list:

- **Coal — `Master Database`** (long format, one row per quote):
  `Date, Location, Importers/Traders, Origin, Coal Grade / Cal (kcal), Mine,
  Quantity (MT), Sale / Retail Rate (BDT/MT), Status, Remarks, Vessel Name,
  Vessel Qty (MT)`. The `Importers/Traders` column is the chart's competitor
  dimension; the `Mine` column usually carries the grade (e.g.
  `SA RB2 5700 Kcal`).
- **Grain — `Khatunganj`** (wide format, competitor columns): `Date, Prouct,
  Origin, Price Category` plus 17 `rate/mound` columns (AEL, MGI, Nabil, PRAN,
  Modina, Sheikh Brothers, Bishwas, KBC, City Commodities, Akij Sunshine,
  Noapara Group, Bismillah Group, AKC, Crown, Hasan Brothers, SS Enterprise,
  Consortium).
- **Grain Stock — `Master Data`**: `Date, Product (Bulk), Item Name, Code, UOM,
  Qty, Value, Plant, Warehouse` (27 rows / 3 dates in the current copy).
- **Coal Stock — `Master Data`**: `Date, SBU, Warehouse, Item Name, Code,
  Physical Qty (MT) 4th lot, Value(BDT)` (8 rows / 2 dates in the current copy).
  Only `Master Data` is used; the dated tabs in the workbooks are backups.

### Stock pages (V2)

- **Grain Stock** — sheet `1a2zNQH_9xPKaE_D7eH67LDb-BoHnlD4A3aoL65FYb34`,
  tab `Master Data`.
- **Coal Stock** — sheet `1sTYUr8gksQx_zu8hPAtwykMr2aU93g-Wh7-asI0yQfg`,
  tab `Master Data`.

The newest date in `Master Data` is selected automatically. The page shows total
quantity, total value, items, warehouses, plants and average rate (with deltas vs
the previous date), charts/tables by product/SBU, item, plant and warehouse, and
an overall table/CSV. Zero-stock warehouses still appear. A yellow banner warns
when the newest date in `Master Data` is more than 2 days old — update that tab,
not the dated backup tabs.

### How columns are detected

- **Grain (wide)** — fixed columns are found by name:
  `Date`/`Prouct`/`Product Name`, `Origin`/`Country`, `Price Category`/`Category`/`Type`.
  A title row above the header is skipped automatically. Every other column is
  treated as a competitor; a trailing `(rate/MT)` or `(rate/mound)` is removed
  from the display name.
- **Coal price (long)** — the Master Database columns are mapped by name: Date,
  Location, Importers/Traders, Origin, Coal Grade/Cal, Mine, Quantity, Sale/
  Retail Rate, Status, Remarks. Extra columns are ignored. A blank or zero rate
  is treated as “no quote” (the row still counts toward quantity).
- **Stock (Master Data)** — maps Date, Product/SBU, Item Name, Code, Warehouse,
  Plant, Qty, Value and UOM. Blank item rows with zero quantity are kept so
  warehouses with no stock still appear.
- Completely empty `Unnamed` columns and empty trailing rows are ignored.
- `aliases` in `config.py` cleans up sheet spellings (e.g.
  `Sheikh Bhorthers` → `Sheikh Brothers`).
- If a tab name changes, update `tab_name` (and `gid` if you use one). The app
  falls back to the first tab and shows a note if the configured tab is missing.

---

## Files

```
app.py                     page setup, navigation, sidebar status
config.py                  sheet/page configuration
core/source.py             Google Sheet / Drive → service account → snapshot
core/transform.py          cleaning, long format, filters, tables
core/stock.py              warehouse stock cleaning and summaries
core/charts.py             Plotly single day-wise price chart and stock bars
core/ui.py                 theme, header, KPI cards, quote/stock tables
views/competitor.py        the shared price page (Coal and Grain)
views/stock.py             the shared stock page (Grain Stock and Coal Stock)
data/*_snapshot.csv        offline fallback copies
.streamlit/config.toml     dark theme
```

---

## Why the dashboard may not show new rows

The page shows exactly what is in the **connected source**. The exact tab, its
newest row, and the fetch time are always shown at the top and in the sidebar.

1. **Status: Live, but Latest row is old**
   The connected source has no newer rows. The dashboard is reading it live.
   For Coal, make sure the new rows are in the `Master Database` tab of the
   connected workbook. If you moved to a different file, update `sheet_id` /
   `tab_name` in `config.py`. A yellow banner appears automatically when the
   source is more than 2 days behind.

2. **Status: Snapshot**
   The source is private (Google returns HTTP 401), so the app is using
   `data/*_snapshot.csv`. Share it as **Anyone with the link · Viewer**, or add
   the service account from Option B above. Updating a private file cannot be
   seen by the dashboard.

3. **You just edited the source**
   Click **Refresh now**. The app caches for 1 hour and auto-refreshes hourly;
   the button bypasses both.

4. **You clicked `run.bat` and still see the old page**
   `run.bat` now stops any old dashboard on port 8501, uses the local `.venv`,
   starts the new version, and opens the browser. Refresh the browser tab once.

5. **Grain specifically**
   The Grain Google Sheet is still private. The Grain page will remain a
   snapshot until that sheet is shared or a service account is configured.

6. **Stock pages**
   Grain Stock and Coal Stock read only the `Master Data` tab. Update that tab;
   the dated tabs are backups and are ignored. The yellow banner tells you the
   newest date in `Master Data` (Coal is currently 04 Nov, so that is what the
   Coal Stock page shows).

## Notes and troubleshooting

- **Prices are shown exactly as reported** in the source. The summary and tables
  include every row. The Coal chart has an optional **Trim extreme outliers**
  switch (on by default) so one bad quote does not flatten the chart; untick it
  to see the full range. Stock quantities/values are shown exactly as iBOS
  reports them.
- A full cell-by-cell audit of the price pages is in
  [`DATA_CHECK.md`](DATA_CHECK.md).
- **Grain duplicates:** if the sheet repeats the same competitor/date/product/
  origin/category, the bottom-most entry is kept and the sidebar reports how many
  quotes were collapsed (currently 21 on Grain). The Coal Master Database is
  long-format and keeps every row; nothing is deduplicated.
- If a chart looks empty, change the date filter or clear the product/importer/
  origin/mine/remarks filters. The page shows an explicit empty state rather than
  a blank chart.
- The page reads Google's public CSV/XLSX export, so the sheet must remain
  viewable by link (Option A) or shared with the service account (Option B).
- Streamlit deep links: Coal price is the default at `/`; Grain price at
  `/grain`; Grain Stock at `/grain-stock`; Coal Stock at `/coal-stock`. Use the
  sidebar navigation rather than typing `/coal`.
- Snapshot files are only fallbacks. Replace them occasionally if the live sheet
  will be unavailable for a long period.
