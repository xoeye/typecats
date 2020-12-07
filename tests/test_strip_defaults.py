from typing import Dict, Any
from typing_extensions import Literal

import attr
from attr import Factory as fac

from typecats import Cat, unstruc_strip_defaults


def test_clean_cats_basic():
    @Cat
    class Clean:
        s: str = ""
        i: int = 8
        lst: list = attr.Factory(list)

    a = Clean()
    assert unstruc_strip_defaults(a) == dict()

    b = Clean(i=4, lst=[1])

    assert unstruc_strip_defaults(b) == dict(lst=[1], i=4)


def test_method_works_also():
    @Cat
    class Clean:
        s: str = ""
        i: int = 8
        lst: list = attr.Factory(list)

    a = Clean()
    assert a.unstruc(strip_defaults=True) == dict()

    b = Clean(i=4, lst=[1])

    assert b.unstruc(strip_defaults=True) == dict(lst=[1], i=4)


def test_clean_wildcat():
    @Cat
    class WC(dict):
        s: str = ""
        i: int = 8
        lst: list = attr.Factory(list)

    a = WC()
    assert unstruc_strip_defaults(a) == dict()

    b = WC(i=4, lst=[1])
    b["f"] = 2

    assert unstruc_strip_defaults(b) == dict(lst=[1], i=4, f=2)


def test_clean_literal():
    @Cat
    class CleanLit:
        g: int
        s: str = ""
        a: Literal["a"] = "a"

    cl = CleanLit(g=12)
    assert unstruc_strip_defaults(cl) == dict(a="a", g=12)


@Cat
class WC(dict):
    has_s: str = ""
    has_b: bool = False


@Cat
class Org(dict):
    id: str
    all: Literal[1] = 1
    strip_me: Dict[str, Any] = fac(dict)
    userClaims: WC = fac(WC)


def test_clean_with_wildcat_underneath():

    # this wildcat has a non-default value for a known key
    od = dict(id="id1", userClaims=dict(has_s="ssss", random="a string 1"))
    assert unstruc_strip_defaults(Org.struc(od)) == dict(od, all=1)

    # this wildcat has no no-default values for known keys, but still
    # has wildcat data and should not be stripped.
    od = dict(id="id2", userClaims=dict(random="a string"))
    assert unstruc_strip_defaults(Org.struc(od)) == dict(od, all=1)


def test_works_with_pure_attrs_obj():
    """don't need a Cat annotation to take advantage of this!"""

    @attr.s(auto_attribs=True)
    class Strippable:
        s: str = ""
        i: int = 8
        lst: list = attr.Factory(list)

    a = Strippable()
    assert unstruc_strip_defaults(a) == dict()

    b = Strippable(i=4, lst=[1])

    assert unstruc_strip_defaults(b) == dict(lst=[1], i=4)


def test_default_comparsion_works_on_structured_value():
    @Cat
    class Nested:
        i: int = 2

    @Cat
    class HasNested:
        id: str
        nested: Nested = fac(Nested)

    hd = HasNested("ben")
    assert hd.nested.i == 2
    assert hd.unstruc(strip_defaults=True) == dict(id="ben")
