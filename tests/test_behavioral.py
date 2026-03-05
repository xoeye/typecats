"""Behavioral tests for typecats.

These tests cover the observable contract of the library, independent of
implementation details. They should produce the same results across versions.
"""
import typing as ty
from decimal import Decimal

import attr
import pytest
from typecats import Cat, StructuringError, struc, try_struc, unstruc


# ---------------------------------------------------------------------------
# disallow_empties — collection types
# ---------------------------------------------------------------------------


def test_disallow_empties_rejects_empty_list():
    @Cat
    class WithList:
        items: ty.List[str]

    with pytest.raises(ValueError):
        WithList([])

    obj = WithList(["a"])
    assert obj.items == ["a"]


def test_disallow_empties_rejects_empty_dict():
    @Cat
    class WithDict:
        mapping: ty.Dict[str, int]

    with pytest.raises(ValueError):
        WithDict({})

    obj = WithDict({"a": 1})
    assert obj.mapping == {"a": 1}


def test_disallow_empties_allows_nonempty_list():
    @Cat
    class WithList:
        items: ty.List[int]

    obj = WithList([1, 2, 3])
    assert obj.items == [1, 2, 3]


def test_disallow_empties_list_with_default_allows_empty():
    """Fields with a default are not subject to the nonempty constraint."""

    @Cat
    class WithDefault:
        items: ty.List[str] = attr.Factory(list)

    obj = WithDefault()
    assert obj.items == []

    obj2 = WithDefault([])
    assert obj2.items == []


def test_disallow_empties_dict_with_default_allows_empty():
    @Cat
    class WithDefault:
        mapping: ty.Dict[str, int] = attr.Factory(dict)

    obj = WithDefault()
    assert obj.mapping == {}


# ---------------------------------------------------------------------------
# disallow_empties — scalar types never blocked
# ---------------------------------------------------------------------------


def test_disallow_empties_never_blocks_int_zero():
    @Cat
    class WithInt:
        count: int

    obj = WithInt(0)
    assert obj.count == 0


def test_disallow_empties_never_blocks_bool_false():
    @Cat
    class WithBool:
        flag: bool

    obj = WithBool(False)
    assert not obj.flag


def test_disallow_empties_never_blocks_float_zero():
    @Cat
    class WithFloat:
        value: float

    obj = WithFloat(0.0)
    assert obj.value == 0.0


def test_disallow_empties_never_blocks_decimal_zero():
    @Cat
    class WithDecimal:
        value: Decimal

    obj = WithDecimal(Decimal("0"))
    assert obj.value == Decimal("0")


# ---------------------------------------------------------------------------
# disallow_empties — Optional fields
# ---------------------------------------------------------------------------


def test_optional_with_default_none_accepts_none():
    """The common pattern: Optional with default=None must accept None."""

    @Cat
    class WithOptional:
        value: ty.Optional[str] = None

    obj = WithOptional()
    assert obj.value is None

    obj2 = WithOptional(None)
    assert obj2.value is None

    obj3 = WithOptional("hello")
    assert obj3.value == "hello"


def test_optional_with_default_none_does_not_restrict_empties():
    """A field with a default is not subject to disallow_empties at all."""

    @Cat
    class WithOptional:
        value: ty.Optional[str] = None

    # Empty string is allowed because the field has a default
    obj = WithOptional("")
    assert obj.value == ""


def test_optional_with_no_default_is_required():
    """Optional[str] with no default: the field is required and cannot be empty."""

    @Cat
    class RequiredOptional:
        value: ty.Optional[str]

    # Must be provided
    obj = RequiredOptional("hello")
    assert obj.value == "hello"

    # Empty string is blocked by disallow_empties (no default = required = nonempty)
    with pytest.raises(ValueError):
        RequiredOptional("")


# ---------------------------------------------------------------------------
# Cat inheritance
# ---------------------------------------------------------------------------


def test_inherited_cat_validators_fire():
    """disallow_empties validators from a base Cat class still fire on subclass instances."""

    @Cat
    class Base:
        name: str

    @Cat
    class Derived(Base):
        extra: str

    # Both fields must be non-empty
    with pytest.raises(ValueError):
        Derived("", "something")

    with pytest.raises(ValueError):
        Derived("something", "")

    obj = Derived("base", "derived")
    assert obj.name == "base"
    assert obj.extra == "derived"


def test_derived_cat_struc_unstruc_round_trip():
    @Cat
    class Base:
        name: str

    @Cat
    class Derived(Base):
        tag: str
        score: int = 0

    d = {"name": "test", "tag": "abc", "score": 5}
    obj = Derived.struc(d)
    assert obj.name == "test"
    assert obj.tag == "abc"
    assert obj.score == 5
    assert obj.unstruc() == d


# ---------------------------------------------------------------------------
# try_struc — failure modes
# ---------------------------------------------------------------------------


def test_try_struc_returns_none_on_missing_required_field():
    @Cat
    class Thing:
        name: str
        code: str

    assert try_struc(Thing, {"name": "foo"}) is None
    assert Thing.try_struc({"name": "foo"}) is None


def test_try_struc_returns_none_on_wrong_type():
    @Cat
    class Thing:
        count: int

    # Passing a string that can't be coerced
    assert try_struc(Thing, "not a dict") is None
    assert Thing.try_struc("not a dict") is None


def test_try_struc_returns_none_on_empty_required_field():
    """disallow_empties triggers a ValueError; try_struc should catch it and return None."""

    @Cat
    class Thing:
        name: str

    assert try_struc(Thing, {"name": ""}) is None
    assert Thing.try_struc({"name": ""}) is None


