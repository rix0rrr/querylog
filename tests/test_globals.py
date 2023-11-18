import unittest

import querylog

from .base_test import QueryLogSuite


class TestQueryLog(QueryLogSuite):
    def test_globals(self):
        """Test the globals interface."""
        querylog.start_global_log_record(banaan='geel')
        querylog.log_value(bloem='rood')
        querylog.finish_global_log_record()

        self.assertEqual(len(self.records), 1)
        self.assertEqual(self.records[0]['banaan'], 'geel')
        self.assertEqual(self.records[0]['bloem'], 'rood')