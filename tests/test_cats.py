import pytest

from typecats import Cat, unstruc, struc


@Cat
class CatTest:
    name: str
    age: int
    neutered: bool
    alive: bool = True


def test_cats_decorator():

    with pytest.raises(TypeError):
        CatTest.struc(dict(name="Tom", age=2, alive=False))
    with pytest.raises(TypeError):
        CatTest.struc(dict(name="Tom", neutered=False, alive=False))
    with pytest.raises(ValueError):
        CatTest.struc(dict(name="", age=2, neutered=True, alive=True))
    dct = dict(name="Tom", age=0, neutered=False)
    ct = CatTest.struc(dct)
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
