"""
Test suite for ScrobblingManager - v0.4.0 WebSocket Integration
Following TDD approach - Red phase (failing tests first)
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import time

# These imports will fail initially (TDD Red phase)
from src.services.scrobbling_manager import ScrobblingManager


class TestScrobblingManagerBasics:
    """Test ScrobblingManager basic functionality."""

    @pytest.fixture
    def mock_anime_service(self):
        """Create a mock anime service."""
        service = Mock()
        service.get_all_anime = Mock(return_value=[])
        return service

    @pytest.fixture
    def mock_config(self):
        """Create a mock config."""
        config = Mock()
        config.get = Mock(return_value={})
        config.set = Mock()
        config.save = Mock()
        return config

    @pytest.fixture
    def manager(self, mock_anime_service, mock_config):
        """Create a ScrobblingManager instance for testing."""
        return ScrobblingManager(mock_anime_service, mock_config)

    def test_manager_init_with_disabled_config(self, mock_anime_service, mock_config):
        """Test manager initializes with scrobbling disabled by default."""
        # Arrange
        mock_config.get.return_value = {}

        # Act
        manager = ScrobblingManager(mock_anime_service, mock_config)

        # Assert
        assert manager.enabled is False
        assert manager.port == 7834
        assert manager.server is None
        mock_config.get.assert_called_with("scrobbling", {})

    def test_manager_init_with_enabled_config(self, mock_anime_service, mock_config):
        """Test manager initializes with scrobbling enabled from config."""
        # Arrange
        mock_config.get.return_value = {"enabled": True, "port": 8080}

        # Act
        manager = ScrobblingManager(mock_anime_service, mock_config)

        # Assert
        assert manager.enabled is True
        assert manager.port == 8080
        assert manager.server is None

    def test_start_when_disabled(self, manager):
        """Test start does nothing when scrobbling is disabled."""
        # Arrange
        manager.enabled = False

        # Act
        result = manager.start()

        # Assert
        assert result is False
        assert manager.server is None

    @patch('src.services.scrobbling_manager.ScrobblingServer')
    def test_start_when_enabled(self, mock_server_class, manager):
        """Test start creates and starts server when enabled."""
        # Arrange
        manager.enabled = True
        mock_server_instance = Mock()
        mock_server_instance.running = True
        mock_server_class.return_value = mock_server_instance

        # Act
        result = manager.start()

        # Assert
        assert result is True
        assert manager.server is mock_server_instance
        mock_server_class.assert_called_once_with(manager.anime_service, 7834)
        mock_server_instance.start.assert_called_once()

    @patch('src.services.scrobbling_manager.ScrobblingServer')
    def test_start_handles_server_error(self, mock_server_class, manager):
        """Test start handles server startup errors gracefully."""
        # Arrange
        manager.enabled = True
        mock_server_class.side_effect = Exception("Port already in use")

        # Act
        result = manager.start()

        # Assert
        assert result is False
        assert manager.server is None

    def test_stop_when_no_server(self, manager):
        """Test stop succeeds when no server is running."""
        # Arrange
        manager.server = None

        # Act
        result = manager.stop()

        # Assert
        assert result is True
        assert manager.server is None

    def test_stop_when_server_running(self, manager):
        """Test stop stops the server when running."""
        # Arrange
        mock_server = Mock()
        manager.server = mock_server

        # Act
        result = manager.stop()

        # Assert
        assert result is True
        assert manager.server is None
        mock_server.stop.assert_called_once()

    def test_is_running_when_no_server(self, manager):
        """Test is_running returns False when no server."""
        # Arrange
        manager.server = None

        # Act & Assert
        assert manager.is_running() is False

    def test_is_running_when_server_running(self, manager):
        """Test is_running returns True when server is running."""
        # Arrange
        mock_server = Mock()
        mock_server.running = True
        manager.server = mock_server

        # Act & Assert
        assert manager.is_running() is True

    def test_is_running_when_server_stopped(self, manager):
        """Test is_running returns False when server is stopped."""
        # Arrange
        mock_server = Mock()
        mock_server.running = False
        manager.server = mock_server

        # Act & Assert
        assert manager.is_running() is False


class TestScrobblingManagerEnableDisable:
    """Test ScrobblingManager enable/disable functionality."""

    @pytest.fixture
    def mock_anime_service(self):
        """Create a mock anime service."""
        return Mock()

    @pytest.fixture
    def mock_config(self):
        """Create a mock config."""
        config = Mock()
        config.get = Mock(return_value={})
        config.set = Mock()
        config.save = Mock()
        return config

    @pytest.fixture
    def manager(self, mock_anime_service, mock_config):
        """Create a ScrobblingManager instance for testing."""
        return ScrobblingManager(mock_anime_service, mock_config)

    @patch('src.services.scrobbling_manager.ScrobblingServer')
    def test_enable_starts_server(self, mock_server_class, manager, mock_config):
        """Test enable() enables scrobbling and starts server."""
        # Arrange
        manager.enabled = False
        mock_server_instance = Mock()
        mock_server_instance.running = True
        mock_server_class.return_value = mock_server_instance

        # Act
        result = manager.enable()

        # Assert
        assert result is True
        assert manager.enabled is True
        mock_config.set.assert_called_with("scrobbling", {"enabled": True, "port": 7834})
        mock_config.save.assert_called_once()
        assert manager.server is mock_server_instance

    def test_disable_stops_server(self, manager, mock_config):
        """Test disable() disables scrobbling and stops server."""
        # Arrange
        manager.enabled = True
        mock_server = Mock()
        manager.server = mock_server

        # Act
        result = manager.disable()

        # Assert
        assert result is True
        assert manager.enabled is False
        mock_config.set.assert_called_with("scrobbling", {"enabled": False, "port": 7834})
        mock_config.save.assert_called_once()
        mock_server.stop.assert_called_once()
        assert manager.server is None


class TestScrobblingManagerPort:
    """Test ScrobblingManager port management."""

    @pytest.fixture
    def mock_anime_service(self):
        """Create a mock anime service."""
        return Mock()

    @pytest.fixture
    def mock_config(self):
        """Create a mock config."""
        config = Mock()
        config.get = Mock(return_value={})
        config.set = Mock()
        config.save = Mock()
        return config

    @pytest.fixture
    def manager(self, mock_anime_service, mock_config):
        """Create a ScrobblingManager instance for testing."""
        return ScrobblingManager(mock_anime_service, mock_config)

    def test_set_port_valid(self, manager, mock_config):
        """Test setting a valid port number."""
        # Act
        result = manager.set_port(8080)

        # Assert
        assert result is True
        assert manager.port == 8080
        mock_config.set.assert_called_with("scrobbling", {"port": 8080})
        mock_config.save.assert_called_once()

    def test_set_port_invalid_low(self, manager):
        """Test setting port below valid range."""
        # Act
        result = manager.set_port(1023)

        # Assert
        assert result is False
        assert manager.port == 7834  # Unchanged

    def test_set_port_invalid_high(self, manager):
        """Test setting port above valid range."""
        # Act
        result = manager.set_port(65536)

        # Assert
        assert result is False
        assert manager.port == 7834  # Unchanged

    @patch('src.services.scrobbling_manager.ScrobblingServer')
    def test_set_port_restarts_running_server(self, mock_server_class, manager):
        """Test changing port restarts a running server."""
        # Arrange
        manager.enabled = True
        mock_old_server = Mock()
        mock_old_server.running = True
        manager.server = mock_old_server

        mock_new_server = Mock()
        mock_new_server.running = True
        mock_server_class.return_value = mock_new_server

        # Act
        result = manager.set_port(9000)

        # Assert
        assert result is True
        assert manager.port == 9000
        mock_old_server.stop.assert_called_once()
        mock_server_class.assert_called_with(manager.anime_service, 9000)
        mock_new_server.start.assert_called_once()


class TestScrobblingManagerStatus:
    """Test ScrobblingManager status reporting."""

    @pytest.fixture
    def mock_anime_service(self):
        """Create a mock anime service."""
        return Mock()

    @pytest.fixture
    def mock_config(self):
        """Create a mock config."""
        config = Mock()
        config.get = Mock(return_value={})
        return config

    @pytest.fixture
    def manager(self, mock_anime_service, mock_config):
        """Create a ScrobblingManager instance for testing."""
        return ScrobblingManager(mock_anime_service, mock_config)

    def test_get_status_when_disabled(self, manager):
        """Test status when scrobbling is disabled."""
        # Arrange
        manager.enabled = False
        manager.server = None

        # Act
        status = manager.get_status()

        # Assert
        assert status == {
            "enabled": False,
            "running": False,
            "port": 7834,
            "clients": 0,
            "sessions": 0
        }

    def test_get_status_when_running(self, manager):
        """Test status when server is running with clients."""
        # Arrange
        manager.enabled = True
        mock_server = Mock()
        mock_server.running = True
        mock_server.clients = ["client1", "client2"]
        mock_server.watching_sessions = {"session1": {}, "session2": {}, "session3": {}}
        manager.server = mock_server

        # Act
        status = manager.get_status()

        # Assert
        assert status == {
            "enabled": True,
            "running": True,
            "port": 7834,
            "clients": 2,
            "sessions": 3
        }


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])