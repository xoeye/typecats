import typing as ty

from typing_extensions import Protocol

from cattr.multistrategy_dispatch import MultiStrategyDispatch


class PostFunctionDispatchPatch(Protocol):
    def __call__(  # noqa
        self, __original_handler: ty.Callable[..., ty.Any], *__handler_args
    ) -> ty.Any:
        ...


def patch_cattrs_function_dispatch(
    multistrategy_dispatch: MultiStrategyDispatch, patch: PostFunctionDispatchPatch
):
    """If you call this, you will be performing a monkey patch on your converter.

    The basic idea here is to let you get a callback right after
    function dispatch existing FunctionDispatch unstructure hook.

    The reason for this is that cattrs doesn't allow you to hook
    directly into each level of unstructuring recursively while still
    using its core logic.

    All of the 'recursive parts' of cattrs unstructuring happens via
    FunctionDispatch within MultistrategyDispatch. So we can simply
    hook into that existing logic.
    """

    def make_patched_handler(handler):
        def wrapper_handler(*args) -> ty.Any:
            return patch(handler, *args)

        return wrapper_handler

    # preserves order and existing can_handle logic.
    multistrategy_dispatch._function_dispatch._handler_pairs = [
        (can_handle, make_patched_handler(handler))
        for can_handle, handler in multistrategy_dispatch._function_dispatch._handler_pairs
    ]
    multistrategy_dispatch._function_dispatch.dispatch.cache_clear()
