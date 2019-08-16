import typing as ty
import json

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
    print(wc)
    wc["favorite_color"] = "green"
    print(wc)

    # print(wc.location)  # would be a mypy type error
    print(wc["location"])  # not a mypy type error

    lwc = LocatedWildcat.struc(wc.unstruc())
    print("Located wildcat at " + lwc.location)

    lwc["location"] = "Georgia"
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
