"""
Test suite for the run_async worker utility (R2b) — the single threading
policy for UI-triggered background work.
"""

import pytest
import sys
import os
import threading
import time
import tkinter as tk

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.worker import run_async


@pytest.fixture(scope="module")
def root():
    """One root for the module — rapid Tk() create/destroy cycles are flaky
    on Windows"""
    root = tk.Tk()
    root.withdraw()
    yield root
    try:
        root.destroy()
    except:
        pass


@pytest.mark.gui
class TestRunAsync:

    def drain(self, root, condition, timeout=5.0):
        """Pump the Tk event loop until condition() or timeout"""
        deadline = time.time() + timeout
        while not condition() and time.time() < deadline:
            root.update()
            time.sleep(0.01)

    def test_result_marshaled_to_main_thread(self, root):
        seen = {}
        main_thread = threading.current_thread()

        def work():
            seen["work_thread"] = threading.current_thread()
            return 42

        def on_done(result):
            seen["result"] = result
            seen["done_thread"] = threading.current_thread()

        run_async(root, work, on_done=on_done)
        self.drain(root, lambda: "result" in seen)

        assert seen["result"] == 42
        assert seen["work_thread"] is not main_thread
        assert seen["done_thread"] is main_thread

    def test_error_marshaled_to_main_thread(self, root):
        seen = {}
        main_thread = threading.current_thread()

        def work():
            raise RuntimeError("boom")

        def on_error(exc):
            seen["error"] = exc
            seen["error_thread"] = threading.current_thread()

        run_async(root, work, on_error=on_error)
        self.drain(root, lambda: "error" in seen)

        assert isinstance(seen["error"], RuntimeError)
        assert str(seen["error"]) == "boom"
        assert seen["error_thread"] is main_thread

    def test_error_without_handler_is_swallowed(self, root):
        thread = run_async(root, lambda: 1 / 0)
        thread.join(timeout=5)
        root.update()  # must not raise

    def test_on_done_not_called_on_error(self, root):
        seen = {"done": False, "error": False}

        run_async(
            root,
            lambda: 1 / 0,
            on_done=lambda r: seen.update(done=True),
            on_error=lambda e: seen.update(error=True),
        )
        self.drain(root, lambda: seen["error"])

        assert seen["error"] is True
        assert seen["done"] is False
