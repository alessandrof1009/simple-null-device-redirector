from __future__ import annotations

import io
import os
import sys
import unittest

from simple_null_device_redirector import null_device_redirect


class TestNullDeviceRedirect(unittest.TestCase):
    def setUp(self) -> None:
        # Snapshot the originals so we can detect any failure to restore,
        # even if a previous test left things in a bad state.
        self._orig_stdout = sys.stdout
        self._orig_stderr = sys.stderr

    def tearDown(self) -> None:
        sys.stdout = self._orig_stdout
        sys.stderr = self._orig_stderr

    def test_stdout_redirected_inside_block(self) -> None:
        """Print output goes to the devnull-backed stream, not the original."""
        sentinel = "sentinel-9f3c"
        capture = io.StringIO()
        with null_device_redirect() as (null_out, null_err):
            sys.stdout = capture
            print(sentinel, end="")
            capture.flush()
            self.assertEqual(capture.getvalue(), sentinel)

    def test_stderr_redirected_inside_block(self) -> None:
        """Writes to stderr go to the devnull-backed stream."""
        sentinel = "err-marker-7a1"
        capture = io.StringIO()
        with null_device_redirect() as (null_out, null_err):
            sys.stderr = capture
            print(sentinel, end="", file=sys.stderr)
            capture.flush()
            self.assertEqual(capture.getvalue(), sentinel)

    def test_streams_restored_on_normal_exit(self) -> None:
        with null_device_redirect():
            self.assertIsNot(sys.stdout, self._orig_stdout)
            self.assertIsNot(sys.stderr, self._orig_stderr)
        self.assertIs(sys.stdout, self._orig_stdout)
        self.assertIs(sys.stderr, self._orig_stderr)

    def test_streams_restored_on_exception(self) -> None:
        class _Marker(Exception):
            pass

        with self.assertRaises(_Marker):
            with null_device_redirect() as (null_out, null_err):
                print("disappears", file=null_out)
                raise _Marker
        self.assertIs(sys.stdout, self._orig_stdout)
        self.assertIs(sys.stderr, self._orig_stderr)

    def test_yielded_objects_are_text_streams(self) -> None:
        """The yielded file objects support text writes, matching sys.stdout."""
        with null_device_redirect() as (null_out, null_err):
            self.assertIsInstance(null_out, io.TextIOBase)
            self.assertIsInstance(null_err, io.TextIOBase)
            # Must be writable in text mode (str accepted, returns int).
            n = null_out.write("abc")
            self.assertEqual(n, 3)
            n = null_err.write("de")
            self.assertEqual(n, 2)

    def test_underlying_stream_target_is_devnull(self) -> None:
        """The file descriptor backing the yielded stream is os.devnull.

        We verify via the file's fileno() and fstat, rather than reading the
        object's name attribute, because the object's .name is exactly
        os.devnull anyway and gives no independent confirmation.
        """
        devnull_stat = os.stat(os.devnull)
        with null_device_redirect() as (null_out, null_err):
            out_stat = os.fstat(null_out.fileno())
            err_stat = os.fstat(null_err.fileno())
        # st_ino and st_dev together identify a file on POSIX.
        self.assertEqual((out_stat.st_dev, out_stat.st_ino), (devnull_stat.st_dev, devnull_stat.st_ino))
        self.assertEqual((err_stat.st_dev, err_stat.st_ino), (devnull_stat.st_dev, devnull_stat.st_ino))

    def test_restoration_uses_original_objects_not_copies(self) -> None:
        """After exit, sys.stdout IS the exact same object as before, by identity."""
        original = sys.stdout
        with null_device_redirect():
            self.assertIsNot(sys.stdout, original)
        self.assertIs(sys.stdout, original)

    def test_nested_redirects_unwind_correctly(self) -> None:
        """Nested blocks restore the immediately-enclosing stdout/stderr on each exit."""
        outer_out = sys.stdout
        with null_device_redirect() as outer_streams:
            inner_out_before = sys.stdout
            with null_device_redirect() as inner_streams:
                self.assertIsNot(sys.stdout, inner_out_before)
                self.assertIsNot(sys.stdout, outer_streams[0])
            self.assertIs(sys.stdout, inner_out_before)
        self.assertIs(sys.stdout, outer_out)

    def test_restore_false_keeps_redirect_after_block(self) -> None:
        """restore=False opts out of automatic restoration on exit."""
        original = sys.stdout
        with null_device_redirect(restore=False) as (null_out, null_err):
            pass
        # Stream is still the devnull object we yielded, not the original.
        self.assertIs(sys.stdout, null_out)
        self.assertIsNot(sys.stdout, original)
        # null_out has been closed by the contextmanager; restore manually
        # so tearDown and other tests stay clean.
        sys.stdout = original
        sys.stderr = self._orig_stderr

    def test_writes_after_exit_do_not_leak_to_devnull(self) -> None:
        """Once the block exits, stdout/stderr are back and writes land on the original."""
        capture = io.StringIO()
        original = sys.stdout
        sys.stdout = capture
        try:
            with null_device_redirect():
                print("hidden", end="")
            print("visible", end="")
        finally:
            sys.stdout = original
        self.assertEqual(capture.getvalue(), "visible")

    def test_yielded_streams_flush_without_error(self) -> None:
        """Calling flush() on the redirected streams succeeds (required for logging)."""
        with null_device_redirect() as (null_out, null_err):
            null_out.flush()
            null_err.flush()

    def test_file_objects_are_distinct(self) -> None:
        """stdout and stderr are backed by two separate file objects.

        This matters because closing one must not close the other, and
        because users sometimes call .flush() or .fileno() on each
        independently.
        """
        with null_device_redirect() as (null_out, null_err):
            self.assertIsNot(null_out, null_err)
            self.assertNotEqual(null_out.fileno(), null_err.fileno())


if __name__ == "__main__":
    unittest.main()
