"""TypecatsConverter: a GenConverter subclass with wildcat, strip_defaults, and typing.Any support."""

import typing as ty

from attr import has as is_attrs_class
from cattrs.converters import GenConverter

from .wildcat import is_wildcat, enrich_structured_wildcat, enrich_unstructured_wildcat
from .strip_defaults import ShouldStripDefaults, strip_attrs_defaults
from .exceptions import _consolidate_exceptions, StructuringError, _embed_exception_info
from .stack_context import stack_context


def _has_with_generic(cls) -> bool:
    origin = ty.get_origin(cls)
    return is_attrs_class(cls) or (origin is not None and is_attrs_class(origin))


class TypecatsConverter(GenConverter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Re-register after super().__init__() so our factories take priority over
        # the mapping/dict hooks, which would otherwise win for wildcat (dict subclass) types.
        self.register_structure_hook_factory(
            _has_with_generic, self.gen_structure_attrs_fromdict
        )
        self.register_unstructure_hook_factory(
            _has_with_generic, self.gen_unstructure_attrs_fromdict
        )
        self.register_unstructure_hook_func(
            lambda cl: cl is ty.Any,
            self._unstructure_any,
        )

    def _unstructure_any(self, obj: ty.Any) -> ty.Any:
        cls = type(obj)
        if is_attrs_class(cls):
            return self.unstructure(obj, cls)
        return self.unstructure(obj)

    def gen_structure_attrs_fromdict(self, cls):
        base = super().gen_structure_attrs_fromdict(cls)

        def structure_typecat(dictionary, Type):
            try:
                with _consolidate_exceptions(self, Type):
                    core_type = ty.get_origin(Type) or Type
                    if is_wildcat(Type) and isinstance(dictionary, core_type):
                        res = self.structure_attrs_fromdict(dictionary, Type)
                    else:
                        res = base(dictionary, Type)
                    if is_wildcat(Type):
                        enrich_structured_wildcat(res, dictionary, Type)
                    return res
            except StructuringError as e:
                _embed_exception_info(e, dictionary, Type)
                raise e

        return structure_typecat

    def gen_unstructure_attrs_fromdict(self, cls):
        base = super().gen_unstructure_attrs_fromdict(cls)

        def unstructure_with_extras(obj):
            res = base(obj)
            if ShouldStripDefaults.get():
                res = strip_attrs_defaults(res, obj)
            if is_wildcat(cls):
                res = enrich_unstructured_wildcat(self, obj, res)
            return res

        return unstructure_with_extras

    def unstructure(
        self,
        obj: ty.Any,
        unstructure_as: ty.Any = None,
        *,
        strip_defaults: bool = False,
    ) -> ty.Any:
        if strip_defaults:
            with stack_context(ShouldStripDefaults, True):
                return super().unstructure(obj, unstructure_as)
        return super().unstructure(obj, unstructure_as)
