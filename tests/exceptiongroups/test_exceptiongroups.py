from functools import partial

import pytest
from typecats._compat import ExceptionGroup
from typecats.exceptiongroups import filtered_flattened_exceptions, flattened_exceptions


@pytest.fixture
def sample_group():
    try:
        raise ExceptionGroup(
            "Sample Error",
            [
                ValueError(1),
                ExceptionGroup(
                    "Sample Error 2",
                    [
                        TypeError(2),
                        NameError("a"),
                        ExceptionGroup(
                            "Sample Error 3",
                            [
                                ValueError(3),
                            ],
                        ),
                    ],
                ),
                ExceptionGroup(
                    "Sample Error 2.1",
                    [
                        TypeError(2.1),
                        ValueError(2.1),
                    ],
                ),
            ],
        )
    except ExceptionGroup as e:
        return e


@pytest.fixture
def sample_flat():
    """Manually flattened sample_group, in lexical (or line-by-line) order from top to bottom"""
    return [
        ValueError(1),
        TypeError(2),
        NameError("a"),
        ValueError(3),
        TypeError(2.1),
        ValueError(2.1),
    ]


def test_flattened_exceptions(sample_group, sample_flat):
    for i, exc in enumerate(flattened_exceptions(sample_group)):
        assert isinstance(exc, type(sample_flat[i]))
        assert exc.args == sample_flat[i].args


get_value_errors = partial(filtered_flattened_exceptions, ValueError)
get_type_errors = partial(filtered_flattened_exceptions, TypeError)


def test_filtered_flattened_exceptions(sample_group):
    value_errors, non_value_errors = get_value_errors(sample_group)
    assert value_errors
    assert len(value_errors) == 3

    type_errors, _others = get_type_errors(sample_group)
    assert type_errors
    assert len(type_errors) == 2


def test_filtered_flattened_exceptions_tuple(sample_group):
    expected = [
        ValueError(1),
        TypeError(2),
        ValueError(3),
        TypeError(2.1),
        ValueError(2.1),
    ]

    matched, others = filtered_flattened_exceptions((ValueError, TypeError), sample_group)
    assert matched
    assert others

    for i, exc in enumerate(matched):
        assert isinstance(exc, type(expected[i]))
        assert exc.args == expected[i].args

    assert len(others) == 1
    assert isinstance(others[0], NameError)
    assert others[0].args == ("a",)


def test_filtered_flattened_exceptions_predicate(sample_group):
    def _is_value_under_3(exc: Exception):
        try:
            return int(exc.args[0]) < 3
        except ValueError:
            return False

    get_errors_under_3 = partial(filtered_flattened_exceptions, _is_value_under_3)

    expected_matched = [
        ValueError(1),
        TypeError(2),
        TypeError(2.1),
        ValueError(2.1),
    ]

    expected_others = [
        NameError("a"),
        ValueError(3),
    ]

    matched, others = get_errors_under_3(sample_group)
    assert matched
    assert others

    for i, exc in enumerate(matched):
        assert isinstance(exc, type(expected_matched[i]))
        assert exc.args == expected_matched[i].args

    for i, exc in enumerate(others):
        assert isinstance(exc, type(expected_others[i]))
        assert exc.args == expected_others[i].args


def test_filtered_flattened_exceptions_match_all_others_return_none(sample_group, sample_flat):
    matched, others = filtered_flattened_exceptions(lambda _: True, sample_group)
    assert others is None
    assert matched

    for i, exc in enumerate(matched):
        assert isinstance(exc, type(sample_flat[i]))
        assert exc.args == sample_flat[i].args


def test_filtered_flattened_exceptions_match_none(sample_group, sample_flat):
    matched, others = filtered_flattened_exceptions(lambda _: False, sample_group)
    assert matched is None
    assert others

    for i, exc in enumerate(others):
        assert isinstance(exc, type(sample_flat[i]))
        assert exc.args == sample_flat[i].args
