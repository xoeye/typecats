"""Implements some nice-to-haves for the 'Wildcat' concept of structurable dynamic Class properties."""
# pylint: disable=protected-access
import typing as ty
import logging

from attr import has as is_attrs_class
from cattr.converters import Converter
from .attrs_shim import get_attrs_names


logger = logging.getLogger(__name__)


MWC = ty.TypeVar("MWC", bound=ty.MutableMapping)
WC = ty.TypeVar("WC", bound=ty.Mapping)


def is_wildcat(cls: type) -> bool:
    return is_attrs_class(cls) and dict in cls.__mro__


def enrich_structured_wildcat(
    wildcat: MWC, prestructured_obj_dict: ty.Mapping[ty.Any, ty.Any], Type: type
) -> None:
    """A Wildcat is a Cat (an attrs class) that additionally allows
    arbitrary key-value access as though it were a dict for data that
    does not have a defined attribute name on the class (i.e. is not typed).

    This is intended to provide a smooth transition for types that
    have some dynamic elements, but as though dynamic elements become
    'settled', they can be directly typed and statically
    typed-checked. It also makes for a good partially-typed
    passthrough defintion if you need to retain and later transmit
    unknown keys while still letting your code reason about the types
    that you do know about.

    """
    wildcat.update(
        {
            key: prestructured_obj_dict[key]
            for key in prestructured_obj_dict
            if key not in get_attrs_names(Type)
        }
    )


def enrich_unstructured_wildcat(converter: Converter, obj: WC, unstructured_obj_dict: dict) -> dict:
    wildcat_attrs_names = get_attrs_names(type(obj))
    wildcat_nonattrs_dict = {
        key: converter.unstructure(obj[key]) for key in obj if key not in wildcat_attrs_names
    }
    # note that typed entries take absolute precedence over untyped in case of collisions.
    # these collisions should generally be prevented at runtime by the wildcat
    # logic that is injected into the type, but if something were to sneak through
    # we would prefer whatever had been set via the attribute.
    return {**wildcat_nonattrs_dict, **unstructured_obj_dict}


def _strip_defined_abstract_methods(cls):
    """If a method has been dynamically defined/mixed-in, then it is no longer abstract,

    but apparently this must be fixed up manually
    """
    abs_methods = getattr(cls, "__abstractmethods__", None)
    if abs_methods:
        new_abs_methods = {
            methodname for methodname in abs_methods if methodname not in cls.__dict__
        }
        setattr(cls, "__abstractmethods__", frozenset(new_abs_methods))


def setup_warnings_for_dangerous_dict_subclass_operations(cls):
    """Adds safeguards that will warn about attributes that 'overlap' keys
    to a class that inherits from dict.
    """
    class_name = getattr(cls, "__name__", str(cls))

    def warn_key_set_on_attribute(key):
        logger.warning(
            f"Attribute '{key}' is explicitly typed on '{class_name}' "
            "so this should be changed to attribute assigment."
        )

    def __setitem__(self, key, item):
        if hasattr(self, key):
            warn_key_set_on_attribute(key)
            setattr(self, key, item)
        else:
            super(cls, self).__setitem__(key, item)  # type: ignore

    setattr(cls, "__setitem__", __setitem__)

    def __getitem__(self, key):
        if hasattr(self, key):
            logger.warning(
                f"Attribute '{key}' is explicitly typed on '{class_name}' "
                "so this should be changed to attribute access."
            )
            return getattr(self, key)
        return super(cls, self).__getitem__(key)  # type: ignore

    setattr(cls, "__getitem__", __getitem__)

    def update(self, other_dict=None, **kwargs):
        if not other_dict:
            other_dict = kwargs
        non_attribute_kvs = {k: v for k, v in other_dict.items() if not hasattr(self, k)}
        for key, value in other_dict.items():
            if key not in non_attribute_kvs:
                self[key] = value  # reuse __setitem__ which will forward to setattr
        super(cls, self).update(non_attribute_kvs)  # type: ignore

    setattr(cls, "update", update)


def mixin_wildcat_post_attrs_methods(cls):
    """Adds a repr to an attrs class that additionally prints out an internal dict"""

    def __repr__(self):
        if dict in cls.__mro__:
            wd = dict(dict.items(self)) if dict.keys(self) else None
            wildcat_part = f"+Wildcat{wd}" if wd else ""
        else:
            wildcat_part = f"+Wildcat{self.__wildcat_dict}" if self.__wildcat_dict else ""
        return self.__attrs_repr__() + wildcat_part

    setattr(cls, "__attrs_repr__", cls.__repr__)
    setattr(cls, "__repr__", __repr__)

    # we ran into an issue where, because a Wildcat is a dict and therefore defined
    # __len__, that value was used as the truth-check in a standard `if wildcat:`
    # check, which was not what was desired since the object itself existed and had data.
    def __bool__(self):
        """An actual Wildcat is truthy based on the entire contents of its
        attributes and dict, unless otherwise defined"""
        is_truthy = bool(len(self))
        for attr_name in get_attrs_names(cls):
            if is_truthy:
                break
            is_truthy |= bool(getattr(self, attr_name, False))
        return is_truthy

    if not hasattr(cls, "__bool__"):
        setattr(cls, "__bool__", __bool__)

    attrs_equals = getattr(cls, "__eq__")

    def __eq__(self, other):
        at_eq = attrs_equals(self, other)
        return at_eq and super(cls, self).__eq__(other)

    setattr(cls, "__eq__", __eq__)

    _strip_defined_abstract_methods(cls)
