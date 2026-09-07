from __future__ import annotations

import json
import logging
import sys

import pytest

from hestia.infrastructure.logging import config as config_module
from hestia.infrastructure.logging.config import (
    request_id_var,
    set_log_level,
    setup_logging,
    shutdown_logging,
)


class _FakeSettings:
    """Duck-typed stand-in for hestia.config.settings.Settings -- setup_logging
    only ever reads log_dir/log_level/log_to_console off it."""

    def __init__(self, log_dir, log_level="INFO", log_to_console=False):
        self.log_dir = log_dir
        self.log_level = log_level
        self.log_to_console = log_to_console


@pytest.fixture(autouse=True)
def _isolate_hestia_logger():
    """setup_logging() mutates process-global logging state (the "hestia"
    logger's handlers/level/propagate, plus this module's _listener/
    _system_handler/_console_handler globals). Snapshot and restore all of it
    around every test so this file never leaks state into test_middleware.py,
    test_audit.py, etc. (which run in the same pytest process and rely on
    caplog propagation through the "hestia" logger)."""
    hestia_logger = logging.getLogger("hestia")
    orig_handlers = list(hestia_logger.handlers)
    orig_level = hestia_logger.level
    orig_propagate = hestia_logger.propagate

    yield

    shutdown_logging()
    hestia_logger.handlers = orig_handlers
    hestia_logger.level = orig_level
    hestia_logger.propagate = orig_propagate
    config_module._listener = None
    config_module._system_handler = None
    config_module._console_handler = None


def _read(path):
    return path.read_text(encoding="utf-8")


class TestSetupLogging:

    def test_creates_log_directory_when_missing(self, tmp_path):
        log_dir = tmp_path / "nested" / "logs"
        assert not log_dir.exists()

        setup_logging(_FakeSettings(log_dir))

        assert log_dir.is_dir()

    def test_writes_json_formatted_message_to_system_log(self, tmp_path):
        setup_logging(_FakeSettings(tmp_path))

        logging.getLogger("hestia.app").info("hello world", extra={"user_id": "u1"})
        shutdown_logging()

        lines = [l for l in _read(tmp_path / "system.log").splitlines() if l.strip()]
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["msg"] == "hello world"
        assert record["level"] == "INFO"
        assert record["logger"] == "hestia.app"
        assert record["user_id"] == "u1"
        assert "ts" in record and record["ts"].endswith("Z")

    def test_audit_records_routed_to_audit_log_only(self, tmp_path):
        setup_logging(_FakeSettings(tmp_path))

        logging.getLogger("hestia.audit").info("auth_attempt", extra={"username": "alice"})
        logging.getLogger("hestia.app").info("system event")
        shutdown_logging()

        audit_lines = [l for l in _read(tmp_path / "audit.log").splitlines() if l.strip()]
        system_lines = [l for l in _read(tmp_path / "system.log").splitlines() if l.strip()]

        assert len(audit_lines) == 1
        assert json.loads(audit_lines[0])["msg"] == "auth_attempt"
        assert len(system_lines) == 1
        assert json.loads(system_lines[0])["msg"] == "system event"

    def test_respects_log_level_filtering(self, tmp_path):
        setup_logging(_FakeSettings(tmp_path, log_level="WARNING"))

        logger = logging.getLogger("hestia.app")
        logger.debug("should be filtered out")
        logger.warning("should appear")
        shutdown_logging()

        lines = [l for l in _read(tmp_path / "system.log").splitlines() if l.strip()]
        assert len(lines) == 1
        assert json.loads(lines[0])["msg"] == "should appear"

    def test_request_id_from_contextvar_is_stamped_on_record(self, tmp_path):
        setup_logging(_FakeSettings(tmp_path))

        token = request_id_var.set("req-123")
        try:
            logging.getLogger("hestia.app").info("with request id")
        finally:
            request_id_var.reset(token)
        shutdown_logging()

        record = json.loads(_read(tmp_path / "system.log").strip())
        assert record["request_id"] == "req-123"

    def test_no_request_id_set_defaults_to_dash(self, tmp_path):
        setup_logging(_FakeSettings(tmp_path))

        logging.getLogger("hestia.app").info("no request id here")
        shutdown_logging()

        record = json.loads(_read(tmp_path / "system.log").strip())
        assert record["request_id"] == "-"

    def test_exception_traceback_reaches_the_log_record(self, tmp_path):
        # Note: the records flow through a QueueHandler (see setup_logging)
        # before reaching the JSON-formatting handlers. QueueHandler.prepare()
        # calls the default (unformatted) Formatter on the record eagerly --
        # baking the traceback into record.msg -- and then clears
        # record.exc_info so it isn't formatted twice downstream. So in
        # practice `_JsonFormatter`'s own `if record.exc_info: data["exc"]`
        # branch never fires for records logged through the app's real
        # logger; the traceback shows up inside "msg" instead. Asserting the
        # sunnier "exc" key would misrepresent how this actually behaves.
        setup_logging(_FakeSettings(tmp_path))

        try:
            raise ValueError("boom")
        except ValueError:
            logging.getLogger("hestia.app").exception("it broke")
        shutdown_logging()

        record = json.loads(_read(tmp_path / "system.log").strip())
        assert "exc" not in record
        assert "ValueError: boom" in record["msg"]
        assert "Traceback" in record["msg"]

    def test_json_formatter_exc_field_when_exc_info_reaches_it_directly(self):
        # Exercises _JsonFormatter's own exc-formatting branch directly,
        # bypassing the QueueHandler entirely -- this is the only way that
        # branch is actually reachable (see the note above), e.g. if a
        # handler were ever attached to the JSON formatter outside of the
        # queue/listener pipeline.
        from hestia.infrastructure.logging.config import _JsonFormatter

        try:
            raise ValueError("boom")
        except ValueError:
            record = logging.LogRecord(
                name="hestia.app", level=logging.ERROR, pathname=__file__, lineno=1,
                msg="it broke", args=None, exc_info=sys.exc_info(),
            )

        formatted = json.loads(_JsonFormatter().format(record))
        assert "exc" in formatted
        assert "ValueError: boom" in formatted["exc"]

    def test_console_handler_added_when_log_to_console_true(self, tmp_path, capsys):
        setup_logging(_FakeSettings(tmp_path, log_to_console=True))

        assert config_module._console_handler is not None

        logging.getLogger("hestia.app").warning("console message")
        shutdown_logging()

        captured = capsys.readouterr()
        assert "console message" in captured.err

    def test_console_handler_not_added_when_log_to_console_false(self, tmp_path):
        setup_logging(_FakeSettings(tmp_path, log_to_console=False))

        assert config_module._console_handler is None

    def test_console_handler_excludes_audit_records(self, tmp_path, capsys):
        setup_logging(_FakeSettings(tmp_path, log_to_console=True))

        logging.getLogger("hestia.audit").info("auth_attempt")
        shutdown_logging()

        captured = capsys.readouterr()
        assert "auth_attempt" not in captured.err

    def test_second_call_resets_console_handler_flag(self, tmp_path):
        # A prior call with log_to_console=True must not leave a stale
        # _console_handler reference once a later call turns it off.
        setup_logging(_FakeSettings(tmp_path, log_to_console=True))
        assert config_module._console_handler is not None
        shutdown_logging()

        setup_logging(_FakeSettings(tmp_path, log_to_console=False))
        assert config_module._console_handler is None


