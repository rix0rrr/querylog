import unittest

import querylog


class QueryLogSuite(unittest.TestCase):
    def setUp(self):
        self._records = []
        self.auto_flush = True
        querylog.initialize(sink=self._fake_sink)

    def _fake_sink(self, ts, records):
        self._records.extend(records)

    @property
    def records(self):
        if self.auto_flush:
            self.auto_flush = False
            querylog.flush()
        return self._records