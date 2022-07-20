import typing as ty

C = ty.TypeVar("C")
StructureHook = ty.Callable[[ty.Any, ty.Type[C]], C]

StrucInput = ty.Mapping[str, ty.Any]
UnstrucOutput = dict
