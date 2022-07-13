# typecats

Structure unstructured data for the purpose of static type
checking. An opinionated wrapper for `attrs` and `cattrs`.

In many web services it is common to consume or generate JSON or some
JSON-like representation of data. JSON translates quite nicely to core
Python objects such as dicts and lists. However, if your data is
structured, it is nice to be able to work with it in a structured
manner, i.e. with Python objects. Python objects give you better code
readability, and in more recent versions of Python they are also
capable of being statically type-checked with a tool like `mypy`.

`attrs` is an excellent library for defining boilerplate-free Python
classes that are easy to work with and that make static type-checking
with `mypy` a breeze. You define your attributes and their types with
a very clean syntax, `attrs` gives you constructors and dunder
methods, and `mypy` brings the static type-checking.

Throwing `cattrs` into the mix, you can have pleasant and simple
conversions to and from unstructured data with extremely low
boilerplate as well.

`typecats`, and its core decorator `Cat`, is a thin opinionated layer
on top of these two runtime libraries (`attrs` and `cattrs`) and the
develop-time `mypy`. It defines an `attrs` class with a few additional
features. The 4 core features are:

## Features

1. ### Built-in `struc` and `unstruc`.

   Static class function `struc` and object method `unstruc` added to
   every class type defined as a Cat, which pass directly through to
   their underlying `structure` and `unstructure` implementations in
   `cattrs`.

   ```python
   @Cat
   class TestCat:
      name: str
      age: int

   try:
      TestCat.struc(dict(name='Tom', age=9)) == TestCat(name='Tom', age=9)

      TestCat.struc(dict(name='Tom', age=9)).unstruc() == dict(name='Tom', age=9)
   except StructuringException as e:
      ...
   ```

   #### Rationale

   Make your code easier to read, create a common pattern for
   defining, structuring, and unstructuring pure data objects, and
   require fewer imports - just import your defined type and go!
   Abbreviated forms of the verbs `structure` and `unstructure` were
   chosen to underscore the difference between the built-in `cattrs`
   verbs and to reduce code clutter slightly for what is intended to
   be a common and idiomatic operation.

   #### Considerations

   Note that a `mypy` plugin is provided to inform the type checker
   that these dynamically-added methods are real and provide the
   intended result types. Add to your `mypy.ini`:

   ```python
   plugins = typecats.cats_mypy_plugin
   ```

   Additionally, `struc` and `unstruc` first-class functions are
   provided if you strongly prefer a functional approach. `struc`
   reverses the order of the `cattrs` function signature to make it
   suitable for the common case of partial application:

   ```python
   TestCat_struc = functools.partial(struc, TestCat)
   TestCat_struc(dict(name='Tom', age=2))
   ```

2. ### Non-empty validators defined for all attributes with no default provided.

   ```python
   @Cat
   class TestCat:
      name: str
      age: int
      neutered: bool = True
      owner: Optional[Owner] = None

   works = TestCat.struc(dict(name='Tom', age=0))
   assert works.neutered == True

   try:
      TestCat.struc(dict(name='', age=0))
   except StructuringError as ve:
      print(ve)
      # Attribute "name" on class <class 'TestCat'> with type <class 'str'> cannot have empty value ''!
   ```

   #### Rationale

   For many types of data, a default value such as an empty string,
   empty list/set, or missing complex type is perfectly valid, and
   `typecats` takes the approach that such attributes should have a
   defined default value in order to simplify the use of those
   objects. This has been found to be particularly useful in the
   context of structuring data from APIs, where the API contract may
   not require all keys to be provided for a given type, and where new
   attributes/keys may be defined later on that old clients would not
   know about (backwards compatibility). In these cases, not defining
   a default value would complicate the code, by forcing developers to
   remember which keys needed to be added to a raw data `dict` before
   structuring it.

   On the other hand, there are some facets of the data that are
   absolutely required. A common example would be a database ID -
   without a defined ID, the object/data is meaningless. `typecats`
   allows you to enforce the most basic level of compliance by not
   defining defaults, which forces clients to provide not simply a
   value of the proper type, but a non-empty value of that type - for
   instance, the empty string would never be a valid database ID.

