from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import atexit

# Global shared executor to avoid per-request thread pool creation/destruction overhead.
# Used for parallelizing I/O-bound operations like external intelligence screening and
# risk classification in the risk assessment hot path.
_global_executor = ThreadPoolExecutor(max_workers=8)


def get_global_executor() -> ThreadPoolExecutor:
    return _global_executor


@atexit.register
def _shutdown_executor():
    _global_executor.shutdown(wait=False)
