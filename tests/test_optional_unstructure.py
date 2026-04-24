"""Tests that Optional field unstructure dispatches by runtime type.

cattrs 26 changed Optional[X] unstructure to use the declared-type hook,
which crashes when the runtime value doesn't match (e.g. str in
Optional[datetime]). We override gen_unstructure_optional to restore
cattrs 22 behavior: dispatch by the value's actual type.
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


class TestOptionalDatetimeWithStrValue:
    """The original production bug: str assigned to Optional[datetime]."""

    def test_str_passes_through_on_unstruc(self):
        j = Job()
        j.completed_on = "2026-04-24T21:41:52.733Z"  # type: ignore[assignment]
        result = j.unstruc()
        assert result["completed_on"] == "2026-04-24T21:41:52.733Z"

    def test_str_is_not_coerced_on_assignment(self):
        j = Job()
        j.completed_on = "2026-04-24T21:41:52.733Z"  # type: ignore[assignment]
        assert isinstance(j.completed_on, str)

    def test_correct_datetime_is_serialized(self):
        j = Job()
        j.completed_on = datetime(2026, 1, 1)
        result = j.unstruc()
        assert result["completed_on"] == "2026-01-01T00:00:00Z"

    def test_none_is_preserved(self):
        j = Job()
        j.completed_on = None
        result = j.unstruc()
        assert result["completed_on"] is None


class TestOptionalCatWithDictValue:
    def test_dict_passes_through_on_unstruc(self):
        @Cat
        class Inner:
            value: str

        @Cat
        class Outer:
            inner: ty.Optional[Inner] = None

        o = Outer()
        o.inner = {"value": "hello"}  # type: ignore[assignment]
        result = o.unstruc()
        assert result["inner"] == {"value": "hello"}

    def test_correct_type_is_unstructured(self):
        @Cat
        class Inner:
            value: str

        @Cat
        class Outer:
            inner: ty.Optional[Inner] = None

        o = Outer()
        o.inner = Inner(value="hello")
        result = o.unstruc()
        assert result["inner"] == {"value": "hello"}


class TestOptionalWithBoolValue:
    def test_bool_passes_through_on_unstruc(self):
        j = Job()
        j.completed_on = True  # type: ignore[assignment]
        result = j.unstruc()
        assert result["completed_on"] is True


class TestOptionalWithIntValue:
    def test_int_in_optional_str_passes_through(self):
        @Cat
        class Labeled:
            label: ty.Optional[str] = None

        obj = Labeled()
        obj.label = 123  # type: ignore[assignment]
        result = obj.unstruc()
        assert result["label"] == 123


class TestNonOptionalFieldsBehavior:
    """Non-optional fields have always used declared-type dispatch.
    This behavior is unchanged from cattrs 22."""

    def test_str_in_non_optional_list_crashes_on_unstruc(self):
        @Cat
        class DocItem:
            content_id: str = ""

        @Cat
        class Step:
            documentation: ty.List[DocItem] = attr.Factory(list)

        s = Step()
        s.documentation = "doc"  # type: ignore[assignment]
        with pytest.raises(AttributeError):
            s.unstruc()


class TestFrozenCat:
    def test_frozen_cat_works(self):
        @Cat(frozen=True)
        class Frozen:
            x: str

        f = Frozen.struc({"x": "hello"})
        assert f.x == "hello"
        assert f.unstruc() == {"x": "hello"}

    def test_child_of_frozen_cat_works(self):
        @Cat(frozen=True)
        class FrozenParent:
            x: str

        @Cat
        class FrozenChild(FrozenParent):
            y: int = 0

        c = FrozenChild.struc({"x": "hello", "y": 1})
        assert c.x == "hello"
        assert c.y == 1
        assert c.unstruc() == {"x": "hello", "y": 1}


class TestWildcatOptional:
    def test_wildcat_optional_field_with_wrong_type(self):
        @Cat
        class FieldUpdates(dict):
            last_updated_on: ty.Optional[datetime] = None

        fu = FieldUpdates()
        fu.last_updated_on = "2026-04-24T21:41:52"  # type: ignore[assignment]
        result = fu.unstruc()
        assert result["last_updated_on"] == "2026-04-24T21:41:52"


class TestCustomConverter:
    def test_custom_converter_also_uses_runtime_dispatch(self):
        from typecats import TypecatsConverter

        custom = TypecatsConverter()
        custom.register_unstructure_hook(datetime, lambda d: d.isoformat() + "Z")

        @Cat(converter=custom)
        class CustomJob:
            done_at: ty.Optional[datetime] = None

        j = CustomJob()
        j.done_at = "not-a-datetime"  # type: ignore[assignment]
        result = j.unstruc()
        assert result["done_at"] == "not-a-datetime"
