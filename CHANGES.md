## 1.3.2

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
