import typing as ty
from datetime import datetime

import pytest
import attr

from typecats import Cat, unstruc, struc, register_struc_hook, register_unstruc_hook


@Cat
class CatTest:
    name: str
    age: int
    neutered: bool
    alive: bool = True


def test_cats_decorator() -> None:

    with pytest.raises(TypeError):
        # missing neutered
        CatTest.struc(dict(name="Tom", age=2, alive=False))
    with pytest.raises(TypeError):
        # missing age
        CatTest.struc(dict(name="Tom", neutered=False, alive=False))
    with pytest.raises(ValueError):
        # missing non-empty name
        CatTest.struc(dict(name="", age=2, neutered=True, alive=True))

    dct = dict(name="Tom", age=0, neutered=False)
    ct = CatTest.struc(dct)
    assert type(ct) == CatTest
    assert ct.name == "Tom"
    assert ct.age == 0
    assert not ct.neutered
    assert ct.alive

    # .struc is just a wrapper around struc
    assert ct == struc(CatTest, dct)
    syl = dict(name="Sylvester", age=45, neutered=True, alive=True)
    assert CatTest.struc(syl) == struc(CatTest, syl)
    assert unstruc(CatTest.struc(syl)) == syl
    assert CatTest.struc(syl).unstruc() == syl


@Cat
class Subtask:
    name: str
    done: bool = False


@Cat
class Task:
    name: str
    created_at: datetime
    subtasks: ty.List[Subtask] = attr.Factory(list)
    completed_at: ty.Optional[datetime] = None


def test_nested_with_structurer() -> None:

    register_struc_hook(
        datetime, lambda s, _t: datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.%fZ")
    )
    register_unstruc_hook(datetime, lambda d: d.isoformat() + "Z")

    dts = "2019-06-27T13:04:04.000111Z"
    dict_task = dict(
        name="feed cats", created_at=dts, subtasks=[dict(name="empty bowl")]
    )
    task = Task.struc(dict_task)

    assert task.subtasks[0] == Subtask("empty bowl")
    assert not task.completed_at

    task.completed_at = datetime(2019, 8, 8, 14, 2, 3, 5)
    unstructured_task = task.unstruc()
    assert unstructured_task["created_at"] == dts
    assert unstructured_task["completed_at"] == "2019-08-08T14:02:03.000005Z"


def test_union_structuring():
    # This tests that a bug in cattrs is fixed
    # In that bug, union types are disambiguated using unique fields that are allowed to be
    # optional fields with defaults. But optional fields might not be present.
    # Here we have a type `Bar` where every field except one is optional, so a previous version of cattrs
    # would usually pick an optional field as the unique field, causing struc to raise an exception.
    # Note that this test is nondeterministic since cattrs' choice of unique field is random.
    @Cat
    class Bar:
        a: str
        b: str = "b"
        c: str = "c"
        d: str = "d"
        e: str = "e"
        f: str = "f"
        g: str = "g"
        h: str = "h"
        i: str = "i"
        j: str = "j"

    @Cat
    class Baz:
        z: str

    @Cat
    class Foo:
        union: ty.Union[Bar, Baz]

    try:
        Foo.struc(dict(union=dict(a="some_value")))
    except Exception as exc:
        raise AssertionError(f"Exception {repr(exc)} was raised when it should not have been.")