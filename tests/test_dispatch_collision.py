"""Reproduction test for dispatch collision between sibling @Cat classes.

The consuming project defined these classes at module level, so hooks persist
across the test session. This file mirrors that setup.
"""

import typing as ty

from attr import Factory as fac
from typecats import Cat, struc, unstruc


@Cat
class Note:
    text: str = ""


@Cat
class NumberEntry:
    is_required: bool = False
    value: ty.Optional[float] = None
    unit: str = ""
    unit_options: ty.Set[str] = fac(set)
    unit_type: str = ""


@Cat
class TextEntry:
    is_required: bool = False
    value: str = ""
    max_length: int = 80


@Cat
class DocumentationItem:
    content_id: str = ""
    url: str = ""


@Cat
class JobStep:
    name: str = ""
    traits: ty.Set[str] = fac(set)
    note: ty.Optional[Note] = None
    text_entry: ty.Optional[TextEntry] = None
    number_entry: ty.Optional[NumberEntry] = None
    documentation: ty.List[DocumentationItem] = fac(list)


def test_unstruc_step_with_all_entry_types():
    """Unstructuring a step with both TextEntry and NumberEntry must use
    the correct hook for each — not confuse them with each other."""
    step = JobStep(
        name="STEP0",
        traits={"note", "text_entry", "number_entry"},
        note=Note(text="some note"),
        text_entry=TextEntry(value="some short text"),
        number_entry=NumberEntry(value=3.0, unit="Kinds of entries on this Job Step"),
    )

    result = unstruc(step)

    assert result["text_entry"] == {
        "is_required": False,
        "value": "some short text",
        "max_length": 80,
    }
    assert result["number_entry"] == {
        "is_required": False,
        "value": 3.0,
        "unit": "Kinds of entries on this Job Step",
        "unit_options": set(),
        "unit_type": "",
    }


def test_roundtrip_step_with_all_entry_types():
    """struc -> unstruc -> struc roundtrip preserves all field values."""
    original = JobStep(
        name="STEP0",
        traits={"note", "text_entry", "number_entry"},
        note=Note(text="some note"),
        text_entry=TextEntry(value="some short text"),
        number_entry=NumberEntry(value=3.0, unit="Kinds of entries on this Job Step"),
        documentation=[DocumentationItem(content_id="content-ONE")],
    )

    raw = unstruc(original)
    restored = struc(JobStep, raw)

    assert restored.text_entry == original.text_entry
    assert restored.number_entry == original.number_entry
    assert restored.note == original.note
