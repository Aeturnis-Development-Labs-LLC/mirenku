"""
Version checker for Mirenku updates
Simple, privacy-respecting update notifications
"""

import json
import logging
import urllib.error
import urllib.request
from datetime import datetime
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class VersionChecker:
    """Check for Mirenku updates from GitHub releases"""

    GITHUB_API_URL = (
        "https://api.github.com/repos/Aeturnis-Development-Labs-LLC/mirenku/releases/latest"
    )

    def __init__(self, current_version: str):
        """Initialize version checker

        Args:
            current_version: Current app version (e.g., "0.3.1")
        """
        self.current_version = self._normalize_version(current_version)

    def _normalize_version(self, version: str) -> str:
        """Normalize version string (remove 'v' prefix if present)

        Args:
            version: Version string

        Returns:
            Normalized version
        """
        return version.lstrip("v").strip()

    def _parse_version(self, version: str) -> Tuple[int, int, int]:
        """Parse version string into tuple for comparison

        Args:
            version: Version string (e.g., "0.3.1")

        Returns:
            Tuple of (major, minor, patch)
        """
        try:
            parts = version.split(".")
            return (
                int(parts[0]) if len(parts) > 0 else 0,
                int(parts[1]) if len(parts) > 1 else 0,
                int(parts[2]) if len(parts) > 2 else 0,
            )
        except (ValueError, IndexError):
            logger.error(f"Invalid version format: {version}")
            return (0, 0, 0)

    def check_for_update(self) -> Optional[Dict]:
        """Check GitHub for latest release

        Returns:
            Update info dict or None if no update/error
            {
                'version': '0.3.2',
                'url': 'https://github.com/.../releases/...',
                'name': 'Release name',
                'notes': 'First 500 chars of release notes...',
                'published': '2025-09-10T12:00:00Z'
            }
        """
        try:
            # Create request with timeout
            request = urllib.request.Request(
                self.GITHUB_API_URL,
                headers={
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "Mirenku-UpdateChecker",  # GitHub requires user agent
                },
            )

            # Fetch with 5 second timeout
            with urllib.request.urlopen(request, timeout=5) as response:
                if response.status != 200:
                    logger.debug(f"GitHub API returned status {response.status}")
                    return None

                data = json.loads(response.read().decode("utf-8"))

                # Extract version info
                latest_version = self._normalize_version(data.get("tag_name", ""))

                if not latest_version:
                    logger.debug("No version tag in GitHub response")
                    return None

                # Compare versions
                if self._is_newer_version(latest_version):
                    # Extract release notes (first 500 chars)
                    notes = data.get("body", "")
                    if notes:
                        # Clean up markdown a bit
                        notes = notes.replace("##", "").replace("**", "")
                        notes = notes[:500] + ("..." if len(notes) > 500 else "")

                    return {
                        "version": latest_version,
                        "url": data.get("html_url", ""),
                        "name": data.get("name", f"Version {latest_version}"),
                        "notes": notes,
                        "published": data.get("published_at", ""),
                    }
                logger.debug(f"Current version {self.current_version} is up to date")
                return None

        except urllib.error.URLError as e:
            # Network error - fail silently
            logger.debug(f"Network error checking for updates: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.debug(f"Invalid JSON from GitHub API: {e}")
            return None
        except Exception as e:
            # Any other error - fail silently
            logger.debug(f"Unexpected error checking for updates: {e}")
            return None

    def _is_newer_version(self, latest: str) -> bool:
        """Check if latest version is newer than current

        Args:
            latest: Latest version string

        Returns:
            True if latest is newer
        """
        current = self._parse_version(self.current_version)
        new = self._parse_version(latest)

        # Compare major.minor.patch
        return new > current

    def should_check(self, last_check: Optional[datetime], check_interval_days: int = 7) -> bool:
        """Determine if we should check for updates

        Args:
            last_check: Last check timestamp
            check_interval_days: Days between checks

        Returns:
            True if should check
        """
        if last_check is None:
            return True

        time_since = datetime.now() - last_check
        return time_since.days >= check_interval_days

    def format_update_message(self, update_info: Dict) -> str:
        """Format update information for display

        Args:
            update_info: Update information dict

        Returns:
            Formatted message
        """
        version = update_info.get("version", "Unknown")
        name = update_info.get("name", "")

        message = f"Mirenku {version} is available!"
        if name and name != f"Version {version}":
            message += f"\n{name}"

        return message


def check_for_updates_async(current_version: str, callback):
    """Check for updates in background thread

    Args:
        current_version: Current app version
        callback: Function to call with result (update_info or None)
    """
    import threading

    def worker():
        checker = VersionChecker(current_version)
        result = checker.check_for_update()
        callback(result)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
