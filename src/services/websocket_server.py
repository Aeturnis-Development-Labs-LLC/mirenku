"""
WebSocket server for browser extension communication.
Part of Mirenku v0.4.0 - Auto-Scrobbling Update

This server runs locally on port 7834 and handles:
- Browser extension connections
- Anime playback detection
- Episode progress tracking
- Queued updates when app is closed
"""

import asyncio
import json
import logging
import queue
import threading
from datetime import datetime
from typing import Dict, Set

import websockets

logger = logging.getLogger(__name__)


class ScrobblingServer:
    """WebSocket server for browser extension communication."""

    def __init__(self, anime_service, port: int = 7834):
        """Initialize the scrobbling server.

        Args:
            anime_service: Service for managing anime in database
            port: Port to listen on (default: 7834)
        """
        self.anime_service = anime_service
        self.port = port
        self.clients: Set = set()  # Will store websocket connections
        self.server = None
        self.loop = None
        self.thread = None
        self.queue = queue.Queue()
        self.running = False
        self.stop_future = None

        # Track current watching sessions
        self.watching_sessions: Dict[str, Dict] = {}

    async def register(self, websocket):
        """Register a new client connection."""
        self.clients.add(websocket)
        logger.info(f"Client connected. Total clients: {len(self.clients)}")

        # Send connection confirmation
        await websocket.send(
            json.dumps(
                {
                    "type": "connected",
                    "message": "Connected to Mirenku",
                    "timestamp": datetime.now().isoformat(),
                }
            )
        )

    async def unregister(self, websocket):
        """Unregister a client connection."""
        self.clients.discard(websocket)
        logger.info(f"Client disconnected. Total clients: {len(self.clients)}")

    async def handle_message(self, websocket, message: str):
        """Handle incoming messages from browser extension.

        Message types:
        - identify: Extension identifies itself and the service
        - playing: Video started playing
        - paused: Video paused
        - progress: Progress update (time watched)
        - completed: Episode completed
        - detected: Anime/episode detected on page
        """
        try:
            data = json.loads(message)
            msg_type = data.get("type")

            logger.debug(f"Received message: {msg_type}")

            if msg_type == "identify":
                # Extension identifying itself
                await self.handle_identify(websocket, data)

            elif msg_type == "detected":
                # Anime detected on page
                await self.handle_detected(websocket, data)

            elif msg_type == "playing":
                # Video started playing
                await self.handle_playing(websocket, data)

            elif msg_type == "paused":
                # Video paused
                await self.handle_paused(websocket, data)

            elif msg_type == "progress":
                # Progress update
                await self.handle_progress(websocket, data)

            elif msg_type == "completed":
                # Episode completed
                await self.handle_completed(websocket, data)

            else:
                logger.warning(f"Unknown message type: {msg_type}")

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON received: {e}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")

    async def handle_identify(self, websocket, data: Dict):
        """Handle extension identification."""
        service = data.get("service", "unknown")
        version = data.get("version", "unknown")

        logger.info(f"Extension identified: {service} v{version}")

        await websocket.send(
            json.dumps(
                {
                    "type": "identified",
                    "message": f"Recognized {service} extension",
                    "supported": True,
                }
            )
        )

    async def handle_detected(self, websocket, data: Dict):
        """Handle anime detection on page."""
        anime_title = data.get("title")
        episode = data.get("episode")
        service = data.get("service")

        if not anime_title:
            return

        logger.info(f"Detected: {anime_title} - Episode {episode} on {service}")

        # Try to match with existing anime in database
        # This is simplified - in production we'd use fuzzy matching
        matched_anime = None
        all_anime = self.anime_service.get_all_anime()

        for anime in all_anime:
            if anime.title.lower() == anime_title.lower():
                matched_anime = anime
                break

        response = {"type": "detection_result", "matched": matched_anime is not None}

        if matched_anime:
            response["anime_id"] = matched_anime.id
            response["current_episode"] = matched_anime.episodes_watched
            response["status"] = matched_anime.status

        await websocket.send(json.dumps(response))

    async def handle_playing(self, websocket, data: Dict):
        """Handle video playing event."""
        session_id = data.get("session_id")
        anime_title = data.get("title")
        episode = data.get("episode")

        if not session_id:
            return

        # Track watching session
        self.watching_sessions[session_id] = {
            "title": anime_title,
            "episode": episode,
            "start_time": datetime.now(),
            "service": data.get("service"),
            "status": "playing",
        }

        logger.info(f"Started watching: {anime_title} - Episode {episode}")

        await websocket.send(json.dumps({"type": "tracking_started", "session_id": session_id}))

    async def handle_paused(self, websocket, data: Dict):
        """Handle video paused event."""
        session_id = data.get("session_id")

        if session_id in self.watching_sessions:
            self.watching_sessions[session_id]["status"] = "paused"
            logger.info(f"Paused session: {session_id}")

    async def handle_progress(self, websocket, data: Dict):
        """Handle progress update."""
        session_id = data.get("session_id")
        progress = data.get("progress", 0)  # Percentage watched

        if session_id in self.watching_sessions:
            self.watching_sessions[session_id]["progress"] = progress

            # Auto-mark as completed if > 85% watched
            if progress > 85:
                await self.handle_completed(websocket, data)

    async def handle_completed(self, websocket, data: Dict):
        """Handle episode completion."""
        session_id = data.get("session_id")

        if session_id not in self.watching_sessions:
            return

        session = self.watching_sessions[session_id]
        anime_title = session["title"]
        episode = session["episode"]

        logger.info(f"Completed: {anime_title} - Episode {episode}")

        # Find and update anime in database
        all_anime = self.anime_service.get_all_anime()
        for anime in all_anime:
            if anime.title.lower() == anime_title.lower():
                # Update progress
                if anime.episodes_watched < episode:
                    self.anime_service.update_anime(anime.id, episodes_watched=episode)
                    logger.info(f"Updated {anime.title} to episode {episode}")

                    await websocket.send(
                        json.dumps(
                            {"type": "progress_updated", "anime_id": anime.id, "episode": episode}
                        )
                    )
                break

        # Clean up session
        del self.watching_sessions[session_id]

    async def handler(self, websocket):
        """Main WebSocket handler."""
        await self.register(websocket)
        try:
            async for message in websocket:
                await self.handle_message(websocket, message)
        finally:
            await self.unregister(websocket)

    def start(self):
        """Start the WebSocket server in a background thread."""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._run_server)
        self.thread.daemon = True
        self.thread.start()
        logger.info(f"WebSocket server starting on port {self.port}")

    def _run_server(self):
        """Run the server in a thread."""

        async def serve():
            async with websockets.serve(
                self.handler, "localhost", self.port, ping_interval=20, ping_timeout=10
            ) as server:
                self.server = server
                logger.info(f"WebSocket server listening on ws://localhost:{self.port}")
                self.stop_future = asyncio.Future()
                try:
                    await self.stop_future
                except asyncio.CancelledError:
                    pass

        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        try:
            self.loop.run_until_complete(serve())
        except asyncio.CancelledError:
            pass
        finally:
            self.loop.close()

    def stop(self):
        """Stop the WebSocket server."""
        if not self.running:
            return

        self.running = False

        if self.loop and self.stop_future:
            self.loop.call_soon_threadsafe(self.stop_future.cancel)

        if self.thread:
            self.thread.join(timeout=5)

        logger.info("WebSocket server stopped")

    def broadcast_update(self, message: Dict):
        """Broadcast a message to all connected clients."""
        if not self.clients:
            return

        message_json = json.dumps(message)

        # Schedule broadcast in the event loop
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self._broadcast(message_json), self.loop)

    async def _broadcast(self, message: str):
        """Internal broadcast implementation."""
        if self.clients:
            await asyncio.gather(
                *[client.send(message) for client in self.clients], return_exceptions=True
            )
