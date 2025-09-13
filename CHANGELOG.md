# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### v0.3.2 (In Progress - Security Hardening Release)

**Release Focus**: Comprehensive security improvements following The Mirenku Way - simple, local, and transparent security without compromising user experience.

**Completion Status**: 50% (4 of 8 major security tasks completed)

#### Completed Security Enhancements
- **CRITICAL**: ✅ Eliminated base64 token storage fallback
  - No automatic fallback to insecure storage
  - Requires explicit user consent for any insecure storage
  - OAuth flow fails safely when secure storage unavailable
  - Added security warning dialogs
  - Automatic migration from insecure to secure storage
  
- **CRITICAL**: ✅ Registry safety checks and backup
  - Check for existing protocol handlers before registration
  - Create registry backups before modifications
  - Safe registration with conflict detection
  - Registry restoration capabilities
  - Prevents accidental overwrites

- **CRITICAL**: ✅ Fixed Windows Credential Manager size limit (1783 error)
  - Implemented split storage for large OAuth tokens
  - Stores refresh token (secret) in keyring, metadata in file
  - Automatic fallback to Fernet encryption when keyring fails
  - Handles MAL's large authorization codes gracefully

#### Improvements
- **UX**: ✅ Silent token refresh at startup
  - No error messages shown for expired tokens at startup
  - Errors only logged when user-initiated actions fail
  - Cleaner startup experience

- **HIGH PRIORITY**: ✅ Token refresh buffer implementation
  - 5-minute proactive refresh before token expiry
  - Prevents authentication failures during operations
  - Concurrent refresh protection with thread locks
  - Network retry logic with exponential backoff
  - Configurable buffer window

- **MEDIUM PRIORITY**: ✅ OAuth state parameter enhancements
  - State parameters now include timestamps
  - 5-minute expiration to prevent replay attacks
  - One-time use enforcement
  - Base64-encoded JSON format
  - Clear error messages for expired states

- **MEDIUM PRIORITY**: ✅ Rate limiting for OAuth operations
  - Maximum 3 authorization attempts per minute
  - Maximum 5 token refresh attempts per minute
  - 5-minute lockout after 5 failed auth attempts
  - Exponential backoff (1s, 2s, 4s, 8s...)
  - Thread-safe implementation with locks

- **MEDIUM PRIORITY**: ✅ Comprehensive error message sanitization
  - Automatic token redaction in logs
  - Client ID partial masking (first 4 chars only)
  - User path anonymization
  - JSON payload sanitization
  - Custom pattern support
  - Logging integration with SanitizedLogHandler

#### Testing & Documentation
- **New Test Coverage**: 54 new security tests added
  - `tests/test_token_refresh_buffer.py` - 13 tests
  - `tests/test_oauth_state_timestamp.py` - 12 tests
  - `tests/test_oauth_rate_limiting.py` - 13 tests
  - `tests/test_error_sanitization.py` - 16 tests
  - All tests passing with comprehensive coverage

- **Security Documentation**:
  - [Token Refresh Buffer](docs/SECURITY_IMPLEMENTATION_TOKEN_REFRESH_BUFFER.md)
  - [OAuth State Timestamps](docs/SECURITY_IMPLEMENTATION_OAUTH_STATE_TIMESTAMP.md)
  - [Rate Limiting](docs/SECURITY_IMPLEMENTATION_RATE_LIMITING.md)
  - [Error Sanitization](docs/SECURITY_IMPLEMENTATION_ERROR_SANITIZATION.md)

#### Pending Security Items
- **CRITICAL**: Remove hardcoded client ID (✅ COMPLETED - now loads from config)
- **LOW PRIORITY**: Enhanced PKCE with 128-char verifier (pending)
- **DOCUMENTATION**: Complete SECURITY.md file (pending)
- **MONITORING**: Security audit logging (pending)
- **ENHANCEMENT**: Token encryption key rotation (pending)
- See [Security TODO](docs/SECURITY_TODO_v0.3.2.md) for full details

### Future Releases
- Browser extension for streaming service integration
- Advanced statistics and analytics
- Themes and customization options
- Cloud synchronization
- AniList integration

## [0.3.1] - 2025-09-09

### Added
- **Custom Protocol Handler (`mirenku://`)**
  - Eliminates localhost:8888 callback issues
  - Automatic registration on first run
  - Works with portable installations
  - Browser returns directly to app
  
- **Enhanced Security**
  - Three-tier token encryption (OS Keyring → Fernet → Base64)
  - PKCE implementation for OAuth2
  - State parameter validation (CSRF protection)
  - Secure token storage with automatic migration
  
- **Improved User Experience**
  - First-run welcome dialog with setup wizard
  - One-click OAuth authentication
  - Automatic token refresh
  - Protocol management in Settings
  - Test protocol button
  
- **Developer Features**
  - 50+ new OAuth tests (81% coverage)
  - Comprehensive OAuth documentation
  - Integration test suite
  - Custom Client ID support

