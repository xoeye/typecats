from typecats import Cat, try_struc


def test_with_no_default():
    @Cat
    class Thing(dict):
        name: str

    assert try_struc(Thing, None) is None
    assert Thing.try_struc(None) is None


def test_with_default():
    @Cat
    class Thing(dict):
        name: str = ""

    assert try_struc(Thing, None) is None
    assert Thing.try_struc(None) is None
