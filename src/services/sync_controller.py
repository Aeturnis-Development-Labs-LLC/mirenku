"""
Sync orchestration, extracted from the main window.

The controller owns what happens during a sync (ordering, aggregation,
outcome shaping); the UI owns only how outcomes are displayed. Callbacks
fire on the Tk main thread via the run_async worker policy.
"""

import logging
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from utils.worker import run_async

logger = logging.getLogger(__name__)


@dataclass
class SyncOutcome:
    """Result of a sync run, ready for display."""

    message: str
    level: str  # "success" | "warning"
    errors: List[str] = field(default_factory=list)
    list_changed: bool = False


class SyncController:
    """Runs MAL sync operations on a worker thread and reports outcomes."""

    def __init__(self, root, sync_service):
        self.root = root
        self.sync_service = sync_service

    def run(
        self,
        sync_type: str,
        on_complete: Callable[[SyncOutcome], None],
        on_error: Optional[Callable[[Exception], None]] = None,
    ):
        """Run a sync in the background.

        Args:
            sync_type: "push", "pull", or "full"
            on_complete: Called on the main thread with a SyncOutcome
            on_error: Called on the main thread if the sync itself raises
        """
        run_async(
            self.root,
            lambda: self._run(sync_type),
            on_done=on_complete,
            on_error=on_error,
            name=f"mal-sync-{sync_type}",
        )

    def _run(self, sync_type: str) -> SyncOutcome:
        """Perform the sync (worker thread; no UI access)"""
        service = self.sync_service
        service.refresh_authentication()

        errors: List[str] = []

        if sync_type == "push":
            success, failed, push_errors = service.process_sync_queue()
            errors.extend(push_errors)
            return SyncOutcome(
                message=f"Push complete: {success} succeeded, {failed} failed",
                level="success" if failed == 0 else "warning",
                errors=errors,
            )

        if sync_type == "pull":
            added, updated, pull_errors = service.full_sync_from_mal()
            errors.extend(pull_errors)
            return SyncOutcome(
                message=f"Pull complete: {added} added, {updated} updated",
                level="success",
                errors=errors,
                list_changed=True,
            )

        if sync_type == "full":
            push_success, push_failed, push_errors = service.process_sync_queue()
            added, updated, pull_errors = service.full_sync_from_mal()
            errors.extend(push_errors)
            errors.extend(pull_errors)
            return SyncOutcome(
                message=(
                    f"Full sync complete: {push_success} pushed, "
                    f"{added} added, {updated} updated"
                ),
                level="success",
                errors=errors,
                list_changed=True,
            )

        raise ValueError(f"Unknown sync type: {sync_type}")
