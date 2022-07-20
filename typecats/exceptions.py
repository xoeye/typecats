"""Not necessarily only for logging, but the default behavior is to log"""

import contextlib
import typing as ty
import traceback
import logging
from .types import C, StrucInput

from cattrs import Converter
from cattrs.errors import BaseValidationError

logger = logging.getLogger(__name__)


_TYPECATS_PATCH_EXCEPTION_ATTR = "__typecats_exc_stack"

TypecatsStack = ty.List[ty.Tuple[ty.Any, type]]

TypecatsCommonExceptionHook = ty.Callable[[Exception, ty.Any, type, TypecatsStack], None]


StructuringError = BaseValidationError

# These are what can be thrown when disabling detailed validation
_BASIC_VALIDATION_EXCEPTIONS = (
    TypeError,
    AttributeError,
    ValueError,
    IndexError,
    KeyError,
)


class SimpleValidationError(BaseValidationError):
    pass


@contextlib.contextmanager
def _consolidate_exceptions(converter: Converter, cl: ty.Type[C]):
    """Re-raises basic validation exceptions as a SimpleValidationException group.
    Cattrs added detailed validation in 22.1.0. TLDR: detailed validation now throws
    a BaseValidationError. Without it, validation can throw a bunch of different errors.
    We are therefore adopting the exception group approach and bubbling up exceptions
    thrown with detailed validation disabled through a SimpleValidationError, which
    extends BaseValidationError. We intend users to catch StructuringError in most cases.
    """

    try:
        yield
    except _BASIC_VALIDATION_EXCEPTIONS as e:
        if not converter.detailed_validation:
            err_msg = "While structuring without detailed validation"
            err = SimpleValidationError(err_msg, [e], cl)
            raise err from e

        raise e


def _simple_type_name(Type: type) -> str:
    return getattr(Type, "__name__", str(Type))


def _assemble_default_exception_msg(
    exception: Exception, item: StrucInput, Type: type, typecats_stack: TypecatsStack
) -> str:
    failure_item, failure_type = typecats_stack[-1]
    type_path = [_simple_type_name(type_) for _item, type_ in typecats_stack]
    full_context = (
        f" at type path {type_path} within item {item}" if failure_item is not item else ""
    )
    return (
        f"Failed to structure {_simple_type_name(failure_type)}"
        f" from item <{failure_item}>{full_context}"
    )


def _default_log_structure_exception(
    exception: Exception, item: StrucInput, Type: type, typecats_stack: TypecatsStack
) -> None:
    if not typecats_stack:
        return
    try:
        logger.warning(
            _assemble_default_exception_msg(exception, item, Type, typecats_stack),
            extra=dict(
                json=dict(item=item, typecats_stack=typecats_stack),
                traceback=traceback.format_exception(None, exception, exception.__traceback__),
            ),
        )
    except Exception:  # noqa # broad catch because this is nonessential
        logger.exception("Logging failure")


_EXCEPTION_HOOK: TypecatsCommonExceptionHook = _default_log_structure_exception


def set_default_exception_hook(hook: TypecatsCommonExceptionHook):
    global _EXCEPTION_HOOK
    _EXCEPTION_HOOK = hook


def _extract_typecats_stack_if_any(exception: Exception) -> TypecatsStack:
    return list(reversed(getattr(exception, _TYPECATS_PATCH_EXCEPTION_ATTR, list())))


def _emit_exception_to_default_handler(
    exception: Exception, item: ty.Optional[StrucInput], Type: type, typecats_stack: TypecatsStack
):
    global _EXCEPTION_HOOK
    _EXCEPTION_HOOK(exception, item, Type, typecats_stack)


def _embed_exception_info(exception: Exception, item: ty.Any, Type: type):
    typecats_stack = getattr(exception, _TYPECATS_PATCH_EXCEPTION_ATTR, list())
    typecats_stack.append((item, Type))
    setattr(exception, _TYPECATS_PATCH_EXCEPTION_ATTR, typecats_stack)
