"""Data persistence and auto-save functionality"""

import csv
import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from models.database import Database
from services.anime_service import AnimeService

logger = logging.getLogger(__name__)


class PersistenceManager:
    """Manages data persistence and auto-save"""

    def __init__(self, config, database: Database):
        """Initialize persistence manager

        Args:
            config: Config instance
            database: Database instance
        """
        self.config = config
        self.db = database
        self.service = AnimeService(database)

        # Auto-save settings
        self.auto_save_enabled = config.get("auto_save", True)
        self.auto_backup_enabled = config.get("backup_enabled", True)
        self.backup_count = config.get("backup_count", 5)

        # Window state
        self.window_state = {}

        # Auto-save thread
        self.auto_save_thread = None
        self.stop_auto_save = threading.Event()

        # Start auto-save if enabled
        if self.auto_save_enabled:
            self.start_auto_save()

    def save_window_state(
        self,
        geometry: str,
        filter_status: str = "All",
        sort_column: str = "title",
        sort_order: str = "ascending",
    ):
        """Save window state to config

        Args:
            geometry: Window geometry string
            filter_status: Current filter status
            sort_column: Current sort column
            sort_order: Current sort order
        """
        self.config.set("window_geometry", geometry)
        self.config.set("last_filter", filter_status)
        self.config.set("sort_column", sort_column)
        self.config.set("sort_order", sort_order)

        logger.info(f"Window state saved: {geometry}")

    def load_window_state(self) -> Dict[str, Any]:
        """Load window state from config

        Returns:
            Dict containing window state
        """
        return {
            "geometry": self.config.get("window_geometry", "1000x600"),
            "filter": self.config.get("last_filter", "All"),
            "sort_column": self.config.get("sort_column", "title"),
            "sort_order": self.config.get("sort_order", "ascending"),
        }

    def export_to_json(self, file_path: Path) -> bool:
        """Export anime list to JSON file

        Args:
            file_path: Path to export file

        Returns:
            bool: Success status
        """
        try:
            anime_list = self.service.export_anime_list()

            # Add metadata
            export_data = {
                "version": "1.0",
                "exported_at": datetime.now().isoformat(),
                "total_count": len(anime_list),
                "anime": anime_list,
            }

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)

            logger.info(f"Exported {len(anime_list)} anime to {file_path}")
            return True

        except Exception as e:
            logger.error(f"Export to JSON failed: {e}")
            return False

    def import_from_json(self, file_path: Path) -> Tuple[int, int, List[str]]:
        """Import anime list from JSON file

        Args:
            file_path: Path to import file

        Returns:
            Tuple of (imported_count, failed_count, error_messages)
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)

            # Validate JSON structure
            if isinstance(data, dict):
                if "anime" in data:
                    anime_list = data["anime"]
                    if not isinstance(anime_list, list):
                        return 0, 0, ["Invalid JSON: 'anime' field must be a list"]
                else:
                    return 0, 0, ["Invalid JSON: Missing 'anime' field in object"]
            elif isinstance(data, list):
                anime_list = data
            else:
                return 0, 0, ["Invalid JSON: Must be an array or object with 'anime' field"]

            # Validate each anime entry
            errors = []
            valid_anime = []
            for idx, anime in enumerate(anime_list, start=1):
                if not isinstance(anime, dict):
                    errors.append(f"Entry {idx}: Must be an object")
                    continue
                if not anime.get("title"):
                    errors.append(f"Entry {idx}: Missing required 'title' field")
                    continue

                # Validate score if present
                if "score" in anime and anime["score"] is not None:
                    try:
                        score = int(anime["score"])
                        if score < 0 or score > 10:
                            errors.append(f"Entry {idx}: Score must be 0-10, got {score}")
                    except (ValueError, TypeError):
                        errors.append(f"Entry {idx}: Invalid score value")

                # Normalize status
                if "status" in anime:
                    status = anime.get("status", "Plan to Watch")
                    valid_statuses = [
                        "Watching",
                        "Completed",
                        "On Hold",
                        "Dropped",
                        "Plan to Watch",
                    ]
                    if status not in valid_statuses:
                        errors.append(f"Entry {idx}: Invalid status '{status}'")

                valid_anime.append(anime)

            # Import valid entries
            imported, failed, import_errors = self.service.import_anime_list(valid_anime)
            errors.extend(import_errors)

            return imported, failed, errors

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON file: {e}")
            return 0, 0, [f"Invalid JSON at line {e.lineno}: {e.msg}"]
        except FileNotFoundError:
            return 0, 0, [f"File not found: {file_path}"]
        except Exception as e:
            logger.error(f"Import from JSON failed: {e}")
            return 0, 0, [f"Import error: {e!s}"]

    def export_to_csv(self, file_path: Path) -> bool:
        """Export anime list to CSV file

        Args:
            file_path: Path to export file

        Returns:
            bool: Success status
        """
        try:
            anime_list = self.service.get_all_anime()

            with open(file_path, "w", newline="", encoding="utf-8") as f:
                fieldnames = [
                    "title",
                    "status",
                    "episodes_watched",
                    "total_episodes",
                    "score",
                    "notes",
                    "date_added",
                    "date_updated",
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)

                writer.writeheader()
                for anime in anime_list:
                    writer.writerow(
                        {
                            "title": anime.title,
                            "status": anime.status,
                            "episodes_watched": anime.episodes_watched,
                            "total_episodes": anime.total_episodes or "",
                            "score": anime.score or "",
                            "notes": anime.notes or "",
                            "date_added": anime.date_added.isoformat() if anime.date_added else "",
                            "date_updated": anime.date_updated.isoformat()
                            if anime.date_updated
                            else "",
                        }
                    )

            logger.info(f"Exported {len(anime_list)} anime to CSV: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Export to CSV failed: {e}")
            return False

    def import_from_csv(self, file_path: Path) -> Tuple[int, int, List[str]]:
        """Import anime list from CSV file

        Args:
            file_path: Path to import file

        Returns:
            Tuple of (imported_count, failed_count, error_messages)
        """
        try:
            anime_list = []
            errors = []

            with open(file_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)

                for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
                    try:
                        title = row.get("title", "").strip()
                        if not title:
                            errors.append(f"Row {row_num}: Missing title")
                            continue

                        anime_data = {
                            "title": title,
                            "status": row.get("status", "Plan to Watch"),
                            "episodes_watched": 0,
                            "notes": row.get("notes", "").strip() or None,
                        }

                        # Parse episodes_watched
                        if row.get("episodes_watched"):
                            try:
                                anime_data["episodes_watched"] = int(row["episodes_watched"])
                            except ValueError:
                                errors.append(
                                    f"Row {row_num}: Invalid episodes_watched '{row['episodes_watched']}'"
                                )

                        # Optional fields
                        if row.get("total_episodes"):
                            try:
                                anime_data["total_episodes"] = int(row["total_episodes"])
                            except ValueError:
                                # Allow blank/unknown total_episodes
                                pass

                        if row.get("score"):
                            try:
                                score = int(row["score"])
                                if 0 <= score <= 10:
                                    anime_data["score"] = score
                                else:
                                    errors.append(f"Row {row_num}: Score must be 0-10, got {score}")
                            except ValueError:
                                errors.append(f"Row {row_num}: Invalid score '{row['score']}'")

                        anime_list.append(anime_data)
                    except Exception as e:
                        errors.append(f"Row {row_num}: {e!s}")

            # Import valid entries
            imported, failed, import_errors = self.service.import_anime_list(anime_list)
            errors.extend(import_errors)

            return imported, failed, errors

        except Exception as e:
            logger.error(f"Import from CSV failed: {e}")
            return 0, 0, [f"CSV import error: {e!s}"]

    def create_backup(self) -> Optional[Path]:
        """Create database backup

        Returns:
            Path to backup file or None if failed
        """
        if not self.auto_backup_enabled:
            return None

        try:
            backup_dir = self.config.get_backup_dir()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = backup_dir / f"anime_tracker_backup_{timestamp}.db"

            self.db.backup(backup_file)

            # Clean old backups
            self._clean_old_backups(backup_dir)

            logger.info(f"Backup created: {backup_file}")
            return backup_file

        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return None

    def _clean_old_backups(self, backup_dir: Path):
        """Clean old backup files

        Args:
            backup_dir: Backup directory path
        """
        try:
            # Get all backup files
            backups = sorted(
                backup_dir.glob("anime_tracker_backup_*.db"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )

            # Keep only the latest N backups
            if len(backups) > self.backup_count:
                for old_backup in backups[self.backup_count :]:
                    old_backup.unlink()
                    logger.info(f"Deleted old backup: {old_backup}")

        except Exception as e:
            logger.error(f"Failed to clean old backups: {e}")

    def restore_from_backup(self, backup_file: Path) -> bool:
        """Restore database from backup

        Args:
            backup_file: Path to backup file

        Returns:
            bool: Success status
        """
        try:
            if not backup_file.exists():
                logger.error(f"Backup file not found: {backup_file}")
                return False

            # Close current database
            self.db.disconnect()

            # Replace database file
            import shutil

            shutil.copy2(backup_file, self.db.db_path)

            # Reconnect
            self.db.connect()

            logger.info(f"Database restored from: {backup_file}")
            return True

        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False

    def start_auto_save(self):
        """Start auto-save thread"""
        if self.auto_save_thread and self.auto_save_thread.is_alive():
            return

        self.stop_auto_save.clear()
        self.auto_save_thread = threading.Thread(target=self._auto_save_worker, daemon=True)
        self.auto_save_thread.start()
        logger.info("Auto-save started")

    def stop_auto_save_thread(self):
        """Stop auto-save thread"""
        if self.auto_save_thread:
            self.stop_auto_save.set()
            self.auto_save_thread.join(timeout=5)
            logger.info("Auto-save stopped")

    def _auto_save_worker(self):
        """Auto-save worker thread"""
        backup_interval = 3600  # 1 hour
        last_backup = time.time()

        while not self.stop_auto_save.is_set():
            # Check every 30 seconds
            if self.stop_auto_save.wait(30):
                break

            # Save config periodically
            self.config.save_settings()

            # Create backup every hour
            current_time = time.time()
            if current_time - last_backup > backup_interval:
                self.create_backup()
                last_backup = current_time

    def optimize_database(self):
        """Optimize database file size"""
        try:
            self.db.vacuum()
            logger.info("Database optimized")
        except Exception as e:
            logger.error(f"Database optimization failed: {e}")

    def get_backup_list(self) -> List[Dict[str, Any]]:
        """Get list of available backups

        Returns:
            List of backup info dictionaries
        """
        backup_dir = self.config.get_backup_dir()
        backups = []

        try:
            for backup_file in backup_dir.glob("anime_tracker_backup_*.db"):
                stat = backup_file.stat()
                backups.append(
                    {
                        "path": backup_file,
                        "name": backup_file.name,
                        "size": stat.st_size,
                        "created": datetime.fromtimestamp(stat.st_mtime),
                        "size_mb": round(stat.st_size / 1024 / 1024, 2),
                    }
                )

            # Sort by creation date, newest first
            backups.sort(key=lambda x: x["created"], reverse=True)

        except Exception as e:
            logger.error(f"Failed to get backup list: {e}")

        return backups
