import typing as ty
import traceback
import logging

import cattr

from .wildcat import is_wildcat, enrich_unstructured_wildcat, enrich_structured_wildcat
from .cattrs_hooks import ConverterContextPatch
from .types import CommonStructuringExceptions, StructureHook, C


logger = logging.getLogger(__name__)


__converters_patched = list()


def patch_converter_for_typecats(converter: cattr.Converter):
    """Any Cat type will work with any cattrs Converter, but applying this
    patch is necessary to make a Wildcat type work, and will add other
    conveniences and possibly future features, so it is recommended
    that any Converters you wish to use on Cat-annotated types be
    patched for typecats by calling this function.
    """
    __converters_patched.append(TypecatsCattrPatch(converter))


class TypecatsCattrPatch(ConverterContextPatch):
    """This patch is what makes Wildcats, in particular, work properly
    within the context of `cattrs`. It should (and may safely) be
    applied to any cattrs Converter that you wish to use with your
    Wildcat types.

    In the future, typecats may also use this patch to provide
    additional functionality, so it is recommended that you patch any
    Converter with which you want to use any Cat-annotated type.
    """

    def unstructure_patch(
        self, original_handler: ty.Callable, obj_to_unstructure: ty.Any
    ) -> ty.Any:
        """Unstructures a Wildcat by extracting the untyped key/value pairs,

        then updating that dict with the result of the typed attrs object unstructure.

        Note that this always chooses the typed value in any key collisions if the Wildcat
        implementation happens to allow those.
        """
        rv = super().unstructure_patch(original_handler, obj_to_unstructure)
        if is_wildcat(type(obj_to_unstructure)):
            return enrich_unstructured_wildcat(self.converter, obj_to_unstructure, rv)
        return rv

    def structure_patch(
        self,
        original_handler: StructureHook,
        obj_to_structure: ty.Any,
        Type: ty.Type[C],
    ) -> C:
        """This handles Wildcat structuring and also provides much nicer error messages
        when you have a structuring failure.
        """
        try:
            structured = original_handler(obj_to_structure, Type)
            if is_wildcat(Type):
                enrich_structured_wildcat(structured, obj_to_structure, Type)
            return structured
        except CommonStructuringExceptions as e:
            log_structure_exception(e, obj_to_structure, Type)
            raise e


def log_structure_exception(exception: Exception, item: ty.Any, Type: type):
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
