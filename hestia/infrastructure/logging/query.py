from __future__ import annotations

import csv
import io
import json
import logging
import pathlib
from typing import Any, Dict, Iterator, List, Literal, Optional, Tuple

LogType = Literal["system", "audit"]

# Fixed columns every log entry is guaranteed to have (stamped by
# _JsonFormatter in config.py) -- everything else is dynamic per call site.
_FIXED_FIELDS = ("ts", "level", "logger", "request_id", "msg")


def list_log_files(log_dir: pathlib.Path, log_type: LogType) -> List[pathlib.Path]:
    """Every file backing a log stream, current + rotated backups.
    system.log rotates by size (system.log, system.log.1, .2, ...);
    audit.log rotates daily (audit.log, audit.log.YYYY-MM-DD, ...)."""
    stem = "system.log" if log_type == "system" else "audit.log"
    current = log_dir / stem
    files = [current] if current.exists() else []
    files += sorted(log_dir.glob(f"{stem}.*"))
    return files


def _read_entries(files: List[pathlib.Path]) -> Iterator[Dict[str, Any]]:
    for path in files:
        try:
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except ValueError:
                        # A torn write (e.g. mid-rotation) or a stray non-JSON
                        # line must never break the whole read -- skip it.
                        continue
                    if isinstance(entry, dict):
                        yield entry
        except OSError:
            # File rotated/removed between listing and reading -- skip it.
            continue


def _level_at_or_above(entry_level: str, min_level: str) -> bool:
    entry_no = logging.getLevelName(entry_level.upper())
    min_no = logging.getLevelName(min_level.upper())
    if not isinstance(entry_no, int) or not isinstance(min_no, int):
        return True  # unknown level name -- don't filter it out
    return entry_no >= min_no


def _matches(
    entry: Dict[str, Any], *, level: Optional[str], search: Optional[str],
    since: Optional[str], until: Optional[str],
) -> bool:
    if level and not _level_at_or_above(str(entry.get("level", "")), level):
        return False
    ts = str(entry.get("ts", ""))
    if since and ts < since:
        return False
    if until and ts > until:
        return False
    if search:
        needle = search.lower()
        haystack = f"{entry.get('msg', '')} {entry.get('logger', '')}".lower()
        if needle not in haystack:
            return False
    return True


def _filtered_sorted(
    log_dir: pathlib.Path, log_type: LogType, *, level: Optional[str] = None,
    search: Optional[str] = None, since: Optional[str] = None, until: Optional[str] = None,
) -> List[Dict[str, Any]]:
    files = list_log_files(log_dir, log_type)
    entries = [e for e in _read_entries(files) if _matches(e, level=level, search=search, since=since, until=until)]
    entries.sort(key=lambda e: str(e.get("ts", "")), reverse=True)
    return entries


def count_failed_logins(log_dir: pathlib.Path, *, since: Optional[str] = None) -> Dict[str, int]:
    """Aggregates audit.auth_attempt(success=False) entries by username.
    Callers should pass a bounded `since` (same ISO-8601 string convention
    as query_logs/export_logs) -- this reads the whole matching file set
    into memory like query_logs does, so an unbounded scan isn't free."""
    counts: Dict[str, int] = {}
    for entry in _read_entries(list_log_files(log_dir, "audit")):
        if entry.get("msg") != "auth_attempt" or entry.get("success") is not False:
            continue
        ts = str(entry.get("ts", ""))
        if since and ts < since:
            continue
        username = entry.get("username")
        if username:
            counts[username] = counts.get(username, 0) + 1
    return counts


def query_logs(
    log_dir: pathlib.Path, log_type: LogType, *, level: Optional[str] = None,
    search: Optional[str] = None, since: Optional[str] = None, until: Optional[str] = None,
    limit: int = 100, offset: int = 0,
) -> Tuple[List[Dict[str, Any]], int]:
    """Reads, filters, and sorts (newest first) every matching log file in
    memory, then paginates. Bounded by the existing rotation limits (<=60MB
    for system.log across backups; audit.log's daily files are individually
    small) -- fine for a v1, not built to scale past that without a real
    index."""
    entries = _filtered_sorted(log_dir, log_type, level=level, search=search, since=since, until=until)
    return entries[offset:offset + limit], len(entries)


def export_logs(
    log_dir: pathlib.Path, log_type: LogType, *, level: Optional[str] = None,
    search: Optional[str] = None, since: Optional[str] = None, until: Optional[str] = None,
    format: Literal["ndjson", "csv"] = "ndjson",
) -> Iterator[str]:
    """Same filtering as query_logs, unpaginated -- exports everything
    currently matching the admin's filter, not the whole file."""
    entries = _filtered_sorted(log_dir, log_type, level=level, search=search, since=since, until=until)
    if format == "ndjson":
        for entry in entries:
            yield json.dumps(entry, default=str, ensure_ascii=False) + "\n"
        return

    # CSV can't represent the dynamic extra-field shape these log lines have
    # -- flatten to the fixed columns plus one JSON-string "extra" column for
    # everything else, rather than silently dropping fields.
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([*_FIXED_FIELDS, "extra"])
    yield buf.getvalue()
    for entry in entries:
        buf = io.StringIO()
        writer = csv.writer(buf)
        extra = {k: v for k, v in entry.items() if k not in _FIXED_FIELDS}
        writer.writerow([
            *(entry.get(f, "") for f in _FIXED_FIELDS),
            json.dumps(extra, default=str, ensure_ascii=False) if extra else "",
        ])
        yield buf.getvalue()
