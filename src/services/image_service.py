"""Image handling service for anime cover images"""

import hashlib
import logging
import threading
import time
from io import BytesIO
from pathlib import Path
from typing import Optional, Tuple

import requests
from PIL import Image

logger = logging.getLogger(__name__)


class ImageService:
    """Service for downloading and caching anime cover images"""

    def __init__(self, cache_dir: Path):
        """Initialize image service

        Args:
            cache_dir: Directory for image cache
        """
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.download_queue = []
        self.download_lock = threading.Lock()
        self.is_downloading = False

        # Create placeholder image if it doesn't exist
        self._create_placeholder()

        logger.info(f"Image service initialized with cache: {cache_dir}")

    def _create_placeholder(self):
        """Create a placeholder image for missing covers"""
        placeholder_path = self.cache_dir / "placeholder.png"
        if not placeholder_path.exists():
            # Create a simple gray placeholder image
            img = Image.new("RGB", (225, 320), color=(128, 128, 128))
            img.save(placeholder_path)
            logger.info("Created placeholder image")

    def get_image_path(
        self, image_url: Optional[str], mal_id: Optional[int] = None, callback=None
    ) -> Path:
        """Get local path for an image, downloading if necessary

        Args:
            image_url: URL of the image
            mal_id: MAL ID for naming
            callback: Optional callback to call when download completes

        Returns:
            Path to local image file
        """
        if not image_url:
            return self.cache_dir / "placeholder.png"

        # Generate filename from URL or MAL ID
        if mal_id:
            filename = f"mal_{mal_id}.jpg"
        else:
            url_hash = hashlib.md5(image_url.encode(), usedforsecurity=False).hexdigest()[:8]
            filename = f"cover_{url_hash}.jpg"

        image_path = self.cache_dir / filename

        # Return if already cached
        if image_path.exists():
            return image_path

        # Queue for download with callback
        self.queue_download(image_url, image_path, callback)

        # Return placeholder while downloading
        return self.cache_dir / "placeholder.png"

    def queue_download(self, url: str, target_path: Path, callback=None):
        """Queue an image for download

        Args:
            url: Image URL
            target_path: Where to save the image
            callback: Optional callback to call when download completes
        """
        with self.download_lock:
            # Check if already in queue (compare just url and path)
            urls_paths = [(item[0], item[1]) for item in self.download_queue]
            if (url, target_path) not in urls_paths:
                self.download_queue.append((url, target_path, callback))

        # Start download thread if not running
        if not self.is_downloading:
            thread = threading.Thread(target=self._process_download_queue)
            thread.daemon = True
            thread.start()

    def _process_download_queue(self):
        """Process the download queue in background"""
        self.is_downloading = True

        while True:
            with self.download_lock:
                if not self.download_queue:
                    break
                item = self.download_queue.pop(0)
                url = item[0]
                target_path = item[1]
                callback = item[2] if len(item) > 2 else None

            try:
                self._download_image(url, target_path)
                # Call callback if provided
                if callback:
                    callback(target_path)
                time.sleep(0.5)  # Rate limiting
            except Exception as e:
                logger.error(f"Failed to download image from {url}: {e}")

        self.is_downloading = False

    def _download_image(self, url: str, target_path: Path):
        """Download an image from URL

        Args:
            url: Image URL
            target_path: Where to save the image
        """
        try:
            # Download with timeout
            response = requests.get(url, timeout=10, headers={"User-Agent": "AnimeTracker/0.2.0"})
            response.raise_for_status()

            # Validate it's an image
            img = Image.open(BytesIO(response.content))

            # Resize if too large (max 450x640)
            if img.width > 450 or img.height > 640:
                img.thumbnail((450, 640), Image.Resampling.LANCZOS)

            # Save as JPEG
            img.convert("RGB").save(target_path, "JPEG", quality=85)
            logger.info(f"Downloaded image: {target_path.name}")

        except Exception as e:
            logger.error(f"Image download failed: {e}")
            raise

    def download_image_sync(self, url: str, mal_id: Optional[int] = None) -> Optional[Path]:
        """Download an image synchronously

        Args:
            url: Image URL
            mal_id: MAL ID for naming

        Returns:
            Path to downloaded image or None if failed
        """
        if not url:
            return None

        # Generate filename
        if mal_id:
            filename = f"mal_{mal_id}.jpg"
        else:
            url_hash = hashlib.md5(url.encode(), usedforsecurity=False).hexdigest()[:8]
            filename = f"cover_{url_hash}.jpg"

        target_path = self.cache_dir / filename

        # Return if already cached
        if target_path.exists():
            return target_path

        # Download synchronously
        try:
            self._download_image(url, target_path)
            return target_path
        except Exception:
            return None

    def clear_cache(self):
        """Clear all cached images except placeholder"""
        count = 0
        for image_file in self.cache_dir.glob("*.jpg"):
            try:
                image_file.unlink()
                count += 1
            except Exception as e:
                logger.error(f"Failed to delete {image_file}: {e}")

        logger.info(f"Cleared {count} cached images")
        return count

    def get_cache_size(self) -> Tuple[int, int]:
        """Get cache statistics

        Returns:
            Tuple of (file_count, total_size_bytes)
        """
        count = 0
        total_size = 0

        for image_file in self.cache_dir.glob("*.jpg"):
            count += 1
            total_size += image_file.stat().st_size

        return count, total_size

    def refresh_image(self, image_url: str, mal_id: Optional[int] = None) -> Optional[Path]:
        """Force refresh an image

        Args:
            image_url: Image URL
            mal_id: MAL ID for naming

        Returns:
            Path to refreshed image or None if failed
        """
        if not image_url:
            return None

        # Generate filename
        if mal_id:
            filename = f"mal_{mal_id}.jpg"
        else:
            url_hash = hashlib.md5(image_url.encode(), usedforsecurity=False).hexdigest()[:8]
            filename = f"cover_{url_hash}.jpg"

        target_path = self.cache_dir / filename

        # Delete existing
        if target_path.exists():
            try:
                target_path.unlink()
            except Exception as e:
                logger.error(f"Failed to delete old image: {e}")

        # Download fresh
        return self.download_image_sync(image_url, mal_id)
