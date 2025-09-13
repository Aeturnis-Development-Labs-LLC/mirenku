"""
Security audit logging for Mirenku
Following The Mirenku Way: Local logging, user owns their data
"""

import csv
import hashlib
import json
import uuid
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional


class SecurityAuditLogger:
    """Handles security audit logging with privacy protection"""

    def __init__(self, log_path: Optional[Path] = None, enable: bool = True):
        """Initialize security audit logger

        Args:
            log_path: Path to audit log file (default: audit.log)
            enable: Whether logging is enabled
        """
        self.log_path = log_path or Path("audit.log")
        self.is_enabled = enable
        self.max_log_size = 10 * 1024 * 1024  # 10MB default
        self.retention_days = 90  # Default 90 days retention
        self._encryption_key = None
        self._events_cache = []

        # Create log file if it doesn't exist
        if self.is_enabled and not self.log_path.exists():
            self.log_path.touch()

    def _generate_event_id(self) -> str:
        """Generate unique event ID"""
        return str(uuid.uuid4())

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        # Use timezone-aware datetime to avoid deprecation warning
        from datetime import timezone

        return datetime.now(timezone.utc).isoformat()

    def _write_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Write event to log file and cache"""
        if not self.is_enabled:
            return event

        # Add to cache for querying
        self._events_cache.append(event)

        # Check for rotation
        if self.log_path.exists() and self.log_path.stat().st_size > self.max_log_size:
            self._rotate_log()

        # Write to file
        with open(self.log_path, "a") as f:
            if self._encryption_key:
                # Encrypt event (simplified for testing)
                json_str = json.dumps(event)
                # In production, use proper encryption
                f.write(self._encrypt(json_str) + "\n")
            else:
                f.write(json.dumps(event) + "\n")

        return event

    def _rotate_log(self):
        """Rotate log file when size limit reached"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rotated_path = Path(f"{self.log_path}.{timestamp}")
        # Handle Windows file system limitations
        if rotated_path.exists():
            # Add microseconds to make it unique
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            rotated_path = Path(f"{self.log_path}.{timestamp}")
        self.log_path.rename(rotated_path)
        self.log_path.touch()

    def _encrypt(self, data: str) -> str:
        """Encrypt data (simplified for testing)"""
        # In production, use proper encryption like Fernet
        # For testing, we'll encode to bytes and back
        import base64

        encrypted = base64.b64encode(data.encode()).decode()
        return "ENCRYPTED:" + encrypted

    def _decrypt(self, data: str) -> str:
        """Decrypt data (simplified for testing)"""
        if data.startswith("ENCRYPTED:"):
            import base64

            encrypted_data = data[10:]
            return base64.b64decode(encrypted_data).decode()
        return data

    def log_auth_success(
        self, user_id: str, method: str, ip_address: str, **kwargs
    ) -> Dict[str, Any]:
        """Log successful authentication"""
        event = {
            "event_type": "AUTH_SUCCESS",
            "event_id": self._generate_event_id(),
            "timestamp": self._get_timestamp(),
            "user_id": user_id,
            "method": method,
            "ip_address": ip_address,
        }

        # Sanitize token if present
        if "token" in kwargs:
            kwargs["token"] = self._sanitize_token(kwargs["token"])

        event.update(kwargs)
        return self._write_event(event)

    def log_auth_failure(
        self, reason: str, ip_address: str, attempted_user: str, **kwargs
    ) -> Dict[str, Any]:
        """Log failed authentication"""
        event = {
            "event_type": "AUTH_FAILURE",
            "event_id": self._generate_event_id(),
            "timestamp": self._get_timestamp(),
            "reason": reason,
            "ip_address": ip_address,
            "attempted_user": attempted_user,
        }
        event.update(kwargs)
        return self._write_event(event)

    def log_auth_attempt(self):
        """Log authentication attempt (for OAuth integration)"""
        # Method for OAuth client to call

    def log_token_refresh(
        self, success: bool, reason: str, old_expiry: str, new_expiry: str, **kwargs
    ) -> Dict[str, Any]:
        """Log token refresh event"""
        event = {
            "event_type": "TOKEN_REFRESH",
            "event_id": self._generate_event_id(),
            "timestamp": self._get_timestamp(),
            "success": success,
            "reason": reason,
            "old_expiry": old_expiry,
            "new_expiry": new_expiry,
        }
        event.update(kwargs)
        return self._write_event(event)

    def log_rate_limit(
        self, operation: str, ip_address: str, attempts_count: int, **kwargs
    ) -> Dict[str, Any]:
        """Log rate limit triggered"""
        event = {
            "event_type": "RATE_LIMIT_TRIGGERED",
            "event_id": self._generate_event_id(),
            "timestamp": self._get_timestamp(),
            "operation": operation,
            "ip_address": ip_address,
            "attempts_count": attempts_count,
        }
        event.update(kwargs)
        return self._write_event(event)

    def log_config_change(
        self, setting: str, old_value: str, new_value: str, changed_by: str, **kwargs
    ) -> Dict[str, Any]:
        """Log security configuration change"""
        event = {
            "event_type": "CONFIG_CHANGE",
            "event_id": self._generate_event_id(),
            "timestamp": self._get_timestamp(),
            "setting": setting,
            "old_value": old_value,
            "new_value": new_value,
            "changed_by": changed_by,
        }
        event.update(kwargs)
        return self._write_event(event)

    def log_suspicious_activity(
        self, activity_type: str, details: str, ip_address: str, severity: str, **kwargs
    ) -> Dict[str, Any]:
        """Log suspicious activity"""
        event = {
            "event_type": "SUSPICIOUS_ACTIVITY",
            "event_id": self._generate_event_id(),
            "timestamp": self._get_timestamp(),
            "activity_type": activity_type,
            "details": details,
            "ip_address": ip_address,
            "severity": severity,
        }
        event.update(kwargs)
        return self._write_event(event)

    def log_data_access(
        self, resource: str, action: str, user_id: str, success: bool, **kwargs
    ) -> Dict[str, Any]:
        """Log data access event"""
        event = {
            "event_type": "DATA_ACCESS",
            "event_id": self._generate_event_id(),
            "timestamp": self._get_timestamp(),
            "resource": resource,
            "action": action,
            "user_id": user_id,
            "success": success,
        }
        event.update(kwargs)
        return self._write_event(event)

    def get_events_by_type(self, event_type: str) -> List[Dict[str, Any]]:
        """Get events filtered by type"""
        # Read from file and filter
        events = self._read_all_events()
        return [e for e in events if e.get("event_type") == event_type]

    def get_events_by_time_range(
        self, start_time: datetime, end_time: datetime
    ) -> List[Dict[str, Any]]:
        """Get events within time range"""
        from datetime import timezone

        events = self._read_all_events()
        filtered = []

        # Make times timezone-aware if they aren't
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)

        for event in events:
            try:
                # Parse ISO format timestamp
                event_time = datetime.fromisoformat(event["timestamp"])
                # Make timezone aware if needed
                if event_time.tzinfo is None:
                    event_time = event_time.replace(tzinfo=timezone.utc)

                if start_time <= event_time <= end_time:
                    filtered.append(event)
            except (KeyError, ValueError):
                continue
        return filtered

    def get_all_events(self) -> List[Dict[str, Any]]:
        """Get all events from log"""
        return self._read_all_events()

    def _read_all_events(self) -> List[Dict[str, Any]]:
        """Read all events from log file"""
        if not self.log_path.exists():
            return []

        events = []
        with open(self.log_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    if self._encryption_key:
                        line = self._decrypt(line)
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return events

    def _sanitize_token(self, token: str) -> str:
        """Sanitize token for logging"""
        if not token:
            return "[EMPTY]"
        if token.startswith("Bearer "):
            return "Bearer [REDACTED]"
        return "[REDACTED]"

    def get_privacy_safe_log(self, event: Dict[str, Any]) -> str:
        """Get privacy-safe version of log entry"""
        safe_event = event.copy()

        # Hash or mask email addresses
        if "user_id" in safe_event and "@" in str(safe_event["user_id"]):
            email = safe_event["user_id"]
            # Hash the email for privacy
            safe_event["user_id"] = hashlib.sha256(email.encode()).hexdigest()[:8] + "..."

        # Mask IP addresses
        if "ip_address" in safe_event:
            ip = safe_event["ip_address"]
            if "." in ip:  # IPv4
                parts = ip.split(".")
                if len(parts) == 4:
                    safe_event["ip_address"] = f"{parts[0]}.{parts[1]}.{parts[2]}.***"

        return json.dumps(safe_event)

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics from audit logs"""
        events = self._read_all_events()

        stats = {
            "total_events": len(events),
            "auth_success_count": 0,
            "auth_failure_count": 0,
            "rate_limit_count": 0,
            "suspicious_activity_count": 0,
        }

        for event in events:
            event_type = event.get("event_type")
            if event_type == "AUTH_SUCCESS":
                stats["auth_success_count"] += 1
            elif event_type == "AUTH_FAILURE":
                stats["auth_failure_count"] += 1
            elif event_type == "RATE_LIMIT_TRIGGERED":
                stats["rate_limit_count"] += 1
            elif event_type == "SUSPICIOUS_ACTIVITY":
                stats["suspicious_activity_count"] += 1

        return stats

    def export_json(self) -> str:
        """Export logs as JSON"""
        events = self._read_all_events()
        return json.dumps(events, indent=2)

    def export_csv(self) -> str:
        """Export logs as CSV"""
        events = self._read_all_events()
        if not events:
            return ""

        output = StringIO()
        fieldnames = set()
        for event in events:
            fieldnames.update(event.keys())

        writer = csv.DictWriter(output, fieldnames=sorted(fieldnames))
        writer.writeheader()
        writer.writerows(events)

        return output.getvalue()

    def clean_old_logs(self):
        """Remove logs older than retention period"""
        if not self.retention_days:
            return

        from datetime import timezone

        cutoff_time = datetime.now(timezone.utc) - timedelta(days=self.retention_days)
        events = self._read_all_events()

        # Filter out old events
        kept_events = []
        for event in events:
            try:
                # Parse ISO format timestamp
                event_time = datetime.fromisoformat(event["timestamp"])
                # Make timezone aware if needed
                if event_time.tzinfo is None:
                    event_time = event_time.replace(tzinfo=timezone.utc)
                if event_time > cutoff_time:
                    kept_events.append(event)
            except (KeyError, ValueError):
                # Keep events with invalid timestamps
                kept_events.append(event)

        # Rewrite log with only kept events
        with open(self.log_path, "w") as f:
            for event in kept_events:
                if self._encryption_key:
                    f.write(self._encrypt(json.dumps(event)) + "\n")
                else:
                    f.write(json.dumps(event) + "\n")

    def enable_encryption(self, key: str):
        """Enable encryption for audit logs"""
        self._encryption_key = key

        # Re-encrypt existing logs
        events = self._read_all_events()
        with open(self.log_path, "w") as f:
            for event in events:
                f.write(self._encrypt(json.dumps(event)) + "\n")
