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
