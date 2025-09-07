# Anime Tracker - Phase 2: MyAnimeList Integration

## Overview
Phase 2 focuses on integrating MyAnimeList (MAL) functionality to enhance the anime tracker with online features while maintaining offline-first capability.

## Phase 2: MAL Integration (Target: v0.2.0)

### API Setup & Authentication
- [x] Research and choose API strategy
  - [x] Evaluate Jikan API (unofficial, no auth for read)
  - [x] Evaluate MAL Official API v2 (OAuth2 required)
  - [x] Document API choice and rationale
  - [x] Create API credentials/registration if needed (Not needed for Jikan)

- [x] Implement API client foundation
  - [x] Create `src/services/mal_service.py`
  - [x] Set up rate limiting (60 requests/min for Jikan)
  - [x] Implement request retry logic
  - [x] Add response caching mechanism
  - [x] Handle API errors gracefully

- [ ] ~~Set up authentication (if using official API)~~ (Not needed for Jikan - Phase 3)
  - [ ] ~~Implement OAuth2 flow~~
  - [ ] ~~Create token storage/refresh logic~~
  - [ ] ~~Add authentication UI dialog~~
  - [ ] ~~Store credentials securely~~

### Search & Import Features
- [x] Implement MAL search functionality
  - [x] Add search UI to main window
  - [x] Create MAL search dialog
  - [x] Implement search API calls
  - [x] Parse and display search results
  - [x] Add "Import from MAL" button for results

- [x] Build metadata import system
  - [x] Map MAL data to local anime model
  - [x] Import anime details (synopsis, genres, studios)
  - [x] Download and cache cover images
  - [x] Handle missing/incomplete data
  - [x] Add progress overlay during import

- [x] Create bulk import feature
  - [x] Add "Import MAL List" menu option
  - [x] Create username input dialog
  - [x] Fetch user's complete anime list
  - [x] Show import preview with checkboxes
  - [x] Implement batch import with progress bar
  - [x] Handle duplicates intelligently

### Data Enrichment
- [x] Enhance anime model for MAL data
  - [x] Add mal_id field to database
  - [x] Add synopsis field
  - [x] Add genres field (many-to-many)
  - [x] Add studios field
  - [x] Add aired_date fields
  - [x] Add image_url field
  - [x] Create database migration script

- [x] Implement cover image handling
  - [x] Create image cache directory
  - [x] Download images asynchronously
  - [x] Add image display in UI
  - [x] Implement placeholder for missing images
  - [x] Add image refresh capability

- [x] Add detailed anime view
  - [x] Create detail view dialog/panel
  - [x] Display synopsis and metadata
  - [x] Show cover image
  - [x] Display genres and studios
  - [x] Add MAL link button

### Synchronization Foundation
- [x] Design sync architecture
  - [x] Define sync states (local-only, mal-only, synced, conflict)
  - [x] Create sync_status field in database
  - [x] Design conflict resolution strategy
  - [x] Plan sync queue system

- [ ] Implement basic MAL export
  - [ ] Add "Push to MAL" button
  - [ ] Create update API calls
  - [ ] Handle authentication for writes
  - [ ] Show sync status indicators
  - [ ] Log sync operations

- [ ] Create sync configuration
  - [ ] Add sync settings to preferences
  - [ ] Auto-sync on/off toggle
  - [ ] Sync frequency setting
  - [ ] Conflict resolution preferences
  - [ ] MAL account connection status

### UI Enhancements
- [x] Update main window for MAL features
  - [x] Add MAL search bar
  - [x] Add sync status indicator
  - [x] Show MAL ID in list view (optional column)
  - [x] Add "Linked to MAL" icon
  - [x] Display last sync timestamp

- [ ] Create MAL-specific dialogs
  - [x] MAL search results dialog
  - [x] Import preview dialog
  - [ ] Sync conflict resolution dialog
  - [ ] MAL connection settings
  - [ ] Sync history viewer

- [x] Enhance status bar
  - [x] Add MAL connection indicator
  - [x] Show sync queue count
  - [ ] Display API rate limit status
  - [ ] Add last successful sync time

