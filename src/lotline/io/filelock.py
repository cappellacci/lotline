"""An exclusive lock on an open file that works on every platform.

`fcntl` is Unix-only, so importing it at the top of a module stopped the package (and its tests) loading on
Windows (stability review, 2026-11-27). This uses `fcntl.flock` where it exists and `msvcrt.locking` on
Windows. The lock is advisory and only coordinates Lotline's own processes (rate limits, shared stores).
"""

from __future__ import annotations

from typing import IO

try:
    import fcntl
except ImportError:  # Windows
    fcntl = None
    import msvcrt


def lock(fh: IO, on: bool = True) -> None:
    """Take (`on`) or release an exclusive lock on `fh`. On Windows it locks the file's first byte."""
    if fcntl is not None:
        fcntl.flock(fh, fcntl.LOCK_EX if on else fcntl.LOCK_UN)
        return
    pos = fh.tell()
    fh.seek(0)
    msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK if on else msvcrt.LK_UNLCK, 1)
    fh.seek(pos)


def unlock(fh: IO) -> None:
    """Release the lock taken with `lock`."""
    lock(fh, on=False)
