"""Utilities for using attrs types with cattrs"""

import typing as ty
import traceback
import logging
from functools import partial

import cattr

from .attrs_shim import cat_attrs, get_attrs_names
from .wildcat import (
    WC,
    MWC,
    mixin_wildcat_post_attrs_methods,
    setup_warnings_for_dangerous_dict_subclass_operations,
)


logger = logging.getLogger(__name__)


CommonStructuringExceptions = (TypeError, AttributeError, ValueError)


C = ty.TypeVar("C")


TYPECATS_CONVERTER = cattr.Converter()


def struc(cl: ty.Type[C], obj: ty.Any) -> C:
    """A wrapper for cattrs structure that logs and re-raises structure exceptions."""
    try:
        return TYPECATS_CONVERTER.structure(obj, cl)
    except CommonStructuringExceptions as e:
        _log_structure_exception(e, obj, cl)
        raise e


def unstruc(obj: ty.Any) -> ty.Any:
    """A wrapper for cattrs unstructure using the internal converter"""
    return TYPECATS_CONVERTER.unstructure(obj)


def struc_wildcat(Type: ty.Type[MWC], d: ty.Mapping) -> MWC:
    """A Wildcat is a Cat (an attrs class) that additionally allows
    arbitrary key-value access as though it were a dict for data that
    does not have a defined attribute name on the class (i.e. is not typed).

    This is intended to provide a smooth transition for types that
    have some dynamic elements, but as though dynamic elements become
    'settled', they can be directly typed and statically
    typed-checked. It also makes for a good partially-typed
    passthrough defintion if you need to retain and later transmit
    unknown keys while still letting your code reason about the types
    that you do know about.

    """
    try:
        wildcat_attrs_names = get_attrs_names(Type)
        # use our converter directly to avoid infinite recursion
        wildcat = TYPECATS_CONVERTER.structure_attrs_fromdict(d, Type)  # type: ignore
        # we have a partial wildcat. now add in all the things that weren't structured
        wildcat.update({key: d[key] for key in d if key not in wildcat_attrs_names})
        return wildcat
    except CommonStructuringExceptions as e:
        _log_structure_exception(e, d, Type)
        raise e


def unstruc_wildcat(wildcat: WC) -> dict:
    """Unstructures a Wildcat by extracting the untyped key/value pairs,

    then updating that dict with the result of the typed attrs object unstructure.

    Note that this always chooses the typed value in any key collisions if the Wildcat
    implementation happens to allow those.
    """
    wildcat_attrs_names = get_attrs_names(type(wildcat))
    # use our converter directly to avoid infinite recursion
    wildcat_dict = TYPECATS_CONVERTER.unstructure_attrs_asdict(wildcat)  # type: ignore
    wildcat_nonattrs_dict = {
        key: wildcat[key] for key in wildcat if key not in wildcat_attrs_names
    }
    # note that typed entries take absolute precedence over untyped in case of collisions.
    # these collisions should generally be prevented at runtime by the wildcat
    # logic that is injected into the type, but if something were to sneak through
    # we would prefer whatever had been set via the attribute.
    return {**wildcat_nonattrs_dict, **wildcat_dict}


def make_try_struc(
    structure_method: ty.Callable[[ty.Type[C], ty.Any], C], cl: ty.Type[C], obj: ty.Any
) -> ty.Optional[C]:
    """A wrapper for cattrs structure that suppresses and logs structure exceptions."""
    try:
        return structure_method(cl, obj)
    except CommonStructuringExceptions:
        return None
    except Exception as e:
        _log_structure_exception(e, obj, cl)
        return None


try_struc = partial(make_try_struc, struc)
try_struc_wildcat = partial(make_try_struc, struc_wildcat)


def register_struc_hook(*args, **kwargs):
    """Use this to register cattrs structuring hooks on the internal cattrs Converter"""
    TYPECATS_CONVERTER.register_structure_hook(*args, **kwargs)


def register_unstruc_hook(*args, **kwargs):
    """Use this to register cattrs unstructuring hooks on the internal cattrs Converter"""
    TYPECATS_CONVERTER.register_unstructure_hook(*args, **kwargs)


class TypeCat:
    """You can use this base class to make PyLint happier
    with the Cat decorator, which it doesn't understand.
    """

    @staticmethod
    def struc(_d: dict) -> ty.Any:
        return TypeCat()  # this is a lie - don't worry about it

    @staticmethod
    def try_struc(_d: dict) -> ty.Any:
        return TypeCat()

    def unstruc(self) -> dict:
        return unstruc(self)


STRUCTURE_NAME = "struc"
TRY_STRUCTURE_NAME = "try_struc"
UNSTRUCTURE_NAME = "unstruc"


def Cat(maybe_cls=None, auto_attribs=True, disallow_empties=True, **kwargs):
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

    """

    def make_cat(cls: ty.Type[C]) -> ty.Type[C]:
        is_wild = dict in cls.__mro__
        if is_wild:
            setup_warnings_for_dangerous_dict_subclass_operations(cls)
            register_struc_hook(cls, lambda obj, typ: struc_wildcat(typ, obj))
            register_unstruc_hook(cls, unstruc_wildcat)

        # it is always safe to apply this decorator, even if there's already an attrs_attrs on a base class.
        cls = cat_attrs(
            cls, auto_attribs=auto_attribs, disallow_empties=disallow_empties, **kwargs
        )

        cat_structure_method = struc_wildcat if is_wild else struc
        cat_try_struc = partial(make_try_struc, cat_structure_method)
        cat_unstructure_method = unstruc_wildcat if is_wild else unstruc

        @staticmethod  # type: ignore
        def struc_cat(d: ty.Mapping) -> C:
            return cat_structure_method(cls, d)

        setattr(cls, STRUCTURE_NAME, struc_cat)

        @staticmethod  # type: ignore
        def try_struc_cat(d: ty.Mapping) -> ty.Optional[C]:
            return cat_try_struc(cls, d)

        setattr(cls, TRY_STRUCTURE_NAME, try_struc_cat)

        def unstruc_to_dict(self) -> dict:
            return cat_unstructure_method(self)

        setattr(cls, UNSTRUCTURE_NAME, unstruc_to_dict)

        if is_wild:
            mixin_wildcat_post_attrs_methods(cls)

        return cls

    if maybe_cls is None:
        return make_cat
    return make_cat(maybe_cls)


def _log_structure_exception(exception: Exception, item: ty.Any, Type: type):
    type_name = getattr(Type, "__name__", str(Type))
    logger.error(
        f"Failed to structure {type_name}",
        extra=dict(
            json=dict(item=item),
            traceback=traceback.format_exception(
                None, exception, exception.__traceback__
            ),
        ),
    )
