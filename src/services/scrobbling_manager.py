"""
Scrobbling Manager for v0.4.0
Manages WebSocket server and browser extension communication
"""

import logging
from typing import Optional

from services.websocket_server import ScrobblingServer

logger = logging.getLogger(__name__)


class ScrobblingManager:
    """Manages scrobbling functionality including WebSocket server."""

    def __init__(self, anime_service, config):
        """Initialize the scrobbling manager.

        Args:
            anime_service: Service for managing anime
            config: Application configuration
        """
        self.anime_service = anime_service
        self.config = config
        self.server: Optional[ScrobblingServer] = None

        # Check if scrobbling is enabled in config
        # Default to False for now - will be enabled via settings
        scrobbling_config = config.get("scrobbling", {})
        self.enabled = scrobbling_config.get("enabled", False)
        self.port = scrobbling_config.get("port", 7834)

    def start(self):
        """Start the scrobbling service if enabled."""
        if not self.enabled:
            logger.info("Scrobbling is disabled in settings")
            return False

        if self.server and self.server.running:
            logger.warning("WebSocket server is already running")
            return True

        try:
            logger.info(f"Starting WebSocket server on port {self.port}")
            self.server = ScrobblingServer(self.anime_service, self.port)
            self.server.start()
            logger.info("WebSocket server started successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {e}")
            return False

    def stop(self):
        """Stop the scrobbling service."""
        if self.server:
            try:
                logger.info("Stopping WebSocket server")
                self.server.stop()
                self.server = None
                logger.info("WebSocket server stopped")
                return True
            except Exception as e:
                logger.error(f"Error stopping WebSocket server: {e}")
                return False
        return True

    def is_running(self) -> bool:
        """Check if the scrobbling server is running.

        Returns:
            True if server is running, False otherwise
        """
        return self.server is not None and self.server.running

    def enable(self):
        """Enable scrobbling and start the server."""
        self.enabled = True
        # Update config
        scrobbling_config = self.config.get("scrobbling", {})
        scrobbling_config["enabled"] = True
        scrobbling_config["port"] = self.port
        self.config.set("scrobbling", scrobbling_config)
        # Config auto-saves when set() is called
        return self.start()

    def disable(self):
        """Disable scrobbling and stop the server."""
        self.enabled = False
        # Update config
        scrobbling_config = self.config.get("scrobbling", {})
        scrobbling_config["enabled"] = False
        scrobbling_config["port"] = self.port
        self.config.set("scrobbling", scrobbling_config)
        # Config auto-saves when set() is called
        return self.stop()

    def set_port(self, port: int) -> bool:
        """Change the WebSocket server port.

        Args:
            port: New port number

        Returns:
            True if port was changed successfully
        """
        if port < 1024 or port > 65535:
            logger.error(f"Invalid port number: {port}")
            return False

        # Store old port to check if restart needed
        old_port = self.port
        self.port = port

        # Update config
        scrobbling_config = self.config.get("scrobbling", {})
        scrobbling_config["port"] = port
        self.config.set("scrobbling", scrobbling_config)
        # Config auto-saves when set() is called

        # Restart server if running and port changed
        if self.is_running() and old_port != port:
            self.stop()
            return self.start()
        return True

    def get_status(self) -> dict:
        """Get current status of the scrobbling service.

        Returns:
            Dictionary with status information
        """
        return {
            "enabled": self.enabled,
            "running": self.is_running(),
            "port": self.port,
            "clients": len(self.server.clients) if self.server else 0,
            "sessions": len(self.server.watching_sessions) if self.server else 0
        }