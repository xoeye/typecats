### 1.7.1

- Correctly reference typing_extensions as a dependency in setup.py

### 1.7.0

- Upgrades `cattrs` from 1.0.0 to 1.1.2 and `attrs` from 19.1.0 to 20.3.0,
  primarily to fix a `cattrs` bug wherein union field types where types in the
  union have defaults are not always correctly structured.

### 1.6.1

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

### 1.4.1

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

### 1.3.2

Reworked Wildcat functionality to use a cleaner hooking process.

### 1.3.1

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

### 1.1.1

Typecats will now preserve user-provided `attrs` validators.

The non-empty validator will still be run on attributes without defaults.

## 1.1.0

No longer block `__setitem__`, `__getitem__`, and `update` for keys
where the Wildcat class defines an attribute with the same name.  Log
warnings instead. This more permissive behavior will allow a smoother
progression for code that was written before an attribute was
subsequently added (typed).

### 1.0.1

Added README and Github url to setup.py.

# 1.0.0

Initial release of typecats.
