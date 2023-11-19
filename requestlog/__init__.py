from .decorators import timed, timed_as
from .log_record import LogRecord
from .globals import (begin_global_log_record, start_global_log_record, end_global_log_record, finish_global_log_record, emergency_shutdown,
    log_counter, log_time, log_value, read_global_log_record, flush, initialize)

__version__ = "v0.1.1"
