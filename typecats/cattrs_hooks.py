import typing as ty

from typing_extensions import Protocol

from cattr.converters import Converter, _is_attrs_class
from cattr.multistrategy_dispatch import MultiStrategyDispatch

C = ty.TypeVar("C")
StructureHook = ty.Callable[[ty.Any, ty.Type[C]], C]


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
    FunctionDispatch chooses the 'matching' structure/unstructure hook.

    The reason for this is that cattrs doesn't allow you to hook
    directly into each level of un/structuring recursively while still
    using its core logic.

    All of the 'recursive parts' of cattrs un/structuring happens via
    FunctionDispatch within MultistrategyDispatch. So we can simply
    hook into that existing logic.
    """

    def make_patched_handler(original_handler):
        def wrapper_handler(*args) -> ty.Any:
            return patch(original_handler, *args)

        return wrapper_handler

    # preserves order and existing can_handle logic.
    multistrategy_dispatch._function_dispatch._handler_pairs = [
        (can_handle, make_patched_handler(orig_handler))
        for can_handle, orig_handler in multistrategy_dispatch._function_dispatch._handler_pairs
    ]
    multistrategy_dispatch._function_dispatch.dispatch.cache_clear()


class ConverterContextPatch:
    def __init__(self, converter: Converter):
        self.converter = converter
        patch_cattrs_function_dispatch(
            converter._unstructure_func, self.unstructure_patch  # type: ignore
        )
        patch_cattrs_function_dispatch(
            converter._structure_func, self.structure_patch  # type: ignore
        )

    def structure_patch(
        self, original_handler: StructureHook, obj: ty.Any, Type: ty.Type[C]
    ) -> C:
        """Meant to be overridden - this is just a passthrough implementation."""
        return original_handler(obj, Type)

    def unstructure_patch(self, original_handler: ty.Callable, obj: ty.Any) -> ty.Any:
        """Meant to be overridden - this is just a passthrough implementation."""
        return original_handler(obj)


class InterceptedRegistryMultistrategyDispatch:
    __slots__ = ("patch", "parent", "attrs_types")

    def __init__(self, patch, parent):
        self.patch = patch
        self.parent = parent
        self.attrs_types = dict()

    def register_cls_list(self, cls_and_handler, *args, **kwargs):
        single_dispatches = list()
        for cls, handler in cls_and_handler:
            if _is_attrs_class(cls):
                self.attrs_types[cls] = self.patch(handler)
            else:
                single_dispatches.append((cls, handler))
        self.parent.register_cls_list(single_dispatches, *args, **kwargs)

    def register_func_list(self, *args, **kwargs):
        return self.parent.register_func_list(*args, **kwargs)

    def dispatch(self, cls):
        direct_dispatch = self.attrs_types.get(cls)
        if direct_dispatch:
            return direct_dispatch
        return self.parent.dispatch(cls)
