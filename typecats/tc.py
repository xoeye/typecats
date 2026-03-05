"""Utilities for using attrs types with cattrs"""

import typing as ty

import attr
import cattrs

from .attrs_shim import make_disallow_empties_transformer
from .converter import TypecatsConverter
from .wildcat import (
    mixin_wildcat_post_attrs_methods,
    setup_warnings_for_dangerous_dict_subclass_operations,
    is_wildcat,
)
from .types import C, StrucInput, UnstrucOutput
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
    def struc(cls, d: StrucInput) -> ty.Self: ...
    @classmethod
    def try_struc(cls, d: ty.Optional[StrucInput]) -> ty.Optional[ty.Self]: ...
    def unstruc(self) -> dict[str, ty.Any]: ...


_TYPECATS_DEFAULT_CONVERTER = TypecatsConverter()


def struc(cl: ty.Type[C], obj: StrucInput) -> C:
    """A wrapper for cattrs structure that logs and re-raises structure exceptions."""
    try:
        return _TYPECATS_DEFAULT_CONVERTER.structure(obj, cl)
    except StructuringError as e:
        _emit_exception_to_default_handler(e, obj, cl, _extract_typecats_stack_if_any(e))
        raise e


def unstruc(obj: ty.Any, *, strip_defaults: bool = False) -> ty.Any:
    """A wrapper for cattrs unstructure using the internal converter."""
    return _TYPECATS_DEFAULT_CONVERTER.unstructure(obj, strip_defaults=strip_defaults)


def _try_struc(
    cl: ty.Type[C],
    obj: ty.Optional[StrucInput],
) -> ty.Optional[C]:
    """A wrapper for cattrs structure that suppresses and logs structure exceptions."""
    try:
        return struc(cl, obj)  # type: ignore
    except StructuringError:
        return None
    except Exception as e:
        _emit_exception_to_default_handler(e, obj, cl, _extract_typecats_stack_if_any(e))
        return None


try_struc = _try_struc


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


@ty.dataclass_transform(
    eq_default=True,
    order_default=False,
    frozen_default=False,
    kw_only_default=False,
    field_specifiers=(attr.attrib, attr.ib, attr.field),
)
def Cat(
    maybe_cls=None,
    auto_attribs=True,
    disallow_empties=True,
    converter: cattrs.Converter = _TYPECATS_DEFAULT_CONVERTER,
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

    Note that each defined Cat type has a 'built-in' cattrs Converter
    that gets used when you call the static or object methods `struc`,
    `try_struc`, or `unstruc`. By default, this is the typecats
    default Converter.  You may choose to specify your own Converter
    at the time of defining your Cat type via the `converter` keyword
    argument.

    However, any Cat type should work with any cattrs Converter
    directly, (i.e. `your_converter.structure(your_data, YourCatType)`)
    as long as that Converter is a TypecatsConverter.

    """

    def make_cat(cls: ty.Type[C]) -> ty.Type[C]:
        user_transformer = kwargs.get("field_transformer")
        cls = attr.attrs(
            cls,
            auto_attribs=auto_attribs,
            field_transformer=make_disallow_empties_transformer(disallow_empties, user_transformer),
            **{k: v for k, v in kwargs.items() if k != "field_transformer"},
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
            _emit_exception_to_default_handler(e, d, cls, _extract_typecats_stack_if_any(e))
            return None

    setattr(cls, STRUCTURE_NAME, staticmethod(struc_cat))
    setattr(cls, TRY_STRUCTURE_NAME, staticmethod(try_struc_cat))


def set_unstruc_converter(cls: ty.Type[C], converter: cattrs.Converter = _TYPECATS_DEFAULT_CONVERTER):
    """If you want to change your mind about the built-in Converter that
    is meant to run when you call the object method YourCatObj.unstruc(), you
    can reset it here. By default, it is defined by the converter
    keyword argument on the Cat decorator.

    """

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
