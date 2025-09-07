# Anime Tracker - Phase 3: Full MAL Synchronization

## Overview
Phase 3 focuses on implementing OAuth2 authentication and enabling full bidirectional synchronization with MyAnimeList, completing the deferred write operations from Phase 2.

## Phase 3: Full MAL Sync (Target: v0.3.0)

### OAuth2 Authentication Implementation

#### MAL API Registration
- [ ] Register application with MAL
  - [ ] Create MAL API application at https://myanimelist.net/apiconfig
  - [ ] Obtain Client ID
  - [ ] Obtain Client Secret
  - [ ] Set redirect URI (localhost for desktop app)
  - [ ] Document API credentials securely

#### OAuth2 Flow Implementation
- [ ] Implement OAuth2 authorization
  - [ ] Create OAuth2 client class
  - [ ] Implement PKCE (Proof Key for Code Exchange) for desktop apps
  - [ ] Generate authorization URL
  - [ ] Handle authorization code callback
  - [ ] Exchange code for access token
  - [ ] Implement token refresh logic
  
- [ ] Token Management
  - [ ] Secure token storage (encrypted)
  - [ ] Token refresh before expiry
  - [ ] Handle token revocation
  - [ ] Implement token validation
  - [ ] Auto-refresh on 401 errors

#### Authentication UI
- [ ] Create MAL login dialog
  - [ ] Design login window
  - [ ] Embed web view or open browser
  - [ ] Handle redirect URI capture
  - [ ] Show authentication progress
  - [ ] Display success/failure messages
  
- [ ] Account management UI
  - [ ] Show connected MAL account
  - [ ] Display account username
  - [ ] Add disconnect button
  - [ ] Show last sync time
  - [ ] Display sync statistics

### Write Operations to MAL

#### Basic Write Operations
- [ ] Implement anime status updates
  - [ ] Push status changes to MAL
  - [ ] Update watching status
  - [ ] Mark as completed
  - [ ] Set on hold/dropped
  - [ ] Add to plan to watch
  
- [ ] Implement progress updates
  - [ ] Push episode progress to MAL
  - [ ] Sync watched episodes
  - [ ] Handle episode increments
  - [ ] Batch episode updates
  - [ ] Validate against total episodes
  
- [ ] Implement score updates
  - [ ] Push score changes to MAL
  - [ ] Validate score range (1-10)
  - [ ] Handle score removal
  - [ ] Update mean score locally

#### Advanced Write Operations
- [ ] Implement list management
  - [ ] Add new anime to MAL list
  - [ ] Remove anime from MAL list
  - [ ] Update start/finish dates
  - [ ] Set rewatch count
  - [ ] Update priority
  
- [ ] Implement notes and tags
  - [ ] Sync personal notes to MAL
  - [ ] Manage tags (if supported)
  - [ ] Handle note character limits
  - [ ] Preserve formatting

### Bidirectional Synchronization

#### Sync Engine
- [ ] Implement sync conflict detection
  - [ ] Compare local vs MAL timestamps
  - [ ] Detect concurrent modifications
  - [ ] Identify field-level conflicts
  - [ ] Track last sync points
  - [ ] Handle deleted items
  
- [ ] Implement conflict resolution
  - [ ] Create conflict resolution UI
  - [ ] Show side-by-side comparison
  - [ ] Allow user to choose version
  - [ ] Implement merge strategies
  - [ ] Support "always prefer local/MAL" option
  
- [ ] Implement sync strategies
  - [ ] Manual sync on demand
  - [ ] Auto-sync on changes
  - [ ] Scheduled sync intervals
  - [ ] Smart sync (batch changes)
  - [ ] Selective field sync

#### Sync Queue Processing
- [ ] Process pending write operations
  - [ ] Execute queued operations
  - [ ] Handle operation dependencies
  - [ ] Implement retry logic
  - [ ] Handle partial failures
  - [ ] Update sync status in UI
  
- [ ] Optimize sync performance
  - [ ] Batch API requests
  - [ ] Implement parallel operations
  - [ ] Use conditional requests
  - [ ] Minimize data transfer
  - [ ] Cache sync state

