# simple-null-device-redirector

Context manager that redirects `sys.stdout` and `sys.stderr` to the platform null device (`os.devnull`) for the duration of a `with` block, then restores the originals on exit.

```python
from simple_null_device_redirector import null_device_redirect

with null_device_redirect():
    print("this vanishes")  # goes to os.devnull

print("this prints normally")  # original stdout restored
```

The yielded value is the `(stdout, stderr)` pair of file objects backing the redirect, in case you need to flush them explicitly inside the block:

```python
with null_device_redirect() as (out, err):
    print("buffered content")
    out.flush()  # ensure content reaches devnull before the block exits
```

## Why this exists

Third-party libraries often print diagnostics to stdout/stderr with no way to silence them. Temporarily swapping `sys.stdout` and `sys.stderr` for an `open(os.devnull, "w")` file object is a four-line idiom, but easy to get wrong under exceptions — forgetting to restore in a `finally`, or closing the null file in the wrong order. This library wraps that idiom and gets the cleanup right.

The trade-off: this is a Python-level redirect only. It rebinds the `sys.stdout` / `sys.stderr` attributes. It does not use `os.dup2` to redirect the underlying C-level file descriptors, so child processes spawned via `subprocess` inside the block will still write to the real stdout/stderr. If you need subprocess-level suppression, this is the wrong tool — use `contextlib.redirect_stdout` combined with manual `dup2`, or run the subprocess with `stdout=DEVNULL` directly.

## Edge to be aware of

By default (`restore=True`) the originals are reinstated on exit, including when the `with` body raises. Pass `restore=False` to keep the redirect active after the block exits — you are then responsible for restoring `sys.stdout`/`sys.stderr` yourself, and the file objects you were yielded will have been closed by the context manager. The common, intended use is the default; `restore=False` exists for narrow scripting scenarios where you want the silence to outlive the block.

The yielded file objects are text streams opened with `encoding="utf-8"`. They are real file objects (they expose `fileno()`, `flush()`, `write()`), not `io.StringIO` wrappers, so calls like `os.fstat(stream.fileno())` work and report `os.devnull`.

`restore` is the only keyword argument. There is no streaming of captured output back to the caller, no per-stream opt-out, and no descriptor-level mode. If you need any of those, compose this with `contextlib.redirect_stdout` or write the four lines yourself.
