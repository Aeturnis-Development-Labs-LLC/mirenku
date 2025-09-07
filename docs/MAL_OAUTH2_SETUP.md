# MyAnimeList OAuth2 Setup Guide

## Overview
MyAnimeList uses OAuth 2.0 for authentication with PKCE (Proof Key for Code Exchange) for desktop applications.

## Prerequisites

### 1. Register Your Application
1. Go to https://myanimelist.net/apiconfig
2. Click "Create ID" 
3. Fill in the application details:
   - **App Name**: Anime Tracker
   - **App Type**: Desktop Application
   - **App Description**: Personal anime tracking application with MAL sync
   - **App Redirect URL**: `http://localhost:8888/callback` (for desktop apps)
   - **Homepage URL**: https://github.com/Aeturnis-Development-Labs-LLC/anime-tracker
   - **Commercial**: No

### 2. Obtain Credentials
After registration, you'll receive:
- **Client ID**: A unique identifier for your app
- **Client Secret**: Not used for public clients (desktop apps) with PKCE

## OAuth2 Flow with PKCE

### Flow Overview
1. Generate code verifier and challenge
2. Direct user to MAL authorization URL
3. User authorizes the application
4. Receive authorization code via redirect
5. Exchange code for access token
6. Use access token for API requests
7. Refresh token when expired

### Required Scopes
For full functionality, request these scopes:
- `anime:read` - Read anime list
- `anime:write` - Update anime list
- `user:read` - Read user info

### PKCE Parameters
- **Code Verifier**: Random string 43-128 characters (A-Z, a-z, 0-9, -, ., _, ~)
- **Code Challenge**: Base64 URL-encoded SHA256 hash of verifier
- **Code Challenge Method**: S256

### Authorization URL Format
```
https://myanimelist.net/v1/oauth2/authorize
  ?response_type=code
  &client_id={client_id}
  &code_challenge={code_challenge}
  &code_challenge_method=S256
  &scope=anime:read anime:write user:read
  &redirect_uri=http://localhost:8888/callback
  &state={random_state}
```

### Token Exchange Request
```
POST https://myanimelist.net/v1/oauth2/token
Content-Type: application/x-www-form-urlencoded

client_id={client_id}
&grant_type=authorization_code
&code={authorization_code}
&redirect_uri=http://localhost:8888/callback
&code_verifier={code_verifier}
```

### Token Response
```json
{
  "token_type": "Bearer",
  "expires_in": 2678400,  // 31 days
  "access_token": "...",
  "refresh_token": "..."
}
```

### Token Refresh Request
```
POST https://myanimelist.net/v1/oauth2/token
Content-Type: application/x-www-form-urlencoded

client_id={client_id}
&grant_type=refresh_token
&refresh_token={refresh_token}
```

## API Endpoints (v2)

### Base URL
`https://api.myanimelist.net/v2`

### Authentication Header
```
Authorization: Bearer {access_token}
```

### Key Endpoints
- `GET /users/@me` - Get authenticated user info
- `GET /users/@me/animelist` - Get user's anime list
- `GET /anime/{anime_id}` - Get anime details
- `PATCH /anime/{anime_id}/my_list_status` - Update anime status

### Update Anime Status
```
PATCH /anime/{anime_id}/my_list_status
Content-Type: application/x-www-form-urlencoded

status={watching|completed|on_hold|dropped|plan_to_watch}
&num_watched_episodes={number}
&score={1-10}
&comments={text}
&start_date={YYYY-MM-DD}
&finish_date={YYYY-MM-DD}
```

## Implementation Notes

### Desktop App Considerations
1. **Local HTTP Server**: Start temporary server on localhost:8888 to receive callback
2. **Browser Launch**: Open authorization URL in user's default browser
3. **PKCE Security**: Always use PKCE for desktop apps (no client secret)
4. **Token Storage**: Store tokens securely (encrypted)

### Rate Limits
- **General**: 90 requests per minute
- **Per endpoint**: Various limits
- Returns `X-RateLimit-*` headers

### Error Handling
- `401 Unauthorized`: Token expired or invalid
- `403 Forbidden`: Insufficient scope
- `404 Not Found`: Resource doesn't exist
- `429 Too Many Requests`: Rate limit exceeded

## Security Best Practices

1. **Never expose tokens** in logs or error messages
2. **Encrypt stored tokens** using OS keychain or encrypted file
3. **Validate state parameter** to prevent CSRF attacks
4. **Use HTTPS** for all API requests
5. **Implement token rotation** - refresh before expiry
6. **Clear tokens on logout** or app uninstall

## Testing

### Test Account
Consider creating a test MAL account for development to avoid affecting your main list.

### OAuth2 Testing Tools
- **Postman**: Test token exchange and API calls
- **Browser DevTools**: Monitor redirect and callbacks
- **Local server**: Test callback handling

## Troubleshooting

### Common Issues
1. **Invalid redirect URI**: Must match exactly what's registered
2. **Invalid code verifier**: Must be 43-128 characters
3. **Code already used**: Authorization codes are single-use
4. **Token expired**: Refresh token or re-authenticate

### Debug Tips
- Log all OAuth2 parameters (except tokens)
- Verify PKCE challenge calculation
- Check scope permissions
- Monitor rate limit headers

## References
- [MAL API v2 Documentation](https://myanimelist.net/apiconfig/references/api/v2)
- [OAuth 2.0 RFC](https://tools.ietf.org/html/rfc6749)
- [PKCE RFC](https://tools.ietf.org/html/rfc7636)