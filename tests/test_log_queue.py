import unittest
import querylog

from .base_test import QueryLogSuite

class TestQueryLog(QueryLogSuite):
    def test_emergency_recovery(self):
        # Write some records to the global queue
        querylog.start_global_log_record(banaan='geel')
        querylog.log_value(bloem='rood')
        # Note: not even finished!

        querylog.emergency_shutdown()

        # Create a new queue object and recover in it
        recovered_queue = querylog.log_queue.LogQueue('querylog', batch_window_s=300)
        recovered_queue.try_load_emergency_saves()
        recovered_queue.set_sink(self._fake_sink)

        self.assertEqual(self.records, [])

        recovered_queue.flush()

        self.assertEqual(self.records[0]['banaan'], 'geel')
        self.assertEqual(self.records[0]['bloem'], 'rood')
        self.assertEqual(self.records[0]['terminated'], True)