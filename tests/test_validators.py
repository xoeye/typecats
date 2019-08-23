from decimal import Decimal

import attr
import typecats
import pytest


def test_typecat_validators():
    @attr.s
    class Foo:
        bar: str = attr.ib()

        @bar.validator
        def _is_bar(self, _, value):
            assert value == "bar"

    with pytest.raises(AssertionError):
        Foo("not bar")

    Foo("bar")

    @typecats.Cat
    class FooCat:
        bar: str = attr.ib()

        @bar.validator
        def _is_bar(self, _, value):
            assert value == "bar"

    with pytest.raises(AssertionError):
        FooCat("not bar")

    FooCat("bar")

    @typecats.Cat
    class NotNone:
        nn: str = attr.ib()

        @nn.validator
        def _isnt_none(self, _, value):
            # this will pass for empty string
            assert value is not None

    with pytest.raises(ValueError):
        NotNone("")

    NotNone("n")

    @typecats.Cat
    class WithDefault:
        wd: str = attr.ib(default="")

        @wd.validator
        def _not_null(self, _, value):
            assert value is not None

    with pytest.raises(AssertionError):
        WithDefault(None)  # type: ignore

    WithDefault("")

    @typecats.Cat(disallow_empties=False)
    class EmptyAllowed:
        empty: str

        not_bar: str = attr.ib(default="")

        @not_bar.validator
        def _not_bar(self, _, value):
            assert value != "bar"

    EmptyAllowed("")

    with pytest.raises(AssertionError):
        EmptyAllowed("", "bar")


def test_decimal_zero():
    @typecats.Cat
    class DecimalZero:
        zero_allowed: Decimal

    DecimalZero(0)  # type: ignore
    DecimalZero(Decimal(0))
