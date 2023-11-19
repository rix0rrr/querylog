Requestlog
=========

A library for recording structured log data, with a focus on performance data.

Why this library?
-----------------

Most logging libraries will emit lines of text, optionally enhanced with a bit
of structured data. If multiple operations are happening in parallel like in a
web server, the log lines from different requests will mix and it might be hard
to find the information for any particular user request.

In contrast, in `requestlog` you define the scope of a logging operation (typically
a scope corresponds to a server request), and all log entries are collected
together in a single dictionary object, so that all information pertaining to a
single server request is collected together.

`requestlog` can store arbitrary keys and values (like `path`, `client_ip` and
`status_code`), but is particularly optimized for storing performance-related
information: timers and counters. This helps answer questions like *"For this
particular web request, how many calls were done to the database?"*, *"How long
did those calls take?"*, and *"How many records were returned?"*.

API
---

The easiest API to `requestlog` is the global API:

```py
import requestlog

# Begin and end a query log scope
requestlog.begin_global_log_record()
requestlog.end_global_log_record()

# You can also use it as a context object
with requestlog.begin_global_log_record():
  # ... code to measure here ...
  pass
```

To log values into the log record, call these functions:

```py
import requestlog

with requestlog.begin_global_log_record():

    # Log keys and values
    requestlog.log_value(status_code='200', path='/user')

    # Counters have the property that they add up. The code below
    # will end up with 'records=7'.
    requestlog.log_counter('records', 5)
    requestlog.log_counter('records', 2)

    # You can also use log_counters, which takes keyword arguments
    requestlog.log_counters(records=5)
    requestlog.log_counters(records=2)

    # Timers are context objects. They will log the following keys:
    # '{name}_cnt' and '{name}_ms', which are the number of times
    # a timer with this name has been logged, and the total time spent
    # in all of them, respectively.
    with requestlog.log_time('database'):
        time.sleep(1)
```

Automatically logged data
-------------------------

`requestlog` logs a bunch of fields into every record by default. These are:

| Field | Contents |
|-------|----------|
| `start_time` | ISO timestamp when the log record was opened. |
| `end_time` | ISO timestamp when the log record was finished; this will correspond to the aggregation bucket. |
| `pid` | PID of the current process |
| `loadavg` | (UNIX only) Load average when the record was opened |
| `user_ms` | (UNIX only) User time spent on the current thread during this operation |
| `sys_ms` | (UNIX only) System time spent on the current thread during this operation |
| `max_rss` | (UNIX only) Maximum memory used by the Python process |
| `inc_max_rss` | (UNIX only) Increase in maximum memory during this operation (use this to statistically find memory-hungry operations) |
| `fault` | `0` or `1` indicating whether an exception occurred in the block |
| `error_message` | (On error) Error message of the exception |
| `error_class` | (On error) Full class name of the exception |
| `dyno` | (On Heroku) The identifier of the current dyno |


Example: Integration with Flask
-------------------------------

Here is an example of how to integrate this with Flask, so that a log record is
produced for every Flask request.

> [!INFO]
> Since `requestlog` uses thread-local storage by default, this assumes you are
using threaded mode or running in a process-per-server model like `gunicorn`.
If you are using greenlets, call `requestlog.globals.set_context_object()`
to store the global log record elsewhere.

Add the following to your main Flask application:

```py
# app.py
import requestlog

# Initialize logging, load any emergency records
requestlog.initialize(sink=...)


@app.before_request
def before_request_begin_logging():
    path = (str(request.path) + '?' + request.query_string.decode('utf-8')
            ) if request.query_string else str(request.path)
    requestlog.begin_global_log_record(
        path=path,
        method=request.method,
        remote_ip=request.headers.get('X-Forwarded-For', request.remote_addr),
        user_agent=request.headers.get('User-Agent'))


@app.after_request
def after_request_log_status(response):
    requestlog.log_value(http_code=response.status_code)
    return response


@app.teardown_request
def teardown_request_finish_logging(exc):
    requestlog.finish_global_log_record(exc)
```

If you are using `gunicorn`, add the following to `gunicorn.conf.py` to
make sure that on server shutdown, any untransmitted records are saved
to disk. They will be automatically loaded and re-enqueued when
`requestlog.initialize()` is called after the server is restarted.

```py
# gunicorn.conf.py
def worker_exit(server, worker):
    import requestlog
    requestlog.emergency_shutdown()
```

Sinks
-----

So far we talked about producing records, but where do those records go? By
default, they will be printed to `stderr` along with a warning that you should
configure a sink.

A sink is a callable object, like a function or a class that implements the
`__call__` method, that will receive a number of records and do something with
those, like sending them off to a logging server or cloud storage.

The signature of the sink function should be:

```py
def my_sink(timestamp: int, records: list[dict]):
    # Implementation here...
    pass
```

You configure the sink by calling `requestlog.initialize()`:

```py
import requestlog

requestlog.initialize(
    batch_window_s=300,
    sink=my_sink)
```

The `batch_window_s` parameter controls how often the sink function is invoked:
a background thread calls the sink function periodically, with all the records
accumulated during that period. The `timestamp` parameter indicates the
timestamp that marks the end of that particular window. If `batch_window_s ==
0`, the sink function will be invoked synchronously whenever any log record is
written.


Example: Saving logs to S3
--------------------------

Here is an example sink that saves logs to S3 in [JSON Lines](https://jsonlines.org) format using `boto3`:

```py
import datetime
import threading
import boto3

# The 'boto3.client' method is not thread safe: https://github.com/boto/boto3/issues/1592
BOTO3_LOCK = threading.Lock()

def s3_sink(timestamp, records):
    """Transmit logfiles to S3 with default config."""
    # No need to configure credentials, we've already confirmed they are in the environment.
    with BOTO3_LOCK:
        s3 = boto3.client("s3", region_name='us-east-1')

    isoformat = datetime.datetime.utcfromtimestamp(timestamp).isoformat() + 'Z'

    # Save every day in a different folder:
    # 's3://my-bucket/my-logs/2020-01-01/13:15:00Z.jsonl'
    bucket_name = 'my-bucket'
    key = (
        '/my-logs/'
        + isoformat.replace("T", "/")
        + '.jsonl'
    )

    # Store as json-lines format
    body = '\n'.join(json.dumps(r) for r in records)

    s3.put_object(
        Bucket=bucket_name,
        Key=key,
        StorageClass="STANDARD_IA",
        Body=body
    )
```
