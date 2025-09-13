"""Anime data model for Anime Tracker"""

import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import List, Optional


@dataclass
class Anime:
    """Represents an anime entry"""

    # Core fields
    title: str
    status: str = "Plan to Watch"
    episodes_watched: int = 0

    # Optional fields
    id: Optional[int] = None
    mal_id: Optional[int] = None
    title_english: Optional[str] = None
    title_japanese: Optional[str] = None
    image_url: Optional[str] = None
    image_cached: Optional[bytes] = None
    total_episodes: Optional[int] = None
    score: Optional[int] = None
    synopsis: Optional[str] = None
    genres: List[str] = field(default_factory=list)
    studio: Optional[str] = None
    aired_from: Optional[date] = None
    aired_to: Optional[date] = None
    season: Optional[str] = None
    year: Optional[int] = None
    source: Optional[str] = None
    rating: Optional[str] = None
    notes: Optional[str] = None

    # Timestamps
    date_added: Optional[datetime] = None
    date_updated: Optional[datetime] = None
    mal_sync_date: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Status options
    STATUS_WATCHING = "Watching"
    STATUS_COMPLETED = "Completed"
    STATUS_ON_HOLD = "On Hold"
    STATUS_DROPPED = "Dropped"
    STATUS_PLAN_TO_WATCH = "Plan to Watch"

    STATUS_OPTIONS = [
        STATUS_WATCHING,
        STATUS_COMPLETED,
        STATUS_ON_HOLD,
        STATUS_DROPPED,
        STATUS_PLAN_TO_WATCH,
    ]

    def __post_init__(self):
        """Validate data after initialization"""
        # Validate status
        if self.status not in self.STATUS_OPTIONS:
            raise ValueError(f"Invalid status: {self.status}")

        # Validate score
        if self.score is not None and (self.score < 0 or self.score > 10):
            raise ValueError(f"Score must be between 0 and 10, got {self.score}")

        # Validate episodes
        if self.episodes_watched < 0:
            raise ValueError(f"Episodes watched cannot be negative: {self.episodes_watched}")

        if self.total_episodes is not None and self.total_episodes < 0:
            raise ValueError(f"Total episodes cannot be negative: {self.total_episodes}")

        if self.total_episodes is not None and self.episodes_watched > self.total_episodes:
            self.episodes_watched = self.total_episodes

        # Auto-complete if all episodes watched
        if (
            self.total_episodes is not None
            and self.episodes_watched == self.total_episodes
            and self.total_episodes > 0
        ):
            if self.status == self.STATUS_WATCHING:
                self.status = self.STATUS_COMPLETED

    @property
    def progress_percentage(self) -> Optional[float]:
        """Calculate watch progress percentage

        Returns:
            Optional[float]: Progress percentage or None if total episodes unknown
        """
        if self.total_episodes and self.total_episodes > 0:
            return (self.episodes_watched / self.total_episodes) * 100
        return None

    @property
    def is_completed(self) -> bool:
        """Check if anime is completed

        Returns:
            bool: True if completed
        """
        return self.status == self.STATUS_COMPLETED

    @property
    def is_watching(self) -> bool:
        """Check if currently watching

        Returns:
            bool: True if watching
        """
        return self.status == self.STATUS_WATCHING

    @property
    def display_progress(self) -> str:
        """Get progress display string

        Returns:
            str: Progress string (e.g., "12/24" or "12/??")
        """
        total = str(self.total_episodes) if self.total_episodes else "??"
        return f"{self.episodes_watched}/{total}"

    @property
    def display_title(self) -> str:
        """Get display title (prefer English if available)

        Returns:
            str: Display title
        """
        return self.title_english or self.title

    def increment_episode(self) -> bool:
        """Increment episodes watched

        Returns:
            bool: True if incremented, False if at maximum
        """
        if self.total_episodes is None or self.episodes_watched < self.total_episodes:
            self.episodes_watched += 1

            # Auto-complete if reached total
            if self.total_episodes is not None and self.episodes_watched == self.total_episodes:
                if self.status == self.STATUS_WATCHING:
                    self.status = self.STATUS_COMPLETED

            return True
        return False

    def decrement_episode(self) -> bool:
        """Decrement episodes watched

        Returns:
            bool: True if decremented, False if at zero
        """
        if self.episodes_watched > 0:
            self.episodes_watched -= 1

            # Change status from completed if decremented
            if self.status == self.STATUS_COMPLETED and self.total_episodes:
                if self.episodes_watched < self.total_episodes:
                    self.status = self.STATUS_WATCHING

            return True
        return False

    def to_dict(self) -> dict:
        """Convert to dictionary

        Returns:
            dict: Anime data as dictionary
        """
        data = asdict(self)

        # Convert genres list to JSON string for database
        if data.get("genres"):
            data["genres"] = json.dumps(data["genres"])
        else:
            data["genres"] = json.dumps([])

        # Convert dates to strings
        if data.get("aired_from"):
            data["aired_from"] = data["aired_from"].isoformat()
        if data.get("aired_to"):
            data["aired_to"] = data["aired_to"].isoformat()

        # Remove None values for database insertion (except genres which should be empty JSON array)
        result = {}
        for k, v in data.items():
            if v is not None or k == "genres":
                result[k] = v
        return result

    @classmethod
    def from_db_row(cls, row: dict) -> "Anime":
        """Create Anime instance from database row

        Args:
            row: Database row as dictionary

        Returns:
            Anime: Anime instance
        """
        data = dict(row)

        # Parse genres from JSON string
        if data.get("genres"):
            try:
                data["genres"] = json.loads(data["genres"])
            except json.JSONDecodeError:
                data["genres"] = []
        else:
            data["genres"] = []

        # Parse dates
        if data.get("aired_from") and isinstance(data["aired_from"], str):
            try:
                data["aired_from"] = date.fromisoformat(data["aired_from"])
            except ValueError:
                data["aired_from"] = None

        if data.get("aired_to") and isinstance(data["aired_to"], str):
            try:
                data["aired_to"] = date.fromisoformat(data["aired_to"])
            except ValueError:
                data["aired_to"] = None

        # Remove fields that are not part of the Anime model
        # These are database-only fields added in migrations
        fields_to_remove = ["sync_status", "last_mal_sync"]
        for field in fields_to_remove:
            data.pop(field, None)

        return cls(**data)

    def validate(self) -> List[str]:
        """Validate anime data

        Returns:
            List[str]: List of validation errors
        """
        errors = []

        # Required fields
        if not self.title or not self.title.strip():
            errors.append("Title is required")

        if self.status not in self.STATUS_OPTIONS:
            errors.append(f"Invalid status: {self.status}")

        # Score validation
        if self.score is not None and (self.score < 0 or self.score > 10):
            errors.append("Score must be between 0 and 10")

        # Episode validation
        if self.episodes_watched < 0:
            errors.append("Episodes watched cannot be negative")

        if self.total_episodes is not None and self.total_episodes < 0:
            errors.append("Total episodes cannot be negative")

        if self.total_episodes is not None and self.episodes_watched > self.total_episodes:
            errors.append("Episodes watched cannot exceed total episodes")

        return errors

    def __str__(self) -> str:
        """String representation

        Returns:
            str: String representation
        """
        return f"Anime(title='{self.display_title}', status='{self.status}', progress='{self.display_progress}')"

    def __repr__(self) -> str:
        """Developer representation

        Returns:
            str: Developer representation
        """
        return f"Anime(id={self.id}, title='{self.title}', mal_id={self.mal_id})"