### Data Integrity & Safety

#### Backup & Recovery
- [ ] Pre-sync backup
  - [ ] Auto-backup before sync
  - [ ] Store multiple backup versions
  - [ ] Quick restore option
  - [ ] Export sync history
  
- [ ] Sync rollback
  - [ ] Implement undo for sync operations
  - [ ] Track sync transactions
  - [ ] Restore previous state
  - [ ] Handle partial rollbacks

#### Validation & Safety
- [ ] Data validation
  - [ ] Validate before pushing to MAL
  - [ ] Check data consistency
  - [ ] Prevent duplicate entries
  - [ ] Verify MAL ID mappings
  
- [ ] Safety features
  - [ ] Dry run mode for sync
  - [ ] Preview changes before sync
  - [ ] Confirmation for destructive operations
  - [ ] Rate limit protection

### Enhanced UI for Sync

#### Sync Status Indicators
- [ ] Real-time sync status
  - [ ] Show sync progress bar
  - [ ] Display current operation
  - [ ] Show items synced/remaining
  - [ ] Indicate sync direction (up/down)
  - [ ] Display sync errors inline
  
- [ ] Visual sync indicators
  - [ ] Add sync status icons to list
  - [ ] Show pending changes badge
  - [ ] Highlight conflicted items
  - [ ] Display last sync timestamp per item

#### Sync Management UI
- [ ] Sync control panel
  - [ ] Manual sync button (enabled)
  - [ ] Pause/resume sync
  - [ ] Cancel ongoing sync
  - [ ] Force sync option
  - [ ] Sync history viewer
  
- [ ] Sync settings dialog
  - [ ] Configure sync frequency
  - [ ] Select sync direction
  - [ ] Choose conflict resolution
  - [ ] Set field preferences
  - [ ] Configure auto-sync triggers

### Advanced Features

#### Bulk Operations
- [ ] Bulk sync operations
  - [ ] Select multiple items to sync
  - [ ] Bulk conflict resolution
  - [ ] Mass update to MAL
  - [ ] Batch import improvements
  
- [ ] Smart sync features
  - [ ] Detect and merge duplicates
  - [ ] Auto-match local to MAL entries
  - [ ] Suggest MAL IDs for unlinked items
  - [ ] Clean up orphaned entries

#### Sync Monitoring
- [ ] Sync analytics
  - [ ] Track sync performance
  - [ ] Monitor API usage
  - [ ] Log sync operations
  - [ ] Generate sync reports
  
- [ ] Sync notifications
  - [ ] Notify on sync completion
  - [ ] Alert on sync errors
  - [ ] Show conflict notifications
  - [ ] Display sync summary

### Testing

#### Unit Tests
- [ ] OAuth2 flow tests
  - [ ] Test token generation
  - [ ] Test token refresh
  - [ ] Test error handling
  - [ ] Mock OAuth2 responses
  
- [ ] Write operation tests
  - [ ] Test status updates
  - [ ] Test progress updates
  - [ ] Test score updates
  - [ ] Test error scenarios

#### Integration Tests
- [ ] End-to-end sync tests
  - [ ] Test full sync cycle
  - [ ] Test conflict resolution
  - [ ] Test offline to online transition
  - [ ] Test concurrent modifications
  
- [ ] MAL API integration tests
  - [ ] Test with real MAL account (sandbox)
  - [ ] Test rate limiting
  - [ ] Test error recovery
  - [ ] Test data consistency

### Documentation

#### User Documentation
- [ ] OAuth2 setup guide
  - [ ] Step-by-step login process
  - [ ] Troubleshooting auth issues
  - [ ] Privacy and security info
  - [ ] Token management guide
  
- [ ] Sync user guide
  - [ ] How to sync with MAL
  - [ ] Understanding sync status
  - [ ] Resolving conflicts
  - [ ] Best practices

#### Technical Documentation
- [ ] OAuth2 implementation details
  - [ ] Flow diagrams
  - [ ] Security considerations
  - [ ] Token storage method
  - [ ] Error handling

- [ ] Sync algorithm documentation
  - [ ] Conflict detection logic
  - [ ] Resolution strategies
  - [ ] Queue processing
  - [ ] Performance optimizations

