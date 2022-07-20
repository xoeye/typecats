import contextlib

from typecats import set_detailed_validation_mode_not_threadsafe


@contextlib.contextmanager
def unsafe_stack_disable_detailed_validation():
    try:
        set_detailed_validation_mode_not_threadsafe(enabled=False)
        yield
    finally:
        set_detailed_validation_mode_not_threadsafe(enabled=True)
