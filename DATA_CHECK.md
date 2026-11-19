# Data accuracy check — 19 Nov 2026

This is an independent check of the dashboard against the source files. It
compares every source row, not a sample. “Accuracy” means the dashboard
reproduces the source exactly; it does not correct errors inside the source.

## Result summary

| Check | Coal | Grain |
|---|---|---|
| Source | Google Drive · `Master Database` (live `.xlsx`) | `Khatunganj` snapshot (live sheet is private) |
| Source rows | 2,298 (1,935 with a date + importer) | 2,143 |
| Valid price cells | 1,689 | 6,092 |
| Quotes shown | 1,689 | 6,071 |
| Missing / extra keys | 0 / 0 | 0 / 0 |
| Value mismatches | **0** | **0** |
| Reporting dates | 16 (11 Oct → 15 Nov 2026) | 183 (22 Feb → 14 Oct 2026) |
| Importers / competitors | 18 | 17 |
| Locations | 8 | — |
| Origins | 3 | 8 |
| Mines | 11 | — |
| Summary / table / chart recomputation | Exact | Exact |

Coal row-level check: **1,935 rows** compared on Date, Importer, Location,
Origin, Mine, Quantity and Sale Rate — **0 mismatches**.

Grain snapshot vs `competitor_localprice.xlsx → Khatunganj`: **0 mismatches**
across all 2,143 × 21 cells.

Grain is still a **snapshot through 14 Oct 2026** because the Google Sheet is
private (HTTP 401). It must be shared as “Anyone with the link · Viewer” (or use
the service account) before the live sheet can be audited.

## Coal — latest-date origin summary (15 Nov 2026)

| Country of Origin | Date | Dumping Quantity (MT) | Average Sale / Retail Rate (BDT/MT) |
|---|---|---:|---:|
| India | 15-Nov-2026 | 8,000 | 23,467 |
| Indonesia | 15-Nov-2026 | 537,100 | 25,178 |
| South Africa | 15-Nov-2026 | 497,000 | 19,685 |
| **Grand Total** | **15-Nov-2026** | **1,042,100** | **22,876** |

The app computes this from the current `Master Database` rows: quantity is the
sum of Quantity (MT), and the rate is the simple mean of the non-zero sale rates
on that date. The pasted pivot sample showed South Africa **19,357** and Grand
Total **22,717**; those values do not match the current rows in the shared
workbook (they may come from an earlier copy or a filtered pivot). If the pivot
has an extra filter, tell us and we can match it.

## Coal source values worth checking

- **TST · Berau · 25 and 27 Oct 2026: rate 3,500 BDT/MT** while every other row
  is 18,000–27,700. This looks like a data-entry error (perhaps 23,500).
  The summary and tables include it. The chart trims it by default so one bad
  quote does not flatten the chart; untick **Trim extreme outliers** to see it.

## Grain duplicate rows in the source

The grain workbook contains 15 duplicate groups where the values **differ**.
Across all duplicate keys (including repeated identical values), **21 quote
cells** are collapsed. The dashboard keeps the **bottom-most (most recently
appended)** entry for that competitor. The sidebar shows
“21 duplicate quote(s) collapsed”.

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

## Grain source values worth checking

- **22 Sep 2026 · Wheat CWRS2 / Canada / Bag** — the duplicate pair above.
- **Nabil · Chickpeas / Australia / Bag** — last positive quote before October
  was 2,600; 10–14 Oct is 3,720. Peers are 3,650–3,700, so 3,720 is plausible
  and the earlier value may simply be stale.

## Stock pages — `Master Data` (checked 19 Nov 2026)

| Check | Grain Stock | Coal Stock |
|---|---|---|
| Source | `Master Data` tab | `Master Data` tab |
| Rows | 27 | 8 |
| Dates stored | 3 (26 Oct, 4 Nov, 15 Nov) | 2 (26 Oct, 4 Nov) |
| Latest date | 15 Nov 2026 | 04 Nov 2026 |
| Latest rows shown | 9 | 4 |
| Items | 8 | 1 |
| Warehouses | 5 | 4 |
| Plants | 4 | 0 |
| Total quantity | 302.868 MT | 23.09 MT |
| Total value | 10,885,753 BDT | 307,353 BDT |
| Average rate | 35,942 BDT/MT | 13,311 BDT/MT |
| Snapshot vs live | 0 mismatches | 0 mismatches |

The stock pages read only `Master Data`; the dated tabs in the workbooks are
backups and are intentionally ignored. The Coal Master Data currently ends on
04 Nov 2026, so the Coal Stock page shows 04 Nov and a yellow “newest date is 15
days ago” banner until the Master Data tab is updated. Grain Master Data ends on
15 Nov 2026, 4 days before this check.

## How the audit was done

- Downloaded the Coal `Master Database` from the live Google Drive file and
  compared it row-by-row with the dashboard's cleaned long-format dataset.
- Compared the Grain snapshot with the source `Khatunganj` tab cell-by-cell.
- Parsed dates, importers/traders, locations, origins, mines, grades, quantities
  and sale rates independently.
- Recomputed the origin summary, latest-quote averages, previous quotes, market
  average, “vs market”, and chart daily means from the source.
- Checked blank/zero rates, duplicates, missing importers and extreme moves.
