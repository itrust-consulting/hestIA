"""Common exceptions, classes, and functions for C5-DEC."""

import argparse
import logging

verbosity = 0  # global verbosity setting for controlling string formatting
PRINT_VERBOSITY = 0  # minimum verbosity to using `print`
STR_VERBOSITY = 3  # minimum verbosity to use verbose `__str__`
MAX_VERBOSITY = 4  # maximum verbosity level implemented


def _trace(self, message, *args, **kws):
    if self.isEnabledFor(logging.DEBUG - 1):
        self._log(logging.DEBUG - 1, message, args, **kws)  # pylint: disable=W0212


logging.addLevelName(logging.DEBUG - 1, "TRACE")  # add new logging level
logging.Logger.trace = _trace  # type: ignore
# logging.basicConfig(filename='error.log', encoding='utf-8', level=logging.DEBUG)

logger = logging.getLogger
log = logger(__name__)


class HelpFormatter(argparse.ArgumentDefaultsHelpFormatter):
    """Command-line help text formatter with wider help text."""

    def __init__(self, *args, **kwargs):
        kwargs["max_help_position"] = 40
        super().__init__(*args, **kwargs)


class hestIAError(Exception):
    """Generic c5dec error."""

class hestIAWarning(hestIAError, Warning):
    """Generic c5dec warning."""

class hestIAInfo(hestIAWarning, Warning):
    """Generic c5dec info."""

class Capture:  # pylint: disable=R0903
    """Context manager to catch :class: hestIAError"""

    def __init__(self, catch=True):
        self.catch = catch
        self._success = True

    def __bool__(self):
        return self._success

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type and issubclass(exc_type, hestIAError):
            self._success = False
            if self.catch:
                log.error(exc_value)
                return True
        return False


# Logging classes #################

class WarningFormatter(logging.Formatter):
    """Logging formatter that displays verbose formatting for WARNING+."""

    def __init__(self, default_format, verbose_format, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.default_format = default_format
        self.verbose_format = verbose_format

    def format(self, record):
        """Python 3 hack to change the formatting style dynamically."""
        if record.levelno > logging.INFO:
            self._style._fmt = self.verbose_format  # pylint: disable=W0212
        else:
            self._style._fmt = self.default_format  # pylint: disable=W0212
        return super().format(record)