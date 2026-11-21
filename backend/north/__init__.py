"""North: a map of US master's programs for international students."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("north")
except PackageNotFoundError:  # running from a source tree without installation
    __version__ = "0.0.0"
