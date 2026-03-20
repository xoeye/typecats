"""Package version."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version(
        __package__,  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]
    )
except PackageNotFoundError:
    __version__ = "0.0.0.dev0"
