# MAL Sync Issues and Fixes

## Issues Found:

### 1. ✅ FIXED: SQLite Thread Safety Error
- **Problem**: Database connections can't be shared across threads
- **Fix**: Create new database connection in sync thread

### 2. ✅ FIXED: Timestamp Format Error
- **Problem**: Using `.isoformat()` creates timestamps SQLite can't parse
- **Fix**: Use `.strftime('%Y-%m-%d %H:%M:%S')` instead

### 3. ✅ FIXED: Lambda Variable Scope Error
- **Problem**: Exception variable `e` not captured properly in lambda
- **Fix**: Store error message in local variable first

### 4. ⚠️ PARTIAL FIX: Push Not Working
- **Problem**: Sync queue is never populated, anime without MAL IDs can't be pushed
- **Partial Fix**: Push now syncs all anime that have MAL IDs
- **TODO**: Need to search MAL for anime without IDs and match them

### 5. ❌ NOT FIXED: Pull Deletes Local Data
- **Problem**: Pull from MAL overwrites local anime list
- **TODO**: Make pull merge data instead of replacing

## Current Behavior:

### Push to MAL:
- Only works for anime that already have MAL IDs
- Local-only anime (without MAL IDs) are skipped
- Need to implement MAL search to find matching anime

### Pull from MAL:
- Creates new entries for MAL anime not in local DB
- Updates existing entries (may overwrite local changes)
- Does NOT delete local-only anime

### Full Sync:
- Pushes local changes (only with MAL IDs)
- Then pulls from MAL (may overwrite)

## Recommended Next Steps:

1. **Implement MAL Search for Push**:
   - For anime without MAL IDs, search MAL by title
   - Present matches to user for confirmation
   - Link local anime to MAL ID before pushing

2. **Improve Pull Merge Logic**:
   - Don't overwrite local status if it's more recent
   - Preserve local notes and custom fields
   - Show conflicts to user for resolution

3. **Add Sync Conflict Resolution**:
   - Detect when local and MAL data differ
   - Let user choose which version to keep
   - Option to keep both (duplicate with suffix)

4. **Better Error Handling**:
   - Show which specific anime failed to sync
   - Provide retry option for failed items
   - Log detailed errors for debugging