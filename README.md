# Mirenku

[![Version](https://img.shields.io/badge/version-0.3.0-blue.svg)](https://github.com/Aeturnis-Development-Labs-LLC/mirenku/releases)
[![License](https://img.shields.io/badge/license-Prosperity%203.0-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-80%20passing-brightgreen.svg)](tests/)

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

### 🚀 Planned Features
- 🔄 Custom protocol handler for improved OAuth2 (v0.4.0)
- 🔄 Browser extension for streaming service integration
- 🔄 Advanced statistics and analytics
- 🔄 Dark/Light theme support
- 🔄 Cloud backup options

## 📦 Installation

### Option 1: Run from Source

1. **Clone the repository:**
```bash
git clone https://github.com/Aeturnis-Development-Labs-LLC/mirenku.git
cd mirenku
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Run the application:**
```bash
python src/main.py
```

### Option 2: Windows Executable (Coming Soon)

Download the latest `.exe` file from the [Releases](https://github.com/Aeturnis-Development-Labs-LLC/mirenku/releases) page.

## 🔗 MyAnimeList Setup

### Connecting to MAL (Beta - v0.3.0)

1. **Register your MAL app** (one-time setup for developers):
   - Go to https://myanimelist.net/apiconfig
   - Create a new application
   - Set redirect URL to: `http://localhost:8888/callback`
   - Note your Client ID

2. **Connect in the app**:
   - Click the "🔗 Connect MAL" button in the toolbar
   - Your browser will open to MyAnimeList
   - Log in and authorize the application
   - You'll be redirected back to the app

3. **Sync your anime**:
   - Use "Tools → Sync with MAL" to sync your lists
   - Choose Push (upload), Pull (download), or Full sync

**Note**: OAuth2 authentication is currently in beta. Some users may experience issues with the localhost callback. This will be improved in v0.4.0 with a custom protocol handler.

## 🎮 Usage

### Keyboard Shortcuts
- `Ctrl+N` - Add new anime
- `Ctrl+E` - Edit selected anime
- `Delete` - Delete selected anime
- `Ctrl+F` - Focus search box
- `Ctrl+S` - Force save (though auto-save is enabled)

### Quick Actions
- **Double-click** any anime to edit it
- **Right-click** for context menu
- Use **+/-** buttons to quickly update episode count
- Click column headers to sort

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
```

**Test Coverage:** 
- 74 unit tests
- 6 end-to-end tests
- >80% code coverage

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

- **Current Version:** v0.1.0 (Phase 1 Complete)
- **Next Release:** v0.2.0 (MyAnimeList Integration)
- **Test Status:** All 80 tests passing
- **Platform:** Windows (primary), Linux/Mac (experimental)

## 📝 Versioning

We use [Semantic Versioning](http://semver.org/). For available versions, see the [tags on this repository](https://github.com/Aeturnis-Development-Labs-LLC/anime-tracker/tags).

- **v0.1.0** - Local functionality complete ✅
- **v0.2.0** - MyAnimeList integration (planned)
- **v0.3.0** - Synchronization features (planned)
- **v1.0.0** - Production release (planned)

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [MyAnimeList](https://myanimelist.net/) for anime data (future integration)
- [Jikan API](https://jikan.moe/) for unofficial MAL API (planned)
- [Tkinter](https://docs.python.org/3/library/tkinter.html) for the GUI framework
- [SQLite](https://www.sqlite.org/) for local data storage

## 📧 Contact

**Aeturnis Development Labs LLC**
- Website: [https://aeturnis.dev](https://aeturnis.dev)
- Email: projects@aeturnis.dev
- GitHub: [@Aeturnis-Development-Labs-LLC](https://github.com/Aeturnis-Development-Labs-LLC)

## 📚 Documentation

For detailed documentation, development planning, and technical specifications, see the [docs folder](docs/).

---

**Note**: This is an experimental project developed as part of our AI-assisted software development methodology research at Aeturnis Development Labs.