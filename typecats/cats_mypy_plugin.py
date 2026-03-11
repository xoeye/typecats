"""Mypy plugin for typecats.

Adds .struc(), .try_struc(), and .unstruc() method signatures to all
@Cat-decorated classes so mypy understands their types.

To enable, add to your pyproject.toml:

    [tool.mypy]
    plugins = ["typecats.cats_mypy_plugin"]

Or to mypy.ini:

    [mypy]
    plugins = typecats.cats_mypy_plugin
"""

from __future__ import annotations

from collections.abc import Callable
from typing import override

from mypy.nodes import (  # pylint: disable=no-name-in-module
    ARG_NAMED_OPT,
    ARG_POS,
    Argument,
    Var,
)
from mypy.plugin import ClassDefContext, Plugin  # pylint: disable=no-name-in-module
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


def plugin(_version: str) -> type[TypecatsPlugin]:
    """Return the plugin class for mypy to instantiate."""
    return TypecatsPlugin


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

    # struc(d: Mapping[str, Any]) -> <Class>
    add_method(ctx, "struc", args=[d_arg], return_type=cls_type, is_classmethod=True)

    # try_struc(d: Mapping[str, Any] | None) -> <Class> | None
    add_method(
        ctx,
        "try_struc",
        args=[d_opt_arg],
        return_type=UnionType([cls_type, NoneType()]),
        is_classmethod=True,
    )

    # unstruc(self, *, strip_defaults: bool = False) -> dict[str, Any]
    add_method(ctx, "unstruc", args=[strip_arg], return_type=dict_type)


class TypecatsPlugin(Plugin):  # pylint: disable=too-few-public-methods
    """Mypy plugin that adds Cat method signatures to decorated classes."""

    @override
    def get_class_decorator_hook(self, fullname: str) -> Callable[..., None] | None:
        """Return the hook for @Cat-decorated classes."""
        if fullname in _CAT_FULLNAMES:
            return _add_cat_methods
        return None