### Error Handling & Offline Support
- [x] Implement offline queue system
  - [x] Queue MAL operations when offline
  - [x] Retry failed operations
  - [x] Process queue when connection restored
  - [x] Show queue status to user

- [x] Add comprehensive error handling
  - [x] Handle rate limit errors (429)
  - [x] Handle authentication errors (401)
  - [x] Handle not found errors (404)
  - [x] Handle server errors (500+)
  - [x] Show user-friendly error messages

- [x] Create fallback mechanisms
  - [x] Work offline when MAL unavailable
  - [x] Use cached data when possible
  - [x] Gracefully degrade features
  - [x] Alert user to connection issues

### Testing
- [x] Write unit tests for MAL service
  - [x] Test API client methods
  - [ ] Test authentication flow (N/A for Jikan)
  - [x] Test data mapping
  - [x] Test error handling
  - [x] Mock API responses

- [ ] Create integration tests
  - [ ] Test search functionality
  - [ ] Test import operations
  - [ ] Test sync operations
  - [ ] Test offline queue
  - [ ] Test rate limiting

- [ ] Perform end-to-end testing
  - [ ] Test complete import workflow
  - [ ] Test search and add workflow
  - [ ] Test sync conflict resolution
  - [ ] Test offline/online transitions
  - [ ] Test with real MAL data

### Documentation
- [ ] Update user documentation
  - [ ] Document MAL setup process
  - [ ] Create import guide
  - [ ] Explain sync behavior
  - [ ] Add troubleshooting section

- [ ] Update technical documentation
  - [ ] Document API integration
  - [ ] Update database schema docs
  - [ ] Document sync algorithm
  - [ ] Add API response examples

## Completion Checklist

### Core Requirements
- [ ] MAL search working
- [ ] Import from MAL functional
- [ ] Cover images displaying
- [ ] Basic sync operational
- [ ] Offline mode maintained

### Quality Gates
- [ ] All tests passing
- [ ] No regression in Phase 1 features
- [ ] API rate limits respected
- [ ] Error handling comprehensive
- [ ] Documentation complete

### Performance Targets
- [ ] Search results < 2 seconds
- [ ] Import speed > 10 anime/second
- [ ] Image cache working efficiently
- [ ] Sync queue processing smoothly
- [ ] Memory usage reasonable with images

## Phase 2 Completion Criteria

**Phase 2 is complete when:**
1. Users can search MAL and import anime data
2. Cover images are displayed in the UI
3. Users can import their entire MAL list
4. Basic push to MAL is working
5. All Phase 1 features still work offline
6. Test coverage remains > 80%
7. Documentation is updated

## Technical Decisions to Make

1. **API Choice**: Jikan (easier, no auth) vs Official (more features, OAuth)
2. **Image Storage**: File system vs embedded database
3. **Sync Strategy**: Manual only vs auto-sync options
4. **Conflict Resolution**: Last-write-wins vs user choice
5. **Rate Limiting**: Client-side vs queue-based

## Risk Mitigation

- **API Changes**: Abstract API client interface
- **Rate Limits**: Implement robust queuing
- **Auth Complexity**: Start with read-only features
- **Data Conflicts**: Clear UI for conflict resolution
- **Performance**: Lazy load images, pagination

## Notes

- Prioritize read operations (search, import) over write (sync to MAL)
- Maintain offline-first principle throughout
- Consider implementing features incrementally
- Test with various MAL list sizes (small to 1000+ entries)
- Keep UI responsive during long operations

---

## Task Tracking

**Total Tasks**: 40 main tasks across 10 categories
**Estimated Time**: 2-3 weeks
**Priority**: Search > Import > Images > Sync

### Quick Reference Commands
```bash
# Run tests for Phase 2
python -m pytest tests/test_mal_service.py

# Test MAL integration
python tests/test_mal_integration.py

# Build with MAL features
python build.py --with-mal
```

---

*Phase 2 Start Date: TBD*  
*Target Completion: TBD*  
*Version Target: v0.2.0*