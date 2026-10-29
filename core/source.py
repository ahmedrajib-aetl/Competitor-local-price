"""Read a Google Sheet tab without asking the user for a login.

Three transports are tried, in order:

1. the public CSV / Excel export (the sheet is shared "anyone with the link");
2. a Google service account from ``st.secrets`` (works with private sheets);
3. the CSV snapshot bundled in ``data/`` so the dashboard always opens.

The sheet is never cached on disk, so a browser refresh shows today's rows.
"""

from __future__ import annotations

import io
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

import config

BASE_DIR = Path(__file__).resolve().parent.parent


class SourceError(RuntimeError):
    """The sheet could not be read."""


# --------------------------------------------------------------------- helpers
def _norm(value: object) -> str:
    text = str(value).replace("\ufeff", "").replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip().lower()


_HEADER_TOKENS = {
    "date": {
        "date", "dates", "report date", "reporting date", "date of report",
        "reporting period", "day",
    },
    "product": {
        "product", "prouct", "products", "product name", "item", "item name",
        "commodity", "commodity name", "grade",
    },
    "origin": {"origin", "origins", "origin country", "country", "source"},
    "category": {
        "price category", "category", "price cat", "price cat.", "price type",
        "category name", "type", "packing", "bag/lighter",
    },
}


def _find_header_row(raw: pd.DataFrame) -> int:
    """Return the row that looks like the real header (sheets often have titles)."""
    best_row, best_score = 0, -1
    for row in range(min(20, len(raw))):
        cells = {_norm(v) for v in raw.iloc[row].tolist()}
        score = sum(
            1 for tokens in _HEADER_TOKENS.values() if cells & tokens
        )
        if score > best_score:
            best_row, best_score = row, score
    return best_row if best_score >= 2 else 0


def _frame_from_grid(raw: pd.DataFrame) -> pd.DataFrame:
    """Turn a header-less grid into a DataFrame with clean column names."""
    if raw.empty:
        raise SourceError("the sheet came back empty")

    header_row = _find_header_row(raw)
    header = []
    for value in raw.iloc[header_row].tolist():
        text = "" if pd.isna(value) else str(value).replace("\n", " ")
        header.append(re.sub(r"\s+", " ", text).strip())

    seen: dict[str, int] = {}
    columns: list[str] = []
    for index, name in enumerate(header):
        name = name or f"Unnamed {index}"
        if name in seen:
            seen[name] += 1
            name = f"{name} ({seen[name]})"
        else:
            seen[name] = 0
        columns.append(name)

    body = raw.iloc[header_row + 1 :].copy()
    body.columns = columns
    body = body.dropna(how="all")

    # Remove columns that are both unnamed and empty (the sheet's spare columns).
    keep = [
        not (col.startswith("Unnamed") and body[col].isna().all())
        for col in body.columns
    ]
    body = body.loc[:, keep]
    return body.reset_index(drop=True)


def _fresh_url(url: str) -> str:
    """Add a cache-buster so Google's CDN never serves yesterday's export."""
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}_cb={int(time.time() * 1000)}"


def _get(url: str) -> bytes:
    response = requests.get(
        _fresh_url(url),
        timeout=config.REQUEST_TIMEOUT_SECONDS,
        headers={
            "User-Agent": "Mozilla/5.0 (competitor-price-dashboard)",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        },
    )
    if response.status_code != 200:
        raise SourceError(f"Google returned HTTP {response.status_code}")
    body = response.content
    if len(body) < 200:
        raise SourceError("Google returned an empty file")
    head = body[:800].lstrip().lower()
    if head.startswith(b"<") or b"<html" in head:
        raise SourceError(
            "Google returned a sign-in page — the sheet is not shared publicly"
        )
    return body


