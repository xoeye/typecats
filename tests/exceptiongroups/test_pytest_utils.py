import warnings
from unittest.mock import MagicMock

import pytest
import typecats.exceptiongroups.pytest_utils as pytest_utils
from pytest_mock import MockerFixture
from typecats._compat import ExceptionGroup
from typecats.exceptiongroups.pytest_utils import PytestInternalAPIChangedError, raises_in_group


class UnitTestFailure(Exception):
    def __init__(self, *args):
        super().__init__(self, *args)


def _throw_instead_of_fail(*args):
    raise UnitTestFailure(*args)


@pytest.fixture
def mocked_fail(mocker: MockerFixture):
    mocked_fail = mocker.patch.object(pytest_utils, "fail")
    mocked_fail.side_effect = _throw_instead_of_fail
    return mocked_fail


def test_fails_if_nothing_raised(mocked_fail):
    with pytest.raises(UnitTestFailure, match="NO EXCEPTIONS RAISED"):
        with raises_in_group(TypeError):
            pass


def test_fails_if_naked_exception_raised(mocked_fail):
    with pytest.raises(UnitTestFailure, match="NAKED EXCEPTION WAS RAISED"):
        with raises_in_group(TypeError):
            raise TypeError("This is not encapsulated in a group")


def test_fails_if_group_does_not_contain_type(mocked_fail):
    with pytest.raises(UnitTestFailure, match="DID NOT RAISE <class 'TypeError'>"):
        with raises_in_group(TypeError):
            raise ExceptionGroup("", [ValueError()])

    with pytest.raises(
        UnitTestFailure, match=r"DID NOT RAISE \(<class 'TypeError'>, <class 'NameError'>\)"
    ):
        with raises_in_group((TypeError, NameError)):
            raise ExceptionGroup("", [ValueError()])

    with pytest.raises(UnitTestFailure, match=r"DID NOT RAISE <function"):

        def match_nothing(x: BaseException):
            return x.args == ("a", "b")

        with raises_in_group(match_nothing):
            raise ExceptionGroup("", [ValueError()])


def test_fails_if_group_has_more_than_one(mocked_fail: MagicMock):
    with pytest.raises(UnitTestFailure, match="GROUP CONTAINED MORE THAN ONE <class 'TypeError'>"):
        with raises_in_group(TypeError):
            raise ExceptionGroup("", [TypeError(), TypeError()])

    mocked_fail.reset_mock()

    with raises_in_group(TypeError, allow_multiple=True):
        raise ExceptionGroup("", [TypeError(), TypeError()])

    mocked_fail.assert_not_called()


def test_fails_if_group_has_unexpected_error():
    with pytest.raises(ExceptionGroup, match="unexpected exceptions"):
        with warnings.catch_warnings(record=True) as w:
            with raises_in_group(ValueError):
                raise ExceptionGroup("", [TypeError(), ValueError()])

            assert len(w) == 1
            warning = w[0]
            assert "Unexpected exceptions" in warning
            assert "ExceptionGroup('', [TypeError()])" in warning


def test_throws_pytest_api_changed_error(mocker: MockerFixture):
    with pytest.raises(PytestInternalAPIChangedError, match="github.com/xoeye/typecats/issues"):
        with raises_in_group(TypeError) as e:
            mocked_init = mocker.patch.object(e, "__init__")
            mocked_init.side_effect = RuntimeError("Pytest api changed")
            raise ExceptionGroup("", [TypeError()])

        mocked_init.assert_called_once()


def test_correctly_populates_forward_exception_reference(mocked_fail):
    with raises_in_group(TypeError) as e:
        raise ExceptionGroup("", [TypeError(1)])

    assert isinstance(e.value, TypeError)
    assert e.value.args[0] == 1


def test_correctly_populates_reference_with_first_instance_in_group(mocked_fail):
    with raises_in_group(TypeError, allow_multiple=True) as e:
        raise ExceptionGroup("", [TypeError(1), TypeError(2), ExceptionGroup("", [TypeError(3)])])

    assert isinstance(e.value, TypeError)
    assert e.value.args[0] == 1


def test_match_expr(mocked_fail):
    with raises_in_group(TypeError, "something happened!"):
        raise ExceptionGroup("", [TypeError("something happened!")])

    with raises_in_group(TypeError, "something happened!", allow_multiple=True):
        raise ExceptionGroup("", [TypeError("something happened!"), TypeError(2)])

    with pytest.raises(AssertionError):
        with raises_in_group(TypeError, "something happened!", allow_multiple=True):
            raise ExceptionGroup("", [TypeError("something else happened!"), TypeError(2)])
