import typing as ty
import json

import pytest

from typecats import Cat

from data_utils import ld


@Cat
class MyWildcat(dict):
    name: str
    age: int = 0


@Cat
class LocatedWildcat(MyWildcat):
    location: str = ""


@Cat
class Wrapper:
    wrap: bool = True
    wildcat: ty.Optional[MyWildcat] = None


@Cat
class EmptyWildcatWithBool(dict):
    has_default: str = ""


@Cat
class UserClaims(dict):
    hasVSCs: bool = False


@Cat
class Organization(dict):
    id: str
    name: str
    userClaims: ty.Optional[UserClaims]


@Cat
class KnowledgebaseMetadata(dict):
    make: str = ""


def test_wildcats():

    dwc = dict(name="Steve", age=4, location="Colorado")

    wrapped = Wrapper.struc(dict(wrap=False, wildcat=dwc))
    print(wrapped)
    if wrapped.wildcat:
        wrapped.wildcat["adjust"] = 88

    wc = MyWildcat.struc(dwc)
    assert type(wc) == MyWildcat
    print(wc)
    wc["favorite_color"] = "green"
    print(wc)

    # print(wc.location)  # would be a mypy type error
    print(wc["location"])  # not a mypy type error

    lwc = LocatedWildcat.struc(wc.unstruc())
    print("Located wildcat at " + lwc.location)

    assert lwc.location == "Colorado"
    lwc["location"] = "Georgia"
    # even when a defined attribut is set on a Wildcat via __setitem__ instead of __set__,
    # the actual __dict__ attribute gets overwritten correctly.
    assert lwc["location"] == "Georgia"
    assert lwc.location == "Georgia"

    lwc["isDangerous"] = False

    lwc.update({"location": "Tennessee"})
    assert lwc.location == "Tennessee"
    assert lwc["location"] == "Tennessee"

    ndwc = lwc.unstruc()
    print(ndwc)
    assert ndwc["location"] == "Tennessee"
    assert not ndwc["isDangerous"]

    xoi_dict = json.loads(open(ld("xoi.json")).read())

    XOi = Organization.struc(xoi_dict)
    assert XOi
    XOi["dynamic"] = dict(inner="type")
    assert XOi.userClaims
    XOi.userClaims.hasVSCs = True
    XOi.userClaims["somethingDynamic"] = 8888
    print(XOi)

    new_xoi = XOi.unstruc()
    print("\nunstructured:")
    print(new_xoi)
    assert new_xoi["userClaims"]["somethingDynamic"] == 8888
    assert new_xoi["dynamic"] == dict(inner="type")

    # test truthy checks that are generated for Wildcats
    assert MyWildcat("named")
    assert not bool(EmptyWildcatWithBool())
    assert bool(EmptyWildcatWithBool("test"))

    assert not KnowledgebaseMetadata()
    assert KnowledgebaseMetadata(make="GM")
    km = KnowledgebaseMetadata()
    km["other_thing"] = True
    assert bool(km)


def test_attr_in_wildcat_dict_is_unstructured():
    """Items inside the Wildcat dict should also be unstructured if they're unstructurable"""

    @Cat
    class MyWildcat(dict):
        whatever: str = ""

    @Cat
    class Hidden:
        number: int

    mw = MyWildcat("blah")
    mw["hidden"] = Hidden(3)

    mwd = mw.unstruc()
    assert mwd["hidden"]["number"] == 3  # 'hidden' is unstructured to dict
    assert mwd["whatever"] == "blah"  # other stuff still works
    with pytest.raises(AttributeError):
        mwd["hidden"].number


def test_nested_wildcats_still_unstructure():
    """It's wildcats all the way down

    Wildcats nested inside a Wildcat dict should be properly unstructured
    as Wildcats, retaining all untyped keys but also unstructuring the typed ones.
    """

    @Cat
    class MyWildcat(dict):
        foo: str = "foo"

    @Cat
    class Hidden(dict):
        bar: str = "bar"

    @Cat
    class NestedHidden:
        reqd: int
        wow: str = "UAU!!"

    mw = MyWildcat()
    mw["hidden"] = Hidden()
    mw["hidden"]["nested_hidden"] = NestedHidden(8, "UAU!!!!!!")

    mwd = mw.unstruc()
    assert mwd["foo"] == "foo"
    assert mwd["hidden"]["bar"] == "bar"
    assert mwd["hidden"]["nested_hidden"] == dict(reqd=8, wow="UAU!!!!!!")


def test_wildcat_with_id():
    @Cat
    class WithId(dict):
        id: str
        age: int

    wi = WithId.struc(dict(id="iii", age=4))
    assert wi == WithId("iii", 4)


def test_wildcat_repr_no_conflicts():
    @Cat
    class WithDictMethodAttrs(dict):
        items: ty.List[int]  # type: ignore
        keys: ty.Set[str]  # type: ignore

    wdma = WithDictMethodAttrs([1, 2, 3], {"a", "b"})

    assert "Wildcat" not in str(wdma)

    wdma["test"] = "a str"

    assert "Wildcat" in str(wdma)


def test_wildcat_equality_takes_wildcat_key_values_into_account():
    @Cat
    class Nested(dict):
        i: int

    @Cat
    class Wildcat2(dict):
        species: str
        n: Nested

    base = dict(species="young", n=dict(i=7, j=10))

    wc = Wildcat2.struc(base)
    assert wc == Wildcat2.struc(base)

    wc.n["p"] = "j"
    assert wc != Wildcat2.struc(base)

    del wc.n["p"]

    assert wc == Wildcat2.struc(base)

    wc.n.i = 8

    assert wc != Wildcat2.struc(base)
