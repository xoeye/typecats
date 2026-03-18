"""Shim for attrs to make `Cat`s possible."""

from __future__ import annotations

import typing as ty
from decimal import Decimal

import attr

_SCALAR_TYPES_WITH_NO_EMPTY_VALUES = (bool, float, int, Decimal)

FieldTransformer = ty.Callable[[type, list[attr.Attribute]], list[attr.Attribute]]


def cat_attrs(
    maybe_cls: type | None = None,
    auto_attribs: bool = False,
    disallow_empties: bool = True,
    field_transformer: FieldTransformer | None = None,
    **kwargs: ty.Any,
) -> type:
    """Compatibility shim. Prefer using the @Cat decorator instead."""

    def wrap(cls: type) -> type:
        return attr.attrs(
            cls,
            auto_attribs=auto_attribs,
            field_transformer=make_disallow_empties_transformer(disallow_empties, field_transformer),
            **kwargs,
        )

    if maybe_cls is None:
        return wrap  # type: ignore[return-value]
    return wrap(maybe_cls)


def nonempty_validator(self: ty.Any, attribute: attr.Attribute[ty.Any], value: ty.Any) -> None:
    """Don't allow strings and collections without attr defaults to have empty/False-y values."""
    if attribute.type in _SCALAR_TYPES_WITH_NO_EMPTY_VALUES:
        # doesn't make sense to 'validate' these types against emptiness
        # since 0 or False are not 'empty' values
        return
    if attribute.default is attr.NOTHING:
        if not value:
            raise ValueError(
                f'Attribute "{attribute.name}" on class {type(self)} '
                f"with type {attribute.type} "
                f"cannot have empty value '{value}'!"
            )


def make_disallow_empties_transformer(
    disallow_empties: bool, user_transformer: FieldTransformer | None = None
) -> FieldTransformer:
    """Returns a field_transformer that optionally injects nonempty validators on required fields."""

    def transformer(cls: type, fields: list[attr.Attribute]) -> list[attr.Attribute]:
        result = []
        for field in fields:
            if (
                disallow_empties
                and field.default is attr.NOTHING
                and field.type not in _SCALAR_TYPES_WITH_NO_EMPTY_VALUES
            ):
                combined = (
                    attr.validators.and_(field.validator, nonempty_validator) if field.validator else nonempty_validator
                )
                field = field.evolve(validator=combined)
            result.append(field)
        if user_transformer is not None:
            result = user_transformer(cls, result)
        return result

    return transformer


def get_attrs_names(Type: type) -> set[str]:
    attrs_attrs = getattr(Type, "__attrs_attrs__", None)
    if attrs_attrs is None:
        raise ValueError(f"type {Type} is not an attrs class")
    return {a.name for a in attrs_attrs}


def drop_nonattrs(d: dict[str, ty.Any], Type: type) -> dict[str, ty.Any]:
    """Return a copy of d with only the keys that correspond to attrs fields on Type."""
    attrs = get_attrs_names(Type)
    return {key: val for key, val in d.items() if key in attrs}
