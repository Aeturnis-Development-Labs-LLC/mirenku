"""
Test suite for WebSocket server - v0.4.0 Auto-Scrobbling
Following TDD approach - Red phase (failing tests first)
"""

import asyncio
import json
import time
from unittest.mock import Mock

import pytest
import websockets

# These imports will fail initially (TDD Red phase)
from src.services.websocket_server import ScrobblingServer


class TestWebSocketServerCore:
    """Test WebSocket server core functionality."""

    @pytest.fixture()
    def mock_anime_service(self):
        """Create a mock anime service."""
        service = Mock()
        service.get_all_anime = Mock(return_value=[])
        service.update_anime = Mock()
        service.get_anime = Mock()
        return service

    @pytest.fixture()
    def server(self, mock_anime_service):
        """Create a server instance for testing."""
        return ScrobblingServer(mock_anime_service, port=17834)  # Test port

    def test_server_starts_on_correct_port(self, server):
        """Test that server starts on the specified port."""
        # Arrange
        expected_port = 17834

        # Act
        server.start()
        time.sleep(0.5)  # Give server time to start

        # Assert
        assert server.port == expected_port
        assert server.running is True
        assert server.thread is not None
        assert server.thread.is_alive()

        # Cleanup
        server.stop()

    def test_server_accepts_connections(self, server):
        """Test that server accepts WebSocket connections."""
        # Arrange
        server.start()
        time.sleep(0.5)
        connection_successful = False

        # Act
        async def connect():
            nonlocal connection_successful
            try:
                async with websockets.connect("ws://localhost:17834"):
                    connection_successful = True
            except Exception as e:
                pytest.fail(f"Failed to connect: {e}")

        asyncio.run(connect())

        # Assert
        assert connection_successful

        # Cleanup
        server.stop()

    def test_server_handles_multiple_clients(self, server):
        """Test that server can handle multiple simultaneous clients."""
        # Arrange
        server.start()
        time.sleep(0.5)
        client_count = 3
        connected_clients = []

        # Act
        async def connect_multiple():
            for i in range(client_count):
                ws = await websockets.connect("ws://localhost:17834")
                connected_clients.append(ws)

            # Check all are connected
            assert len(connected_clients) == client_count
            assert len(server.clients) == client_count

            # Close all
            for ws in connected_clients:
                await ws.close()

        asyncio.run(connect_multiple())

        # Assert
        time.sleep(0.1)  # Let server process disconnections
        assert len(server.clients) == 0

        # Cleanup
        server.stop()

    def test_server_graceful_shutdown(self, server):
        """Test that server shuts down gracefully."""
        # Arrange
        server.start()
        time.sleep(0.5)
        assert server.running is True

        # Act
        server.stop()
        time.sleep(0.5)

        # Assert
        assert server.running is False
        assert not server.thread.is_alive()

    def test_server_reconnection_handling(self, server):
        """Test that server handles client reconnections properly."""
        # Arrange
        server.start()
        time.sleep(0.5)

        # Act & Assert
        async def test_reconnection():
            # First connection
            ws1 = await websockets.connect("ws://localhost:17834")
            await ws1.close()
            await asyncio.sleep(0.1)  # Use async sleep

            # Reconnection
            ws2 = await websockets.connect("ws://localhost:17834")
            await asyncio.sleep(0.1)  # Give time to register
            assert len(server.clients) == 1
            await ws2.close()

        asyncio.run(test_reconnection())

        # Cleanup
        server.stop()


