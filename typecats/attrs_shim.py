"""Shim for attrs to make `Cat`s possible."""
import typing as ty
from decimal import Decimal

import attr

_SCALAR_TYPES_WITH_NO_EMPTY_VALUES = (bool, float, int, Decimal)


def nonempty_validator(self, attribute, value):
    """Don't allow strings and collections without attr defaults to have empty/False-y values."""
    if attribute.type in _SCALAR_TYPES_WITH_NO_EMPTY_VALUES:
        return
    if attribute.default is attr.NOTHING:
        if not value:
            raise ValueError(
                f'Attribute "{attribute.name}" on class {type(self)} '
                f"with type {attribute.type} "
                f"cannot have empty value '{value}'!"
            )


def make_disallow_empties_transformer(disallow_empties: bool, user_transformer=None):
    """Returns a field_transformer that optionally injects nonempty validators on required fields."""

    def transformer(cls, fields):
        result = []
        for field in fields:
            if (
                disallow_empties
                and field.default is attr.NOTHING
                and field.type not in _SCALAR_TYPES_WITH_NO_EMPTY_VALUES
            ):
                combined = (
                    attr.validators.and_(field.validator, nonempty_validator)
                    if field.validator
                    else nonempty_validator
                )
                field = field.evolve(validator=combined)
            result.append(field)
        if user_transformer is not None:
            result = user_transformer(cls, result)
        return result

    return transformer


def get_attrs_names(Type: type) -> ty.Set[str]:
    attrs_attrs = getattr(Type, "__attrs_attrs__", None)
    if attrs_attrs is None:
        raise ValueError(f"type {Type} is not an attrs class")
    return {a.name for a in attrs_attrs}


