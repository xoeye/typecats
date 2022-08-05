import sys

version_info = sys.version_info[0:3]
is_py37 = version_info[:2] == (3, 7)
is_py38_plus = version_info[:2] >= (3, 8)
is_py39_plus = version_info[:2] >= (3, 9)
is_py310_plus = version_info[:2] >= (3, 10)
is_py311_plus = version_info[:2] >= (3, 11)

if is_py38_plus:
    from typing import Literal, Protocol  # type: ignore # noqa
else:
    from typing_extensions import Literal, Protocol  # type: ignore # noqa

if is_py311_plus:
    ExceptionGroup = ExceptionGroup  # noqa
    BaseExceptionGroup = BaseExceptionGroup  # noqa
else:
    from exceptiongroup import ExceptionGroup, BaseExceptionGroup  # noqa
