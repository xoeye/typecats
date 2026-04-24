"""Lightweight constants shared between runtime and the mypy plugin.

This module must remain free of heavy imports (no cattrs, no converter
creation) so the mypy plugin can import it without triggering runtime
side effects.
"""

import enum
import typing as ty

CLASSES_INCOMPATIBLE_WITH_ATTRS: ty.Final = (
    enum.Enum,  # attrs generates __call__(**{}) but EnumType.__call__ requires a value arg.
)