3. ### Wildcats - partial/gradual types via classes.

   Objects may subclass `dict` in order to transparently retain
   untyped key/value pairs for a roundtrip
   structure-unstructure. These are called `Wildcats`, since they
   allow a significant amount of extra functionality at the cost of
   not fully enforcing type-checking.

   ```python
   @Cat
   class TestWildcat(dict):
      name: str
      age: int

   cat_from_db = dict(name='Tom', age=8, gps_tracker=True)
   wc = TestWildcat.struc(cat_from_db)
   assert wc.name == Tom
   assert wc.age == 8
   assert wc['gps_tracker'] == True  # cattrs would normally drop this key at structure time
   assert wc.unstruc() == cat_from_db  # `gps_tracker` survived the roundtrip
   ```

   #### Rationale

   Effectively provides a partially-typed overlay on top of existing
   data, as gradual/partial typing within a specific data format can
   be very useful.

   In other static type-checking systems such as Flow for JavaScript,
   you may define a type as being a simple overlay on top of an object
   which does not prevent that object from containing other data for
   keys outside the typed set. A `Cat` is an `attrs` class with a
   defined set of attributes that will be structured from raw data,
   and as of `cattrs` 1.0.0rc0, unexpected keys are silently dropped
   in order to prevent users from needing to sanitize their data
   before structuring (as opposed to being a runtime error). This
   behavior means that a structured object is not suitable for being
   passed between different parts of a program if there may be other
   parts to the data that the structuring class does not know
   about. This is an unfortunately common requirement, for instance
   when operating a roundtrip read/write transaction to/from a
   database. Since the alternative of passing around the raw data and
   performing many separate structuring/unstructuring roundtrips can
   be prohibitively expensive, and additionally it is arguably (e.g.,
   the design philosophy behind Clojure's Maps, or simply
   duck/structural typing in general) better software design in many
   cases to allow code to operate on a limited subset of attributes
   without preventing objects with a superset of their functionality
   from being used, `typecats` provides the `Wildcat` functionality to
   mimic these more expressive and flexible type/data systems.

   #### Considerations

   Note that, as with the rest of `typecats`, this is a local optimum
   designed for specific, though arguably common, usecases. You don't
   need to use the Wildcat functionality to take advantage of features
   1 and 2, and since it is presumably (for good reason) quite rare to
   explicity subclass `dict` for normal Python classes, it seems
   unlikely that this implementation choice to require inheritance
   would prevent most practical use cases of `Cat` even if the
   functionality of preserving unknown data was specifically not
   desirable for a given application.

   If an application attempts to get or set items within a Wildcat
   which are defined attributes on the class, this will (as of v1.1)
   be allowed but a warning will be logged. This seems to be a better
   in-practice balance for evolving codebases than the v1.0 behavior of
   raising an error. A future version could potentially allow this to
   be toggled globally or per Wildcat class, but the default will
   remain permissive for backwards compatiblity.

   A further design note on Wildcats: A non-inheriting implementation
   was considered and rejected (so far) for two reasons: first, that
   this would require major additional work in order to support
   `pylint` and `mypy` understanding that dict-like access was legal
   for these objects; and second, that _not_ inheriting `dict` but
   overriding `__getitem__` and `__setitem__` would be even more
   likely to conflict with existing class hierarchies, since any
   object that already inherited from `dict` would appear to 'work' as
   a Wildcat but its underlying `dict` would be overlaid and
   inaccessible as a Wildcat.

4. ### Strip `attrs` defaults on unstructure

   All attributes where the value matches the default, except for
   attributes annotated as `Literal`, can have their defaults stripped
   recursively during unstructure.

   This is accomplished via a new built-in Converter instance, and
   does not require use of features 1-3; in fact it will work with
   pure `attrs` classes.

   This is new as of 1.5.0, is not the default behavior, and is
   fully backwards-compatible. It is enabled by a specific call to
   `unstruc_strip_defaults` or via a boolean keyword-only argument on
   the mixin method, `obj.unstruc(strip_defaults=True)`.

## Notes on intent, compatibility, and dependencies

`typecats` and `Cat` are explictly intended to solve a _few_ specific
but common uses, and though they do not intentionally override or
replace `attrs` or `cattrs` features, any complex use of those
underlying features may or may not be fully operational. If you want
to write complex validator or constructor/builder logic of your own,
this library may not be for you.

That said, it is common in our experience to register a number of
specific structure and unstructure hooks with `cattrs` to make certain
specific scenarios work ideally with your data, and `typecats`
provides convenient wrappers to allow adding your hooks to its
internal `cattrs` `Converter` instance. By defining its own converter
instance, `typecats` does not interfere in any way with an existing
application's usage of `attrs` or `cattrs`, and may be used in
addition to, rather than as a replacement for, those libraries.

Use `register_struc_hook` and `register_unstruc_hook` to register on
the built-in converter instance.

`typecats` uses newer-style static typing within its own codebase, and
is therefore currently only compatible with Python 3.6 and up.

### Python version compatibility

As core parts of the implementation, both `attrs` and `cattrs` are
specific-version runtime dependencies. `cattrs` is the more
restrictive library in terms of its compatibility, so as of 1.7.0,
because of the upgrade to `cattrs` 1.1.x, `typecats` is compatible
with Python 3.7 through 3.9.

#### mypy plugin

`typecats` provides a mypy plugin that tells mypy how to interpret the
dynamically-generated `struc` and `unstruc` methods on `Cat`-annotated
classes and objects.

This plugin was most recently updated to account for plugin API
changes in mypy 0.750.

## Users/Stability

`typecats` has been used in production in the Vision system at XOi
Technologies since early 2019.
