from __future__ import annotations

import typing as ty
from functools import lru_cache
import contextvars as cv

import attr
from attr import has as is_attrs_class

from typing import Literal

ShouldStripDefaults = cv.ContextVar("TypecatsShouldStripDefaults", default=False)


_MISSING = object()


@lru_cache(128)
def _get_factory_default(_attr: attr.Attribute[ty.Any]) -> ty.Any:
    return _attr.default.factory()  # type: ignore[union-attr]


def _get_attr_default_value(attribute: attr.Attribute[ty.Any]) -> ty.Any:
    if hasattr(attribute.default, "factory"):
        return _get_factory_default(attribute)
    return attribute.default


def _get_names_of_defaulted_nonliteral_attrs(attrs_obj: ty.Any) -> set[str]:
    res: set[str] = set()
    for _attr in attrs_obj.__attrs_attrs__:
        if getattr(_attr.type, "__origin__", None) is Literal:
            # don't strip attributes annotated as Literals - they're requirements, not "defaults"
            continue
        if getattr(attrs_obj, _attr.name, _MISSING) == _get_attr_default_value(_attr):
            res.add(_attr.name)
    return res


def strip_attrs_defaults(
    unstructured_but_unclean: dict[str, ty.Any], obj_to_unstructure: ty.Any
) -> dict[str, ty.Any]:
    """The idea here is that when you are using pure dicts, a key can be
    missing to indicate absence.  But if you're dealing with typed
    objects, that's not possible since all keys are always present.  So
    the only 'reasonable' way to determine what a 'union' means in a
    class-based world is to prefer non-default values to default values at
    all times, which attrs can tell us about.
    """

    if not is_attrs_class(obj_to_unstructure.__class__):
        raise TypeError(f"{type(obj_to_unstructure)} is not an attrs class")
    keys_to_strip = _get_names_of_defaulted_nonliteral_attrs(obj_to_unstructure)
    return {k: v for k, v in unstructured_but_unclean.items() if k not in keys_to_strip}
