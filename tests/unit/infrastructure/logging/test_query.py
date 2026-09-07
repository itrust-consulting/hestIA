from __future__ import annotations

import csv
import io
import json

import pytest

from hestia.infrastructure.logging.query import (
    count_failed_logins,
    export_logs,
    list_log_files,
    query_logs,
)


def _entry(ts, level="INFO", msg="something happened", logger="hestia.app", **extra):
    return {
        "ts": ts, "level": level, "logger": logger, "request_id": "req-1", "msg": msg,
        **extra,
    }


def _write_jsonl(path, entries):
    path.write_text("\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# list_log_files
# ---------------------------------------------------------------------------

class TestListLogFiles:

    def test_no_files_returns_empty(self, tmp_path):
        assert list_log_files(tmp_path, "system") == []

    def test_current_system_log_only(self, tmp_path):
        f = tmp_path / "system.log"
        f.write_text("")
        assert list_log_files(tmp_path, "system") == [f]

    def test_current_plus_rotated_backups_sorted(self, tmp_path):
        current = tmp_path / "system.log"
        current.write_text("")
        b2 = tmp_path / "system.log.2"
        b2.write_text("")
        b1 = tmp_path / "system.log.1"
        b1.write_text("")
        files = list_log_files(tmp_path, "system")
        assert files == [current, b1, b2]

    def test_audit_stem_and_daily_rotation(self, tmp_path):
        current = tmp_path / "audit.log"
        current.write_text("")
        old = tmp_path / "audit.log.2024-01-01"
        old.write_text("")
        files = list_log_files(tmp_path, "audit")
        assert files == [current, old]

    def test_no_current_file_still_lists_backups(self, tmp_path):
        backup = tmp_path / "system.log.1"
        backup.write_text("")
        files = list_log_files(tmp_path, "system")
        assert files == [backup]


# ---------------------------------------------------------------------------
# query_logs -- reading, malformed-line tolerance, filtering, pagination
# ---------------------------------------------------------------------------

class TestQueryLogsReading:

    def test_reads_entries_from_current_file(self, tmp_path):
        _write_jsonl(tmp_path / "system.log", [_entry("2024-01-01T00:00:00.000Z")])
        entries, total = query_logs(tmp_path, "system")
        assert total == 1
        assert entries[0]["msg"] == "something happened"

    def test_skips_blank_and_malformed_lines(self, tmp_path):
        f = tmp_path / "system.log"
        f.write_text(
            json.dumps(_entry("2024-01-01T00:00:00.000Z")) + "\n"
            "\n"
            "not json at all\n"
            "[1, 2, 3]\n"  # valid JSON but not a dict -- must be skipped too
            "   \n",
            encoding="utf-8",
        )
        entries, total = query_logs(tmp_path, "system")
        assert total == 1

    def test_reads_across_rotated_backups(self, tmp_path):
        _write_jsonl(tmp_path / "system.log", [_entry("2024-01-03T00:00:00.000Z", msg="current")])
        _write_jsonl(tmp_path / "system.log.1", [_entry("2024-01-02T00:00:00.000Z", msg="backup1")])
        entries, total = query_logs(tmp_path, "system")
        assert total == 2
        msgs = {e["msg"] for e in entries}
        assert msgs == {"current", "backup1"}

    def test_missing_log_dir_returns_empty(self, tmp_path):
        missing = tmp_path / "does-not-exist"
        entries, total = query_logs(missing, "system")
        assert entries == []
        assert total == 0

    def test_unreadable_file_is_skipped_not_raised(self, tmp_path):
        # Simulates a file rotated/removed between listing and reading: any
        # OSError raised while opening a listed file must be swallowed, not
        # propagated. A directory named like the log file reliably raises
        # OSError (PermissionError/IsADirectoryError) on open() cross-platform.
        (tmp_path / "system.log").mkdir()
        entries, total = query_logs(tmp_path, "system")
        assert entries == []
        assert total == 0

    def test_sorted_newest_first(self, tmp_path):
        _write_jsonl(tmp_path / "system.log", [
            _entry("2024-01-01T00:00:00.000Z", msg="oldest"),
            _entry("2024-01-03T00:00:00.000Z", msg="newest"),
            _entry("2024-01-02T00:00:00.000Z", msg="middle"),
        ])
        entries, _ = query_logs(tmp_path, "system")
        assert [e["msg"] for e in entries] == ["newest", "middle", "oldest"]


class TestQueryLogsFilterByLevel:

    def _setup(self, tmp_path):
        _write_jsonl(tmp_path / "system.log", [
            _entry("2024-01-01T00:00:00.000Z", level="DEBUG", msg="debug-msg"),
            _entry("2024-01-01T00:00:01.000Z", level="INFO", msg="info-msg"),
            _entry("2024-01-01T00:00:02.000Z", level="WARNING", msg="warning-msg"),
            _entry("2024-01-01T00:00:03.000Z", level="ERROR", msg="error-msg"),
        ])

    def test_filters_at_or_above_min_level(self, tmp_path):
        self._setup(tmp_path)
        entries, total = query_logs(tmp_path, "system", level="WARNING")
        assert total == 2
        assert {e["level"] for e in entries} == {"WARNING", "ERROR"}

    def test_no_level_filter_returns_all(self, tmp_path):
        self._setup(tmp_path)
        _, total = query_logs(tmp_path, "system")
        assert total == 4

    def test_lowercase_level_filter_works(self, tmp_path):
        self._setup(tmp_path)
        _, total = query_logs(tmp_path, "system", level="error")
        assert total == 1

    def test_unknown_level_name_does_not_filter_out(self, tmp_path):
        _write_jsonl(tmp_path / "system.log", [
            _entry("2024-01-01T00:00:00.000Z", level="TRACE", msg="custom-level"),
        ])
        entries, total = query_logs(tmp_path, "system", level="INFO")
        assert total == 1
        assert entries[0]["msg"] == "custom-level"


class TestQueryLogsFilterByTimeRange:

    def _setup(self, tmp_path):
        _write_jsonl(tmp_path / "system.log", [
            _entry("2024-01-01T00:00:00.000Z", msg="jan1"),
            _entry("2024-01-15T00:00:00.000Z", msg="jan15"),
            _entry("2024-02-01T00:00:00.000Z", msg="feb1"),
        ])

    def test_since_excludes_earlier_entries(self, tmp_path):
        self._setup(tmp_path)
        entries, total = query_logs(tmp_path, "system", since="2024-01-10T00:00:00.000Z")
        assert total == 2
        assert {e["msg"] for e in entries} == {"jan15", "feb1"}

    def test_until_excludes_later_entries(self, tmp_path):
        self._setup(tmp_path)
        entries, total = query_logs(tmp_path, "system", until="2024-01-20T00:00:00.000Z")
        assert total == 2
        assert {e["msg"] for e in entries} == {"jan1", "jan15"}

    def test_since_and_until_bound_a_window(self, tmp_path):
        self._setup(tmp_path)
        entries, total = query_logs(
            tmp_path, "system",
            since="2024-01-05T00:00:00.000Z", until="2024-01-20T00:00:00.000Z",
        )
        assert total == 1
        assert entries[0]["msg"] == "jan15"


class TestQueryLogsFilterBySearch:

    def _setup(self, tmp_path):
        _write_jsonl(tmp_path / "system.log", [
            _entry("2024-01-01T00:00:00.000Z", msg="user login succeeded", logger="hestia.auth"),
            _entry("2024-01-01T00:00:01.000Z", msg="document uploaded", logger="hestia.ingestion"),
        ])

    def test_matches_msg_substring_case_insensitive(self, tmp_path):
        self._setup(tmp_path)
        entries, total = query_logs(tmp_path, "system", search="LOGIN")
        assert total == 1
        assert entries[0]["msg"] == "user login succeeded"

    def test_matches_logger_substring(self, tmp_path):
        self._setup(tmp_path)
        entries, total = query_logs(tmp_path, "system", search="ingestion")
        assert total == 1
        assert entries[0]["msg"] == "document uploaded"

    def test_no_match_returns_empty(self, tmp_path):
        self._setup(tmp_path)
        _, total = query_logs(tmp_path, "system", search="nonexistent-term")
        assert total == 0


class TestQueryLogsPagination:

    def _setup(self, tmp_path, n=10):
        _write_jsonl(tmp_path / "system.log", [
            _entry(f"2024-01-01T00:00:{i:02d}.000Z", msg=f"entry-{i}") for i in range(n)
        ])

    def test_limit_bounds_page_size(self, tmp_path):
        self._setup(tmp_path)
        entries, total = query_logs(tmp_path, "system", limit=3)
        assert len(entries) == 3
        assert total == 10  # total reflects the full filtered set, not the page

    def test_offset_skips_entries(self, tmp_path):
        self._setup(tmp_path)
        # Newest-first: entry-9 is first, entry-0 is last.
        entries, total = query_logs(tmp_path, "system", limit=3, offset=3)
        assert total == 10
        assert [e["msg"] for e in entries] == ["entry-6", "entry-5", "entry-4"]

    def test_offset_beyond_total_returns_empty_page(self, tmp_path):
        self._setup(tmp_path)
        entries, total = query_logs(tmp_path, "system", limit=5, offset=100)
        assert entries == []
        assert total == 10

    def test_default_pagination_returns_up_to_100(self, tmp_path):
        self._setup(tmp_path, n=5)
        entries, total = query_logs(tmp_path, "system")
        assert len(entries) == 5
        assert total == 5


# ---------------------------------------------------------------------------
# count_failed_logins
# ---------------------------------------------------------------------------

class TestCountFailedLogins:

    def test_counts_by_username(self, tmp_path):
        _write_jsonl(tmp_path / "audit.log", [
            _entry("2024-01-01T00:00:00.000Z", msg="auth_attempt", username="alice", success=False),
            _entry("2024-01-01T00:00:01.000Z", msg="auth_attempt", username="alice", success=False),
            _entry("2024-01-01T00:00:02.000Z", msg="auth_attempt", username="bob", success=False),
        ])
        counts = count_failed_logins(tmp_path)
        assert counts == {"alice": 2, "bob": 1}

    def test_ignores_successful_attempts(self, tmp_path):
        _write_jsonl(tmp_path / "audit.log", [
            _entry("2024-01-01T00:00:00.000Z", msg="auth_attempt", username="alice", success=True),
        ])
        assert count_failed_logins(tmp_path) == {}

    def test_ignores_non_auth_attempt_entries(self, tmp_path):
        _write_jsonl(tmp_path / "audit.log", [
            _entry("2024-01-01T00:00:00.000Z", msg="logout", username="alice"),
        ])
        assert count_failed_logins(tmp_path) == {}

    def test_since_bounds_the_scan(self, tmp_path):
        _write_jsonl(tmp_path / "audit.log", [
            _entry("2024-01-01T00:00:00.000Z", msg="auth_attempt", username="alice", success=False),
            _entry("2024-02-01T00:00:00.000Z", msg="auth_attempt", username="alice", success=False),
        ])
        counts = count_failed_logins(tmp_path, since="2024-01-15T00:00:00.000Z")
        assert counts == {"alice": 1}

    def test_missing_username_not_counted(self, tmp_path):
        _write_jsonl(tmp_path / "audit.log", [
            _entry("2024-01-01T00:00:00.000Z", msg="auth_attempt", success=False, username=None),
        ])
        assert count_failed_logins(tmp_path) == {}


# ---------------------------------------------------------------------------
# export_logs -- ndjson and csv formats
# ---------------------------------------------------------------------------

class TestExportLogsNdjson:

    def test_exports_all_matching_entries_as_json_lines(self, tmp_path):
        _write_jsonl(tmp_path / "system.log", [
            _entry("2024-01-01T00:00:00.000Z", msg="one"),
            _entry("2024-01-02T00:00:00.000Z", msg="two"),
        ])
        lines = list(export_logs(tmp_path, "system", format="ndjson"))
        assert len(lines) == 2
        parsed = [json.loads(l) for l in lines]
        # newest first
        assert [p["msg"] for p in parsed] == ["two", "one"]

    def test_respects_filters(self, tmp_path):
        _write_jsonl(tmp_path / "system.log", [
            _entry("2024-01-01T00:00:00.000Z", level="DEBUG", msg="debug-msg"),
            _entry("2024-01-02T00:00:00.000Z", level="ERROR", msg="error-msg"),
        ])
        lines = list(export_logs(tmp_path, "system", level="ERROR", format="ndjson"))
        assert len(lines) == 1
        assert json.loads(lines[0])["msg"] == "error-msg"

    def test_empty_result_yields_no_lines(self, tmp_path):
        lines = list(export_logs(tmp_path, "system", format="ndjson"))
        assert lines == []


class TestExportLogsCsv:

    def test_header_row_has_fixed_columns_plus_extra(self, tmp_path):
        _write_jsonl(tmp_path / "system.log", [_entry("2024-01-01T00:00:00.000Z")])
        rows = list(export_logs(tmp_path, "system", format="csv"))
        header = next(csv.reader(io.StringIO(rows[0])))
        assert header == ["ts", "level", "logger", "request_id", "msg", "extra"]

    def test_fixed_fields_populate_correctly(self, tmp_path):
        _write_jsonl(tmp_path / "system.log", [
            _entry("2024-01-01T00:00:00.000Z", level="INFO", msg="hello", logger="hestia.x"),
        ])
        rows = list(export_logs(tmp_path, "system", format="csv"))
        data_row = next(csv.reader(io.StringIO(rows[1])))
        ts, level, logger_, request_id, msg, extra = data_row
        assert ts == "2024-01-01T00:00:00.000Z"
        assert level == "INFO"
        assert logger_ == "hestia.x"
        assert msg == "hello"
        assert extra == ""

    def test_extra_fields_flattened_into_json_column(self, tmp_path):
        _write_jsonl(tmp_path / "system.log", [
            _entry("2024-01-01T00:00:00.000Z", user_id="u1", collection="col1"),
        ])
        rows = list(export_logs(tmp_path, "system", format="csv"))
        data_row = next(csv.reader(io.StringIO(rows[1])))
        extra_json = data_row[-1]
        extra = json.loads(extra_json)
        assert extra == {"user_id": "u1", "collection": "col1"}

    def test_no_entries_still_yields_header_only(self, tmp_path):
        rows = list(export_logs(tmp_path, "system", format="csv"))
        assert len(rows) == 1
        header = next(csv.reader(io.StringIO(rows[0])))
        assert header[0] == "ts"
