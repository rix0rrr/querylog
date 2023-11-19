import logging
import unittest

import querylog


class TestSinks(unittest.TestCase):
  def test_defaultsink(self):
    querylog.initialize(sink=querylog.sinks.DefaultSink())
    self.log_something()

  def test_buffersink(self):
    querylog.initialize(sink=querylog.sinks.BufferSink())
    self.log_something()

  def test_printsink(self):
    querylog.initialize(sink=querylog.sinks.PrintSink())
    self.log_something()

  def test_loggersink(self):
    querylog.initialize(sink=querylog.sinks.LoggerSink(logging.getLogger('test')))
    self.log_something()

  def log_something(self):
    with querylog.begin_global_log_record():
      pass
    querylog.flush()