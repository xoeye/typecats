"""Utilities for using attrs types with cattrs"""

import typing as ty
from functools import partial

import attr
import cattrs

from .attrs_shim import FieldTransformer, make_disallow_empties_transformer
from .converter import TypecatsConverter
from .wildcat import (
    mixin_wildcat_post_attrs_methods,
    setup_warnings_for_dangerous_dict_subclass_operations,
    is_wildcat,
)
from .types import C, StrucInput
from .exceptions import (
    _extract_typecats_stack_if_any,
    _emit_exception_to_default_handler,
    TypecatsCommonExceptionHook,
    StructuringError,
)
from .strip_defaults import ShouldStripDefaults
from .stack_context import stack_context


class TypeCat:
    """Base class that documents the interface added by the @Cat decorator.

    Type checkers understand @Cat through dataclass_transform and the typecats
    mypy plugin, so inheriting from this is not required. It exists for
    environments that don't run a type checker (e.g. pylint), or as an
    explicit documentation aid.
    """

    @classmethod
    def struc(cls, d: StrucInput) -> ty.Self:
        raise NotImplementedError

    @classmethod
    def try_struc(cls, d: ty.Optional[StrucInput]) -> ty.Optional[ty.Self]:
        raise NotImplementedError

    def unstruc(self, *, strip_defaults: bool = False) -> dict[str, ty.Any]:
        raise NotImplementedError


def make_struc(
    converter: TypecatsConverter,
    *,
    hook_common_errors: TypecatsCommonExceptionHook = _emit_exception_to_default_handler,
):
    def _struc(cl: ty.Type[C], obj: StrucInput) -> C:
        """A wrapper for cattrs structure that logs and re-raises structure exceptions."""
        try:
            return converter.structure(obj, cl)
        except StructuringError as e:
            hook_common_errors(e, obj, cl, _extract_typecats_stack_if_any(e))
            raise e

    return _struc


def make_unstruc(converter: TypecatsConverter):
    def _unstruc(obj: ty.Any, *, strip_defaults: bool = False) -> ty.Any:
        """A wrapper for cattrs unstructure using the internal converter."""
        return converter.unstructure(obj, strip_defaults=strip_defaults)

    return _unstruc


def _try_struc(
    structure_method: ty.Callable[[ty.Type[C], StrucInput], C],
    cl: ty.Type[C],
    obj: ty.Optional[StrucInput],
) -> ty.Optional[C]:
    """A wrapper for cattrs structure that suppresses StructuringErrors and logs unexpected exceptions."""
    try:
        return structure_method(cl, obj)  # type: ignore
    except StructuringError:
        return None
    except Exception as e:
        # unexpected errors will only go through the default handler
        _emit_exception_to_default_handler(
            e, obj, cl, _extract_typecats_stack_if_any(e)
        )
        return None


# This is the default pre-configured converter. All of its functionality
# can be applied to any TypecatsConverter instance.
_TYPECATS_DEFAULT_CONVERTER = TypecatsConverter()

struc = make_struc(_TYPECATS_DEFAULT_CONVERTER)
unstruc = make_unstruc(_TYPECATS_DEFAULT_CONVERTER)
try_struc = partial(_try_struc, struc)


def get_default_converter() -> TypecatsConverter:
    """Intended only for advanced uses"""
    return _TYPECATS_DEFAULT_CONVERTER


def register_struc_hook(*args, **kwargs):
    """Use this to register cattrs structuring hooks on the internal cattrs Converter"""
    _TYPECATS_DEFAULT_CONVERTER.register_structure_hook(*args, **kwargs)


def register_unstruc_hook(*args, **kwargs):
    """Use this to register cattrs unstructuring hooks on the internal cattrs Converter"""
    _TYPECATS_DEFAULT_CONVERTER.register_unstructure_hook(*args, **kwargs)


def register_struc_hook_func(*args, **kwargs):
    """Use this to register cattrs structuring hooks on the internal cattrs Converter"""
    _TYPECATS_DEFAULT_CONVERTER.register_structure_hook_func(*args, **kwargs)


def register_unstruc_hook_func(*args, **kwargs):
    """Use this to register cattrs unstructuring hooks on the internal cattrs Converter"""
    _TYPECATS_DEFAULT_CONVERTER.register_unstructure_hook_func(*args, **kwargs)


def set_detailed_validation_mode_not_threadsafe(enabled=True):
    """
    Controls the cattrs converter detailed validation mode.
    Cattrs claims a 25% performance improvement from disabling detailed validation mode, YMMV.
    WARNING: Not thread safe.
    You should only call this once, preferrably at the start of your application.
    """
    _TYPECATS_DEFAULT_CONVERTER.detailed_validation = enabled
    _TYPECATS_DEFAULT_CONVERTER._structure_func.clear_cache()


# Overloads disambiguate the bare (@Cat) and factory (@Cat(...)) call forms.
# @dataclass_transform instructs pyright/mypy to synthesize __init__ signatures
# from field annotations, allowing Cat to get dataclass-like type inference.
@ty.overload
@ty.dataclass_transform(
    eq_default=True,
    order_default=False,
    frozen_default=False,
    kw_only_default=False,
    field_specifiers=(attr.attrib, attr.ib, attr.field),
)
def Cat(
    maybe_cls: ty.Type[C],
    auto_attribs: bool = ...,
    disallow_empties: bool = ...,
    converter: TypecatsConverter = ...,
    field_transformer: FieldTransformer | None = None,
    **kwargs: ty.Any,
) -> ty.Type[C]: ...


