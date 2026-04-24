# Changelog

## v2.4.0

Replaces v2.3.x. The on_setattr coercion approach in 2.3.0–2.3.2 changed assignment behavior and introduced regressions. **Skip 2.3.x entirely.**

Bug fixes:

- Restore cattrs 22 behavior for `Optional` field unstructure. Override `gen_unstructure_optional` to dispatch by runtime type instead of declared type, so mismatched values (e.g. `str` in `Optional[datetime]`) pass through instead of crashing.
- Remove `on_setattr` coercion hook (introduced in 2.3.0) which caused `ValueError` on frozen inheritance, `TypeError` on generic fields, and silent data corruption on container fields.

## v2.3.2

Bug fixes:

- Fix `ValueError: Frozen classes can't use on_setattr` when a `@Cat` inherits from a frozen parent.

## v2.3.1

Bug fixes:

- Fix `TypeError` in coerce hook for fields annotated with subscripted generics (e.g. `Dict[str, Optional[X]]`).

## v2.3.0

New features:

- **Coerce on setattr** — `@Cat` fields auto-coerce mismatched values through the cattrs converter on assignment, preventing `unstruc()` crashes under cattrs 26+. Frozen classes are unaffected.

## v2.2.0

New features:

- **Improved mypy support** — `@Cat` classes are now recognized as full attrs classes by mypy, fixing false positives with `attr.fields()`, field validators, frozen inheritance, and default ordering.
- **`CatT` TypeVar** — new public `TypeVar` for typing generic functions that operate on `@Cat` types. Import with `from typecats import CatT`.

## v2.1.2

Bug fixes:

- Fix `@Cat`-decorated `enum.Enum` subclasses failing to structure/unstructure on Python 3.12+. `attr.attrs()` is incompatible with `enum.Enum` (`EnumType.__call__` requires a value argument), so `@Cat` now skips the attrs wrapping for enum classes and registers only the structuring/unstructuring converters.

## v2.1.1

Bug fixes:

- Fix `__eq__` on wildcat (dict-based) `@Cat` subclasses for Python 3.14, where `NotImplemented` in a boolean context is now a `TypeError`. Parent/child wildcat equality is preserved.

## v2.1.0

Adds Python 3.12–3.14 support, drops 3.10 and 3.11, and improves type inference for `@Cat` classes.

Breaking changes:

- Python >=3.12 required
- `attrs >=25.4.0,<27.0.0` and `cattrs >=26.1.0,<27.0.0` required
- `patch_converter_for_typecats` removed — instantiate `TypecatsConverter()` directly instead

New features:

- **Full IDE constructor inference on `@Cat` classes** — field names, types, and defaults are now visible at call sites in pyright and mypy. `@Cat(frozen=True)` also enforces field immutability statically.
- **Mypy plugin** (`typecats.cats_mypy_plugin`) — `.struc()`, `.try_struc()`, and `.unstruc()` are now visible to mypy on all `@Cat` classes, with correct return types for generics and `strip_defaults` on `unstruc`. Enable with `plugins = ["typecats.cats_mypy_plugin"]` in your mypy config.
- `TypecatsConverter` — public `GenConverter` subclass; use this if you need to register custom hooks or extend converter behavior
- `TypeCat`, `set_default_exception_hook`, and `FieldTransformer` are now public exports

Bug fixes:

- Parameterized generic wildcats (e.g. `MyWildcat[str]`) now structure and unstructure correctly
- Restored cattrs 22 behavior where plain dicts stored in attrs-typed fields are coerced before unstructuring

## v2.0.2

- Fixes regression in post cattrs-1.1.2 where attrs objects in `typing.Any` fields are
  returned as-is and not unstructured

## v2.0.1

- Fixes error in structuring parameterized generic wildcats

## v2.0.0

Breaking changes:

- Upgrades `cattrs` from 1.1.2 to 22.1.0, `attrs` from 20.3.0 to 21.4.0 and switches to the
  GenConverter, which supports the newer style type annotations (e.g, list[] instead of typing.List[]).
- Detailed validation from cattrs is enabled by default. Disable it if you wish by calling `set_detailed_validation_mode_not_threadsafe(enable=False)`
- Removed `typecats.types.CommonStructuringExceptions`. Structuring validation errors are now all `typecats.StructuringError`s (aliased to `cattrs.errors.BaseValidationError`), regardless of detailed validation.
- MyPy plugin changed from resolving from `__builtins__.<type>` to `builtins.<type>` to avoid errors. This might not work on older mypy versions.

Other changes:

- Exports `register_struc_hook_func` and `register_unstruc_hook_func`, which are methods bound to typecats's default cattrs converter.
- Changed imports from `cattr` to `cattrs`
- Supports Python 3.8 and 3.9.
- Changed function parameter types from `cattrs.Converter` to `cattrs.GenConverter` where necessary, though typecats assumes `GenConverter` throughout, so you should probably update too.

## 1.7.1

- Correctly reference typing_extensions as a dependency in setup.py

## 1.7.0

- Upgrades `cattrs` from 1.0.0 to 1.1.2 and `attrs` from 19.1.0 to 20.3.0,
  primarily to fix a `cattrs` bug wherein union field types where types in the
  union have defaults are not always correctly structured.

## 1.6.1

- Wildcats now properly implement `__eq__` to include the actual
  wildcat dictionary. Additionally, this fixes a bug where
  `unstruc_strip_defaults` did not properly strip attributes that
  themselves had unstructurable data.

## 1.6.0

Added new exception hook functionality for better visibility into
structuring errors. By default adds verbose logging when your item
fails to structure, but this default behavior may be replaced.

## 1.5.0

New converter which will strip (recursively) all attributes which are
equal to their attrs defaults, except for attributes annotated as
`Literal`, which are assumed to be required.

Can be called using `unstruc_strip_defaults(your_attrs_obj)`, or on a
Cat type using the new boolean keyword argument on `unstruc`,
`your_cats_obj.unstruc(strip_defaults=True)`.

## 1.4.1

No longer assume that the `dict` methods will not be overlaid on a
Wildcat by `attrs` attributes.

## 1.4.0

Extracted the default `cattrs` Converter from all implementations to
make `typecats` fully compatible with the use of any
application-provided Converter(s).

All that is necessary to use an externally-supplied converter is to
call the new `patch_converter_for_typecats` function exported by the
package root on the Converter. This will patch your Converter to
enable `typecats` functionality while still maintaining all the
existing functionality and previously-registered function-dispatched
structure and unstructure hooks within your Converter.

## 1.3.2

Reworked Wildcat functionality to use a cleaner hooking process.

## 1.3.1

Corrected return type of `try_struc` to be `Optional[T]`.

## 1.3.0

Improved mypy plugin that recognizes `Mapping[str, Any]` as the
appropriate input type for `struc`, and `Optional[Mapping[str, Any]]`
for `try_struc`.

Also resolves the incompatibility with the mypy plugin API change in
0.750.

## 1.2.0

Wildcats will now unstructure their 'wild' key/value pairs instead of
passing them through.

Improved structure exception logging.

## 1.1.1

Typecats will now preserve user-provided `attrs` validators.

The non-empty validator will still be run on attributes without defaults.

## 1.1.0

No longer block `__setitem__`, `__getitem__`, and `update` for keys
where the Wildcat class defines an attribute with the same name. Log
warnings instead. This more permissive behavior will allow a smoother
progression for code that was written before an attribute was
subsequently added (typed).

## 1.0.1

Added README and Github url to setup.py.

## 1.0.0

Initial release of typecats.
