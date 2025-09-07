# Anime Tracker

[![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)](https://github.com/Aeturnis-Development-Labs-LLC/anime-tracker/releases)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-80%20passing-brightgreen.svg)](tests/)

A simple, offline-first desktop application for tracking your anime viewing progress.

## 🎯 Features

### ✅ Completed (v0.1.0)
- **Full CRUD Operations** - Add, edit, delete, and manage your anime list
- **Episode Tracking** - Track watched episodes with quick increment/decrement buttons
- **Status Management** - Organize with 5 status types (Watching, Completed, On Hold, Dropped, Plan to Watch)
- **Search & Filter** - Real-time search and status filtering
- **Scoring System** - Rate anime on a 1-10 scale
- **Import/Export** - Backup and share your list in JSON or CSV format
- **Auto-Save** - Never lose your progress with automatic saving
- **Keyboard Shortcuts** - Quick access to common actions
- **Statistics** - View your watching statistics at a glance
- **Data Persistence** - SQLite database for reliable local storage
- **Error Handling** - User-friendly notifications and error messages

### 🚀 Planned (v0.2.0+)
- 🔄 MyAnimeList (MAL) integration
- 🔄 Two-way synchronization with MAL
- 🔄 Advanced statistics and analytics
- 🔄 Dark/Light theme support
- 🔄 Cloud backup options

## 📦 Installation

### Option 1: Run from Source

1. **Clone the repository:**
```bash
git clone https://github.com/Aeturnis-Development-Labs-LLC/anime-tracker.git
cd anime-tracker
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

Download the latest `.exe` file from the [Releases](https://github.com/Aeturnis-Development-Labs-LLC/anime-tracker/releases) page.

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