from typecats import Cat, is_wildcat, struc, unstruc


def test_funcs_work():
    @Cat
    class SimpleCat:
        s: str
        i: int = 2

    orig = dict(s="Peter", i=8)
    sc = struc(SimpleCat, orig)
    assert SimpleCat("Peter", 8) == sc

    assert orig == unstruc(sc)

    @Cat
    class Wild(dict):
        name: str = "Tom"
        old: bool = True

    orig = dict(name="Alice", old=False, sick=True)
    wc = struc(Wild, orig)
    assert wc.name == "Alice"
    assert not wc.old
    assert wc["sick"]

    assert is_wildcat(type(wc))
