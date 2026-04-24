import typing as ty

import attr

C = ty.TypeVar("C")
CatT = ty.TypeVar("CatT", bound=attr.AttrsInstance)
"""TypeVar for generic functions that operate on @Cat types.

Bounded by AttrsInstance rather than a Cat-specific protocol because
@Cat is a decorator that produces attrs classes — it does not
introduce its own type identity. @Cat classes are attrs classes at
both runtime and in mypy's type system (via the cats_mypy_plugin).
There is no narrower protocol that distinguishes @Cat from @attr.s
because the struc/try_struc/unstruc methods are added dynamically
by the decorator at runtime and by the plugin at analysis time,
not through inheritance or a protocol.
"""
StructureHook = ty.Callable[[ty.Any, ty.Type[C]], C]

StrucInput = ty.Mapping[str, ty.Any]
UnstrucOutput = dict[str, ty.Any]