def _read_public(cfg: config.SheetConfig) -> tuple[pd.DataFrame, str, str]:
    """Read the public export. Returns (frame, source label, note)."""
    errors: list[str] = []

    if cfg.gid is not None:
        url = (
            f"https://docs.google.com/spreadsheets/d/{cfg.sheet_id}"
            f"/export?format=csv&gid={cfg.gid}"
        )
        try:
            body = _get(url)
            raw = pd.read_csv(
                io.BytesIO(body), header=None, dtype=object, encoding="utf-8-sig"
            )
            return _frame_from_grid(raw), "Google Sheet · live", ""
        except Exception as exc:  # fall through to the Excel export
            errors.append(f"CSV export: {exc}")

    url = f"https://docs.google.com/spreadsheets/d/{cfg.sheet_id}/export?format=xlsx"
    try:
        body = _get(url)
        book = pd.ExcelFile(io.BytesIO(body))
        note = ""
        if cfg.tab_name and cfg.tab_name in book.sheet_names:
            sheet_name = cfg.tab_name
        else:
            sheet_name = book.sheet_names[0]
            note = (
                f"Tab “{cfg.tab_name}” was not found; reading the first tab "
                f"“{sheet_name}” instead."
            )
        raw = book.parse(sheet_name=sheet_name, header=None, dtype=object)
        return _frame_from_grid(raw), f"Google Sheet · live · {sheet_name}", note
    except Exception as exc:
        errors.append(f"Excel export: {exc}")

    raise SourceError(" | ".join(errors))


def _service_account_info() -> dict | None:
    try:
        section = st.secrets["gcp_service_account"]
        info = dict(section)
        return info if info.get("client_email") else None
    except Exception:
        return None


def _read_service_account(cfg: config.SheetConfig) -> tuple[pd.DataFrame, str, str]:
    info = _service_account_info()
    if not info:
        raise SourceError("no service account is configured")

    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except Exception as exc:  # pragma: no cover - dependency problem
        raise SourceError(f"service account libraries are missing: {exc}") from exc

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    credentials = Credentials.from_service_account_info(info, scopes=scopes)
    client = gspread.authorize(credentials)
    book = client.open_by_key(cfg.sheet_id)

    note = ""
    try:
        worksheet = book.worksheet(cfg.tab_name) if cfg.tab_name else book.sheet1
    except Exception:
        worksheet = book.sheet1
        note = (
            f"Tab “{cfg.tab_name}” was not found; reading the first tab "
            f"“{worksheet.title}” instead."
        )

    values = worksheet.get_all_values()
    if not values:
        raise SourceError("the tab is empty")
    raw = pd.DataFrame(values, dtype=object)
    return (
        _frame_from_grid(raw),
        f"Google Sheet · service account · {worksheet.title}",
        note,
    )


def _read_snapshot(cfg: config.SheetConfig) -> tuple[pd.DataFrame, dict]:
    path = BASE_DIR / cfg.snapshot
    if not path.exists():
        raise SourceError(f"snapshot not found: {path}")
    raw = pd.read_csv(path, header=None, dtype=object, encoding="utf-8-sig")
    frame = _frame_from_grid(raw)
    stamp = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
    return frame, stamp


# ------------------------------------------------------------------- public API
@st.cache_data(ttl=config.CACHE_TTL_SECONDS, show_spinner=False)
def _load_cached(key: str, nonce: int = 0) -> tuple[pd.DataFrame, dict]:
    cfg = config.get_sheet(key)
    errors: list[str] = []

    readers = [_read_public]
    if _service_account_info():
        # A configured service account is the right transport for a private
        # sheet, and avoids a pointless 401 from the public export.
        readers.insert(0, _read_service_account)

    for reader in readers:
        try:
            frame, label, note = reader(cfg)
            return frame, {
                "source": label,
                "live": True,
                "fetched_at": datetime.now(timezone.utc),
                "note": note,
                "error": "",
            }
        except Exception as exc:
            errors.append(str(exc))

    try:
        frame, stamp = _read_snapshot(cfg)
        return frame, {
            "source": "Bundled snapshot",
            "live": False,
            "fetched_at": datetime.now(timezone.utc),
            "snapshot_mtime": stamp,
            "note": (
                "Live Google Sheets could not be read, so the bundled copy is shown. "
                "Share the sheet as “Anyone with the link · Viewer” (or add a "
                "service account in Streamlit secrets) to switch to live data."
            ),
            "error": " | ".join(errors),
        }
    except Exception as exc:
        raise SourceError(
            "Could not read the sheet and no usable snapshot was found. "
            f"Details: {' | '.join(errors)} | {exc}"
        ) from exc


def load_sheet(key: str, nonce: int = 0) -> tuple[pd.DataFrame, dict]:
    return _load_cached(key, nonce)


def clear_cache() -> None:
    _load_cached.clear()


def age_label(fetched_at: datetime) -> str:
    seconds = max(0, int((datetime.now(timezone.utc) - fetched_at).total_seconds()))
    if seconds < 90:
        return "just now"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} min ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} hr ago"
    return f"{hours // 24} d ago"
