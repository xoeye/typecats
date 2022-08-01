"""WARNING: This module is experimental.
Motivation:
Filtering exception groups for certain exceptions while maintaining expected behavior
from pytest.raises which fails a test if either:
 - the expected exception is not thrown
 - a different kind is thrown
    - `raises_in_group` takes this one step further and fails the test
      if the group contains an exception that was not expected

cattrs is using the exceptiongroup backport package from PyPI
This is also further inconvenient because:
  - PEP-654 (exception groups) includes language features in CPython >= 3.11
  - We aim to support Python 3.6
  - The backport package's `except*` implementation tries its best but isn't all that great
  - Python 3.11 is in its pre-release stages and exceptiongroup adoption among libraries is limited
  - Pytest currently has no ongoing work or discussions for this
  - Even the `unittest` module in the current 3.11 pre-release does not offer any additional support



It relies on internal pytest APIs which are succeptible to change at any time.
Where needed, we pass `_ispytest=True` to suppress warnings.
"""
import warnings
from inspect import getfullargspec
from types import TracebackType
from typing import Optional, Type, cast

from _pytest._code import ExceptionInfo
from pytest import fail

from .._compat import BaseExceptionGroup, ExceptionGroup
from . import ExceptionMatch, flattened_exceptions

BYPASS_PYTEST_INTERNAL_WARNING = "_ispytest" in getfullargspec(ExceptionInfo.__init__).kwonlyargs


class PytestInternalAPIChangedError(Exception):
    ...


class RaisesExceptionGroupContext(object):
    """Captures the only (or first of, if allow_multiple=True) exception in a group.

    This is based on _pytest.python_api.RaisesExceptionContext.
    """

    def __init__(
        self, exception_match: ExceptionMatch, match_expr: str = None, allow_multiple=False
    ):
        self.exception_match = exception_match
        self.match_expr = match_expr
        self.allow_multiple = allow_multiple
        self.excinfo: Optional[ExceptionInfo] = None

    def __enter__(self):
        self.excinfo = ExceptionInfo.for_later()
        return self.excinfo

    def __exit__(
        self,
        exc_type: Type[BaseException] = None,
        exc_value: BaseException = None,
        traceback: TracebackType = None,
    ):
        assert self.excinfo

        if exc_type is None:
            fail(f"NO EXCEPTIONS RAISED, EXPECTED GROUP CONTAINING {self.exception_match}")

        if not issubclass(exc_type, BaseExceptionGroup):
            fail(f"NAKED EXCEPTION WAS RAISED: {repr(exc_value)}")

        exc_group = cast(BaseExceptionGroup, exc_value)

        (matched_exc, others) = exc_group.split(self.exception_match)

        if matched_exc is None:
            fail(f"DID NOT RAISE {self.exception_match} IN EXCEPTION GROUP")

        if others is not None:
            warnings.warn(f"Unexpected exceptions: {others!r}", stacklevel=2)
            raise ExceptionGroup(
                "Thrown group contained unexpected exceptions", others.exceptions
            ) from exc_value

        exceptions = flattened_exceptions(matched_exc)

        if len(exceptions) > 1 and not self.allow_multiple:
            fail(f"GROUP CONTAINED MORE THAN ONE {self.exception_match}")

        exc = exceptions[0]

        try:
            exc_info = (type(exc), exc, exc.__traceback__)
            if BYPASS_PYTEST_INTERNAL_WARNING:
                self.excinfo.__init__(exc_info, _ispytest=True)  # type: ignore
            else:
                self.excinfo.__init__(exc_info)  # type: ignore
        except BaseException as e:
            msg = (
                "Failed to populate exception info, please open an issue over at "
                "https://github.com/xoeye/typecats/issues."
                "Make sure to mention your Python and Pytest versions!"
            )
            raise PytestInternalAPIChangedError(msg) from e
        if self.match_expr is not None:
            self.excinfo.match(self.match_expr)

        return True  # suppress exception


def raises_in_group(exception_match: ExceptionMatch, match_expr: str = None, allow_multiple=False):
    """Captures the only (or first of, if allow_multiple=True) exception in a group.
    Fails the test in the following order:
      - No exceptions are thrown
      - Thrown exception is not an exception group
      - Thrown group does not contain expected exception
      - Thrown group contained unexpected exceptions
      - (if allow_multiple=False): Thrown group contains more than one of the expected exception
      - (if matched_expr is not None): First matched exception does not match the passed regex

    Parameters:
    exception_match: Same as ExceptionGroup.subgroup
    match_expr: Same as pytest.raises. If set, will only check against the first found exception.


    If you need to capture multiple exceptions from a group, you should instead
    use `pytest.raises(BaseExceptionGroup)` and consider
    using `typecats.exceptiongroups.filter_flattened_exceptions`, though you will
    need to account for any other unmatched exceptions on your own.
    """
    return RaisesExceptionGroupContext(exception_match, match_expr, allow_multiple)