def test_try_struc_succeeds_on_valid_input():
    @Cat
    class Thing:
        name: str
        value: int = 0

    obj = try_struc(Thing, {"name": "hello"})
    assert obj is not None
    assert obj.name == "hello"
    assert obj.value == 0


# ---------------------------------------------------------------------------
# struc — extra keys
# ---------------------------------------------------------------------------


def test_struc_ignores_extra_keys():
    """Extra keys in the input dict are silently ignored."""

    @Cat
    class Thing:
        name: str

    obj = Thing.struc({"name": "test", "extra_key": "ignored", "another": 42})
    assert obj.name == "test"
    assert not hasattr(obj, "extra_key")


def test_struc_raises_on_missing_required():
    @Cat
    class Thing:
        name: str
        code: str

    with pytest.raises(StructuringError):
        Thing.struc({"name": "foo"})


# ---------------------------------------------------------------------------
# slots passthrough
# ---------------------------------------------------------------------------


def test_slots_true_passthrough():
    @Cat(slots=True)
    class Slotted:
        name: str
        value: int = 0

    obj = Slotted("hello")
    assert obj.name == "hello"
    assert obj.value == 0

    # slots=True means __dict__ is absent
    assert not hasattr(obj, "__dict__")

    # disallow_empties still fires
    with pytest.raises(ValueError):
        Slotted("")


def test_slots_true_struc_unstruc():
    @Cat(slots=True)
    class Slotted:
        name: str
        count: int = 0

    obj = Slotted.struc({"name": "test", "count": 3})
    assert obj.name == "test"
    assert obj.count == 3
    assert obj.unstruc() == {"name": "test", "count": 3}


# ---------------------------------------------------------------------------
# Round-trip struc/unstruc for various field types
# ---------------------------------------------------------------------------


def test_round_trip_nested():
    @Cat
    class Inner:
        x: int

    @Cat
    class Outer:
        inner: Inner
        label: str

    data = {"inner": {"x": 5}, "label": "hello"}
    obj = Outer.struc(data)
    assert obj.inner.x == 5
    assert obj.label == "hello"
    assert obj.unstruc() == data


def test_round_trip_optional_present():
    @Cat
    class WithOpt:
        name: str
        tag: ty.Optional[str] = None

    data = {"name": "foo", "tag": "bar"}
    obj = WithOpt.struc(data)
    assert obj.tag == "bar"
    assert obj.unstruc() == data


def test_round_trip_optional_absent():
    @Cat
    class WithOpt:
        name: str
        tag: ty.Optional[str] = None

    data = {"name": "foo", "tag": None}
    obj = WithOpt.struc(data)
    assert obj.tag is None
    assert obj.unstruc() == data


def test_round_trip_list_of_nested():
    @Cat
    class Item:
        value: int

    @Cat
    class Container:
        name: str
        items: ty.List[Item]

    data = {"name": "container", "items": [{"value": 1}, {"value": 2}]}
    obj = Container.struc(data)
    assert len(obj.items) == 2
    assert obj.items[0].value == 1
    assert obj.unstruc() == data


def test_round_trip_bool_false_preserved():
    """bool False (falsy) must survive round-trip without disallow_empties interference."""

    @Cat
    class Flags:
        enabled: bool
        archived: bool = False

    obj = Flags(False)
    assert not obj.enabled
    d = obj.unstruc()
    assert d == {"enabled": False, "archived": False}

    obj2 = Flags.struc(d)
    assert not obj2.enabled


def test_round_trip_int_zero_preserved():
    @Cat
    class Counts:
        total: int
        offset: int = 0

    obj = Counts(0)
    assert obj.total == 0
    d = obj.unstruc()
    assert d == {"total": 0, "offset": 0}

    obj2 = Counts.struc(d)
    assert obj2.total == 0


# ---------------------------------------------------------------------------
# disallow_empties=False
# ---------------------------------------------------------------------------


def test_disallow_empties_false_allows_empty_str():
    @Cat(disallow_empties=False)
    class Lenient:
        name: str

    obj = Lenient("")
    assert obj.name == ""


def test_disallow_empties_false_allows_empty_list():
    @Cat(disallow_empties=False)
    class Lenient:
        items: ty.List[str]

    obj = Lenient([])
    assert obj.items == []


def test_disallow_empties_false_allows_empty_dict():
    @Cat(disallow_empties=False)
    class Lenient:
        mapping: ty.Dict[str, int]

    obj = Lenient({})
    assert obj.mapping == {}


def test_disallow_empties_false_does_not_remove_user_validators():
    """disallow_empties=False must not strip validators the user defined."""

    @Cat(disallow_empties=False)
    class WithValidator:
        code: str = attr.ib(default="")

        @code.validator
        def _check_code(self, _, value):
            if value and len(value) != 3:
                raise ValueError("code must be 3 chars or empty")

    WithValidator("")
    WithValidator("abc")

    with pytest.raises(ValueError):
        WithValidator("ab")


# ---------------------------------------------------------------------------
# struc via module-level function vs class method
# ---------------------------------------------------------------------------


def test_module_struc_and_class_struc_are_equivalent():
    @Cat
    class Thing:
        name: str
        value: int = 0

    data = {"name": "hello", "value": 7}
    via_module = struc(Thing, data)
    via_class = Thing.struc(data)
    assert via_module == via_class


def test_module_unstruc_and_method_unstruc_are_equivalent():
    @Cat
    class Thing:
        name: str
        value: int = 0

    obj = Thing("hello", 7)
    assert unstruc(obj) == obj.unstruc()
