from typing import Callable, List, Optional, Tuple, Type, TypeVar, Union

from .._compat import BaseExceptionGroup

E = TypeVar("E", bound=BaseException)
ExceptionMatch = Union[
    Type[E],
    Tuple[Type[E], ...],
    Callable[[E], bool],
]


def flattened_exceptions(group: BaseExceptionGroup) -> List[Exception]:
    exceptions = []

    for e in group.exceptions:
        if isinstance(e, BaseExceptionGroup):
            exceptions += flattened_exceptions(e)
        else:
            exceptions.append(e)

    return exceptions


def _flattened_exceptions_if_not_none(
    group: Optional[BaseExceptionGroup],
) -> Optional[List[Exception]]:
    if group is not None:
        return flattened_exceptions(group)
    return None


def filtered_flattened_exceptions(
    exception_match: ExceptionMatch,
    group: BaseExceptionGroup,
) -> Tuple[Optional[List[Exception]], Optional[List[Exception]]]:
    matched, others = group.split(exception_match)

    return (_flattened_exceptions_if_not_none(matched), _flattened_exceptions_if_not_none(others))
