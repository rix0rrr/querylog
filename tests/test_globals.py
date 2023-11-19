import unittest

import requestlog

from .base_test import RequestLogSuite


class TestGlobals(RequestLogSuite):
    def test_globals(self):
        """Test the globals interface."""
        requestlog.start_global_log_record(banaan='geel')
        requestlog.log_value(bloem='rood')
        requestlog.finish_global_log_record()

        self.assertEqual(len(self.records), 1)
        self.assertEqual(self.records[0]['banaan'], 'geel')
        self.assertEqual(self.records[0]['bloem'], 'rood')