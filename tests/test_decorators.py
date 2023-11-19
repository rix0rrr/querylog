import unittest
import time

import requestlog

from .base_test import RequestLogSuite

class TestRequestLog(RequestLogSuite):
    def test_decorator_one(self):
        with requestlog.begin_global_log_record():
            timed_function()

        self.assertIn('timed_function_ms', self.records[0])

    def test_decorator_two(self):
        with requestlog.begin_global_log_record():
            timed_function_2()

        self.assertIn('sleepy_ms', self.records[0])


@requestlog.timed
def timed_function():
    time.sleep(0.01)


@requestlog.timed_as('sleepy')
def timed_function_2():
    time.sleep(0.01)