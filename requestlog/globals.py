import threading

from .log_queue import LogQueue
from .log_record import LogRecord, NullRecord, set_default_log_queue, get_default_log_queue


CONTEXT_OBJECT = threading.local()
CONTEXT_OBJECT.current_log_record = NullRecord()


def set_context_object(context):
    """Override the context object for the global log record.

    By default, uses `threading.local()`, i.e. thread-local storage.
    """
    global CONTEXT_OBJECT
    CONTEXT_OBJECT = context


def start_global_log_record(**kwargs):
    """Open a new global log record with the given attributes."""
    record = GlobalLogRecord(**kwargs)
    _set_current_record(record)
    return record


def begin_global_log_record(**kwargs):
    """Alias for 'start_global_log_record'."""
    return start_global_log_record(**kwargs)


def read_global_log_record():
    """Read the current global log record."""
    return _get_current_record().as_data()


def finish_global_log_record(exc=None):
    """Finish the global log record, and return it."""
    try:
        # When developing, this can sometimes get called before 'current_log_record' has been set.
        record = _get_current_record()
        if exc:
            record.record_exception(exc)
        record.finish()
        return record
    finally:
        _set_current_record(NullRecord())


def end_global_log_record(exc=None):
    """An alias for finish_global_log_record."""
    finish_global_log_record(exc)


def log_value(**kwargs):
    """Log values into the currently globally active Log Record."""
    # For some malformed URLs, the records are not initialized,
    # so we check whether there's a current_log_record
    _get_current_record().set(**kwargs)


def log_time(name):
    """Log a time into the currently globally active Log Record."""
    return _get_current_record().timer(name)


def log_counter(name, count=1):
    """Increase the count of something in the currently globally active Log Record."""
    return _get_current_record().inc(name, count)


def log_counters(**kwargs):
    """Use keyword args to log counters."""
    return _get_current_record().inc_all(name, count)


def emergency_shutdown():
    """The process is being killed. Save the logs to disk."""
    _get_current_record().set(terminated=True)
    _get_current_record().finish()
    get_default_log_queue().emergency_save_to_disk()


def initialize(name="requestlog", batch_window_s=0, load_emergency_saves=True, sink=None):
    """Initialize the global log record.

    Configures the name and batch window, and loads old records saved by
    'emergency_shutdown'.

    A batch window of 0 (default) will lead to records being transmitted
    as soon as they are enqueued.
    """
    queue = get_default_log_queue()
    if name != queue.name or batch_window_s != queue.batch_window_s:
        queue = LogQueue(name, batch_window_s=batch_window_s)
        set_default_log_queue(queue)

    if sink:
        # Configure the sink
        queue.set_sink(sink)

    if load_emergency_saves:
        # Load emergency saves
        queue.try_load_emergency_saves()


def flush():
    """Flush the global log record queue now."""
    get_default_log_queue().flush()


def _get_current_record():
    return getattr(CONTEXT_OBJECT, 'current_log_record', NullRecord())


def _set_current_record(rec):
    setattr(CONTEXT_OBJECT, 'current_log_record', rec)


class GlobalLogRecord(LogRecord):
    """A LogRecord that can be used as a context object.

    It will close the global log record when closed. This is an
    alternative to calling 'finish_global_log_record'.
    """

    def __exit__(self, type, value, tb):
        """Call finish_global_log_record."""
        finish_global_log_record(exc=value)