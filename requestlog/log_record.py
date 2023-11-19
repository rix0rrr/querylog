import datetime
import functools
import os
import threading
import time


from .log_queue import LogQueue


IS_WINDOWS = os.name == "nt"
if not IS_WINDOWS:
    import resource

    preferred_rusage = resource.RUSAGE_SELF
    try:
        preferred_rusage = resource.RUSAGE_THREAD
    except:
        # Not on a platform that supports RUSAGE_THREAD
        pass


class LogRecord:
    """A log record."""

    def __init__(self, queue=None, **kwargs):
        self.queue = queue or LOG_QUEUE
        self.start_time = time.time()

        if not IS_WINDOWS:
            self.start_rusage = resource.getrusage(resource.RUSAGE_SELF)
        self.attributes = kwargs
        self.running_timers = set([])
        loadavg = os.getloadavg()[0] if not IS_WINDOWS else None
        self.set(start_time=dtfmt(self.start_time), pid=os.getpid(), loadavg=loadavg, fault=0)

        # If running on Heroku
        dyno = os.getenv("DYNO")
        if dyno:
            self.set(dyno=dyno)

    def finish(self):
        end_time = time.time()
        if not IS_WINDOWS:
            end_rusage = resource.getrusage(resource.RUSAGE_SELF)
            user_ms = ms_from_fsec(end_rusage.ru_utime - self.start_rusage.ru_utime)
            sys_ms = ms_from_fsec(end_rusage.ru_stime - self.start_rusage.ru_stime)
            max_rss = end_rusage.ru_maxrss
            inc_max_rss = max_rss - self.start_rusage.ru_maxrss
        else:
            user_ms = None
            sys_ms = None
            max_rss = None
            inc_max_rss = None

        self.set(
            end_time=dtfmt(end_time),
            user_ms=user_ms,
            sys_ms=sys_ms,
            max_rss=max_rss,
            inc_max_rss=inc_max_rss,
            duration_ms=ms_from_fsec(end_time - self.start_time),
        )

        # There should be 0, but who knows
        self._terminate_running_timers()

        self.queue.submit(self.as_data())

    def log_value(self, **kwargs):
        """Set keys based on keyword arguments."""
        self.set(**kwargs)

    def set(self, **kwargs):
        """Set keys based on keyword arguments."""
        self.attributes.update(kwargs)

    def update(self, dict):
        """Set keys based on a dictionary."""
        self.attributes.update(dict)

    def timer(self, name):
        return LogTimer(self, name)

    def inc(self, name, amount=1):
        if name in self.attributes:
            self.attributes[name] = self.attributes[name] + amount
        else:
            self.attributes[name] = amount

    def inc_all(self, **kwargs):
        for key, value in kwargs.items():
            self.inc(key, value)

    def inc_timer(self, name, time_ms):
        self.inc(name + "_ms", time_ms)
        self.inc(name + "_cnt")

    def log_time(self, name):
        """Alias for 'timer'."""
        return self.timer(name)

    def log_counter(self, name, amount=1):
        """Alias for 'inc'."""
        return self.inc(name, amount)

    def log_counters(self, **kwargs):
        """Alias for inc_all."""
        return self.inc_all(**kwargs)

    def record_exception(self, exc):
        self.set(fault=1, error_class=get_full_class_name(exc), error_message=str(exc))

    def as_data(self):
        return self.attributes

    def _remember_timer(self, timer):
        self.running_timers.add(timer)

    def _forget_timer(self, timer):
        if timer in self.running_timers:
            self.running_timers.remove(timer)

    def _terminate_running_timers(self):
        for timer in list(self.running_timers):
            timer.finish()

    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        if value:
            self.record_exception(value)
        self.finish()


class NullRecord(LogRecord):
    """A dummy log record that doesn't do anything.

    Will be returned if we don't have a default record.
    """

    def __init__(self, **kwargs):
        pass

    def finish(self):
        pass

    def set(self, **kwargs):
        pass

    def _remember_timer(self, _):
        pass

    def _forget_timer(self, _):
        pass

    def _terminate_running_timers(self):
        pass

    def inc_timer(self, _, _2):
        pass

    def inc(self, name, amount=1):
        pass

    def as_data(self):
        return {}

    def record_exception(self, exc):
        self.set(fault=1, error_message=str(exc))


def dtfmt(timestamp):
    dt = datetime.datetime.utcfromtimestamp(timestamp)
    return dt.isoformat() + "Z"


class LogTimer:
    """A quick and dirty timer."""

    def __init__(self, record, name):
        self.record = record
        self.name = name
        self.running = False

    def finish(self):
        if self.running:
            delta = ms_from_fsec(time.time() - self.start)
            self.record.inc_timer(self.name, delta)
            self.record._forget_timer(self)
            self.running = False

    def __enter__(self):
        self.record._remember_timer(self)
        self.start = time.time()
        self.running = True

    def __exit__(self, type, value, tb):
        self.finish()


def ms_from_fsec(x):
    """Milliseconds from fractional seconds."""
    return int(x * 1000)


LOG_QUEUE = LogQueue("requestlog", batch_window_s=0)

def set_default_log_queue(log_queue: LogQueue):
    global LOG_QUEUE
    log_queue.stop()
    LOG_QUEUE = log_queue


def get_default_log_queue():
    return LOG_QUEUE


def get_full_class_name(obj):
    module = obj.__class__.__module__
    if module is None or module == str.__class__.__module__:
        return obj.__class__.__name__
    return module + '.' + obj.__class__.__name__