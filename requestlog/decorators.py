import functools

from .globals import log_time

def timed(fn):
    """Function decorator to make the given function timed into the currently active log record."""

    @functools.wraps(fn)
    def wrapped(*args, **kwargs):
        with log_time(fn.__name__):
            return fn(*args, **kwargs)

    return wrapped


def timed_as(name):
    """Function decorator to make the given function timed into the currently active log record.

    Use a different name from the actual function name.
    """

    def decoractor(fn):
        @functools.wraps(fn)
        def wrapped(*args, **kwargs):
            with log_time(name):
                return fn(*args, **kwargs)

        return wrapped

    return decoractor