import typing as ty

from .cattrs_hooks import C, StructureHook  # noqa

StrucInput = ty.Mapping[str, ty.Any]
UnstrucOutput = dict

CommonStructuringExceptions = (TypeError, AttributeError, ValueError)