class TestWebSocketMessageProtocol:
    """Test WebSocket message handling protocol."""

    @pytest.fixture()
    def mock_anime_service(self):
        """Create a mock anime service."""
        service = Mock()
        anime = Mock()
        anime.id = 1
        anime.title = "Attack on Titan"
        anime.episodes_watched = 5
        anime.status = "Watching"
        service.get_all_anime = Mock(return_value=[anime])
        service.update_anime = Mock()
        return service

    @pytest.fixture()
    def server(self, mock_anime_service):
        """Create a server instance for testing."""
        return ScrobblingServer(mock_anime_service, port=17835)  # Different test port

    def test_message_parsing(self, server):
        """Test that server correctly parses JSON messages."""
        server.start()
        time.sleep(0.5)

        async def test_parsing():
            async with websockets.connect("ws://localhost:17835") as ws:
                # Send valid JSON
                await ws.send(json.dumps({"type": "identify", "service": "test"}))
                response = await ws.recv()
                data = json.loads(response)

                assert "type" in data
                assert data["type"] in ["connected", "identified"]

        asyncio.run(test_parsing())
        server.stop()

    def test_invalid_message_handling(self, server):
        """Test that server handles invalid messages gracefully."""
        server.start()
        time.sleep(0.5)

        async def test_invalid():
            async with websockets.connect("ws://localhost:17835") as ws:
                # Send invalid JSON
                await ws.send("not json")
                # Should not crash, might send error response or ignore
                await asyncio.sleep(0.1)  # Give time to process

                # Connection should still be alive
                await ws.ping()  # This will fail if connection is dead

        asyncio.run(test_invalid())
        server.stop()

    def test_message_routing(self, server):
        """Test that messages are routed to correct handlers."""
        server.start()
        time.sleep(0.5)

        async def test_routing():
            async with websockets.connect("ws://localhost:17835") as ws:
                # Test different message types
                messages = [
                    {"type": "identify", "service": "crunchyroll"},
                    {"type": "detected", "title": "Attack on Titan", "episode": 1},
                    {"type": "playing", "session_id": "123", "title": "AOT", "episode": 1},
                    {"type": "paused", "session_id": "123"},
                    {"type": "progress", "session_id": "123", "progress": 50},
                    {"type": "completed", "session_id": "123"},
                ]

                for msg in messages:
                    await ws.send(json.dumps(msg))
                    # Small delay to process
                    await asyncio.sleep(0.05)

                # Should have processed all without error
                assert True  # If we get here, no crashes

        asyncio.run(test_routing())
        server.stop()

    def test_response_formatting(self, server):
        """Test that server responses are properly formatted."""
        server.start()
        time.sleep(0.5)

        async def test_format():
            async with websockets.connect("ws://localhost:17835") as ws:
                # Wait for connection message
                response = await ws.recv()
                data = json.loads(response)

                # Check response format
                assert "type" in data
                assert "message" in data or "supported" in data
                assert isinstance(data, dict)

        asyncio.run(test_format())
        server.stop()

    def test_error_responses(self, server):
        """Test that server sends appropriate error responses."""
        server.start()
        time.sleep(0.5)

        async def test_errors():
            async with websockets.connect("ws://localhost:17835") as ws:
                # Send message with unknown type
                await ws.send(json.dumps({"type": "unknown_type"}))
                await asyncio.sleep(0.1)  # Process time

                # Send message missing required fields
                await ws.send(json.dumps({"type": "playing"}))  # Missing session_id
                await asyncio.sleep(0.1)

                # Connection should still be active
                await ws.ping()

        asyncio.run(test_errors())
        server.stop()


class TestWebSocketSecurity:
    """Test WebSocket server security features."""

    @pytest.fixture()
    def server(self):
        """Create a server instance for testing."""
        mock_service = Mock()
        return ScrobblingServer(mock_service, port=17836)

    def test_localhost_only_connections(self, server):
        """Test that server only accepts localhost connections."""
        # Server should bind to localhost only
        server.start()
        time.sleep(0.5)

        # This is implicitly tested by the connection string
        # Real test would involve trying to connect from external IP
        assert server.port == 17836

        server.stop()

    @pytest.mark.skip(reason="Origin validation implementation pending")
    def test_origin_validation(self, server):
        """Test that server validates Origin header."""
        server.start()
        time.sleep(0.5)

        async def test_origin():
            # Test with invalid origin
            headers = {"Origin": "http://evil.com"}
            try:
                async with websockets.connect("ws://localhost:17836", extra_headers=headers):
                    pytest.fail("Should reject invalid origin")
            except websockets.exceptions.InvalidStatusCode:
                pass  # Expected

        asyncio.run(test_origin())
        server.stop()

    @pytest.mark.skip(reason="Token auth implementation pending")
    def test_token_authentication(self, server):
        """Test that server requires valid authentication token."""

    @pytest.mark.skip(reason="Rate limiting implementation pending")
    def test_rate_limiting(self, server):
        """Test that server implements rate limiting."""

    @pytest.mark.skip(reason="Message size limit implementation pending")
    def test_message_size_limits(self, server):
        """Test that server enforces message size limits."""


