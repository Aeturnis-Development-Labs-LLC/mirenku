#!/usr/bin/env python
"""Quick user workflow test for CI - The Mirenku Way"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models.database import Database
from services.anime_service import AnimeService

def test_basic_user_workflow():
    """Test that basic user operations work"""

    # Initialize
    db = Database(':memory:')
    db.initialize()
    service = AnimeService(db)

    # User adds an anime
    result = service.add_anime('Test Anime', status='Watching')
    # add_anime returns (success, message, anime_id)
    success, message, anime_id = result
    assert success, f"Failed to add anime: {message}"

    anime = service.get_anime(anime_id)
    assert anime is not None, "Failed to get anime"
    print(f'[OK] User can add anime: {anime.title}')

    # User tracks progress
    service.increment_episode(anime_id)
    anime = service.get_anime(anime_id)
    assert anime.episodes_watched == 1, "Failed to track progress"
    print('[OK] User can track progress')

    # User completes anime
    service.update_anime(anime_id, status='Completed')
    anime = service.get_anime(anime_id)
    assert anime.status == 'Completed', "Failed to complete anime"
    print('[OK] User can complete anime')

    # User can list their anime
    all_anime = service.get_all_anime()
    assert len(all_anime) == 1, "Failed to list anime"
    print('[OK] User can see their anime list')

    print('\n[SUCCESS] Basic user operations work!')
    return True

if __name__ == '__main__':
    try:
        success = test_basic_user_workflow()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f'[FAIL] Test failed: {e}')
        sys.exit(1)