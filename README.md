# Khatunganj Competitor Local Price — Streamlit dashboard

Two pages, one per market:

| Page | Sheet | Unit | Status |
|---|---|---|---|
| **Coal** | `COAL APPX PRICE` tab of the coal Google Sheet | BDT/MT | Live (sheet is public) |
| **Grain** | `Khatunganj` tab of the grain Google Sheet | BDT/mound | Snapshot until the sheet is shared (see below) |

A page is generated automatically for every `SheetConfig` in `config.py`, so
adding a third market later is a small config change — not a rewrite.

---

## What it does

- **Filters with search everywhere**
  - **Date dropdown**: all dates, last 7 / 30 / 90 days, the latest report, or a
    specific month.
  - Product buttons with **All** and a search box (both Coal and Grain).
  - Origin and competitor dropdowns, both searchable.
  - **Price category buttons** on Grain: **All / Bag / Lighter** (Coal is Retail only).
  - An empty dropdown means **All**.
- **One single day-wise chart**: one line per competitor across the selected
  products, with the full competitor legend. AEL / Akij Bongo is highlighted and
  the grey dashed line is the market average. When **All** products (or several
  origins / categories) are selected, each date is that competitor's average for
  the selected quotes; hover shows the product, quote count and source. Pick one
  product for an exact product-wise line. Click a legend item to hide/show a
  competitor; double-click to isolate it.
- **Latest quotes table**: cheapest first within each product / price category,
  previous quote, change, % change, number of quotes, min–max, and the gap to the
  market average.
- **Detail exports**: day × competitor matrix, all filtered rows, and the latest
  quotes — each downloadable as CSV.
- **Live updates**: Google is read again after 30 seconds; the page refreshes
  itself every minute. **Refresh now** in the header or sidebar forces an
  immediate pull and clears the cache. Every response is cache-busted, so
  Google's CDN cannot serve an older export.
- **Flexible columns**: competitor columns are discovered from the sheet. If a
  new company column is added (with a rate/MT or rate/mound header), the
  dashboard picks it up on the next refresh with no code change.

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

The app opens at <http://localhost:8501>. Coal is the default page; Grain is at
`/grain` (or click **Grain** in the sidebar).

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
4. Deploy. The app reads the live sheets on every refresh.

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
    product_pills=True,
    own_brand="AEL",
    aliases={"Some Sheet Spelling": "Nice Name"},
)
SHEETS.append(RICE)
```

A new page and sidebar item appear automatically.

### Current sheet layouts

The dashboard reads each tab's real headers, not a hard-coded list:

- **Coal — `COAL APPX PRICE`**: `Date, Product, Origin, Price Category` plus
  15 `rate/MT` columns (Akij Bongo Traders, Nabil Group, Shahara, Noapara,
  TST/JHM, Sheikh, Sabisa, Abul Khair, Sarker, Soinik, Bashundhara, Crown,
  Meghna Group, Fakr Uddin, Falal Uddin). Fakr Uddin has no prices in the current
  data, so 14 active competitors are shown.
- **Grain — `Khatunganj`**: `Date, Prouct, Origin, Price Category` plus 17
  `rate/mound` columns (AEL, MGI, Nabil, PRAN, Modina, Sheikh Brothers, Bishwas,
  KBC, City Commodities, Akij Sunshine, Noapara Group, Bismillah Group, AKC,
  Crown, Hasan Brothers, SS Enterprise, Consortium).

The company list in the brief (AEL, MGI, Nabil …) matches the Grain tab. The Coal
tab currently uses different competitor names and MT units. If the Coal tab is
later changed to the Grain-style layout, the page follows automatically.

### How columns are detected

- **Fixed columns** are found by name, tolerating variants:
  `Date`/`Prouct`/`Product Name`, `Origin`/`Country`, `Price Category`/`Category`/`Type`.
  A title row above the header is skipped automatically.
- **Every other column is treated as a competitor.** A trailing unit such as
  `(rate/MT)` or `(rate/mound)` is removed from the display name.
- Completely empty `Unnamed` columns are ignored. Empty / zero prices are treated
  as missing quotes, not as zero.
- `aliases` in `config.py` cleans up sheet spellings (e.g.
  `TST/JHM` → `TST / JHM`).
- If the tab name changes, update `tab_name` (and `gid` if you use one). The app
  falls back to the first tab and shows a note if the configured tab is missing.

---

## Files

```
app.py                     page setup, navigation, sidebar status
config.py                  sheet/page configuration
core/source.py             public export → service account → snapshot
core/transform.py          cleaning, long format, filters, tables
core/charts.py             Plotly single day-wise price chart
core/ui.py                 theme, header, KPI cards, quote table
views/competitor.py        the shared page used by Coal and Grain
data/*_snapshot.csv        offline fallback copies
.streamlit/config.toml     dark theme
```

---

## Why the dashboard may not show new rows

The page shows exactly what is in the **connected tab**. The exact tab, its
newest row, and the fetch time are always shown at the top and in the sidebar.

1. **Status: Live sheet, but Latest row is old**
   The connected tab has no newer rows. The dashboard is reading it live.
   If you added rows to another tab or another Google Sheet, point
   `config.py` at that tab/sheet (`tab_name`, `gid`, `sheet_id`). A yellow
   banner appears automatically when the tab is more than 2 days behind.

2. **Status: Snapshot**
   The Google Sheet is private (Google returns HTTP 401), so the app is using
   `data/*_snapshot.csv`. Share it as **Anyone with the link · Viewer**, or add
   the service account from Option B above. Updating a private sheet cannot be
   seen by the dashboard.

3. **You just edited the sheet**
   Wait 30 seconds, or click **Refresh now**. The app caches for 30 seconds and
   refreshes itself every minute.

4. **You clicked `run.bat` and still see the old page**
   `run.bat` now stops any old dashboard on port 8501, uses the local `.venv`,
   starts the new version, and opens the browser. Refresh the browser tab once.

5. **Grain specifically**
   The Grain Google Sheet is still private. The Grain page will remain a
   snapshot until that sheet is shared or a service account is configured.

## Notes and troubleshooting

- **Prices are shown exactly as reported** in the sheet. The dashboard does not
  smooth, adjust or drop outliers.
- A full cell-by-cell audit of both pages (including source anomalies worth
  checking) is in [`DATA_CHECK.md`](DATA_CHECK.md).
- If the sheet repeats the same competitor/date/product/origin/category, the
  bottom-most (most recently appended) entry is kept. The sidebar reports how
  many duplicate quotes were collapsed (currently 21 on Grain).
- If a chart looks empty, change the date filter or clear the product/competitor
  filters. The page shows an explicit empty state rather than a blank chart.
- The page reads Google's public CSV/XLSX export, so the sheet must remain
  viewable by link (Option A) or shared with the service account (Option B).
- Streamlit deep links: the default page (Coal) is served at `/`; Grain is at
  `/grain`. Use the sidebar navigation rather than typing `/coal`.
- Snapshot files are only fallbacks. Replace them occasionally if the live sheet
  will be unavailable for a long period.
