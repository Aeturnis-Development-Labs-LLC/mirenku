# Mirenku Feature Roadmap
*Following "The Mirenku Way" - Simple, Private, User-Owned*

## Development Philosophy
**No deadlines, no pressure. Features ship when they're ready.**

---

## v0.4.0 - "Auto-Scrobbling & BYOC Update"
**Focus: Automatic Progress Tracking + Bring Your Own Cloud**

### Core Features
- [ ] **Browser Extension for Streaming**
  - Lightweight extension (< 100KB)
  - Support for: Crunchyroll, Netflix, Hulu, HiDive, Funimation
  - Local-only communication via WebSocket
  - Auto-detect episode/series from page
  - Queue updates when Mirenku is closed

- [ ] **System Tray Mode**
  - Minimize to system tray
  - Quick access menu
  - "Now Watching" indicator
  - Pause/resume tracking
  - Quick episode increment buttons

- [ ] **Local Media Scrobbling**
  - VLC plugin/integration
  - MPV support
  - Plex server detection
  - Watch folder monitoring
  - Smart filename parsing

- [ ] **BYOC (Bring Your Own Cloud)**
  - Use any cloud storage you already have
  - Dropbox, Google Drive, OneDrive, iCloud support
  - Git-based sync for advanced users
  - Network share support (SMB, WebDAV)
  - Self-hosted options (Syncthing, NextCloud)
  - Zero Mirenku infrastructure - your cloud, your data

- [ ] **Conflict Resolution**
  - Simple merge dialog when local/MAL differ
  - Multi-device sync conflict handling
  - Preview changes before applying
  - Rollback option

---

## v0.5.0 - "Data Control Update"
**Focus: Better Data Management & Portability**

### Core Features
- [ ] **Versioned Backups**
  - Timeline saves with restore points
  - Diff viewer to see changes
  - Auto-backup before major operations

- [ ] **Portable Mode**
  - Fully self-contained folder
  - USB stick friendly
  - No registry/system modifications
  - Settings migration tool

- [ ] **Custom Tags & Labels**
  - User-defined tags (favorites, rewatch, etc.)
  - Tag-based filtering
  - Bulk tag operations
  - Export tags with data

- [ ] **Enhanced Import/Export**
  - AniList support
  - Kitsu integration
  - Universal anime format
  - Batch import from multiple sources

---

## v0.6.0 - "Power User Update"
**Focus: Efficiency for Heavy Users**

### Core Features
- [ ] **Keyboard-First Navigation**
  - Vim-style shortcuts
  - Command palette (Ctrl+K)
  - Quick add via hotkey
  - Navigate without mouse

- [ ] **Batch Operations**
  - Multi-select mode
  - Bulk status changes
  - Mass score updates
  - Group operations

- [ ] **Smart Filters & Search**
  - Advanced query builder
  - Saved filter presets
  - Quick filter bar
  - Regex support

- [ ] **Custom Fields**
  - Add personal data fields
  - Streaming service tracking
  - Priority/watchlist order
  - Custom scoring systems

---

## v0.7.0 - "Insights Update"
**Focus: Understanding Your Viewing Habits**

### Core Features
- [ ] **Statistics Dashboard**
  - Total time watched
  - Completion trends
  - Genre preferences
  - Score distribution
  - Viewing patterns

- [ ] **Rewatch Tracking**
  - Track rewatch count
  - Rewatch dates
  - Favorite episodes
  - Rewatch notes

- [ ] **Export for Sharing**
  - HTML blog export
  - Markdown for forums
  - Image card generation
  - Stats infographic

---

## v0.8.0 - "Polish Update"
**Focus: UI/UX Refinement**

### Core Features
- [ ] **Theme System**
  - Dark/Light/Auto modes
  - Custom accent colors
  - Font size options
  - Compact/comfortable views

- [ ] **Rich Notes**
  - Markdown support
  - Episode-specific notes
  - Spoiler tags
  - Note templates

- [ ] **Performance Optimizations**
  - Faster startup
  - Lazy loading for large lists
  - Background sync
  - Reduced memory usage

---

## v0.9.0 - "Community Update"
**Focus: Sharing Without Sacrificing Privacy**

### Core Features
- [ ] **Local Recommendation Engine**
  - Based on your scores/genres
  - No external data collection
  - Similarity matching
  - "More like this" feature

- [ ] **List Comparison**
  - Compare exported lists
  - Find common anime
  - Compatibility scores
  - Watch together suggestions

- [ ] **Quick Share Options**
  - Generate share links
  - QR codes for mobile
  - Temporary public links
  - Password-protected shares

---

## v1.0.0 - "Stable Release"
**Focus: Production Ready**

### Goals
- [ ] Zero critical bugs
- [ ] Comprehensive documentation
- [ ] Video tutorials
- [ ] Stable API for extensions
- [ ] Migration tools from competitors
- [ ] Professional installer
- [ ] Auto-update system (optional)
- [ ] Accessibility compliance

---

## Future Possibilities
*Ideas for after v1.0 - no commitments*

### Maybe Someday
- Local-only AI recommendations
- Self-hosted sync server
- Episode discussion notes
- Watch party coordination
- Voice memo support
- Screenshot gallery
- Opening/ending skip markers
- Custom notification sounds

### Probably Never
These don't align with The Mirenku Way:
- ❌ Cloud sync service
- ❌ User accounts/login
- ❌ Social network features
- ❌ Ads or paid features
- ❌ Telemetry/analytics
- ❌ Always-online DRM
- ❌ Gamification/achievements
- ❌ Push notifications

---

## Feature Evaluation Criteria

Each feature must pass "The Mirenku Way" test:

### ✅ MUST Have
- Improves user experience significantly
- Respects user privacy
- Works offline
- User maintains data ownership
- Simple to understand and use

### ⚠️ SHOULD Have
- Cross-platform compatible
- Lightweight (< 5MB addition)
- Optional/can be disabled
- No external dependencies

### ❌ MUST NOT Have
- Require user accounts
- Send telemetry without consent
- Add complexity without value
- Break existing workflows
- Compromise performance

---

## Development Principles

1. **Quality over Speed** - Ship when ready, not by deadline
2. **User First** - Every feature solves a real problem
3. **Privacy Always** - No compromise on user data
4. **Simplicity** - If it needs a manual, it's too complex
5. **Reliability** - Better to work always than work perfectly sometimes
6. **No Pressure** - Sustainable development, no crunch

---

## Version Release Approach

- **When It's Ready™** - Features ship when properly tested
- **No Fixed Schedule** - Quality determines release, not calendar
- **User-Driven** - Community feedback shapes priorities
- **Iterative** - Small, stable releases over big risky ones

---

## Success Metrics

Version success measured by:
- User-reported bugs < 5 per release
- Startup time < 2 seconds
- Memory usage < 100MB
- No data loss incidents
- No privacy violations
- Community satisfaction (not metrics)

---

## How to Contribute

While source-available (not open source), we welcome:
- Feature suggestions via GitHub Issues
- Bug reports with reproduction steps
- Use case descriptions
- Feedback on roadmap priorities
- Beta testing participation

---

*This roadmap is a living document. Features may be added, removed, or reordered based on user needs and technical discoveries. No dates are promises - they're shipped when they're good.*

**Remember: Mirenku is built for joy, not deadlines.**
