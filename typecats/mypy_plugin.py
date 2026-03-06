"""Mypy plugin for typecats.

Adds .struc(), .try_struc(), and .unstruc() method signatures to all
@Cat-decorated classes so mypy understands their types.

To enable, add to your pyproject.toml:

    [tool.mypy]
    plugins = ["typecats.mypy_plugin"]

Or to mypy.ini:

    [mypy]
    plugins = typecats.mypy_plugin
"""

from __future__ import annotations

from mypy.plugin import ClassDefContext, Plugin
from mypy.plugins.common import add_method
from mypy.nodes import ARG_POS, Argument, Var
from mypy.types import AnyType, Instance, NoneType, TypeOfAny, UnionType

_CAT_FULLNAMES = frozenset(
    {
        "typecats.Cat",
        "typecats.tc.Cat",
    }
)


def _add_cat_methods(ctx: ClassDefContext) -> None:
    any_type = AnyType(TypeOfAny.special_form)
    str_type = ctx.api.named_type("builtins.str")
    dict_type = ctx.api.named_type("builtins.dict", [str_type, any_type])
    cls_type = Instance(ctx.cls.info, [])

    d_arg = Argument(Var("d", any_type), any_type, None, ARG_POS)

    # struc(d: Any) -> <Class>
    add_method(ctx, "struc", args=[d_arg], return_type=cls_type, is_classmethod=True)

    # try_struc(d: Any) -> Optional[<Class>]
    add_method(
        ctx,
        "try_struc",
        args=[d_arg],
        return_type=UnionType([cls_type, NoneType()]),
        is_classmethod=True,
    )

    # unstruc(self) -> dict[str, Any]
    add_method(ctx, "unstruc", args=[], return_type=dict_type)


class TypecatsPlugin(Plugin):
    def get_class_decorator_hook(self, fullname: str):
        if fullname in _CAT_FULLNAMES:
            return _add_cat_methods
        return None


def plugin(version: str) -> type[TypecatsPlugin]:
    return TypecatsPlugin
