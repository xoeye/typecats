"""Not necessarily only for logging, but the default behavior is to log"""

import typing as ty
import traceback
import logging

from .patch import _TYPECATS_PATCH_EXCEPTION_ATTR

logger = logging.getLogger(__name__)


TypecatsStack = ty.List[ty.Tuple[ty.Any, type]]

TypecatsCommonExceptionHook = ty.Callable[
    [Exception, ty.Any, type, TypecatsStack], None
]


def _simple_type_name(Type: type) -> str:
    return getattr(Type, "__name__", str(Type))


def _default_log_structure_exception(
    exception: Exception, item: ty.Any, Type: type, typecats_stack: TypecatsStack
) -> None:

    failure_item, failure_type = typecats_stack[-1]
    type_path = [_simple_type_name(type_) for _item, type_ in typecats_stack]
    full_context = (
        f" at type path {type_path} within item {item}"
        if failure_item is not item
        else ""
    )
    logger.warning(
        f"Failed to structure {_simple_type_name(failure_type)} from item <{failure_item}>{full_context}",
        extra=dict(
            json=dict(item=item, typecats_stack=typecats_stack),
            traceback=traceback.format_exception(
                None, exception, exception.__traceback__
            ),
        ),
    )


_EXCEPTION_HOOK: TypecatsCommonExceptionHook = _default_log_structure_exception


def set_default_exception_hook(hook: TypecatsCommonExceptionHook):
    global _EXCEPTION_HOOK
    _EXCEPTION_HOOK = hook


def _extract_typecats_stack_if_any(exception: Exception) -> TypecatsStack:
    return list(reversed(getattr(exception, _TYPECATS_PATCH_EXCEPTION_ATTR, list())))


def _emit_exception_to_default_handler(
    exception: Exception, item: ty.Any, Type: type, typecats_stack: TypecatsStack
):
    global _EXCEPTION_HOOK
    _EXCEPTION_HOOK(exception, item, Type, typecats_stack)
