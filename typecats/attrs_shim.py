"""Shim for attrs to make `Cat`s possible.

Current attrs version supported is 19.1.0

"""
# pylint: disable=redefined-builtin
import typing as ty
from decimal import Decimal

from attr._make import NOTHING, _ClassBuilder


_SCALAR_TYPES_WITH_NO_EMPTY_VALUES = (bool, float, int, Decimal)


def cat_attrs(
    maybe_cls=None,
    these=None,
    repr_ns=None,
    repr=True,
    cmp=True,
    hash=None,
    init=True,
    slots=False,
    frozen=False,
    weakref_slot=True,
    str=False,
    auto_attribs=False,
    kw_only=False,
    cache_hash=False,
    disallow_empties=True,
    auto_exc=False,
):
    """Copied from attrs._make in attrs 19.1.0 in order to allow dynamic adding of validators!

    The only difference is (or should be...) the hook_builder_before_doing_anything call.
    """

    def wrap(cls):
        if getattr(cls, "__class__", None) is None:
            raise TypeError("attrs only works with new-style classes.")

        is_exc = auto_exc is True and issubclass(cls, BaseException)

        builder = _ClassBuilder(
            cls,
            these,
            slots,
            frozen,
            weakref_slot,
            auto_attribs,
            kw_only,
            cache_hash,
            is_exc,
        )

        _hook_builder_before_doing_anything(builder, disallow_empties=disallow_empties)

        if repr is True:
            builder.add_repr(repr_ns)
        if str is True:
            builder.add_str()
        if cmp is True and not is_exc:
            builder.add_cmp()

        if hash is not True and hash is not False and hash is not None:
            # Can't use `hash in` because 1 == True for example.
            raise TypeError("Invalid value for hash.  Must be True, False, or None.")
        elif hash is False or (hash is None and cmp is False):
            if cache_hash:
                raise TypeError(
                    "Invalid value for cache_hash.  To use hash caching,"
                    " hashing must be either explicitly or implicitly "
                    "enabled."
                )
        elif (
            hash is True
            or (hash is None and cmp is True and frozen is True)
            and is_exc is False
        ):
            builder.add_hash()
        else:
            if cache_hash:
                raise TypeError(
                    "Invalid value for cache_hash.  To use hash caching,"
                    " hashing must be either explicitly or implicitly "
                    "enabled."
                )
            builder.make_unhashable()

        if init is True:
            builder.add_init()
        else:
            if cache_hash:
                raise TypeError(
                    "Invalid value for cache_hash.  To use hash caching,"
                    " init must be True."
                )

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
