# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- MyAnimeList.net integration
- Advanced statistics and analytics
- Themes and customization options
- Cloud synchronization

## [0.1.0] - 2025-01-20

### Added
- **Core Features**
  - Full CRUD operations for anime entries
  - Add new anime with title, status, episodes, score, and notes
  - Edit existing anime entries
  - Delete anime with confirmation dialog
  - Mark anime as completed (auto-updates episode count)
  
- **Episode Tracking**
  - Track watched episodes vs total episodes
  - Quick increment/decrement buttons in list view
  - Progress bar visualization
  - Auto-complete when reaching total episodes
  
- **Status Management**
  - Five status types: Watching, Completed, On Hold, Dropped, Plan to Watch
  - Filter anime by status
  - Status counts in status bar
  
- **Search & Filter**
  - Real-time search across title and notes
  - Filter by status with dropdown
  - Sort by any column (title, episodes, status, score)
  - Persistent sort preferences
  
- **Data Management**
  - SQLite database for local storage
  - Auto-save on all changes
  - Import/Export to JSON format
  - Import/Export to CSV format
  - Automatic backup creation
  - Backup restoration functionality
  
- **User Interface**
  - Clean Tkinter-based GUI
  - Sortable table/list view
  - Add/Edit dialog with validation
  - Status bar with statistics
  - Toast notifications for user feedback
  - Error handling with user-friendly messages
  
- **Quality of Life**
  - Keyboard shortcuts (Ctrl+N, Ctrl+E, Delete, Ctrl+F, Ctrl+S)
  - Window state persistence (size, position, filters)
  - Settings persistence
  - Right-click context menu
  - Double-click to edit
  
- **Testing**
  - 74 unit tests covering all components
  - 6 comprehensive end-to-end tests
  - Performance testing with 100+ entries
  - Test coverage >80%

### Technical Details
- Python 3.11+ support
- Repository pattern for data access
- Service layer for business logic
- Comprehensive error handling
- Thread-safe auto-save system
- Efficient caching for performance
- Cross-platform compatibility (Windows focus)
- PyInstaller build support for standalone executable

---

## Version History

- **0.1.0** - Initial release with core local functionality (Phase 1)
- **0.2.0** - (Planned) MyAnimeList integration (Phase 2)
- **0.3.0** - (Planned) Synchronization features (Phase 3)
- **1.0.0** - (Planned) Production-ready release (Phase 4)

[Unreleased]: https://github.com/Aeturnis-Development-Labs-LLC/anime-tracker/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Aeturnis-Development-Labs-LLC/anime-tracker/releases/tag/v0.1.0