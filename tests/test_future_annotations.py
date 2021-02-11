from __future__ import annotations

from typecats import Cat


def test_new_annotations():
    @Cat
    class Annotated:
        bugs: list[str]
        bees: dict[str, int]
        toy: float | None = None

    bugs = ["a", "b"]
    bees = dict(one=1, two=2)
    foo = Annotated(["b"], dict(f=3))
    print(foo)
    a = Annotated.struc(dict(bugs=bugs, bees=bees))
    assert a == Annotated(bugs=bugs, bees=bees)
