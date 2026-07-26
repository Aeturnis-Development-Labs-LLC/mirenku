"""
One threading policy for UI-triggered background work.

Every background task in the app goes through run_async: work runs on a
daemon worker thread, results and errors are always marshaled back to the
Tk main thread. No call site hand-rolls threading again.

Marshaling detail: worker threads NEVER call into Tk. tkinter's after() is
not reliably thread-safe (it raises "main thread is not in main loop" when
the main thread is outside mainloop, and can misbehave even inside it).
Instead, callbacks are posted to a plain thread-safe queue that a pump —
scheduled on the main thread via after() — drains every 50ms.
"""

import logging
import queue
import threading

logger = logging.getLogger(__name__)

_PUMP_INTERVAL_MS = 50
_DISPATCHER_ATTR = "_mirenku_worker_dispatcher"


class _TkDispatcher:
    """Delivers callables to the Tk main thread via a polled queue."""

    def __init__(self, root):
        self._root = root
        self._queue = queue.SimpleQueue()
        self._pump()

    def post(self, callback):
        """Thread-safe: enqueue a callable to run on the main thread"""
        self._queue.put(callback)

    def _pump(self):
        """Drain pending callbacks; runs on the main thread only"""
        while True:
            try:
                callback = self._queue.get_nowait()
            except queue.Empty:
                break
            try:
                callback()
            except Exception:
                logger.exception("Marshaled callback failed")
        try:
            self._root.after(_PUMP_INTERVAL_MS, self._pump)
        except Exception:
            # Root destroyed — stop pumping
            pass


def _get_dispatcher(root) -> _TkDispatcher:
    dispatcher = getattr(root, _DISPATCHER_ATTR, None)
    if dispatcher is None:
        dispatcher = _TkDispatcher(root)
        setattr(root, _DISPATCHER_ATTR, dispatcher)
    return dispatcher


def run_async(root, fn, on_done=None, on_error=None, name=None):
    """Run fn() on a worker thread and marshal the outcome to the Tk thread.

    Must be called from the main thread (it starts the marshaling pump on
    first use). All app call sites are UI event handlers, which satisfies
    this naturally.

    Args:
        root: Tk root (owns the event loop used for marshaling)
        fn: No-arg callable executed on the worker thread
        on_done: Called on the MAIN thread with fn's return value
        on_error: Called on the MAIN thread with the exception if fn raises.
            If omitted, the error is logged and swallowed.
        name: Thread name for logs/debugging

    Returns:
        The started thread (daemon).
    """
    task_name = name or getattr(fn, "__name__", "task")
    dispatcher = _get_dispatcher(root)

    def _target():
        try:
            result = fn()
        except Exception as e:
            logger.error(f"Background task '{task_name}' failed: {e}", exc_info=True)
            if on_error is not None:
                dispatcher.post(lambda exc=e: on_error(exc))
            return
        if on_done is not None:
            dispatcher.post(lambda r=result: on_done(r))

    thread = threading.Thread(target=_target, daemon=True, name=f"worker-{task_name}")
    thread.start()
    return thread