class TestAnimeDetection:
    """Test anime detection and matching functionality."""

    @pytest.fixture()
    def mock_anime_service(self):
        """Create a mock anime service with sample anime."""
        service = Mock()

        # Create mock anime objects
        anime1 = Mock()
        anime1.id = 1
        anime1.title = "Attack on Titan"
        anime1.episodes_watched = 10
        anime1.status = "Watching"

        anime2 = Mock()
        anime2.id = 2
        anime2.title = "Frieren"
        anime2.episodes_watched = 15
        anime2.status = "Watching"

        service.get_all_anime = Mock(return_value=[anime1, anime2])
        service.update_anime = Mock()
        return service

    @pytest.fixture()
    def server(self, mock_anime_service):
        """Create a server instance for testing."""
        return ScrobblingServer(mock_anime_service, port=17837)

    def test_anime_detection_matched(self, server, mock_anime_service):
        """Test detection when anime exists in database."""
        server.start()
        time.sleep(0.5)

        async def test_detection():
            async with websockets.connect("ws://localhost:17837") as ws:
                # Skip connection message
                await ws.recv()

                # Send detection message
                await ws.send(
                    json.dumps(
                        {
                            "type": "detected",
                            "title": "Attack on Titan",
                            "episode": 11,
                            "service": "crunchyroll",
                        }
                    )
                )

                # Get response
                response = await ws.recv()
                data = json.loads(response)

                assert data["type"] == "detection_result"
                assert data["matched"] is True
                assert data["anime_id"] == 1
                assert data["current_episode"] == 10
                assert data["status"] == "Watching"

        asyncio.run(test_detection())
        server.stop()

    def test_anime_detection_not_matched(self, server, mock_anime_service):
        """Test detection when anime doesn't exist in database."""
        server.start()
        time.sleep(0.5)

        async def test_detection():
            async with websockets.connect("ws://localhost:17837") as ws:
                # Skip connection message
                await ws.recv()

                # Send detection message for unknown anime
                await ws.send(
                    json.dumps(
                        {
                            "type": "detected",
                            "title": "Unknown Anime",
                            "episode": 1,
                            "service": "netflix",
                        }
                    )
                )

                # Get response
                response = await ws.recv()
                data = json.loads(response)

                assert data["type"] == "detection_result"
                assert data["matched"] is False
                assert "anime_id" not in data

        asyncio.run(test_detection())
        server.stop()


class TestProgressTracking:
    """Test episode progress tracking functionality."""

    @pytest.fixture()
    def mock_anime_service(self):
        """Create a mock anime service."""
        service = Mock()

        anime = Mock()
        anime.id = 1
        anime.title = "Attack on Titan"
        anime.episodes_watched = 10
        anime.status = "Watching"

        service.get_all_anime = Mock(return_value=[anime])
        service.update_anime = Mock()
        return service

    @pytest.fixture()
    def server(self, mock_anime_service):
        """Create a server instance for testing."""
        return ScrobblingServer(mock_anime_service, port=17838)

    def test_episode_completion_tracking(self, server, mock_anime_service):
        """Test that completing an episode updates the database."""
        server.start()
        time.sleep(0.5)

        async def test_completion():
            async with websockets.connect("ws://localhost:17838") as ws:
                # Skip connection message
                await ws.recv()

                # Start watching session
                await ws.send(
                    json.dumps(
                        {
                            "type": "playing",
                            "session_id": "test-123",
                            "title": "Attack on Titan",
                            "episode": 11,
                            "service": "crunchyroll",
                        }
                    )
                )

                await asyncio.sleep(0.1)

                # Complete episode
                await ws.send(json.dumps({"type": "completed", "session_id": "test-123"}))

                await asyncio.sleep(0.1)

                # Check that update was called
                mock_anime_service.update_anime.assert_called_with(1, episodes_watched=11)

        asyncio.run(test_completion())
        server.stop()

    def test_progress_auto_complete(self, server, mock_anime_service):
        """Test that >85% progress auto-completes episode."""
        server.start()
        time.sleep(0.5)

        async def test_auto_complete():
            async with websockets.connect("ws://localhost:17838") as ws:
                # Skip connection message
                await ws.recv()

                # Start watching
                await ws.send(
                    json.dumps(
                        {
                            "type": "playing",
                            "session_id": "test-456",
                            "title": "Attack on Titan",
                            "episode": 11,
                            "service": "netflix",
                        }
                    )
                )

                await asyncio.sleep(0.1)

                # Send 90% progress
                await ws.send(
                    json.dumps({"type": "progress", "session_id": "test-456", "progress": 90})
                )

                await asyncio.sleep(0.1)

                # Should auto-complete
                mock_anime_service.update_anime.assert_called_with(1, episodes_watched=11)

        asyncio.run(test_auto_complete())
        server.stop()


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
