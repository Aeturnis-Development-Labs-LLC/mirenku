# MyAnimeList API Strategy Decision

## Date: 2025-09-07
## Decision: Use Jikan API for Phase 2

## API Comparison

### Jikan API (Unofficial)
**URL**: https://jikan.moe/

#### Pros:
- ✅ **No authentication required for read operations**
- ✅ Simple REST API with straightforward endpoints
- ✅ No OAuth2 complexity for basic features
- ✅ Well-documented with clear examples
- ✅ Active community and maintenance
- ✅ Faster development time for Phase 2
- ✅ Can search without user login
- ✅ Can fetch anime details without authentication

#### Cons:
- ❌ Rate limited to 60 requests/minute
- ❌ No write operations (can't update MAL)
- ❌ Unofficial (could break if MAL changes)
- ❌ Depends on third-party service availability
- ❌ Can't access user's private lists

#### Endpoints Available:
- `/v4/anime/{id}` - Get anime details
- `/v4/anime` - Search anime
- `/v4/users/{username}/animelist` - Get public user lists
- `/v4/seasons/{year}/{season}` - Get seasonal anime
- `/v4/top/anime` - Get top anime

### MAL Official API v2
**URL**: https://myanimelist.net/apiconfig

#### Pros:
- ✅ **Official API with guaranteed support**
- ✅ Full read/write capabilities
- ✅ Can update user's MAL list
- ✅ Access to private user data
- ✅ Higher rate limits
- ✅ More stable long-term

#### Cons:
- ❌ **Requires OAuth2 authentication**
- ❌ Complex setup with client registration
- ❌ Requires API key and client secret
- ❌ User must authorize the app
- ❌ More complex error handling
- ❌ Longer development time

## Decision Rationale

### Why Jikan for Phase 2:

1. **Faster MVP Development**: We can implement search and import features immediately without OAuth2 complexity

2. **User Experience**: Users can search and import anime without creating/linking MAL accounts

3. **Offline-First Philosophy**: Aligns with our principle - MAL features are additive, not required

4. **Progressive Enhancement**: We can add OAuth2 and write operations in Phase 3

5. **Risk Mitigation**: Test MAL integration value before investing in OAuth2 implementation

## Implementation Strategy

### Phase 2 (v0.2.0) - Read-Only with Jikan
- Search anime from MAL database
- Import anime metadata (synopsis, genres, images)
- Import public user lists
- Browse seasonal anime
- View top anime

### Phase 3 (v0.3.0) - Full Sync with Official API
- Implement OAuth2 authentication
- Two-way synchronization
- Update MAL from local changes
- Access private user data
- Full MAL integration

## Technical Implementation

### Rate Limiting Strategy
```python
# 60 requests per minute = 1 request per second
# Implement token bucket algorithm
class RateLimiter:
    def __init__(self, requests_per_minute=60):
        self.rate = requests_per_minute / 60.0
        self.allowance = requests_per_minute
        self.last_check = time.time()
```

### Caching Strategy
- Cache anime details for 7 days
- Cache search results for 1 hour
- Cache images permanently
- Use SQLite for cache storage

### Error Handling
- 429 (Rate Limit): Wait and retry
- 500/503 (Server Error): Exponential backoff
- Network Error: Work offline with cached data
- 404 (Not Found): Mark as MAL-unavailable

## API Endpoints to Implement

### Priority 1 (Core Features)
1. **Search Anime**: `GET /v4/anime?q={query}&limit=20`
2. **Get Anime Details**: `GET /v4/anime/{id}`
3. **Get Anime Full**: `GET /v4/anime/{id}/full`

### Priority 2 (Import Features)  
4. **User Anime List**: `GET /v4/users/{username}/animelist?status=all`
5. **Anime Pictures**: `GET /v4/anime/{id}/pictures`

### Priority 3 (Browse Features)
6. **Current Season**: `GET /v4/seasons/now`
7. **Top Anime**: `GET /v4/top/anime`
8. **Anime Recommendations**: `GET /v4/anime/{id}/recommendations`

## Migration Path

When we move to Official API in Phase 3:
1. Keep Jikan for search/browse (no auth needed)
2. Use Official API only for user-specific operations
3. Gradual migration with feature flags
4. Maintain backward compatibility

## Conclusion

Jikan API is the optimal choice for Phase 2 because it allows us to quickly deliver value with MAL integration features without the complexity of OAuth2. This aligns with our iterative development approach and offline-first philosophy.

---

*Decision made by: Development Team*  
*Date: 2025-09-07*  
*Version: 1.0*