class TestShutdownLogging:

    def test_stops_the_listener_thread(self, tmp_path):
        setup_logging(_FakeSettings(tmp_path))
        listener = config_module._listener
        assert listener._thread is not None
        assert listener._thread.is_alive()

        shutdown_logging()

        assert listener._thread is None

    def test_noop_when_setup_never_called(self):
        # Must not raise even though module-level _listener is None.
        shutdown_logging()

    def test_does_not_detach_queue_handler_from_hestia_logger(self, tmp_path):
        # Documented/actual behavior: shutdown_logging() only stops the
        # QueueListener thread. It never calls hestia_logger.removeHandler(),
        # so the QueueHandler added by setup_logging() is still attached
        # afterwards -- a second setup_logging() call in the same process
        # adds *another* QueueHandler rather than replacing the first one.
        # This test documents that accumulation rather than assuming it away.
        hestia_logger = logging.getLogger("hestia")

        setup_logging(_FakeSettings(tmp_path))
        count_after_first = len(hestia_logger.handlers)
        shutdown_logging()

        assert len(hestia_logger.handlers) == count_after_first

        setup_logging(_FakeSettings(tmp_path))
        count_after_second = len(hestia_logger.handlers)
        shutdown_logging()

        assert count_after_second == count_after_first + 1


class TestSetLogLevel:

    def test_changes_system_handler_level(self, tmp_path):
        settings = _FakeSettings(tmp_path, log_level="INFO")
        setup_logging(settings)

        set_log_level(settings, "ERROR")

        assert config_module._system_handler.level == logging.ERROR
        assert settings.log_level == "ERROR"

    def test_changes_console_handler_level_when_present(self, tmp_path):
        settings = _FakeSettings(tmp_path, log_level="INFO", log_to_console=True)
        setup_logging(settings)

        set_log_level(settings, "DEBUG")

        assert config_module._console_handler.level == logging.DEBUG

    def test_raises_on_unknown_level_name(self, tmp_path):
        settings = _FakeSettings(tmp_path)
        setup_logging(settings)

        with pytest.raises(ValueError, match="Unknown log level"):
            set_log_level(settings, "NOT_A_LEVEL")

    def test_noop_on_handlers_when_setup_never_called(self):
        settings = _FakeSettings("unused")
        # Must not raise even though _system_handler/_console_handler are None.
        set_log_level(settings, "DEBUG")
        assert settings.log_level == "DEBUG"

    def test_audit_handler_level_untouched(self, tmp_path):
        # set_log_level only ever touches _system_handler/_console_handler --
        # there's deliberately no module-level handle on the audit handler,
        # so turning system verbosity down/up can never affect audit.log.
        setup_logging(_FakeSettings(tmp_path, log_level="INFO"))
        settings = _FakeSettings(tmp_path, log_level="INFO")

        set_log_level(settings, "CRITICAL")

        logging.getLogger("hestia.audit").info("auth_attempt still logged")
        shutdown_logging()

        lines = [l for l in _read(tmp_path / "audit.log").splitlines() if l.strip()]
        assert len(lines) == 1
