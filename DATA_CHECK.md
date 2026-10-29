# Data accuracy check — 18 Oct 2026

> **Re-checked 29 Oct 2026:** the live `COAL APPX PRICE` tab still ends at
> 18 Oct 2026, and the Grain Google Sheet still returns HTTP 401 (private).
> The dashboard is reading the configured tabs correctly; those tabs have no
> newer data visible to Google's export. If new rows were added elsewhere, point
> `config.py` at that tab/sheet, or share the Grain sheet.

This is an independent check of the dashboard against the source sheets. It
tests every source cell, not a sample. “Accuracy” means the dashboard reproduces
the sheet exactly; it does not correct errors inside the sheet.

## Result summary

| Check | Coal | Grain |
|---|---|---|
| Source | Live `COAL APPX PRICE` tab | `Khatunganj` snapshot (live sheet is private) |
| Source rows | 363 | 2,143 |
| Valid price cells in source | 749 | 6,092 |
| Quotes shown in dashboard | 749 | 6,071 |
| Missing / extra keys | 0 / 0 | 0 / 0 |
| Value mismatches | 0 | 0 |
| Reporting dates | 52 (1 Nov 2025 → 18 Oct 2026) | 183 (22 Feb 2026 → 14 Oct 2026) |
| Products | 7 | 9 |
| Origins | 2 | 8 |
| Competitors with data | 14 | 17 |
| KPI / table / chart recomputation | Exact | Exact |

Additional checks:

- **Coal:** the live CSV export and the Excel export were compared cell-by-cell:
  **0 mismatches**. The dashboard matches the live CSV **749 / 749** cells.
- **Grain:** the bundled snapshot was compared with
  `competitor_localprice.xlsx → Khatunganj`: **0 mismatches** across all
  2,143 × 21 cells.
- **Aggregations:** the latest-quote averages, previous quote, market average,
  “vs market”, and chart daily means were recomputed independently. Maximum
  difference: **0.000000000000**.
- The empty `FAKR UDDIN` column in Coal (0 prices) is correctly omitted.
- Grain is still a **snapshot through 14 Oct 2026** because the Google Sheet is
  private (HTTP 401). It must be shared as “Anyone with the link · Viewer” (or
  use the service account) before the live sheet itself can be audited.

## Grain duplicate rows in the source

The grain workbook contains 15 duplicate groups where the values **differ**.
Across all duplicate keys (including repeated identical values), **21 quote
cells** are collapsed. The dashboard resolves every duplicate deterministically:
**the bottom-most (most recently appended) entry wins** for that competitor. The
sidebar shows “21 duplicate quote(s) collapsed”.

| Date | Product | Origin | Category | Competitor | Values in the sheet (row) | Kept |
|---|---|---|---|---|---|---|
| 23 Feb 2026 | Nipper Lentils | Australia | Bag | AEL | 2,540 (16), 2,520 (17) | 2,520 |
| 24 Feb 2026 | Nipper Lentils | Australia | Bag | AEL | 2,540 (27), 2,535 (28) | 2,535 |
| 25 Feb 2026 | Nipper Lentils | Australia | Bag | AEL | 2,540 (39), 2,520 (40) | 2,520 |
| 26 Feb 2026 | Nipper Lentils | Australia | Bag | AEL | 2,550 (51), 2,520 (52) | 2,520 |
| 08 Mar 2026 | Nipper Lentils | Australia | Bag | AEL | 2,560 (141), 2,570 (142) | 2,570 |
| 29 Mar 2026 | Wheat 10.5% | Argentina | Lighter | AEL | 1,275 (228), 1,260 (229), 1,300 (230) | 1,300 |
| 26 Jul 2026 | Wheat 11.5% | Argentina | Bag | AEL | 1,380 (1191), 1,360 (1398) | 1,360 |
| 28 Jul 2026 | Wheat 11.5% | Argentina | Bag | AEL | 1,380 (1213), 1,390 (1420) | 1,390 |
| 29 Jul 2026 | Wheat CWRS2 | Canada | Lighter | AEL | 1,770 (1220), 1,785 (1429) | 1,785 |
| 03 Aug 2026 | Wheat CWRS2 | Canada | Lighter | AEL | 1,770 (1264), 1,800 (1462) | 1,800 |
| 06 Aug 2026 | Wheat CWRS2 | Canada | Lighter | AEL | 1,800 (1297), 1,845 (1484) | 1,845 |
| 22 Sep 2026 | Wheat CWRS2 | Canada | Bag | Bishwas | 1,928 (1923), 1,922 (1933) | 1,922 |
| 22 Sep 2026 | Wheat CWRS2 | Canada | Bag | City Commodities | 1,930 (1923), 1,925 (1933) | 1,925 |
| 22 Sep 2026 | Wheat CWRS2 | Canada | Bag | Consortium | 1,925 (1923), 1,920 (1933) | 1,920 |
| 22 Sep 2026 | Wheat CWRS2 | Canada | Bag | SS Enterprise | 1,925 (1923), 1,920 (1933) | 1,920 |

The 22 Sep pair is a whole row duplicated with small differences. The other 11
conflicts are an AEL-only block appended later in the sheet.

**Recommendation:** delete the duplicate rows in the Google Sheet. Until then,
the dashboard behaviour is deterministic and visible in the sidebar.

## Source values worth a manual check

These are **in the sheet exactly as shown** — the dashboard is not altering
them. They look unusual and may be entry errors or genuine different grades.

1. **Coal · 18 Oct 2026 · Coal Indo BANPU**
   - Akij Bongo Traders: **18,100**
   - Noapara: **26,000** (25,500 on 14 Oct)
   - Meghna Group: **26,000** (25,000 on 14 Oct)
   - A ~44% spread inside the same product. Check whether Noapara/Meghna were
     quoting a different coal grade or the BANPU row received a wrong price.

2. **Grain · 22 Sep 2026 · Wheat CWRS2 / Canada / Bag**
   - Two rows exist with slightly different prices (see table above). Check
     which row is the correct one.

3. **Grain · Nabil · Chickpeas / Australia / Bag**
   - Last positive quote before October was **2,600**; from 10–14 Oct it is
     **3,720**. The other competitors are 3,650–3,700, so 3,720 is plausible and
     the earlier 2,600 may simply be a stale quote. Worth confirming.

## How the audit was done

- Read the live Coal CSV and Excel exports separately.
- Read the Grain workbook and the bundled snapshot separately.
- Parsed dates, products, origins, categories and competitor names independently.
- Compared every non-empty price cell with the dashboard’s long-format dataset
  by `(Date, Product, Origin, Category, Competitor)`.
- Recomputed the KPI, latest-quote table and chart means from the raw source.
- Checked duplicate keys, empty columns, zero/negative prices and large moves.
