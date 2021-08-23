import sys

version_info = sys.version_info[0:3]
is_py37 = version_info[:2] == (3, 7)
# is_py38 = version_info[:2] == (3, 8)
# is_py39_plus = version_info[:2] >= (3, 9)

if sys.version_info <= (3, 7):
    from typing_extensions import Protocol, Literal  # noqa
else:
    from typing import Protocol, Literal  # noqa
