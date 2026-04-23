"""Mypy plugin for typecats.

Delegates to mypy's built-in attrs plugin so that @Cat classes are
fully understood as attrs classes (field reordering, frozen semantics,
AttrsInstance protocol, __attrs_attrs__, etc.), then layers on the
.struc(), .try_struc(), and .unstruc() method signatures.

To enable, add to your pyproject.toml:

    [tool.mypy]
    plugins = ["typecats.cats_mypy_plugin"]

Or to mypy.ini:

    [mypy]
    plugins = typecats.cats_mypy_plugin
"""

from __future__ import annotations

from collections.abc import Callable

from mypy.nodes import (  # pylint: disable=no-name-in-module
    ARG_NAMED_OPT,
    ARG_POS,
    Argument,
    Var,
)
from mypy.plugin import ClassDefContext, Plugin  # pylint: disable=no-name-in-module
from mypy.plugins.attrs import (  # pylint: disable=no-name-in-module
    attr_class_maker_callback,
    attr_tag_callback,
)
from mypy.plugins.common import add_method  # pylint: disable=no-name-in-module
from mypy.typeops import fill_typevars  # pylint: disable=no-name-in-module
from mypy.types import (  # pylint: disable=no-name-in-module
    AnyType,
    NoneType,
    TypeOfAny,
    UnionType,
)

_CAT_FULLNAMES = frozenset(
    {
        "typecats.Cat",
        "typecats.tc.Cat",
    },
)


def plugin(_version: str) -> type[CatsPlugin]:
    return CatsPlugin


class CatsPlugin(Plugin):
    def get_class_decorator_hook(
        self, fullname: str
    ) -> Callable[[ClassDefContext], None] | None:
        if fullname in _CAT_FULLNAMES:
            return attr_tag_callback
        return None

    def get_class_decorator_hook_2(
        self, fullname: str
    ) -> Callable[[ClassDefContext], bool] | None:
        if fullname in _CAT_FULLNAMES:
            return _cat_class_maker_callback
        return None


def _cat_class_maker_callback(ctx: ClassDefContext) -> bool:
    """Run the attrs plugin first, then add Cat-specific methods."""
    ok = attr_class_maker_callback(ctx, auto_attribs_default=True)
    if ok:
        _add_cat_methods(ctx)
    return ok


def _add_cat_methods(ctx: ClassDefContext) -> None:
    any_type = AnyType(TypeOfAny.special_form)
    str_type = ctx.api.named_type("builtins.str")
    bool_type = ctx.api.named_type("builtins.bool")
    dict_type = ctx.api.named_type("builtins.dict", [str_type, any_type])
    mapping_type = ctx.api.named_type("collections.abc.Mapping", [str_type, any_type])
    optional_mapping_type = UnionType([mapping_type, NoneType()])
    cls_type = fill_typevars(ctx.cls.info)

    d_arg = Argument(Var("d", mapping_type), mapping_type, None, ARG_POS)
    d_opt_arg = Argument(
        Var("d", optional_mapping_type), optional_mapping_type, None, ARG_POS
    )
    strip_arg = Argument(
        Var("strip_defaults", bool_type), bool_type, None, ARG_NAMED_OPT
    )

    add_method(ctx, "struc", args=[d_arg], return_type=cls_type, is_classmethod=True)
    add_method(
        ctx,
        "try_struc",
        args=[d_opt_arg],
        return_type=UnionType([cls_type, NoneType()]),
        is_classmethod=True,
    )
    add_method(ctx, "unstruc", args=[strip_arg], return_type=dict_type)