@ty.overload
@ty.dataclass_transform(
    eq_default=True,
    order_default=False,
    frozen_default=False,
    kw_only_default=False,
    field_specifiers=(attr.attrib, attr.ib, attr.field),
)
def Cat(
    maybe_cls: None = ...,
    auto_attribs: bool = ...,
    disallow_empties: bool = ...,
    converter: TypecatsConverter = ...,
    field_transformer: FieldTransformer | None = None,
    **kwargs: ty.Any,
) -> ty.Callable[[ty.Type[C]], ty.Type[C]]: ...


def Cat(
    maybe_cls=None,
    auto_attribs=True,
    disallow_empties=True,
    converter: TypecatsConverter = _TYPECATS_DEFAULT_CONVERTER,
    field_transformer: FieldTransformer | None = None,
    **kwargs,
):
    """A Cat knows how to take care of itself.

    This decorator combines the beauty of attrs-style classes with the
    extreme, ferocious power of cattrs, and provides it all in a convenient package.
    Simply import your type and call YourType.struc(dict_of_your_type), and
    you'll have an object of your type returned to you! Want a raw
    dict back? YourObject.unstruc()!

    Sublime.

    Additionally: Cats don't like to feel empty. If you've defined an
    attribute without a default value, it is assumed that a non-empty
    value is required for that attribute, and a validator requiring
    that will automatically be added. If you for some reason want to
    require attributes but allow empty values (very strange!), you can turn
    off this behavior with the pedestrianly-named boolean flag
    'disallow_empties=False'.

    Note that each defined Cat type has a 'built-in' TypecatsConverter
    that gets used when you call the static or object methods `struc`,
    `try_struc`, or `unstruc`. By default, this is the typecats
    default Converter. You may supply your own TypecatsConverter instance
    via the `converter` keyword argument.

    """

    def _would_attrs_produce_fields(cls) -> bool:
        return attr.has(cls) or bool(cls.__dict__.get("__annotations__", {}))

    def make_cat(cls: ty.Type[C]) -> ty.Type[C]:
        if _would_attrs_produce_fields(cls):
            cls = attr.attrs(
                cls,
                auto_attribs=auto_attribs,
                field_transformer=make_disallow_empties_transformer(
                    disallow_empties, field_transformer
                ),
                **kwargs,
            )
            if is_wildcat(cls):
                setup_warnings_for_dangerous_dict_subclass_operations(cls)

        set_struc_converter(cls, converter)
        set_unstruc_converter(cls, converter)

        if is_wildcat(cls):
            mixin_wildcat_post_attrs_methods(cls)

        return cls

    if maybe_cls is None:
        return make_cat
    return make_cat(maybe_cls)


STRUCTURE_NAME = "struc"
TRY_STRUCTURE_NAME = "try_struc"
UNSTRUCTURE_NAME = "unstruc"


def set_struc_converter(
    cls: ty.Type[C],
    converter: cattrs.Converter = _TYPECATS_DEFAULT_CONVERTER,
    *,
    hook_common_errors: TypecatsCommonExceptionHook = _emit_exception_to_default_handler,
):
    """If you want to change your mind about the built-in Converter that
    is meant to run when you call the class static method
    YourCatType.struc(...) or YourCatType.try_struc(...), you can
    reset that here. By default, it is defined by the converter
    keyword argument to the Cat decorator.

    """

    def struc_cat(d: StrucInput) -> C:
        try:
            return converter.structure(d, cls)
        except StructuringError as e:
            hook_common_errors(e, d, cls, _extract_typecats_stack_if_any(e))
            raise e

    def try_struc_cat(d: ty.Optional[StrucInput]) -> ty.Optional[C]:
        try:
            return converter.structure(d, cls)
        except StructuringError:
            return None
        except Exception as e:
            _emit_exception_to_default_handler(
                e, d, cls, _extract_typecats_stack_if_any(e)
            )
            return None

    setattr(cls, STRUCTURE_NAME, staticmethod(struc_cat))
    setattr(cls, TRY_STRUCTURE_NAME, staticmethod(try_struc_cat))


def set_unstruc_converter(
    cls: ty.Type[C], converter: cattrs.Converter = _TYPECATS_DEFAULT_CONVERTER
):
    """If you want to change your mind about the built-in Converter that
    is meant to run when you call the object method YourCatObj.unstruc(), you
    can reset it here. By default, it is defined by the converter
    keyword argument on the Cat decorator.

    The converter must be a TypecatsConverter; strip_defaults behavior
    relies on the ShouldStripDefaults context var being honored during
    unstructuring, which is only guaranteed for TypecatsConverter.
    """
    if not isinstance(converter, TypecatsConverter):
        raise TypeError(
            f"set_unstruc_converter requires a TypecatsConverter; got {type(converter)}"
        )

    def _unstruc(obj, *, strip_defaults: bool = False):
        with stack_context(ShouldStripDefaults, strip_defaults):
            return converter.unstructure(obj)

    setattr(cls, UNSTRUCTURE_NAME, _unstruc)


def unstruc_strip_defaults(obj: ty.Any) -> ty.Any:
    """A functional-ish interface for stripping defaults.

    Note that if you need to use a specific converter,
    you'll want to dig in and set this context directly.
    """
    return _TYPECATS_DEFAULT_CONVERTER.unstructure(obj, strip_defaults=True)
