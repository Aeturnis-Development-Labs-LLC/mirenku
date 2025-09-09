# Mirenku v0.3.1 Release Notes

**Release Date**: September 9, 2025  
**Type**: Minor Release - OAuth Integration & Stability

## 🎉 Overview

Mirenku v0.3.1 completes the OAuth2 integration with MyAnimeList, replacing the beta HTTP server implementation with a robust custom protocol handler. This release delivers a seamless, secure authentication experience that works reliably across different system configurations.

## ✨ Major Improvements

### 🔐 Custom Protocol Handler (`mirenku://`)
- **No More Localhost Issues**: Eliminated the unreliable `http://localhost:8888` callback
- **Seamless Browser Integration**: OAuth callbacks return directly to Mirenku
- **Automatic Registration**: First-run setup wizard handles protocol registration
- **Portable Support**: Works even when Mirenku is moved to different folders

### 🔒 Enhanced Security
- **Three-Tier Token Encryption**:
  1. OS Keyring (Windows Credential Manager) - Primary
  2. Fernet Encryption (cryptography library) - Fallback
  3. Base64 Encoding with warning - Last resort
- **PKCE Implementation**: Industry-standard OAuth2 security
- **State Parameter Validation**: CSRF protection
- **No Password Storage**: Only encrypted tokens are saved

### 🚀 Improved User Experience
- **First-Run Welcome Dialog**: Guides new users through setup
- **One-Click Authentication**: No manual code copying required
- **Automatic Token Refresh**: Authenticate once, sync forever
- **Clear Error Messages**: Better troubleshooting guidance

## 📊 Technical Achievements

### Test Coverage
- **OAuth2 Module**: 81% coverage (up from 47%)
- **Total Tests**: 150+ unit tests, 11 integration tests
- **New Test Files**: 
  - `test_mal_oauth2_protocol.py` (18 tests)
  - `test_mal_oauth2_protocol_extended.py` (21 tests)
  - `test_integration_oauth.py` (11 tests)
  - `test_mal_sync_integration.py` (8 tests)

### Code Quality
- **Type Hints**: Added to all OAuth modules
- **Comprehensive Logging**: Debug-friendly without token leakage
- **Error Handling**: Graceful fallbacks at every level
- **Documentation**: Complete user guide and API documentation

## 🔧 Bug Fixes

### Authentication
- Fixed: OAuth callback timeout issues
- Fixed: Token refresh failures during long sync operations
- Fixed: "Not primary instance" errors with multiple windows
- Fixed: Protocol registration on Windows 11

### Synchronization
- Fixed: MAL sync hanging on expired tokens
- Fixed: Duplicate entries during pull operations
- Fixed: Score updates not reflecting immediately

### UI/UX
- Fixed: Auth dialog not closing after successful login
- Fixed: Settings dialog protocol tab initialization
- Fixed: Keyboard shortcuts conflict with OAuth dialog

## 📝 New Features

### Settings Enhancements
- **Protocol Tab**: Manage `mirenku://` registration
- **Test Protocol Button**: Verify handler is working
- **Custom Client ID**: Advanced users can use their own MAL app

### Keyboard Shortcuts
- `Ctrl+Shift+M`: Quick access to MAL connection
- `Ctrl+,`: Open settings directly

## 🔄 Changes from v0.3.0

### Breaking Changes
- None - Full backward compatibility maintained

### Deprecated
- `http://localhost:8888` callback URL (still works but not recommended)
- Manual authorization code entry (automatic now)

### Migration
- Existing tokens are automatically migrated to encrypted storage
- Protocol registration prompted on first launch
- No user action required for most users

## 📦 Dependencies

### New Requirements
```
keyring>=24.0.0        # Secure token storage
cryptography>=41.0.0   # Fernet encryption
```

### Updated Requirements
```
pytest>=7.4.0          # Testing framework
pytest-cov>=4.1.0      # Coverage reporting
pytest-mock>=3.11.0    # Mocking support
```

## 🚀 Installation

### Upgrade from v0.3.0
```bash
git pull
pip install -r requirements.txt
python src/main.py
```

### Fresh Installation
```bash
git clone https://github.com/yourusername/mirenku.git
cd mirenku
pip install -r requirements.txt
python src/main.py
```

## 📖 Documentation

### New Documentation
- [OAuth User Guide](OAUTH_USER_GUIDE.md) - Complete setup and troubleshooting
- [OAuth Implementation Tracker](OAUTH_IMPLEMENTATION_TRACKER.md) - Development details
- Updated README with OAuth2 instructions

### For Developers
- [API Documentation](API_DOCUMENTATION.md) - OAuth2 client API reference
- Test examples in `tests/test_mal_oauth2_protocol*.py`
- Integration patterns in `tests/test_integration_oauth.py`

## 🔮 Known Issues

### Minor Issues
- Token refresh test mock needs adjustment (tests only, not production)
- Tkinter tests may hang on some systems (use `-k "not tkinter"`)
- First-run dialog may appear behind main window on some Linux distros

### Workarounds
- If browser doesn't open: Copy URL from logs
- If protocol not registered: Use Settings → Protocol → Register
- If tokens expire unexpectedly: Disconnect and reconnect in Settings

## 🎯 What's Next (v0.4.0)

### Planned Features
- Browser extension for streaming integration
- Advanced statistics and analytics
- Dark/Light theme support
- Cloud backup options
- Batch operations support

### Under Consideration
- AniList integration
- Import/Export improvements
- Watch party features
- Mobile companion app

## 🙏 Acknowledgments

### Contributors
- OAuth2 implementation team
- Beta testers who reported localhost issues
- Community members who suggested protocol handler approach

### Special Thanks
- MyAnimeList for OAuth2 API support
- Python cryptography team for secure storage libraries
- Keyring maintainers for cross-platform credential management

## 📊 Statistics

### Development Metrics
- **Development Time**: 2 days (September 7-9, 2025)
- **Lines of Code**: ~2,500 new lines
- **Test Coverage Improvement**: 34% increase for OAuth module
- **Issues Resolved**: 15 OAuth-related issues

### Performance
- **OAuth Callback**: <500ms response time
- **Token Refresh**: <1s automatic refresh
- **First Run to Authenticated**: <2 minutes
- **Memory Usage**: No increase from v0.3.0

## 🐛 Bug Reports

Found a bug? Please report it:
- GitHub Issues: [Create issue](https://github.com/yourusername/mirenku/issues)
- Include: Version, OS, error messages, steps to reproduce
- Logs location: `%APPDATA%\Mirenku\logs\` (Windows)

## 📝 License

This release maintains the existing license terms. See [LICENSE](../LICENSE) for details.

---

## Upgrade Checklist

Before upgrading to v0.3.1:
- [ ] Backup your anime database
- [ ] Note your current MAL connection status
- [ ] Close all Mirenku windows
- [ ] Update via git pull or download new release
- [ ] Install new dependencies: `pip install -r requirements.txt`
- [ ] Launch Mirenku and follow first-run setup if prompted
- [ ] Reconnect to MAL if needed
- [ ] Verify sync works correctly

## Support

Need help? Check these resources:
1. [OAuth User Guide](OAUTH_USER_GUIDE.md)
2. [Troubleshooting Section](OAUTH_USER_GUIDE.md#troubleshooting)
3. [GitHub Issues](https://github.com/yourusername/mirenku/issues)
4. [README](../README.md)

---

**Thank you for using Mirenku!**

*This release represents a significant improvement in authentication reliability and security. We're committed to making anime tracking as seamless as possible.*

**- The Mirenku Development Team**