from __future__ import annotations

import os
import time
from contextlib import contextmanager


@contextmanager
def interprocess_lock(lock_path: str, *, timeout_seconds: float = 10.0, poll_seconds: float = 0.05):
    """Best-effort cross-process lock using stdlib only.

    Uses an atomic create of a lock file. This is not crash-proof, but prevents
    common partial-write races in MVP scope.
    """

    start = time.time()
    lock_dir = os.path.dirname(lock_path)
    if lock_dir:
        os.makedirs(lock_dir, exist_ok=True)

    fd: int | None = None
    while fd is None:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_RDWR)
        except FileExistsError:
            if time.time() - start >= timeout_seconds:
                raise TimeoutError(f"Timed out waiting for lock: {lock_path}")
            time.sleep(poll_seconds)

    try:
        yield
    finally:
        try:
            if fd is not None:
                os.close(fd)
        finally:
            try:
                os.remove(lock_path)
            except FileNotFoundError:
                pass
