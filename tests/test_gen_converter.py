import typing as ty

from attr import Factory as fac
from typecats import Cat, unstruc
from typecats._compat import Protocol
from typecats.patch import is_attrs_class


class IdMessage(Protocol):
    @property
    def id(self) -> str:
        ...


M = ty.TypeVar("M", bound=IdMessage, contravariant=True)


@Cat
class Container(ty.Generic[M]):
    name: str
    id_messages: ty.List[M] = fac(list)


@Cat
class RealMessage:
    id: str
    val: int


def test_generic_typevar_unstructure():
    """This used to not work until cattrs 3.9"""
    cont = Container("testA", [RealMessage("a", 3)])

    assert unstruc(cont) == dict(name="testA", id_messages=[dict(id="a", val=3)])


T = ty.TypeVar("T")


def test_generic_with_unstruc_strip_defaults():
    @Cat
    class Tee:
        pig: str

    @Cat
    class Gee:
        bar: int
        quux: float = 1.0

    @Cat
    class HasT(ty.Generic[T]):
        t: T
        default: int = 0

    assert is_attrs_class(HasT)

    @Cat
    class MultiGenericContainer:
        a: HasT[Tee]
        b: HasT[Gee]

    mgc = MultiGenericContainer(a=HasT(Tee("babe")), b=HasT(Gee(4)))

    assert unstruc(mgc, strip_defaults=True) == dict(
        a=dict(t=dict(pig="babe")), b=dict(t=dict(bar=4))
    )
