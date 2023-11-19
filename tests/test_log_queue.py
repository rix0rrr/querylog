import unittest
import requestlog

from .base_test import RequestLogSuite

class TestRequestLog(RequestLogSuite):
    def test_emergency_recovery_local(self):
        """Test emergency recovery using specific queues."""
        saving_queue = requestlog.log_queue.LogQueue('requestlog', batch_window_s=300)

        # Write some records to the global queue
        with requestlog.LogRecord(queue=saving_queue, banaan='geel') as record:
            record.log_value(bloem='rood')
        saving_queue.emergency_save_to_disk()

        # Create a new queue object and recover in it
        recovered_queue = requestlog.log_queue.LogQueue('requestlog', batch_window_s=300)
        recovered_queue.try_load_emergency_saves()
        recovered_queue.set_sink(self._fake_sink)

        # Use self._records instead of self.records, as those aren't autoflushed
        self.assertEqual(self._records, [])

        recovered_queue.flush()

        self.assertEqual(self._records[0]['banaan'], 'geel')
        self.assertEqual(self._records[0]['bloem'], 'rood')
        # self.assertEqual(self._records[0]['terminated'], True)

    def test_emergency_recovery_global(self):
        """Test emergency recovery using the global queue."""
        requestlog.initialize(batch_window_s=300)

        # Write some records to the global queue
        requestlog.begin_global_log_record(banaan='geel')
        requestlog.log_value(bloem='rood')
        # NOTE: not even finished
        requestlog.emergency_shutdown()

        # Create a new queue object and recover in it
        recovered_queue = requestlog.log_queue.LogQueue('requestlog', batch_window_s=300)
        recovered_queue.try_load_emergency_saves()
        recovered_queue.set_sink(self._fake_sink)

        # Use self._records instead of self.records, as those aren't autoflushed
        self.assertEqual(self._records, [])

        recovered_queue.flush()

        self.assertEqual(self._records[0]['banaan'], 'geel')
        self.assertEqual(self._records[0]['bloem'], 'rood')
        # self.assertEqual(self._records[0]['terminated'], True)

        # Reset the global config
        requestlog.initialize(batch_window_s=0)