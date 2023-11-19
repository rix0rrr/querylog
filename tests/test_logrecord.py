import unittest

import requestlog

from .base_test import RequestLogSuite
from . import submodule

class TestRequestLog(RequestLogSuite):
    def test_with_statement(self):
        """Test a 'with' statement."""
        with requestlog.LogRecord(banaan='geel') as record:
            record.set(bloem='rood')

        self.assertEqual(len(self.records), 1)
        self.assertEqual(self.records[0]['banaan'], 'geel')
        self.assertEqual(self.records[0]['bloem'], 'rood')

    def test_timer(self):
        with requestlog.LogRecord(banaan='geel') as record:
            with record.timer('something'):
                record.set(bloem='rood')

        self.assertEqual(len(self.records), 1)
        self.assertIn('something_ms', self.records[0])
        self.assertIn('something_cnt', self.records[0])

    def test_exception(self):
        try:
            with requestlog.LogRecord() as record:
                raise ValueError('Wrong wrong wrong')
        except:
            pass

        self.assertEqual(self.records[0]['fault'], 1)
        self.assertEqual(self.records[0]['error_message'], 'Wrong wrong wrong')
        self.assertEqual(self.records[0]['error_class'], 'ValueError')

    def test_exception2(self):
        try:
            with requestlog.LogRecord() as record:
                raise submodule.MyException('Oops')
        except:
            pass

        self.assertEqual(self.records[0]['fault'], 1)
        self.assertEqual(self.records[0]['error_class'], 'tests.submodule.MyException')
