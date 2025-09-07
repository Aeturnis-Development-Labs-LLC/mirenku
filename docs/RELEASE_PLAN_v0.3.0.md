# Release Plan for v0.3.0

## Current State Assessment

### Completed Features (Since v0.1.1)

#### Phase 2 - MAL Integration (v0.2.0 features)
- ✅ Jikan API integration with rate limiting
- ✅ MAL search functionality  
- ✅ Import anime from MAL
- ✅ Import user's MAL list
- ✅ Image caching service
- ✅ Response caching with TTL
- ✅ MAL metadata enrichment

#### Phase 3 - OAuth2 & Synchronization (v0.3.0 features)
- ✅ MAL OAuth2 authentication (with PKCE)
- ✅ MAL API v2 service implementation
- ✅ Full CRUD operations on MAL
- ✅ Bidirectional sync service
- ✅ Sync queue for offline changes
- ✅ Conflict detection
- ⚠️ OAuth2 callback issues (localhost:8888)

### Known Issues
1. OAuth2 redirect works but token exchange fails
2. MAL auth dialog buttons have display issues
3. Need better error messages for auth failures

## Version Strategy

### Option 1: Release as v0.3.0 (Recommended)
- Skip v0.2.0 since we implemented Phase 2 & 3 together
- Document all features from both phases
- Mark OAuth2 as "beta" due to callback issues

### Option 2: Split Releases
- Release v0.2.0 with Jikan/read-only features
- Release v0.3.0 with OAuth2/write features
- More work but cleaner history

## Documentation Updates Needed

### 1. CHANGELOG.md
Add entries for:
- v0.2.0 (if splitting) or combined in v0.3.0
- All MAL features
- OAuth2 implementation
- Sync capabilities

### 2. README.md
Update with:
- MAL integration instructions
- OAuth2 setup guide
- Sync features
- Known limitations

### 3. Design Document
- Mark Phase 2 & 3 as complete
- Add Phase 4 (Polish) and Phase 5 (Custom Protocol)
- Update timeline

## Scope Management

### In Scope for v0.3.0
- All current MAL features
- OAuth2 (with known issues documented)
- Basic sync functionality

### Out of Scope (Future Versions)
- Custom protocol handler (v0.4.0)
- Browser extension (v0.5.0)
- Streaming service integration (v1.0.0)
- OAuth2 callback fix (patch in v0.3.1)

## Release Checklist

- [ ] Update version to 0.3.0 in __init__.py
- [ ] Update CHANGELOG.md with all changes
- [ ] Update README.md with new features
- [ ] Document OAuth2 setup in docs/
- [ ] Run full test suite
- [ ] Build executable with PyInstaller
- [ ] Test executable on clean system
- [ ] Create GitHub release
- [ ] Tag version in git

## Next Steps Decision

1. **Fix OAuth2 first** - Spend time debugging callback
2. **Release as-is** - Document OAuth2 as experimental
3. **Remove OAuth2** - Ship v0.3.0 with Jikan only
4. **Implement workaround** - Add manual code entry

## Recommendation

Release v0.3.0 with current features, documenting OAuth2 as "experimental". Focus on custom protocol in v0.4.0 as a proper solution to the OAuth2 callback issues.

This maintains momentum while being transparent about limitations.