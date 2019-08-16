"""Implements some nice-to-haves for the 'Wildcat' concept of structurable dynamic Class properties."""
# pylint: disable=protected-access
import typing as ty
import logging

from .attrs_shim import get_attrs_names


logger = logging.getLogger(__name__)


MWC = ty.TypeVar("MWC", bound=ty.MutableMapping)
WC = ty.TypeVar("WC", bound=ty.Mapping)


def is_wildcat(cls_or_obj: ty.Union[object, type]) -> bool:
    return (
        hasattr(cls_or_obj, "__setitem__")
        and hasattr(cls_or_obj, "__getitem__")
        and hasattr(cls_or_obj, "__iter__")
    )


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
        non_attribute_kvs = {
            k: v for k, v in other_dict.items() if not hasattr(self, k)
        }
        for key, value in other_dict.items():
            if key not in non_attribute_kvs:
                self[key] = value  # reuse __setitem__ which will forward to setattr
        super(cls, self).update(non_attribute_kvs)  # type: ignore

    setattr(cls, "update", update)


def mixin_wildcat_post_attrs_methods(cls):
    """Adds a repr to an attrs class that additionally prints out an internal dict"""

    def __repr__(self):
        if dict in cls.__mro__:
            wildcat_part = f"+Wildcat{dict(self.items())}" if self.keys() else ""
        else:
            wildcat_part = (
                f"+Wildcat{self.__wildcat_dict}" if self.__wildcat_dict else ""
            )
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

    _strip_defined_abstract_methods(cls)
