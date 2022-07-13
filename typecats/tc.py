"""Utilities for using attrs types with cattrs"""

import typing as ty
from functools import partial

import cattrs

from .attrs_shim import cat_attrs
from .wildcat import (
    mixin_wildcat_post_attrs_methods,
    setup_warnings_for_dangerous_dict_subclass_operations,
    is_wildcat,
)
from .types import C, StrucInput, UnstrucOutput
from .patch import patch_converter_for_typecats
from .exceptions import (
    _extract_typecats_stack_if_any,
    _emit_exception_to_default_handler,
    TypecatsCommonExceptionHook,
    StructuringError,
)
from .strip_defaults import ShouldStripDefaults
from .stack_context import stack_context


class TypeCat:
    """This is mostly just an example of the interface presented by a
    Cat-annotated class - it is unused within typecats itself.

    You could use this base class to make PyLint happier with the Cat
    decorator, which it doesn't understand. It's probably cleaner to
    just tell Pylint not to worry about it, by ignoring generated
    methods with these names.

    """

    @staticmethod
    def struc(_d: StrucInput) -> ty.Any:
        return TypeCat()  # this is a lie - don't worry about it

    @staticmethod
    def try_struc(_d: ty.Optional[StrucInput]) -> ty.Any:
        return TypeCat()

    def unstruc(self) -> UnstrucOutput:
        return unstruc(self)


def make_struc(
    converter: cattrs.Converter,
    *,
    hook_common_errors: ty.Optional[TypecatsCommonExceptionHook] = None,
):
    """Typecats provides some of its functionality by hooking into your
    cattrs Converter. By default, typecats provides its own Converter,
    but if you need to configure more than one Converter then you may
    wish to make your own top-level structure and unstructure
    functions, and maybe even set them specifically on various
    different Cat-annotated classes.
    """

    def _struc_with_hook(cl: ty.Type[C], obj: StrucInput) -> C:
        """A wrapper for cattrs structure that logs and re-raises structure exceptions."""
        try:
            return converter.structure(obj, cl)
        except StructuringError as e:
            if hook_common_errors:
                hook_common_errors(e, obj, cl, _extract_typecats_stack_if_any(e))
            raise e

    return _struc_with_hook


def make_unstruc(converter: cattrs.Converter):
    def _unstruc(obj: ty.Any, *, strip_defaults: bool = False) -> ty.Any:
        """A wrapper for cattrs unstructure using the internal converter"""
        with stack_context(ShouldStripDefaults, strip_defaults):
            return converter.unstructure(obj)

    return _unstruc


def _try_struc(
    structure_method: ty.Callable[[ty.Type[C], StrucInput], C],
    cl: ty.Type[C],
    obj: ty.Optional[StrucInput],
) -> ty.Optional[C]:
    """A wrapper for cattrs structure that suppresses and logs structure exceptions."""
    try:
        return structure_method(cl, obj)  # type: ignore
    except StructuringError:
        return None
    except Exception as e:
        # unexpected errors will only go through the default handler
        _emit_exception_to_default_handler(e, obj, cl, _extract_typecats_stack_if_any(e))
        return None


# This is just the default, pre-registered cattrs Converter.
# Although typecats will not work fully without a defined Converter,
# all of its functionality can be applied to any Converter instantiated by
# an application.
_TYPECATS_DEFAULT_CONVERTER = cattrs.GenConverter()

struc = make_struc(
    _TYPECATS_DEFAULT_CONVERTER, hook_common_errors=_emit_exception_to_default_handler
)
unstruc = make_unstruc(_TYPECATS_DEFAULT_CONVERTER)
try_struc = partial(_try_struc, struc)


patch_converter_for_typecats(_TYPECATS_DEFAULT_CONVERTER)


def get_default_converter():
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
    as long as that Converter has been patched using
    `patch_converter_for_typecats`.

    """

    def make_cat(cls: ty.Type[C]) -> ty.Type[C]:
        # it is always safe to apply this attrs-class-making decorator,
        # even if there's already an __attrs_attrs__ on a base class.
        cls = cat_attrs(cls, auto_attribs=auto_attribs, disallow_empties=disallow_empties, **kwargs)
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
    _struc = make_struc(converter, hook_common_errors=hook_common_errors)
    __try_struc = partial(_try_struc, make_struc(converter))

    @staticmethod  # type: ignore
    def struc_cat(d: StrucInput) -> C:
        return _struc(cls, d)

    @staticmethod  # type: ignore
    def try_struc_cat(d: ty.Optional[StrucInput]) -> ty.Optional[C]:
        return __try_struc(cls, d)

    setattr(cls, STRUCTURE_NAME, struc_cat)
    setattr(cls, TRY_STRUCTURE_NAME, try_struc_cat)


def set_unstruc_converter(
    cls: ty.Type[C], converter: cattrs.Converter = _TYPECATS_DEFAULT_CONVERTER
):
    """If you want to change your mind about the built-in Converter that
    is meant to run when you call the object method YourCatObj.unstruc(), you
    can reset it here. By default, it is defined by the converter
    keyword argument on the Cat decorator.

    """
    setattr(cls, UNSTRUCTURE_NAME, make_unstruc(converter))


def unstruc_strip_defaults(obj: ty.Any) -> ty.Any:
    """A functional-ish interface for stripping defaults.

    Note that if you need to use a specific converter,
    you'll want to dig in and set this context directly.
    """
    with stack_context(ShouldStripDefaults, True):
        return _TYPECATS_DEFAULT_CONVERTER.unstructure(obj)
