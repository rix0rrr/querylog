import unittest

import querylog

from .base_test import QueryLogSuite

class TestQueryLog(QueryLogSuite):
    def test_with_statement(self):
        """Test a 'with' statement."""
        with querylog.LogRecord(banaan='geel') as record:
            record.set(bloem='rood')

        self.assertEqual(len(self.records), 1)
        self.assertEqual(self.records[0]['banaan'], 'geel')
        self.assertEqual(self.records[0]['bloem'], 'rood')

    def test_timer(self):
        with querylog.LogRecord(banaan='geel') as record:
            with record.timer('something'):
                record.set(bloem='rood')

        self.assertEqual(len(self.records), 1)
        self.assertIn('something_ms', self.records[0])
        self.assertIn('something_cnt', self.records[0])