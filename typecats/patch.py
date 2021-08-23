"""A new way of using cattrs that should simplify our code while
allowing us to make use of the new GenConverter in cattrs, which is
faster and supports new-style Python type annotations, e.g. list[int]
instead of typing.List[int].

"""
from functools import partial

from attr import has as is_attrs_class
from cattr.converters import Converter
from cattr.gen import make_dict_structure_fn, make_dict_unstructure_fn

from .wildcat import is_wildcat, enrich_structured_wildcat, enrich_unstructured_wildcat
from .strip_defaults import ShouldStripDefaults, strip_attrs_defaults
from .exceptions import _embed_exception_info
from .types import CommonStructuringExceptions

__patched_converters = list()


def structure_wildcat_factory(converter, cls):
    base_structure_func = make_dict_structure_fn(cls, converter)

    def structure_typecat(dictionary, Type):
        try:
            res = base_structure_func(dictionary, Type)
            if is_wildcat(Type):
                enrich_structured_wildcat(res, dictionary, Type)
            return res
        except CommonStructuringExceptions as e:
            _embed_exception_info(e, dictionary, Type)
            raise e

    return structure_typecat


def unstructure_strip_defaults_factory(converter, cls):

    base_unstructure_func = make_dict_unstructure_fn(cls, converter)

    def unstructure_strip_defaults(obj):
        res = base_unstructure_func(obj)
        if ShouldStripDefaults.get():
            res = strip_attrs_defaults(res, obj)
        if is_wildcat(cls):
            return enrich_unstructured_wildcat(converter, obj, res)
        return res

    return unstructure_strip_defaults


def patch_converter_for_typecats(converter: Converter) -> Converter:
    if converter in __patched_converters:
        return converter

    converter.register_structure_hook_factory(
        is_attrs_class, partial(structure_wildcat_factory, converter)
    )

    converter.register_unstructure_hook_factory(
        is_attrs_class, partial(unstructure_strip_defaults_factory, converter)
    )

    __patched_converters.append(converter)
    return converter
