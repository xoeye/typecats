import typing as ty
from functools import lru_cache
from typing_extensions import Literal

import attr
from cattr.converters import _is_attrs_class, Converter

from .patch import TypecatsCattrPatch

C = ty.TypeVar("C")


_MISSING = object()


@lru_cache(128)
def _get_factory_default(_attr):
    return _attr.default.factory()


def _get_attr_default_value(attribute) -> ty.Any:
    if not isinstance(attribute.default, attr.Factory):  # type: ignore
        return attribute.default
    return _get_factory_default(attribute)


def _strip_attr_defaults(
    attrs_type: ty.Type, m: ty.Mapping[str, ty.Any]
) -> ty.Dict[str, ty.Any]:
    """The idea here is that when you are using pure dicts, a key can be
    missing to indicate absence.  But if you're dealing with typed
    objects, that's not possible since all keys are always present.  So
    the only 'reasonable' way to determine what a 'union' means in a
    class-based world is to prefer non-default values to default values at
    all times, which attrs can tell us about.
    """
    attr_defaults_by_name = {
        attribute.name: _get_attr_default_value(attribute)
        for attribute in attrs_type.__attrs_attrs__
    }
    return {
        k: v
        for k, v in m.items()
        if k not in attr_defaults_by_name or v != attr_defaults_by_name[k]
    }


def _get_names_of_defaulted_nonliteral_attrs(attrs_obj: ty.Any) -> ty.Set[str]:
    res: ty.Set[str] = set()
    for _attr in attrs_obj.__attrs_attrs__:
        if getattr(_attr.type, "__origin__", None) is Literal:
            # don't strip attributes annotated as Literals - they're requirements, not "defaults"
            continue
        if getattr(attrs_obj, _attr.name, _MISSING) == _get_attr_default_value(_attr):
            res.add(_attr.name)
    return res


def _strip_attrs_defaults(
    unstructured_but_unclean: ty.Any, obj_to_unstructure: ty.Any
) -> ty.Any:
    if _is_attrs_class(obj_to_unstructure.__class__):
        keys_to_strip = _get_names_of_defaulted_nonliteral_attrs(obj_to_unstructure)
        return {
            k: v for k, v in unstructured_but_unclean.items() if k not in keys_to_strip
        }
    return unstructured_but_unclean


class StripAttrsDefaultsOnUnstructurePatch(TypecatsCattrPatch):
    def unstructure_patch(
        self, original_handler: ty.Callable, obj_to_unstructure: ty.Any
    ) -> ty.Any:
        rv = super().unstructure_patch(original_handler, obj_to_unstructure)
        return _strip_attrs_defaults(rv, obj_to_unstructure)


_STRIP_DEFAULTS_CONVERTER = Converter()  # create converter
__PATCH = StripAttrsDefaultsOnUnstructurePatch(_STRIP_DEFAULTS_CONVERTER)  # patch it


def get_stripping_converter() -> Converter:
    return _STRIP_DEFAULTS_CONVERTER


def unstruc_strip_defaults(obj: ty.Any) -> ty.Any:
    """This is the only thing anyone outside needs to worry about"""
    return _STRIP_DEFAULTS_CONVERTER.unstructure(obj)
