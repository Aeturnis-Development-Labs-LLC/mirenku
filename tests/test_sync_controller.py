"""
Test suite for SyncController (R3) — sync orchestration extracted from the
main window.
"""

import pytest
import sys
import os
from unittest.mock import Mock

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from services.sync_controller import SyncController, SyncOutcome


@pytest.fixture
def sync_service():
    service = Mock()
    service.process_sync_queue.return_value = (3, 0, [])
    service.full_sync_from_mal.return_value = (2, 5, [])
    return service


@pytest.fixture
def controller(sync_service):
    return SyncController(root=Mock(), sync_service=sync_service)


class TestSyncOrchestration:
    def test_push(self, controller, sync_service):
        outcome = controller._run("push")

        sync_service.refresh_authentication.assert_called_once()
        sync_service.process_sync_queue.assert_called_once()
        sync_service.full_sync_from_mal.assert_not_called()
        assert outcome.message == "Push complete: 3 succeeded, 0 failed"
        assert outcome.level == "success"
        assert outcome.list_changed is False

    def test_push_with_failures_is_warning(self, controller, sync_service):
        sync_service.process_sync_queue.return_value = (1, 2, ["err1", "err2"])

        outcome = controller._run("push")

        assert outcome.level == "warning"
        assert outcome.errors == ["err1", "err2"]

    def test_pull(self, controller, sync_service):
        outcome = controller._run("pull")

        sync_service.full_sync_from_mal.assert_called_once()
        sync_service.process_sync_queue.assert_not_called()
        assert outcome.message == "Pull complete: 2 added, 5 updated"
        assert outcome.list_changed is True

    def test_full_pushes_before_pulling(self, controller, sync_service):
        calls = []
        sync_service.process_sync_queue.side_effect = lambda: calls.append("push") or (3, 0, [])
        sync_service.full_sync_from_mal.side_effect = lambda: calls.append("pull") or (2, 5, [])

        outcome = controller._run("full")

        assert calls == ["push", "pull"]
        assert outcome.message == "Full sync complete: 3 pushed, 2 added, 5 updated"
        assert outcome.list_changed is True

    def test_full_aggregates_errors_from_both_directions(self, controller, sync_service):
        sync_service.process_sync_queue.return_value = (1, 1, ["push_err"])
        sync_service.full_sync_from_mal.return_value = (0, 0, ["pull_err"])

        outcome = controller._run("full")

        assert outcome.errors == ["push_err", "pull_err"]

    def test_unknown_sync_type_raises(self, controller):
        with pytest.raises(ValueError):
            controller._run("sideways")
