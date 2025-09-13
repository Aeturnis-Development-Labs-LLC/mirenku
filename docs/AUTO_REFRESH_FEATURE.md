# Auto-Refresh Feature

## Overview
Automatic UI refresh system that monitors the database for changes and updates the interface in real-time. Essential for future scrobbling features and multi-window support.

## Implementation Date
2025-09-13

## Features Implemented

### 1. Database File Monitoring
- **File system watcher** monitors anime.db for changes
- **Cross-platform** compatible (Windows, Linux, macOS)
- **Efficient polling** every 250ms
- **Size and modification time** tracking

### 2. Smart Debouncing
- **300ms debounce** prevents excessive UI updates
- **Batches rapid changes** into single refresh
- **Thread-safe** implementation
- **Cancellable timers** for responsiveness

### 3. Intelligent Refresh
- **Preserves selection** during refresh
- **Maintains scroll position**
- **Silent operation** (debug logs only)
- **Main thread execution** for UI safety

### 4. Self-Trigger Prevention
- **Manual operation tracking**
- **Begin/end operation markers**
- **Ignores self-triggered changes**
- **Prevents refresh loops**

### 5. User Control
- **Toggle menu option** (View → Auto-refresh)
- **Enabled by default**
- **Notification on toggle**
- **Manual refresh still available** (F5)

## Technical Implementation

### Database Watcher
```python
class SmartDatabaseWatcher:
    - Monitors database file for changes
    - Debounces rapid changes
    - Thread-safe operation
    - Pause/resume capability
```

### Integration Points
1. **MainWindow initialization**: Starts watcher
2. **Add/Edit operations**: Wrapped with begin/end markers
3. **Window closing**: Stops watcher cleanly
4. **Menu system**: Toggle option added

### Files Modified
1. `src/utils/database_watcher.py` (new)
   - DatabaseWatcher class
   - SmartDatabaseWatcher with operation tracking

2. `src/ui/main_window.py`
   - Integrated watcher
   - Added auto-refresh callbacks
   - Wrapped manual operations
   - Added menu toggle

## User Benefits

### For Current Use
- **No manual refresh needed** after operations
- **Consistent view** of data
- **Smooth experience** with automatic updates

### For Future Scrobbling
- **Real-time updates** when anime watched
- **External tool integration** possible
- **Multi-instance support** (multiple windows)
- **Background service ready**

## Performance Impact
- **Minimal CPU usage**: 250ms polling interval
- **Low memory footprint**: Single thread
- **Efficient updates**: Only refreshes on actual changes
- **Debounced refreshes**: Prevents UI flickering

## Usage

### Normal Operation
1. Auto-refresh is **enabled by default**
2. Make changes (add, edit, delete anime)
3. UI updates automatically after ~300ms
4. No manual refresh needed

### Toggling Auto-Refresh
- **Menu**: View → Auto-refresh (checkmark)
- **Notification** shown when toggled
- **Setting persists** for session

### Manual Operations Still Work
- **F5** key for manual refresh
- **View → Refresh** menu option
- Works whether auto-refresh is on or off

## Future Enhancements

### Planned for Scrobbling
1. **Watch folder monitoring** for video files
2. **Media player integration** APIs
3. **Real-time progress updates**
4. **Automatic episode increment**
5. **Smart detection** of watched episodes

### Potential Improvements
1. **Configurable debounce time**
2. **Different refresh strategies** (full/partial)
3. **Change detection** (what changed)
4. **Multi-database support**
5. **Remote database monitoring**

## Testing Checklist

- [x] Database changes trigger refresh
- [x] Debouncing prevents excessive updates
- [x] Selection preserved after refresh
- [x] Manual operations don't double-trigger
- [x] Toggle menu works correctly
- [x] Watcher stops on window close
- [x] Thread-safe operation
- [x] No memory leaks

## Known Limitations

1. **File-based detection**: Only detects file changes, not specific records
2. **Full refresh**: Entire list refreshes (could be optimized)
3. **Local only**: Doesn't work with network databases
4. **Session setting**: Auto-refresh toggle doesn't persist

## The Mirenku Way Alignment

This implementation follows The Mirenku Way:
- **Local monitoring**: No external services needed
- **User control**: Can be toggled on/off
- **Simple implementation**: Straightforward file watching
- **Privacy first**: No data leaves the system
- **No bullshit**: Just works, no configuration needed

## Code Example

```python
# Database watcher automatically detects changes
db_watcher = SmartDatabaseWatcher(
    db_path=Path("anime.db"),
    callback=self._on_database_change,
    debounce_ms=300
)

# Start monitoring
db_watcher.start()

# Manual operations wrapped to prevent self-triggering
db_watcher.begin_operation()
# ... perform database operation ...
db_watcher.end_operation()

# Stop monitoring
db_watcher.stop()
```

## Conclusion

The auto-refresh feature provides a seamless user experience by automatically updating the UI when the database changes. This is essential groundwork for future scrobbling features and ensures users always see the current state of their anime list without manual intervention.