"""Tests for coercing values through cattrs on attribute assignment.

Verifies that assigning a value of the wrong type to a Cat field
(e.g. a str to an Optional[datetime] field) is coerced to the correct
type, so that unstruc() does not crash under cattrs 26+.
"""

import typing as ty
from datetime import datetime
import attr
import pytest
from typecats import Cat, register_struc_hook, register_unstruc_hook


@pytest.fixture(autouse=True, scope="module")
def _register_datetime_hooks():
    register_struc_hook(
        datetime, lambda s, _t: datetime.fromisoformat(s) if isinstance(s, str) else s
    )
    register_unstruc_hook(datetime, lambda d: d.isoformat() + "Z")


@Cat
class Job:
    id: str = ""
    completed_on: ty.Optional[datetime] = None
    name: str = ""


class TestStringAssignedToDatetimeFieldIsCoerced:
    def test_assignment_coerces_str_to_datetime(self):
        j = Job()
        j.completed_on = "2026-04-24T21:41:52.733000"  # type: ignore[assignment]
        assert isinstance(j.completed_on, datetime)

    def test_unstruc_succeeds_after_str_assignment(self):
        j = Job()
        j.completed_on = "2026-04-24T21:41:52.733000"  # type: ignore[assignment]
        result = j.unstruc()
        assert isinstance(result["completed_on"], str)

    def test_round_trip_preserves_value(self):
        j = Job()
        j.completed_on = "2026-04-24T21:41:52.733000"  # type: ignore[assignment]
        result = j.unstruc()
        j2 = Job.struc(result)
        assert j2.completed_on is not None
        assert j.completed_on is not None
        assert j2.completed_on.replace(tzinfo=None) == j.completed_on.replace(
            tzinfo=None
        )


class TestCorrectTypeAssignmentIsUnchanged:
    def test_datetime_stays_datetime(self):
        dt = datetime(2026, 4, 24, 21, 41, 52, 733000)
        j = Job()
        j.completed_on = dt
        assert j.completed_on is dt

    def test_none_stays_none(self):
        j = Job()
        j.completed_on = datetime(2026, 1, 1)
        j.completed_on = None
        assert j.completed_on is None

    def test_str_to_str_field_unchanged(self):
        j = Job()
        j.name = "test"
        assert j.name == "test"
        assert isinstance(j.name, str)


class TestNestedCatCoercion:
    def test_dict_assigned_to_cat_field_is_structured(self):
        @Cat
        class Inner:
            value: str

        @Cat
        class Outer:
            inner: Inner = attr.Factory(lambda: Inner(value="default"))

        o = Outer()
        o.inner = {"value": "hello"}  # type: ignore[assignment]
        assert isinstance(o.inner, Inner)
        assert o.inner.value == "hello"
        assert o.unstruc() == {"inner": {"value": "hello"}}


class TestWildcatCoercion:
    def test_wildcat_typed_field_is_coerced(self):
        @Cat
        class FieldUpdates(dict):
            last_updated_on: datetime

        fu = FieldUpdates.struc(
            {"last_updated_on": "2026-04-24T21:41:52", "extra_key": "raw_string"}
        )
        assert isinstance(fu.last_updated_on, datetime)

        fu.last_updated_on = "2026-05-01T00:00:00"  # type: ignore[assignment]
        assert isinstance(fu.last_updated_on, datetime)


class TestSubscriptedGenericFields:
    def test_dict_field_with_generic_type_is_not_coerced(self):
        @Cat
        class Container:
            data: ty.Dict[str, ty.Optional[int]] = attr.Factory(dict)

        c = Container()
        d = {"a": 1, "b": None}
        c.data = d
        assert c.data is d

    def test_list_field_with_generic_type_is_not_coerced(self):
        @Cat
        class Container:
            items: ty.List[ty.Optional[str]] = attr.Factory(list)

        c = Container()
        items = ["a", None, "b"]
        c.items = items
        assert c.items is items

    def test_unstruc_works_with_generic_fields(self):
        @Cat
        class Container:
            data: ty.Dict[str, int] = attr.Factory(dict)

        c = Container()
        c.data = {"x": 1}
        result = c.unstruc()
        assert result == {"data": {"x": 1}}


class TestFrozenCatIsUnaffected:
    def test_frozen_cat_still_rejects_setattr(self):
        @Cat(frozen=True)
        class Frozen:
            x: str

        f = Frozen.struc({"x": "hello"})
        with pytest.raises(attr.exceptions.FrozenInstanceError):
            f.x = "world"  # type: ignore[misc]

    def test_child_of_frozen_cat_can_be_defined(self):
        @Cat(frozen=True)
        class FrozenParent:
            x: str

        @Cat
        class FrozenChild(FrozenParent):
            y: int = 0

        c = FrozenChild.struc({"x": "hello", "y": 1})
        assert c.x == "hello"
        assert c.y == 1
        with pytest.raises(attr.exceptions.FrozenInstanceError):
            c.y = 2  # type: ignore[misc]


class TestCustomConverterCoercion:
    def test_cat_with_custom_converter_coerces(self):
        from typecats import TypecatsConverter

        custom = TypecatsConverter()
        custom.register_structure_hook(
            datetime,
            lambda s, _t: datetime.fromisoformat(s) if isinstance(s, str) else s,
        )

        @Cat(converter=custom)
        class CustomJob:
            done_at: ty.Optional[datetime] = None

        j = CustomJob()
        j.done_at = "2026-01-01T00:00:00"  # type: ignore[assignment]
        assert isinstance(j.done_at, datetime)
