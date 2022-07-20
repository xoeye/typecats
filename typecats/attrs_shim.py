"""Shim for attrs to make `Cat`s possible.

Current attrs version supported is 20.3.0

"""
# pylint: disable=redefined-builtin
import typing as ty
from decimal import Decimal

from attr._make import (
    NOTHING,
    _ClassBuilder,
    _determine_attrs_eq_order,
    _determine_whether_to_implement,
    _has_frozen_base_class,
    _has_own_attribute,
)
from attr import setters
from attr.exceptions import PythonTooOldError
from attr._compat import PY2, PY310


_SCALAR_TYPES_WITH_NO_EMPTY_VALUES = (bool, float, int, Decimal)


def cat_attrs(
    maybe_cls=None,
    these=None,
    repr_ns=None,
    repr=None,
    cmp=None,
    hash=None,
    init=None,
    slots=False,
    frozen=False,
    weakref_slot=True,
    str=False,
    auto_attribs=False,
    kw_only=False,
    cache_hash=False,
    disallow_empties=True,
    auto_exc=False,
    eq=None,
    order=None,
    auto_detect=False,
    collect_by_mro=False,
    getstate_setstate=None,
    on_setattr=None,
    field_transformer=None,
    match_args=True,
):
    """Copied from attrs._make in attrs 21.4.0 in order to allow dynamic adding of validators!
    https://github.com/python-attrs/attrs/blob/21.4.0/src/attr/_make.py#L1219

    The only differences are (or should be...):
    - This docstring
    - disallow_empties=True keyword argument
    - hook_builder_before_doing_anything call.
    """
    if auto_detect and PY2:
        raise PythonTooOldError("auto_detect only works on Python 3 and later.")

    eq_, order_ = _determine_attrs_eq_order(cmp, eq, order, None)
    hash_ = hash  # work around the lack of nonlocal

    if isinstance(on_setattr, (list, tuple)):
        on_setattr = setters.pipe(*on_setattr)

    def wrap(cls):

        if getattr(cls, "__class__", None) is None:
            raise TypeError("attrs only works with new-style classes.")

        is_frozen = frozen or _has_frozen_base_class(cls)
        is_exc = auto_exc is True and issubclass(cls, BaseException)
        has_own_setattr = auto_detect and _has_own_attribute(cls, "__setattr__")

        if has_own_setattr and is_frozen:
            raise ValueError("Can't freeze a class with a custom __setattr__.")

        builder = _ClassBuilder(
            cls,
            these,
            slots,
            is_frozen,
            weakref_slot,
            _determine_whether_to_implement(
                cls,
                getstate_setstate,
                auto_detect,
                ("__getstate__", "__setstate__"),
                default=slots,
            ),
            auto_attribs,
            kw_only,
            cache_hash,
            is_exc,
            collect_by_mro,
            on_setattr,
            has_own_setattr,
            field_transformer,
        )

        # This should be the only change in here.
        # I'm not sure why we're not hooking ClassBuilder's __init__ instead
        # but I will be continuing the trend to keep things simple for now.
        _hook_builder_before_doing_anything(builder, disallow_empties=disallow_empties)

        if _determine_whether_to_implement(cls, repr, auto_detect, ("__repr__",)):
            builder.add_repr(repr_ns)
        if str is True:
            builder.add_str()

        eq = _determine_whether_to_implement(cls, eq_, auto_detect, ("__eq__", "__ne__"))
        if not is_exc and eq is True:
            builder.add_eq()
        if not is_exc and _determine_whether_to_implement(
            cls, order_, auto_detect, ("__lt__", "__le__", "__gt__", "__ge__")
        ):
            builder.add_order()

        builder.add_setattr()

        if hash_ is None and auto_detect is True and _has_own_attribute(cls, "__hash__"):
            hash = False
        else:
            hash = hash_
        if hash is not True and hash is not False and hash is not None:
            # Can't use `hash in` because 1 == True for example.
            raise TypeError("Invalid value for hash.  Must be True, False, or None.")
        elif hash is False or (hash is None and eq is False) or is_exc:
            # Don't do anything. Should fall back to __object__'s __hash__
            # which is by id.
            if cache_hash:
                raise TypeError(
                    "Invalid value for cache_hash.  To use hash caching,"
                    " hashing must be either explicitly or implicitly "
                    "enabled."
                )
        elif hash is True or (hash is None and eq is True and is_frozen is True):
            # Build a __hash__ if told so, or if it's safe.
            builder.add_hash()
        else:
            # Raise TypeError on attempts to hash.
            if cache_hash:
                raise TypeError(
                    "Invalid value for cache_hash.  To use hash caching,"
                    " hashing must be either explicitly or implicitly "
                    "enabled."
                )
            builder.make_unhashable()

        if _determine_whether_to_implement(cls, init, auto_detect, ("__init__",)):
            builder.add_init()
        else:
            builder.add_attrs_init()
            if cache_hash:
                raise TypeError(
                    "Invalid value for cache_hash.  To use hash caching," " init must be True."
                )

        if PY310 and match_args and not _has_own_attribute(cls, "__match_args__"):
            builder.add_match_args()

        return builder.build_class()

    # maybe_cls's type depends on the usage of the decorator.  It's a class
    # if it's used as `@attrs` but ``None`` if used as `@attrs()`.
    if maybe_cls is None:
        return wrap
    else:
        return wrap(maybe_cls)


def nonempty_validator(self, attribute, value):
    """Don't allow strings and collections without attr defaults to have empty/False-y values."""
    if attribute.type in _SCALAR_TYPES_WITH_NO_EMPTY_VALUES:
        # doesn't make sense to 'validate' these types against emptiness
        # since 0 or False are not 'empty' values
        return
    if attribute.default == NOTHING:
        if not value:
            raise ValueError(
                f'Attribute "{attribute.name}" on class {type(self)} '
                f"with type {attribute.type} "
                f"cannot have empty value '{value}'!"
            )


def _hack_add_validator(attrib, validator):
    """Hacks into an attrs attribute to validate something."""
    existing_validator = getattr(attrib, "validator")
    if existing_validator and existing_validator != nonempty_validator:
        input_validator = validator

        def combine_validators(self, att, val):
            existing_validator(self, att, val)
            input_validator(self, att, val)

        validator = combine_validators
    attrib._setattrs((("validator", validator),))


def _hook_builder_before_doing_anything(builder, disallow_empties=True):
    """This is a callback of sorts that I would love to be able
    to have in attrs by default."""
    if not disallow_empties:
        return  # no hook to run other than this one
    for attrib in builder._attrs:
        if attrib.type in _SCALAR_TYPES_WITH_NO_EMPTY_VALUES:
            continue
        # validate ALL attributes that don't have valid default values.
        if attrib.default == NOTHING:
            _hack_add_validator(attrib, nonempty_validator)


def get_attrs_names(Type: type) -> ty.Set[str]:
    attrs_attrs = getattr(Type, "__attrs_attrs__", None)
    if attrs_attrs is None:
        raise ValueError(f"type {Type} is not an attrs class")
    attrs: ty.Set[str] = {attr.name for attr in attrs_attrs}
    return attrs


def drop_nonattrs(d: dict, Type: type) -> dict:
    """gets rid of all members of the dictionary that wouldn't fit in the given 'attrs' Type"""
    attrs = get_attrs_names(Type)
    return {key: val for key, val in d.items() if key in attrs}