### Migration & Compatibility

#### Migration from Phase 2
- [ ] Database migration
  - [ ] Update schema for OAuth2
  - [ ] Migrate existing MAL IDs
  - [ ] Update sync status fields
  - [ ] Preserve user data
  
- [ ] Settings migration
  - [ ] Import Phase 2 settings
  - [ ] Set default sync preferences
  - [ ] Migrate cached data
  - [ ] Update configuration

### Security Considerations

#### OAuth2 Security
- [ ] Secure token storage
  - [ ] Encrypt tokens at rest
  - [ ] Use OS keychain if available
  - [ ] Implement token rotation
  - [ ] Clear tokens on logout
  
- [ ] API security
  - [ ] Validate SSL certificates
  - [ ] Implement request signing
  - [ ] Prevent token leakage
  - [ ] Audit security logs

## Completion Checklist

### Core Requirements
- [ ] OAuth2 authentication working
- [ ] Can push updates to MAL
- [ ] Can pull updates from MAL
- [ ] Conflict resolution implemented
- [ ] Sync queue processing

### Quality Gates
- [ ] All tests passing
- [ ] No data loss during sync
- [ ] Sync completes < 30 seconds for 100 items
- [ ] OAuth2 tokens properly secured
- [ ] Error recovery working

### User Experience
- [ ] Clear sync status indicators
- [ ] Intuitive conflict resolution
- [ ] Helpful error messages
- [ ] Smooth authentication flow
- [ ] Reliable sync operations

## Phase 3 Completion Criteria

**Phase 3 is complete when:**
1. Users can authenticate with MAL using OAuth2
2. All local changes sync to MAL automatically
3. MAL changes sync down to local database
4. Conflicts are detected and resolved properly
5. Sync operations are reliable and recoverable
6. Security best practices are implemented
7. Full test coverage for sync operations
8. Documentation is complete

## Technical Decisions

1. **Token Storage**: OS keychain vs encrypted file
2. **Sync Strategy**: Optimistic vs pessimistic locking
3. **Conflict Resolution**: Last-write-wins vs user choice
4. **Sync Frequency**: Real-time vs batch intervals
5. **OAuth2 Flow**: Browser vs embedded webview

## Risk Mitigation

- **API Changes**: Abstract MAL API interface
- **Token Security**: Multiple encryption layers
- **Data Loss**: Automatic backups before sync
- **Rate Limits**: Intelligent request batching
- **Network Issues**: Robust retry mechanisms

## Dependencies on Deferred Phase 2 Tasks

### From Phase 2 Sync Foundation
- [x] Sync architecture design (completed)
- [x] Database sync fields (completed)
- [x] Sync service foundation (completed)
- [ ] Enable sync button (currently disabled)
- [ ] Activate sync status indicators

### From Phase 2 MAL Export
- [ ] Implement "Push to MAL" functionality
- [ ] Create update API calls
- [ ] Handle authentication for writes
- [ ] Log sync operations

### From Phase 2 Sync Configuration
- [ ] Sync settings in preferences
- [ ] Auto-sync toggle
- [ ] Sync frequency settings
- [ ] Conflict resolution preferences
- [ ] MAL account connection status

## Notes

- OAuth2 is required for all write operations to MAL
- Consider implementing read operations via OAuth2 as well for consistency
- Maintain backward compatibility with Jikan for users who don't want to authenticate
- Provide clear value proposition for why users should connect their MAL account
- Ensure sync never causes data loss - always preserve user data

---

## Task Tracking

**Total Tasks**: ~150 tasks across 12 categories
**Estimated Time**: 3-4 weeks
**Priority**: OAuth2 > Basic Writes > Sync Engine > Conflict Resolution

### Quick Reference Commands
```bash
# Run OAuth2 tests
python -m pytest tests/test_oauth2.py

# Test sync operations
python tests/test_sync_engine.py

# Build with full MAL sync
python build.py --with-oauth2
```

---

*Phase 3 Start Date: TBD*  
*Target Completion: TBD*  
*Version Target: v0.3.0*