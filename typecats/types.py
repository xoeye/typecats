import typing as ty

import attr

C = ty.TypeVar("C")
CatT = ty.TypeVar("CatT", bound=attr.AttrsInstance)
StructureHook = ty.Callable[[ty.Any, ty.Type[C]], C]

StrucInput = ty.Mapping[str, ty.Any]
UnstrucOutput = dict[str, ty.Any]
