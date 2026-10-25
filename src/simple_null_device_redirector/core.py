from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from typing import IO, Iterator, TextIO


@contextmanager
def null_device_redirect(*, restore: bool = True) -> Iterator[tuple[TextIO, TextIO]]:
    """Redirect ``sys.stdout`` and ``sys.stderr`` to ``os.devnull``.

    Yields a ``(new_stdout, new_stderr)`` tuple: the two file objects that
    now back the standard streams while the block is active.

    On normal exit, or on any exception propagated out of the ``with`` body,
    the original streams are restored by default. The restoration uses
    ``sys.stdout = ...``/``sys.stderr = ...`` assignments rather than
    ``dup2``-level descriptor manipulation: this means we only affect the
    *Python-level* file objects, not the underlying C-level file descriptors
    shared with child processes spawned via ``subprocess``. We chose this
    deliberately — it keeps the scope of the redirect predictable and avoids
    silently changing the fd table out from under unrelated code.

    Parameters
    ----------
    restore:
        When ``True`` (default) the original ``sys.stdout`` and ``sys.stderr``
        are reinstated on context exit. When ``False`` the redirect persists
        after the ``with`` block — useful only in narrow scripting scenarios;
        caller is responsible for restoring manually.

    Yields
    ------
    tuple[TextIO, TextIO]
        The new ``stdout`` and ``stderr`` objects (both opened on
        ``os.devnull`` in text mode).
    """
    original_stdout = sys.stdout
    original_stderr = sys.stderr

    null_out = open(os.devnull, "w", encoding="utf-8")
    null_err = open(os.devnull, "w", encoding="utf-8")

    sys.stdout = null_out
    sys.stderr = null_err

    try:
        yield null_out, null_err
    finally:
        if restore:
            sys.stdout = original_stdout
            sys.stderr = original_stderr
        # Close the null-sink file objects we opened. If ``restore`` is False
        # we close them anyway: the caller who opted out of restoration is
        # expected to have swapped ``sys.stdout``/``sys.stderr`` to their own
        # objects before leaving the block; keeping our file objects alive
        # would just leak descriptors.
        null_out.close()
        null_err.close()
