import logging
import sys


class BufferSink:
    """A sink that buffers records."""
    def __init__(self):
        self.records = []

    def __call__(self, ts, records):
        self.records.extend(records)


class PrintSink:
    """A sink that prints records to stdout or stderr."""
    def __init__(self, stream=sys.stderr):
        self.stream = stream

    def __call__(self, ts, records):
        for record in records:
            self.stream.write('%r\n' % record)


class DefaultSink(PrintSink):
    """A printing sink that also prints a warning the first time."""
    def __init__(self, stream=sys.stderr):
        super().__init__(stream)
        self.warn = True

    def __call__(self, ts, records):
        if self.warn:
            self.stream.write('WARNING: No sink configured for requestlog. Call requestlog.initialize(sink=...)\n')
            self.warn = False
        super().__call__(ts, records)


class LoggerSink:
    """A sink that logs to a Python logger."""
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger('requestlog')

    def __call__(self, ts, records):
        for record in records:
            self.logger.debug(repr(record))