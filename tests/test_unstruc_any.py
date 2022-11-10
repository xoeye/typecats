import typing as ty

from typecats import Cat, register_unstruc_hook_func


@Cat
class Container:
    one: ty.Any
    many: ty.List[ty.Any]


@Cat
class SecondContainer:
    thing: ty.Any


@Cat
class SomeCat:
    field: str


class HasUnstrucHook:
    def __init__(self, unstruc_field):
        self.unstruc_field = unstruc_field


class WithoutUnstrucHook:
    def __init__(self, some_field):
        self.some_field = some_field


def test_unstruc_cat_types_in_any_fields():
    container = Container(
        one=SecondContainer(
            thing=SomeCat(field="a"),
        ),
        many=[
            SecondContainer(
                thing=SomeCat(field="b"),
            ),
            SomeCat(field="c"),
        ],
    )

    expected = {
        "one": {"thing": {"field": "a"}},
        "many": [{"thing": {"field": "b"}}, {"field": "c"}],
    }

    assert container.unstruc() == expected


def test_unstruc_of_non_cat_in_any_field_with_unstruc_hook():
    register_unstruc_hook_func(
        lambda t: t == HasUnstrucHook, lambda x: {"unstruc_field": x.unstruc_field}
    )

    # This has no unstruc hook registered and should therefore be returned as-is
    no_unstruc = WithoutUnstrucHook("some_str_0")

    container = Container(
        one=HasUnstrucHook("some_str_1"),
        many=[no_unstruc, HasUnstrucHook("some_str_2")],
    )

    expected = {
        "one": {"unstruc_field": "some_str_1"},
        "many": [no_unstruc, {"unstruc_field": "some_str_2"}],
    }

    assert container.unstruc() == expected
