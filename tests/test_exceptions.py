from typing import List

import pytest

from typecats import Cat
from typecats.types import CommonStructuringExceptions


def test_exceptions_get_logged(caplog):
    @Cat
    class Bar:
        baz: int

    @Cat
    class Quux:
        foo: str
        bar: Bar

    with pytest.raises(CommonStructuringExceptions):
        Quux.struc(dict(foo="foos", bar=[1, 2, 3]))

    rec = caplog.records.pop(0)
    assert rec.msg.startswith("Failed to structure Bar ")
    assert "type path ['Quux', 'Bar']" in rec.msg


@Cat
class Foo:
    baz: str


@Cat
class Zap:
    x: int
    y: int
    foo_matrix: List[List[Foo]]


def test_exceptions_have_type_path(caplog):

    with pytest.raises(CommonStructuringExceptions):
        Zap.struc(
            dict(
                x=3,
                y=55,
                foo_matrix=[[dict(baz="a"), dict(baz="b")], [dict(baz="c")], [4]],
            )
        )

    rec = caplog.records.pop(0)
    print(rec.msg)
    assert "Failed to structure Foo from item <4> at type path" in rec.msg


def test_try_struc_no_exception_if_common(caplog):

    assert None is Zap.try_struc(dict(x=4, y=55, foo_matrix=[[[]]]))

    assert not caplog.records
