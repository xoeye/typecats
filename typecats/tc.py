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
    is_wildcat,
)
from .cattrs_hooks import patch_cattrs_function_dispatch


logger = logging.getLogger(__name__)


CommonStructuringExceptions = (TypeError, AttributeError, ValueError)


C = ty.TypeVar("C")

StrucInput = ty.Mapping[str, ty.Any]
UnstrucOutput = dict


class TypeCat:
    """This is mostly just an example of the interface - it is unused
    within typecats itself.

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


def make_struc(converter: cattr.Converter):
    def _struc(cl: ty.Type[C], obj: StrucInput) -> C:
        """A wrapper for cattrs structure that logs and re-raises structure exceptions."""
        try:
            return converter.structure(obj, cl)
        except CommonStructuringExceptions as e:
            _log_structure_exception(e, obj, cl)
            raise e

    return _struc


def make_unstruc(converter: cattr.Converter):
    def _unstruc(obj: ty.Any) -> ty.Any:
        """A wrapper for cattrs unstructure using the internal converter"""
        return converter.unstructure(obj)

    return _unstruc


TYPECATS_CONVERTER = cattr.Converter()

struc = make_struc(TYPECATS_CONVERTER)
unstruc = make_unstruc(TYPECATS_CONVERTER)


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
        # use our converter directly to avoid infinite recursion
        wildcat = TYPECATS_CONVERTER.structure_attrs_fromdict(d, Type)  # type: ignore
        # we have a partial wildcat. now add in all the things that weren't structured
        wildcat.update({key: d[key] for key in d if key not in get_attrs_names(Type)})
        return wildcat
    except CommonStructuringExceptions as e:
        _log_structure_exception(e, d, Type)
        raise e


def _enrich_unstructured_wildcat(
    obj: WC, unstructured_obj_dict: UnstrucOutput
) -> UnstrucOutput:
    wildcat_attrs_names = get_attrs_names(type(obj))
    wildcat_nonattrs_dict = {
        key: unstruc(obj[key]) for key in obj if key not in wildcat_attrs_names
    }
    # note that typed entries take absolute precedence over untyped in case of collisions.
    # these collisions should generally be prevented at runtime by the wildcat
    # logic that is injected into the type, but if something were to sneak through
    # we would prefer whatever had been set via the attribute.
    return {**wildcat_nonattrs_dict, **unstructured_obj_dict}


def _unstruc_wildcat(unstructure_handler, obj) -> UnstrucOutput:
    """Unstructures a Wildcat by extracting the untyped key/value pairs,

    then updating that dict with the result of the typed attrs object unstructure.

    Note that this always chooses the typed value in any key collisions if the Wildcat
    implementation happens to allow those.
    """
    rv = unstructure_handler(obj)
    if (
        unstructure_handler == TYPECATS_CONVERTER.unstructure_attrs_asdict
        and is_wildcat(type(obj))
    ):
        return _enrich_unstructured_wildcat(obj, rv)
    return rv


# this is how we make sure that we get to enrich wildcats at unstructure time
patch_cattrs_function_dispatch(
    TYPECATS_CONVERTER._unstructure_func, _unstruc_wildcat  # type: ignore
)


def make_try_struc(
    structure_method: ty.Callable[[ty.Type[C], StrucInput], C],
    cl: ty.Type[C],
    obj: ty.Optional[StrucInput],
) -> ty.Optional[C]:
    """A wrapper for cattrs structure that suppresses and logs structure exceptions."""
    try:
        return structure_method(cl, obj)  # type: ignore
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

        # it is always safe to apply this decorator, even if there's already an attrs_attrs on a base class.
        cls = cat_attrs(
            cls, auto_attribs=auto_attribs, disallow_empties=disallow_empties, **kwargs
        )

        cat_structure_method = struc_wildcat if is_wild else struc
        cat_try_struc = partial(make_try_struc, cat_structure_method)

        @staticmethod  # type: ignore
        def struc_cat(d: StrucInput) -> C:
            return cat_structure_method(cls, d)

        @staticmethod  # type: ignore
        def try_struc_cat(d: ty.Optional[StrucInput]) -> ty.Optional[C]:
            return cat_try_struc(cls, d)

        setattr(cls, STRUCTURE_NAME, struc_cat)
        setattr(cls, TRY_STRUCTURE_NAME, try_struc_cat)
        setattr(cls, UNSTRUCTURE_NAME, unstruc)

        if is_wild:
            mixin_wildcat_post_attrs_methods(cls)

        return cls

    if maybe_cls is None:
        return make_cat
    return make_cat(maybe_cls)


def _log_structure_exception(exception: Exception, item: ty.Any, Type: type):
    type_name = getattr(Type, "__name__", str(Type))
    logger.info(
        f"Failed to structure {type_name} from {item}",
        extra=dict(
            json=dict(item=item),
            traceback=traceback.format_exception(
                None, exception, exception.__traceback__
            ),
        ),
    )
