"""Implements some nice-to-haves for the 'Wildcat' concept of structurable dynamic Class properties."""
# pylint: disable=protected-access
import typing as ty

from .attrs_shim import get_attrs_names


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


def block_dangerous_dict_subclass_operations(cls):
    """Adds safeguards against overlapping keys and attributes

    to a class that inherits from dict
    """
    class_name = getattr(cls, "__name__", str(cls))

    def raise_key_set_error(key):
        raise KeyError(
            f"Attribute '{key}' is explicitly typed on '{class_name}' "
            "so setting it as a dictionary key is dangerous and therefore disallowed."
        )

    def __setitem__(self, key, item):
        if hasattr(self, key):
            raise_key_set_error(key)
        super(cls, self).__setitem__(key, item)  # type: ignore

    setattr(cls, "__setitem__", __setitem__)

    def __getitem__(self, key):
        if hasattr(self, key):
            raise KeyError(
                f"Attribute '{key}' is explicitly typed on '{class_name}' "
                "so getting it as a dictionary key is dangerous and therefore disallowed."
            )
        return super(cls, self).__getitem__(key)  # type: ignore

    setattr(cls, "__getitem__", __getitem__)

    def update(self, other_dict=None, **kwargs):
        if other_dict:
            for key in other_dict.keys():
                if hasattr(self, key):
                    raise_key_set_error(key)
            super(cls, self).update(other_dict)  # type: ignore
        else:
            for arg in kwargs:
                if hasattr(self, arg):
                    raise_key_set_error(arg)
            super(cls, self).update(**kwargs)  # type: ignore

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
