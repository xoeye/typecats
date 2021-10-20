from __future__ import annotations
import sys
import typing as ty

from typecats import Cat
from attr import Factory as fac

if sys.version_info > (3, 8):
    # these tests only work with the new type annotations
    def test_new_annotations_work_fine():
        @Cat
        class TestAnnots:
            a_list: list[float]
            a_set: set[int]
            a_dict: dict[str, ty.Optional[str]] = fac(dict)

        val = dict(a_list=[1.2, 3.4], a_set={3, 8, 9})
        TestAnnots.struc(val).unstruc(strip_defaults=True) == val
