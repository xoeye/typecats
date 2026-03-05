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


def test_field_transformer_combined_with_disallow_empties():
    """User-supplied field_transformer and disallow_empties both take effect."""
    transformer_was_called = []

    def recording_transformer(cls, fields):
        transformer_was_called.append(cls.__name__)
        return fields

    @typecats.Cat(field_transformer=recording_transformer)
    class Recorded:
        name: str
        count: int = 0

    assert transformer_was_called == ["Recorded"]

    # disallow_empties still fires
    with pytest.raises(ValueError):
        Recorded("")

    Recorded("ok")


def test_field_transformer_can_modify_fields():
    """User-supplied field_transformer modifications take effect alongside disallow_empties."""

    def add_length_validator(cls, fields):
        result = []
        for field in fields:
            if field.name == "code":
                existing = field.validator
                def exact_length(self, attribute, value, _existing=existing):
                    if _existing:
                        _existing(self, attribute, value)
                    if len(value) != 3:
                        raise ValueError(f"{attribute.name} must be 3 characters")
                field = field.evolve(validator=exact_length)
            result.append(field)
        return result

    @typecats.Cat(field_transformer=add_length_validator)
    class WithCode:
        code: str

    with pytest.raises(ValueError):
        WithCode("")  # fails nonempty (injected before user transformer)

    with pytest.raises(ValueError):
        WithCode("ab")  # fails length (injected by user transformer)

    WithCode("abc")
