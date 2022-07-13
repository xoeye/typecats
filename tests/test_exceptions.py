from typing import List

import pytest
from typecats import Cat
from typecats.exceptions import StructuringError

from detailed_validation_utils import unsafe_stack_disable_detailed_validation


def test_exceptions_dont_have_type_path(caplog):
    """All offending type paths are reported with detailed validation by cattrs.
    This makes this feature redundant, so we don't bother including the offending paths.
    """

    with pytest.raises(StructuringError):
        Zap.struc(
            dict(
                x=3,
                y=55,
                foo_matrix=[[dict(baz="a"), dict(baz="b")], [dict(baz="c")], [4]],
            )
        )

    rec = caplog.records.pop(0)
    assert "Failed to structure Foo from item <4> " in rec.msg
    assert "at type path" not in rec.msg


def test_exceptions_get_logged_no_detailed_validation(caplog):
    @Cat
    class Bar:
        baz: int

    @Cat
    class Quux:
        foo: str
        bar: Bar

    with pytest.raises(StructuringError):
        with unsafe_stack_disable_detailed_validation():
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


def test_exceptions_have_type_path_no_detailed_validation(caplog):

    with pytest.raises(StructuringError):
        with unsafe_stack_disable_detailed_validation():
            Zap.struc(
                dict(
                    x=3,
                    y=55,
                    foo_matrix=[[dict(baz="a"), dict(baz="b")], [dict(baz="c")], [4]],
                )
            )

    rec = caplog.records.pop(0)
    assert "Failed to structure Foo from item <4> at type path" in rec.msg


def test_try_struc_no_exception_if_common(caplog):

    assert None is Zap.try_struc(dict(x=4, y=55, foo_matrix=[[[]]]))

    assert not caplog.records
