import logging
import unittest

import requestlog


class TestSinks(unittest.TestCase):
  def test_defaultsink(self):
    requestlog.initialize(sink=requestlog.sinks.DefaultSink())
    self.log_something()

  def test_buffersink(self):
    requestlog.initialize(sink=requestlog.sinks.BufferSink())
    self.log_something()

  def test_printsink(self):
    requestlog.initialize(sink=requestlog.sinks.PrintSink())
    self.log_something()

  def test_loggersink(self):
    requestlog.initialize(sink=requestlog.sinks.LoggerSink(logging.getLogger('test')))
    self.log_something()

  def log_something(self):
    with requestlog.begin_global_log_record():
      pass
    requestlog.flush()