### Changed
- OAuth2 now uses `mirenku://` protocol instead of localhost
- MAL auth dialog uses new `MALOAuth2ProtocolClient`
- Token storage automatically migrates to encrypted format
- Updated README with new OAuth instructions
- Improved error messages throughout

### Fixed
- OAuth callback timeout issues completely resolved
- Token refresh failures during long sync operations
- "Not primary instance" errors with multiple windows
- Protocol registration on Windows 11
- MAL sync hanging on expired tokens
- Auth dialog not closing after successful login
- Settings dialog protocol tab initialization
- Keyboard shortcuts conflict with OAuth dialog

### Security
- Tokens encrypted using OS credential manager when available
- PKCE prevents authorization code interception
- State validation prevents CSRF attacks
- No passwords stored, only encrypted OAuth tokens
- Token leakage prevention in logs

## [0.3.0] - 2025-09-07

### Added
- **MyAnimeList Integration (Phase 2 & 3 Complete)**
  - Full MAL API v2 integration with OAuth2 authentication (PKCE flow)
  - Bidirectional synchronization with MyAnimeList
  - Import anime from MAL search
  - Import full user anime list from MAL
  - Push local changes to MAL
  - Pull updates from MAL
  - Sync queue for offline changes
  
- **MAL Search & Import**
  - Search MAL database directly from app
  - Import anime metadata (synopsis, genres, studios, images)
  - Import user's complete MAL list
  - Auto-populate anime details from MAL
  - Image caching for cover art
  
- **Authentication System**
  - OAuth2 with PKCE implementation
  - Secure token storage
  - Auto-refresh expired tokens
  - MAL authentication dialog
  - Connect/Disconnect from toolbar
  
- **Sync Features**
  - Push to MAL: Upload local changes
  - Pull from MAL: Download MAL updates
  - Full sync: Bidirectional synchronization
  - Conflict detection
  - Sync status indicators
  - Sync history tracking
  
- **API Services**
  - Jikan API integration for public data
  - MAL API v2 for authenticated operations
  - Rate limiting (60 req/min for Jikan)
  - Response caching with TTL
  - Automatic retry logic
  - Token bucket rate limiter
  
- **UI Enhancements**
  - MAL Connect button in toolbar
  - MAL Search dialog with preview
  - Import preview dialog
  - Sync dialog with options
  - MAL status indicators
  - Progress notifications

### Known Issues
- OAuth2 callback may fail on some systems (localhost:8888 redirect issues)
- MAL authentication dialog buttons may appear thin on some displays
- Token exchange occasionally fails requiring retry
- Browser may not auto-close after OAuth2 authorization

### Technical
- Implemented MAL OAuth2 client with PKCE
- Created MAL API v2 service layer
- Added sync service with queue management
- Database schema v2 with sync support
- Image service for cover art management
- Note: Some unit tests need updating for new MAL service API

## [0.1.1] - 2025-09-07

### Added
- **About/Diagnostics Dialog**
  - System information display
  - Application diagnostics
  - Path verification with existence indicators
  - Database statistics
  - Memory usage tracking

### Fixed
- **Version Management**
  - Unified version string across all components (was 0.1.0-dev, now 0.1.1)
  - Dynamic version display in window title and About dialog
  
- **Path Consistency**
  - Unified logging directory with config directory
  - Logs now stored under data directory/logs
  - Consistent path handling across Windows/Linux/Mac
  
- **Code Quality**
  - Removed stray duplicate import in config.py
  - Removed unused ttk import in notifications.py
  - Thread shutdown already properly implemented in MainWindow.on_close
  
- **Data Management**
  - date_added and date_updated now properly set when creating/updating anime
  - Timestamps automatically managed by service layer
  
- **Import/Export**
  - Improved CSV import error messages with row numbers
  - Enhanced JSON import validation with detailed error reporting
  - Better handling of invalid data during import
  - Score validation (0-10 range) during import

### Changed
- Version logging at application startup
- Config now accepts instance for logging setup
- Better error context in import operations

## [0.1.0] - 2025-09-06

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

- **0.3.1** - OAuth2 improvements with custom protocol handler (mirenku://)
- **0.3.0** - MyAnimeList integration with OAuth2 and full synchronization (Phase 2 & 3 complete)
- **0.1.1** - Bug fixes and improvements based on v0.1.0 feedback  
- **0.1.0** - Initial release with core local functionality (Phase 1)
- **0.4.0** - (Planned) Browser extension and advanced features
- **1.0.0** - (Planned) Production-ready release with streaming integration

[Unreleased]: https://github.com/Aeturnis-Development-Labs-LLC/anime-tracker/compare/v0.3.1...HEAD
[0.3.1]: https://github.com/Aeturnis-Development-Labs-LLC/anime-tracker/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/Aeturnis-Development-Labs-LLC/anime-tracker/compare/v0.1.1...v0.3.0
[0.1.1]: https://github.com/Aeturnis-Development-Labs-LLC/anime-tracker/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/Aeturnis-Development-Labs-LLC/anime-tracker/releases/tag/v0.1.0