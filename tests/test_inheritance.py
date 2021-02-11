from cattr.converters import GenConverter
import attr


@attr.s(auto_attribs=True)
class A:
    i: int


@attr.s(auto_attribs=True)
class B(A):
    j: int


def test_inheritance():
    converter = GenConverter()

    assert A(1) == converter.structure(dict(i=1), A)

    assert B(1, 2) == converter.structure(dict(i=1, j=2), B)
