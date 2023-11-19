import collections
import glob
import json
import logging
import os
import threading
import time
import traceback

from .sinks import DefaultSink

class LogQueue:
    """A queue of records that still need to be written out.

    For efficiency's sake, records are grouped into time windows of
    'batch_window_s' seconds (say, 5 minutes). x'es below indicate
    log record events:

          300               600               900
         |   x    x x      |             x   |
       --+-----------------+-----------------+---------
          ↑                 ↑                 ↑
        wake               wake              wake

    Upon 'wake' events (every batch window seconds), a background thread
    wakes up and collects all events from previous time windows.

    We need to use a mutex since the dict we keep the queue in is not
    thread-safe. We do as little work as possible every time we hold the mutex
    to allow for maximum parallelism.
    """

    def __init__(self, name, batch_window_s):
        self.name = name
        self.records_queue = collections.defaultdict(list)
        self.batch_window_s = batch_window_s
        self.sink = DefaultSink()
        self.mutex = threading.Lock()
        self.running = True
        self.wake_event = threading.Event()
        if self.batch_window_s > 0:
            self.thread = threading.Thread(target=self._write_thread, name=f"{self.name}Writer", daemon=True)
            self.thread.start()

    def stop(self):
        self.running = False
        self.wake_event.set()

    def submit(self, data):
        bucket = div_clip(time.time(), self.batch_window_s)

        with self.mutex:
            self.records_queue[bucket].append(data)

        if self.batch_window_s == 0:
            self.flush()

    def set_sink(self, sink):
        """Configure a function that will be called for every set of records.

        The sink should be a callable object that looks like:

            def sink(timestamp, records) -> Boolean:
                ...

        If this function returns `False`, we assume that saving/transmitting
        the records failed, and it will be retried in the future. If True
        or None is returned, the records will be purged.
        """
        self.sink = sink

    def emergency_save_to_disk(self):
        """Save all untransmitted records to disk.

        They will be picked up and attempted to be transmitted by a future
        (restarted) process.
        """
        all_records = []
        with self.mutex:
            for records in self.records_queue.values():
                all_records.extend(records)
            self.records_queue.clear()

        if not all_records:
            return

        filename = f"{self.name}_dump.{os.getpid()}.{time.time()}.jsonl"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(all_records, f)

    def try_load_emergency_saves(self):
        """Try to load emergency saves from disk, if found.

        There may be multiple LogQueues trying to load the same files at the
        same time, so we need to be careful that only one of them actually
        loads a single file (in order to avoid record duplication).

        We use the atomicity of renaming the file as a way of claiming ownership of it.
        """
        candidates = glob.glob(f"{self.name}_dump.*.jsonl")
        for candidate in candidates:
            try:
                claim_name = candidate + ".claimed"
                os.rename(candidate, claim_name)

                # If this succeeded, we're guaranteed to be able to read this file (and because
                # we renamed it to something not matching the glob pattern, no one else is going to
                # try to pick it up later)
                with open(claim_name, "r", encoding="utf-8") as f:
                    all_records = json.load(f)

                bucket = div_clip(time.time(), self.batch_window_s)
                with self.mutex:
                    self.records_queue[bucket].extend(all_records)
                os.unlink(claim_name)
            except OSError:
                pass

    def flush(self, max_time=None):
        """(Try to) transmit all pending records with recording timestamps
        smaller than the given time now."""
        with self.mutex:
            keys = list(self.records_queue.keys())
        keys.sort()

        max_time = max_time or time.time()
        buckets_to_send = [k for k in keys if k < max_time]

        for bucket_ts in buckets_to_send:
            # Get the records out of the queue
            with self.mutex:
                bucket_records = self.records_queue[bucket_ts]

            # Try to send the records (to signal failure, this can either
            # throw or return False, depending on how loud it wants to be).
            success = self._save_records(bucket_ts, bucket_records)

            # Remove them from the queue if sending didn't fail
            if success is not False:
                with self.mutex:
                    del self.records_queue[bucket_ts]

    def _save_records(self, timestamp, records):
          return self.sink(timestamp, records)

    def _write_thread(self):
        """Background thread which will wake up every batch_window_s seconds
        to emit records from the queue."""
        next_wake = div_clip(time.time(), self.batch_window_s) + self.batch_window_s
        while self.running:
            try:
                # Interruptible sleep for next wake time
                self.wake_event.wait(timeout=max(0, next_wake - time.time()))
                if not self.running:
                    break

                # Once woken, see what buckets we have left to push (all buckets
                # with numbers lower than next_wake)
                self.flush(next_wake)
            except Exception:
                traceback.print_exc()
            next_wake += self.batch_window_s


def div_clip(x, y):
    """Return the highest value < x that's a multiple of y.

    Make an exception for y == 0, in which case we just return x.
    """
    if y == 0:
        return x
    return int(x // y) * y
