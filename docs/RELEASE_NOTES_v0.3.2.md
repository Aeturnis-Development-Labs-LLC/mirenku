# Mirenku v0.3.2 Release Notes

**Release Date**: September 13, 2025
**Version**: 0.3.2
**Codename**: "Security Hardening & Quality Release"

## 🎉 Overview

Mirenku v0.3.2 brings comprehensive security enhancements, UI improvements, and robust development infrastructure. This release focuses on hardening the OAuth2 implementation, improving the user experience, and establishing professional development practices.

## 🔐 Security Enhancements

### OAuth2 Hardening
- **Token Refresh Buffer**: 5-minute buffer prevents edge-case authentication failures
- **State Parameter Expiration**: 10-minute expiration for enhanced security
- **Enhanced PKCE**: SHA256 with cryptographically secure random generation
- **Token Storage**: Automatic encryption key rotation every 90 days

### API Protection
- **Rate Limiting**: Intelligent rate limiting with exponential backoff
- **Error Sanitization**: Comprehensive sanitization prevents information leakage
- **Security Audit Logging**: Complete audit trail with privacy protection

### Documentation
- **SECURITY.md**: Comprehensive security documentation and vulnerability reporting

## 🎨 User Interface Improvements

### Visual Enhancements
- **Zebra Striping**: Alternating row colors using Mirenku's signature teal palette
- **Platform Fonts**: Automatic selection (Segoe UI/Windows, SF Pro/macOS, Noto Sans/Linux)
- **Synopsis Display**: Prominent 10-line box near top of detail dialog

### Functionality
- **Column Sorting**: Click any column header to sort the anime list
- **Hidden ID Column**: More space for anime titles
- **Auto-Refresh**: Intelligent database monitoring with debouncing

## 🔧 Bug Fixes

### MAL Synchronization
- Fixed SQLite thread safety issues
- Fixed missing episode counts in API requests
- Proper NULL handling for total_episodes field
- Optimized pull operation performance
- Fixed "Plan to Watch" status synchronization

## 🛠️ Development Infrastructure

### Code Quality
- **Ruff Integration**: Python linting and formatting (2000+ issues resolved)
- **Pre-commit Hooks**: Automated quality checks on every commit
- **CI/CD Pipeline**: Cross-platform testing via GitHub Actions
- **Code Coverage**: Automated reporting with Codecov

### Testing
- 105+ security-focused tests
- Cross-platform compatibility suite
- Python 3.8-3.11 support
- 80%+ code coverage maintained

## 📦 Installation

### Windows
1. Download `mirenku_v0.3.2_windows.zip`
2. Extract to desired location
3. Run `mirenku.exe`

### From Source
```bash
git clone https://github.com/yourusername/mirenku.git
cd mirenku
pip install -r requirements.txt
python src/main.py
```

## ⚡ Quick Start

1. **First Launch**: Automatic setup wizard guides you through initial configuration
2. **MAL Connection**: Click "Connect MAL" in the toolbar for one-click authentication
3. **Sync**: Use the sync button to keep your local and MAL lists synchronized

## 🐛 Known Issues

- MAL OAuth2 callback occasionally requires manual browser refresh
- Some Unicode characters in anime titles may display incorrectly on Windows
- First sync with large MAL lists (500+ anime) may take several minutes

## 🔄 Upgrade Notes

### From v0.3.1
- Tokens will be automatically migrated to the new encryption system
- First launch may prompt for secure storage permission
- Settings and database are fully compatible

### From v0.3.0 or earlier
- Backup your database before upgrading
- Re-authenticate with MAL for enhanced security features
- Review settings for new options

## 🙏 Acknowledgments

Thank you to all users who provided feedback and bug reports. Special thanks to the testers who helped validate the security enhancements.

## 📝 License

Mirenku is released under the Prosperity License 3.0. See LICENSE file for details.

## 🔗 Links

- **GitHub**: [https://github.com/yourusername/mirenku](https://github.com/yourusername/mirenku)
- **Issues**: [Report bugs or request features](https://github.com/yourusername/mirenku/issues)
- **Website**: [https://mirenku.com](https://mirenku.com)

---

*Mirenku - Track your anime journey with simplicity and privacy*
