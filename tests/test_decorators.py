import unittest
import time

import querylog

from .base_test import QueryLogSuite

class TestQueryLog(QueryLogSuite):
    def test_decorator_one(self):
        with querylog.begin_global_log_record():
            timed_function()

        self.assertIn('timed_function_ms', self.records[0])

    def test_decorator_two(self):
        with querylog.begin_global_log_record():
            timed_function_2()

        self.assertIn('sleepy_ms', self.records[0])


@querylog.timed
def timed_function():
    time.sleep(0.01)


@querylog.timed_as('sleepy')
def timed_function_2():
    time.sleep(0.01)