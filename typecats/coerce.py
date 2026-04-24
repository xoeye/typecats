"""on_setattr hook that coerces values through the cattrs converter on type mismatch."""

import typing as ty

import attr

if ty.TYPE_CHECKING:
    from .converter import TypecatsConverter


def _unwrap_optional(field_type: type) -> type | None:
    """Return the inner type if field_type is Optional[X], else None."""
    origin = ty.get_origin(field_type)
    if origin is ty.Union:
        args = [a for a in ty.get_args(field_type) if a is not type(None)]
        if len(args) == 1:
            return args[0]
    return None


def make_coerce_hook(
    converter: "TypecatsConverter",
) -> ty.Callable[[ty.Any, attr.Attribute, ty.Any], ty.Any]:  # type: ignore[type-arg]
    """Build an attrs on_setattr hook that structures mismatched values.

    When a value is assigned to a Cat field and the value's runtime type does
    not match the declared type, the converter structures the value into the
    correct type. This prevents cattrs 26+ from crashing during unstructure
    when it encounters, e.g., a str where a datetime is declared.
    """

    def _coerce(instance: ty.Any, attrib: attr.Attribute, new_value: ty.Any) -> ty.Any:  # type: ignore[type-arg]
        if new_value is None:
            return new_value

        field_type = attrib.type
        if field_type is None:
            return new_value

        inner = _unwrap_optional(field_type)
        check_type = inner if inner is not None else field_type

        # Subscripted generics (e.g. Dict[str, X]) can't be used with isinstance.
        # Use the origin type for the check, or skip if there is none.
        origin = ty.get_origin(check_type)
        if origin is not None:
            if isinstance(new_value, origin):
                return new_value
        elif isinstance(check_type, type) and isinstance(new_value, check_type):
            return new_value

        return converter.structure(new_value, check_type)

    return _coerce
