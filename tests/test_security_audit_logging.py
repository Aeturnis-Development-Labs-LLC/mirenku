"""
Test suite for security audit logging
Ensures all security events are properly logged for monitoring
Following The Mirenku Way: Local logging, user owns their data
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


class TestSecurityAuditLogging:
    """Test security audit logging functionality"""

    @pytest.fixture()
    def audit_logger(self):
        """Create security audit logger instance"""
        from utils.security_audit import SecurityAuditLogger

        # Use temp file for testing
        logger = SecurityAuditLogger(log_path=Path("test_audit.log"))
        yield logger
        # Cleanup
        if Path("test_audit.log").exists():
            Path("test_audit.log").unlink()

    @pytest.fixture()
    def oauth_client(self):
        """Create OAuth2 client with audit logging"""
        with patch("services.mal_oauth2_protocol.TokenStorage"):
            from services.mal_oauth2_protocol import MALOAuth2ProtocolClient

            client = MALOAuth2ProtocolClient(
                client_id="test_client",
                token_storage_path=Path("test_tokens.json"),
                enable_audit_logging=True,
            )
            return client

    def test_audit_logger_initialization(self, audit_logger):
        """Test that audit logger initializes correctly"""
        assert audit_logger is not None
        assert audit_logger.log_path.name == "test_audit.log"
        assert audit_logger.is_enabled is True

    def test_log_authentication_success(self, audit_logger):
        """Test logging successful authentication"""
        event = audit_logger.log_auth_success(
            user_id="test_user", method="oauth2", ip_address="127.0.0.1"
        )

        assert event["event_type"] == "AUTH_SUCCESS"
        assert event["user_id"] == "test_user"
        assert event["method"] == "oauth2"
        assert event["ip_address"] == "127.0.0.1"
        assert "timestamp" in event
        assert "event_id" in event

    def test_log_authentication_failure(self, audit_logger):
        """Test logging failed authentication"""
        event = audit_logger.log_auth_failure(
            reason="invalid_token", ip_address="192.168.1.1", attempted_user="unknown"
        )

        assert event["event_type"] == "AUTH_FAILURE"
        assert event["reason"] == "invalid_token"
        assert event["ip_address"] == "192.168.1.1"
        assert event["attempted_user"] == "unknown"

    def test_log_token_refresh(self, audit_logger):
        """Test logging token refresh events"""
        event = audit_logger.log_token_refresh(
            success=True,
            reason="expiry",
            old_expiry="2025-01-01T00:00:00",
            new_expiry="2025-02-01T00:00:00",
        )

        assert event["event_type"] == "TOKEN_REFRESH"
        assert event["success"] is True
        assert event["reason"] == "expiry"
        assert "old_expiry" in event
        assert "new_expiry" in event

    def test_log_rate_limit_triggered(self, audit_logger):
        """Test logging rate limit events"""
        event = audit_logger.log_rate_limit(
            operation="authorize", ip_address="10.0.0.1", attempts_count=5
        )

        assert event["event_type"] == "RATE_LIMIT_TRIGGERED"
        assert event["operation"] == "authorize"
        assert event["attempts_count"] == 5

    def test_log_security_configuration_change(self, audit_logger):
        """Test logging security configuration changes"""
        event = audit_logger.log_config_change(
            setting="refresh_buffer_minutes", old_value="5", new_value="10", changed_by="admin"
        )

        assert event["event_type"] == "CONFIG_CHANGE"
        assert event["setting"] == "refresh_buffer_minutes"
        assert event["old_value"] == "5"
        assert event["new_value"] == "10"
        assert event["changed_by"] == "admin"

    def test_log_suspicious_activity(self, audit_logger):
        """Test logging suspicious activity"""
        event = audit_logger.log_suspicious_activity(
            activity_type="multiple_failed_logins",
            details="5 failed attempts in 60 seconds",
            ip_address="suspicious.ip",
            severity="high",
        )

        assert event["event_type"] == "SUSPICIOUS_ACTIVITY"
        assert event["activity_type"] == "multiple_failed_logins"
        assert event["severity"] == "high"

    def test_log_data_access(self, audit_logger):
        """Test logging data access events"""
        event = audit_logger.log_data_access(
            resource="user_tokens", action="read", user_id="test_user", success=True
        )

        assert event["event_type"] == "DATA_ACCESS"
        assert event["resource"] == "user_tokens"
        assert event["action"] == "read"
        assert event["success"] is True

    def test_audit_log_persistence(self, audit_logger):
        """Test that audit logs are persisted to file"""
        # Log several events
        audit_logger.log_auth_success("user1", "oauth2", "127.0.0.1")
        audit_logger.log_auth_failure("invalid_token", "192.168.1.1", "user2")
        audit_logger.log_token_refresh(True, "expiry", "", "")

        # Read the log file
        with open(audit_logger.log_path) as f:
            lines = f.readlines()

        assert len(lines) == 3
        # Each line should be valid JSON
        for line in lines:
            event = json.loads(line)
            assert "event_type" in event
            assert "timestamp" in event
            assert "event_id" in event

    def test_audit_log_rotation(self, audit_logger):
        """Test that audit logs rotate when size limit reached"""
        # Set small size limit for testing
        audit_logger.max_log_size = 1024  # 1KB

        # Write many events to exceed size
        for i in range(100):
            audit_logger.log_auth_success(f"user{i}", "oauth2", "127.0.0.1")

        # Check that rotation occurred
        rotated_files = list(Path().glob("test_audit.log.*"))
        assert len(rotated_files) > 0

        # Cleanup rotated files
        for f in rotated_files:
            f.unlink()

    def test_audit_log_filtering(self, audit_logger):
        """Test filtering audit log events"""
        # Log various events
        audit_logger.log_auth_success("user1", "oauth2", "127.0.0.1")
        audit_logger.log_auth_failure("invalid_token", "192.168.1.1", "user2")
        audit_logger.log_rate_limit("authorize", "10.0.0.1", 3)

        # Get filtered events
        auth_events = audit_logger.get_events_by_type("AUTH_SUCCESS")
        assert len(auth_events) == 1
        assert auth_events[0]["user_id"] == "user1"

        failure_events = audit_logger.get_events_by_type("AUTH_FAILURE")
        assert len(failure_events) == 1

    def test_audit_log_time_range_query(self, audit_logger):
        """Test querying audit logs by time range"""
        from datetime import timezone

        # Log events with time gaps
        start_time = datetime.now(timezone.utc)
        audit_logger.log_auth_success("user1", "oauth2", "127.0.0.1")

        time.sleep(0.1)
        mid_time = datetime.now(timezone.utc)
        audit_logger.log_auth_failure("invalid_token", "192.168.1.1", "user2")

        time.sleep(0.1)
        end_time = datetime.now(timezone.utc)

        # Query by time range
        events = audit_logger.get_events_by_time_range(start_time, mid_time)
        assert len(events) == 1
        assert events[0]["event_type"] == "AUTH_SUCCESS"

    def test_oauth_integration_logs_events(self, oauth_client):
        """Test that OAuth client logs security events"""
        with patch.object(oauth_client, "audit_logger") as mock_audit:
            # Simulate authorization
            oauth_client.track_auth_attempt()
            mock_audit.log_auth_attempt.assert_called_once()

            # Set up refresh token for refresh test
            oauth_client.refresh_token = "test_refresh_token"

            # Simulate token refresh
            with patch("services.mal_oauth2_protocol.urllib.request.urlopen") as mock_urlopen:
                # Mock successful response
                mock_response = Mock()
                mock_response.status = 200
                mock_response.read.return_value = b'{"access_token": "new_token", "refresh_token": "new_refresh", "expires_in": 3600}'
                mock_urlopen.return_value.__enter__.return_value = mock_response

                oauth_client.refresh_access_token()
                mock_audit.log_token_refresh.assert_called()

    def test_audit_log_sanitization(self, audit_logger):
        """Test that sensitive data is sanitized in audit logs"""
        event = audit_logger.log_auth_success(
            user_id="test_user",
            method="oauth2",
            ip_address="127.0.0.1",
            token="Bearer secret_token_12345",  # Should be sanitized
        )

        # Token should be sanitized
        assert "secret_token_12345" not in str(event)
        if "token" in event:
            assert "[REDACTED]" in event["token"] or "***" in event["token"]

    def test_audit_log_statistics(self, audit_logger):
        """Test generating statistics from audit logs"""
        # Log various events
        for i in range(5):
            audit_logger.log_auth_success(f"user{i}", "oauth2", "127.0.0.1")
        for i in range(3):
            audit_logger.log_auth_failure("invalid_token", "192.168.1.1", f"user{i}")
        audit_logger.log_rate_limit("authorize", "10.0.0.1", 5)

        # Get statistics
        stats = audit_logger.get_statistics()

        assert stats["total_events"] == 9
        assert stats["auth_success_count"] == 5
        assert stats["auth_failure_count"] == 3
        assert stats["rate_limit_count"] == 1

    def test_audit_log_export(self, audit_logger):
        """Test exporting audit logs in different formats"""
        # Log some events
        audit_logger.log_auth_success("user1", "oauth2", "127.0.0.1")
        audit_logger.log_auth_failure("invalid_token", "192.168.1.1", "user2")

        # Export as JSON
        json_export = audit_logger.export_json()
        data = json.loads(json_export)
        assert len(data) == 2

        # Export as CSV
        csv_export = audit_logger.export_csv()
        lines = csv_export.strip().split("\n")
        assert len(lines) == 3  # Header + 2 events

    def test_audit_log_privacy_compliance(self, audit_logger):
        """Test that audit logs comply with privacy requirements"""
        # Log event with PII
        event = audit_logger.log_auth_success(
            user_id="john.doe@example.com", method="oauth2", ip_address="192.168.1.100"
        )

        # User ID should be hashed or partially masked
        assert "john.doe@example.com" not in audit_logger.get_privacy_safe_log(event)

        # IP should be partially masked for privacy
        privacy_log = audit_logger.get_privacy_safe_log(event)
        assert "192.168.1.***" in privacy_log or "192.168.1.0/24" in privacy_log

    def test_audit_log_retention_policy(self, audit_logger):
        """Test that old audit logs are cleaned up per retention policy"""
        # Set short retention for testing (1 second)
        audit_logger.retention_days = 1 / 86400  # 1 second in days

        # Log old event
        old_event = audit_logger.log_auth_success("user1", "oauth2", "127.0.0.1")

        # Wait for retention period
        time.sleep(1.1)

        # Log new event
        new_event = audit_logger.log_auth_success("user2", "oauth2", "127.0.0.1")

        # Clean old events
        audit_logger.clean_old_logs()

        # Only new event should remain
        all_events = audit_logger.get_all_events()
        assert len(all_events) == 1
        assert all_events[0]["user_id"] == "user2"

    def test_audit_log_encryption(self, audit_logger):
        """Test that audit logs can be encrypted at rest"""
        # Enable encryption
        audit_logger.enable_encryption(key="test_encryption_key")

        # Log event
        event = audit_logger.log_auth_success("user1", "oauth2", "127.0.0.1")

        # Read raw file - should be encrypted
        with open(audit_logger.log_path, "rb") as f:
            raw_content = f.read()

        # Should not contain plaintext
        assert b"user1" not in raw_content
        assert b"AUTH_SUCCESS" not in raw_content

        # But should be readable through logger
        events = audit_logger.get_all_events()
        assert len(events) == 1
        assert events[0]["user_id"] == "user1"
