import typing as ty

C = ty.TypeVar("C")
StructureHook = ty.Callable[[ty.Any, ty.Type[C]], C]

StrucInput = ty.Mapping[str, ty.Any]
UnstrucOutput = dict[str, ty.Any]


class StrucFunc(ty.Protocol):  # pylint: disable=too-few-public-methods
    """Protocol for a structure callable: maps (type[C], StrucInput) -> C."""

    def __call__[C](self, cl: type[C], obj: StrucInput) -> C: ...  # pylint: disable=redefined-outer-name


class UnstrucFunc(ty.Protocol):  # pylint: disable=too-few-public-methods
    """Protocol for an unstructure callable: maps any object to its unstructured form."""

    def __call__[T](self, obj: T, *, strip_defaults: bool = False) -> ty.Any: ...
