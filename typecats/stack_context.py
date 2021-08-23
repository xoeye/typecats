import contextlib as cl
import contextvars as cv
import typing as ty

T = ty.TypeVar("T")


@cl.contextmanager
def stack_context(contextvar: cv.ContextVar[T], value: T) -> ty.Iterator:
    try:
        token = contextvar.set(value)
        yield
    finally:
        contextvar.reset(token)
