# Mirenku

[![CI/CD](https://github.com/Aeturnis-Development-Labs-LLC/mirenku/actions/workflows/ci.yml/badge.svg)](https://github.com/Aeturnis-Development-Labs-LLC/mirenku/actions/workflows/ci.yml)
[![Tests](https://github.com/Aeturnis-Development-Labs-LLC/mirenku/actions/workflows/cross-platform-test.yml/badge.svg)](https://github.com/Aeturnis-Development-Labs-LLC/mirenku/actions/workflows/cross-platform-test.yml)
[![codecov](https://codecov.io/gh/Aeturnis-Development-Labs-LLC/mirenku/branch/main/graph/badge.svg)](https://codecov.io/gh/Aeturnis-Development-Labs-LLC/mirenku)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/Aeturnis-Development-Labs-LLC/mirenku/main.svg)](https://results.pre-commit.ci/latest/github/Aeturnis-Development-Labs-LLC/mirenku/main)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

[![Version](https://img.shields.io/badge/version-0.3.2-blue.svg)](https://github.com/Aeturnis-Development-Labs-LLC/mirenku/releases)
[![License](https://img.shields.io/badge/license-Prosperity%203.0-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/Windows-Stable-green)](https://github.com/Aeturnis-Development-Labs-LLC/mirenku)
[![Platform](https://img.shields.io/badge/macOS%20%7C%20Linux-Experimental-yellow)](https://github.com/Aeturnis-Development-Labs-LLC/mirenku)

A powerful desktop application for tracking your anime viewing progress with MyAnimeList integration and synchronization.

## 🎯 Features

### ✅ Core Features
- **Full CRUD Operations** - Add, edit, delete, and manage your anime list
- **Episode Tracking** - Track watched episodes with quick increment/decrement buttons
- **Status Management** - Organize with 5 status types (Watching, Completed, On Hold, Dropped, Plan to Watch)
- **Search & Filter** - Real-time search and status filtering
- **Scoring System** - Rate anime on a 1-10 scale
- **Import/Export** - Backup and share your list in JSON or CSV format
- **Auto-Save** - Never lose your progress with automatic saving
- **Keyboard Shortcuts** - Quick access to common actions
- **Statistics** - View your watching statistics at a glance

### 🌐 MyAnimeList Integration (v0.3.0)
- **MAL Search** - Search and import anime directly from MyAnimeList
- **OAuth2 Authentication** - Secure connection to your MAL account
- **Bidirectional Sync** - Push local changes to MAL and pull updates
- **Import MAL List** - Import your entire MAL anime list
- **Metadata Enrichment** - Auto-populate anime details from MAL
- **Cover Art** - Download and cache anime cover images
- **Offline Queue** - Queue changes when offline, sync when connected

### 🚀 New in v0.3.0
- ✅ **Custom Protocol Handler** - Seamless OAuth2 with `mirenku://` protocol
- ✅ **Secure Token Storage** - Three-tier encryption for credentials
- ✅ **First-Run Experience** - Automatic setup wizard
- ✅ **PKCE Security** - Industry-standard OAuth2 security
- ✅ **Auto Token Refresh** - Never re-authenticate manually

### 🔮 Planned Features
- 🔄 Browser extension for streaming service integration
- 🔄 Advanced statistics and analytics
- 🔄 Dark/Light theme support
- 🔄 Cloud backup options

## 🔒 Privacy

Mirenku is local-first. Your list lives in a SQLite database on your
computer; there is no cloud storage, no account requirement, no telemetry,
and no analytics. With no MAL account connected and update checking off
(the default), the app makes **zero** network requests.

The complete list of hosts Mirenku can ever contact:

| Host | When |
|---|---|
| `myanimelist.net` / `api.myanimelist.net` | Only after you connect a MAL account |
| MAL image CDN | Cover art, when MAL features are used |
| `api.jikan.moe` (Jikan, a third-party MAL API mirror) | Unauthenticated search / public-list import |
| `api.github.com` | Update check — off by default, opt-in |

See [SECURITY.md](SECURITY.md) for the full disclosure, including token
storage trade-offs.

## 📦 Installation

### Windows (Stable)
1. Download `mirenku_v*_windows.zip` from the [Releases](https://github.com/Aeturnis-Development-Labs-LLC/mirenku/releases) page
2. Extract the ZIP file
3. Run `mirenku.exe`

### macOS (Experimental)
**⚠️ Note: macOS support is experimental and may have issues**
1. Download `mirenku_v*_macos.dmg` from the [Releases](https://github.com/Aeturnis-Development-Labs-LLC/mirenku/releases) page
2. Open the DMG and drag Mirenku to your Applications folder
3. On first run, you may need to right-click and select "Open" to bypass Gatekeeper

### Linux (Experimental)
**⚠️ Note: Linux support is experimental and may have issues**

#### AppImage (Recommended)
1. Download `Mirenku-*-x86_64.AppImage` from the [Releases](https://github.com/Aeturnis-Development-Labs-LLC/mirenku/releases) page
2. Make it executable: `chmod +x Mirenku-*.AppImage`
3. Run it: `./Mirenku-*.AppImage`

#### Tarball
1. Download `mirenku_v*_linux_x64.tar.gz` from the [Releases](https://github.com/Aeturnis-Development-Labs-LLC/mirenku/releases) page
2. Extract: `tar -xzf mirenku_v*_linux_x64.tar.gz`
3. Install: `cd mirenku_v*_linux_x64 && sudo ./install.sh`

### Run from Source (All Platforms)
1. Clone the repository:
```bash
git clone https://github.com/Aeturnis-Development-Labs-LLC/mirenku.git
cd mirenku
```
2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. Run the application:
```bash
python src/main.py
```

## 🔗 MyAnimeList Setup

### Quick Connect (v0.3.0+)

1. **First Launch**:
   - Mirenku will show a welcome dialog on first run
   - Check "Register protocol handler" for seamless OAuth
   - Click "Continue" to set up

2. **Connect to MyAnimeList**:
   - Click **File → Connect to MAL** or press `Ctrl+Shift+M`
   - Click "Connect to MAL" button
   - Your browser opens to MyAnimeList
   - Log in and authorize Mirenku
   - You're automatically returned to the app - no copying codes!

3. **Sync Your Anime**:
   - Use **Tools → Sync with MAL** to sync your lists
   - Choose Push (upload), Pull (download), or Full sync
   - Tokens refresh automatically - authenticate once, sync forever

### Security Features
- **No Password Storage** - Only secure OAuth tokens
- **Encrypted Tokens** - Three-tier encryption (OS Keyring → Fernet → Base64)
- **PKCE Protection** - Prevents authorization code interception
- **Automatic Refresh** - Tokens refresh seamlessly in background

### Advanced Setup (Optional)
For developers wanting to use their own Client ID:
1. Register at [MAL API Config](https://myanimelist.net/apiconfig)
2. Set redirect URL to: `mirenku://auth`
3. Enter your Client ID in Settings → MyAnimeList

## 🎮 Usage

### Keyboard Shortcuts
- `Ctrl+N` - Add new anime
- `Ctrl+E` - Edit selected anime
- `Delete` - Delete selected anime
- `Ctrl+F` - Focus search box
- `Ctrl+S` - Force save (though auto-save is enabled)
- `Ctrl+Shift+M` - Open MAL connection dialog
- `Ctrl+,` - Open Settings

### Quick Actions
- **Double-click** any anime to edit it
- **Right-click** for context menu
- Use **+/-** buttons to quickly update episode count
- Click column headers to sort

## 🔧 Troubleshooting

### Common Issues

**Browser doesn't open when connecting to MAL:**
- Check your default browser settings
- Try manually copying the URL from the logs
- Ensure no firewall is blocking the browser

**"Protocol not registered" error:**
- Open Settings → Protocol tab
- Click "Register Protocol"
- Restart Mirenku

**OAuth fails after moving Mirenku to new folder:**
- Launch Mirenku from the new location
- Accept the prompt to update protocol registration
- Reconnect to MAL if needed

**"Not primary instance" error:**
- Close all Mirenku windows
- Check Task Manager for lingering processes
- Restart Mirenku

**Token expired errors:**
- Mirenku should auto-refresh tokens
- If it fails, disconnect and reconnect in Settings

For more detailed troubleshooting, see [OAuth User Guide](docs/OAUTH_USER_GUIDE.md).

## 🛠️ Development

### Project Structure
```
anime-tracker/
├── src/                # Source code
│   ├── main.py        # Application entry point
│   ├── ui/            # User interface components
│   ├── models/        # Data models and database
│   ├── services/      # Business logic
│   └── utils/         # Utilities (config, persistence, notifications)
├── tests/             # Test suite (80 tests)
├── assets/            # Images and icons
├── docs/              # Documentation
└── build.py          # Build script for executable
```

### Running Tests

```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python tests/test_end_to_end.py

# Run with coverage
python -m pytest tests/ --cov=src

# Run OAuth tests specifically
python -m pytest tests/test_mal_oauth2_protocol*.py tests/test_integration_oauth.py
```

**Test Coverage:**
- 150+ unit tests
- 11 integration tests
- 6 end-to-end tests
- 81% OAuth module coverage
- >75% overall code coverage

### Building Executable

To create a standalone Windows executable:

```bash
python build.py
```

Or manually with PyInstaller:

```bash
pyinstaller --onefile --windowed --icon=assets/icon.ico --name "AnimeTracker" src/main.py
```

## 🤝 Contributing

We welcome contributions! Here's how you can help:

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📊 Project Status

- **Current Version:** v0.3.2 (Security Enhancements & UI Improvements)
- **Test Status:** 150+ tests passing (81% OAuth coverage)
- **Platform Support:**
  - **Windows:** ✅ Stable (Primary platform)
  - **macOS:** ⚠️ Experimental (Build available, limited testing)
  - **Linux:** ⚠️ Experimental (AppImage/tarball available, limited testing)

## 📝 Versioning

We use [Semantic Versioning](http://semver.org/). For available versions, see the [tags on this repository](https://github.com/Aeturnis-Development-Labs-LLC/anime-tracker/tags).

- **v0.1.0** - Local functionality complete ✅
- **v0.2.0** - MyAnimeList integration ✅
- **v0.3.0** - OAuth2 with custom protocol handler ✅
- **v0.3.1** - OAuth2 improvements with custom protocol handler ✅
- **v0.3.2** - Security enhancements & UI improvements ✅
- **v1.0.0** - Production release (planned)

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [MyAnimeList](https://myanimelist.net/) for anime data and OAuth2 API
- [Tkinter](https://docs.python.org/3/library/tkinter.html) for the GUI framework
- [SQLite](https://www.sqlite.org/) for local data storage
- [Cryptography](https://cryptography.io/) for secure token storage
- [Keyring](https://pypi.org/project/keyring/) for OS credential management

## 📧 Contact

**Aeturnis Development Labs LLC**
- Website: [https://aeturnis.dev](https://aeturnis.dev)
- Email: projects@aeturnis.dev
- GitHub: [@Aeturnis-Development-Labs-LLC](https://github.com/Aeturnis-Development-Labs-LLC)

## 📚 Documentation

For detailed documentation, development planning, and technical specifications, see the [docs folder](docs/).

---

**Note**: This is an experimental project developed as part of our AI-assisted software development methodology research at Aeturnis Development Labs.
