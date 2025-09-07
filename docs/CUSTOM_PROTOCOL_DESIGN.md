# Anime Tracker Custom Protocol Design

## Overview
Design specification for the `animetracker://` custom protocol handler to enable seamless OAuth2 authentication and future streaming service integrations.

## Protocol Registration
- **Protocol Scheme**: `animetracker://`
- **Platform**: Windows (initially), macOS and Linux (future)
- **Registration Method**: Windows Registry modification

## Protocol Commands

### Authentication Commands
```
animetracker://auth?code={auth_code}&state={state}
```
- **Purpose**: OAuth2 callback from MyAnimeList
- **Parameters**:
  - `code`: Authorization code from MAL
  - `state`: CSRF protection token
- **Usage**: Set as redirect URL in MAL app configuration

### Tracking Commands (Future)
```
animetracker://track?anime={title}&episode={num}&service={name}
```
- **Purpose**: Manual tracking from external sources
- **Parameters**:
  - `anime`: Anime title or MAL ID
  - `episode`: Episode number
  - `service`: Source service (crunchyroll, netflix, etc.)

```
animetracker://watching?mal_id={id}&episode={num}&timestamp={time}
```
- **Purpose**: Auto-capture from streaming services
- **Parameters**:
  - `mal_id`: MyAnimeList anime ID
  - `episode`: Current episode
  - `timestamp`: Current playback position (optional)

### Quick Actions
```
animetracker://add?mal_id={id}
```
- **Purpose**: Quick-add anime from MAL website or other sources
- **Parameters**:
  - `mal_id`: MAL anime ID to add

```
animetracker://sync
```
- **Purpose**: Trigger manual sync with MAL
- **Parameters**: None

```
animetracker://search?q={query}
```
- **Purpose**: Open app with search pre-filled
- **Parameters**:
  - `q`: Search query

## Implementation Plan

### Phase 1: OAuth2 Authentication
1. **Registry Setup**
   - Add protocol handler to Windows Registry
   - Associate with anime_tracker.exe
   - Handle admin privileges if needed

2. **App Changes**
   - Add command-line argument parser
   - Handle protocol URLs on startup
   - Process OAuth callbacks

3. **MAL Configuration**
   - Update redirect URL to `animetracker://auth`
   - Test with MAL OAuth2 flow

### Phase 2: Browser Extension (Future)
1. **Extension Development**
   - Chrome/Firefox/Edge support
   - Detect anime on streaming sites
   - Extract episode information

2. **Streaming Service Detection**
   - Crunchyroll
   - Netflix (if possible)
   - Funimation
   - Hulu
   - Others

3. **Communication Flow**
   ```
   Extension detects anime → 
   Sends animetracker://watching?... → 
   App updates progress → 
   Syncs to MAL
   ```

## Security Considerations

### Protocol Security
- **CSRF Protection**: Use state parameter for OAuth
- **Input Validation**: Sanitize all protocol parameters
- **Rate Limiting**: Prevent spam from malicious sites
- **User Confirmation**: Optional prompt for non-OAuth commands

### Privacy
- **No Tracking Without Consent**: User must enable auto-tracking
- **Local Processing**: No data sent to third parties
- **Secure Storage**: OAuth tokens encrypted locally

## User Experience

### First-Time Setup
1. App installation registers protocol
2. User clicks "Connect MAL"
3. Browser opens MAL authorization
4. After authorization, redirects to `animetracker://auth?...`
5. Windows prompts "Open Anime Tracker?"
6. App receives code and completes authentication

### Streaming Integration (Future)
1. User installs browser extension
2. Watches anime on streaming service
3. Extension detects and sends to app
4. App silently updates progress
5. Periodic sync to MAL

## Technical Implementation

### Windows Registry Keys (Per-User, No Admin Required)
```
HKEY_CURRENT_USER\Software\Classes
  animetracker
    (Default) = "URL:Anime Tracker Protocol"
    URL Protocol = ""
    DefaultIcon
      (Default) = "anime_tracker.exe,0"
    shell
      open
        command
          (Default) = "C:\path\to\anime_tracker.exe" "%1"
```

### PowerShell Registration Script
```powershell
$proto = "animetracker"
$exe   = (Get-Item "$PSScriptRoot\AnimeTracker.exe").FullName
$base  = "HKCU:\Software\Classes\$proto"
New-Item -Path $base -Force | Out-Null
New-ItemProperty -Path $base -Name "(Default)" -Value "URL:Anime Tracker Protocol" -Force | Out-Null
New-ItemProperty -Path $base -Name "URL Protocol" -Value "" -Force | Out-Null
New-Item -Path "$base\DefaultIcon" -Force | Out-Null
New-ItemProperty -Path "$base\DefaultIcon" -Name "(Default)" -Value "$exe,0" -Force | Out-Null
New-Item -Path "$base\shell\open\command" -Force | Out-Null
New-ItemProperty -Path "$base\shell\open\command" -Name "(Default)" -Value "`"$exe`" `"%1`"" -Force | Out-Null
Write-Host "Registered animetracker:// for current user."
```

### Command Line Parsing (Pre-UI)
```python
# In main.py - before UI initialization
import sys
import urllib.parse

def handle_deeplink(argv, db):
    if len(argv) <= 1 or not argv[1].startswith("animetracker://"):
        return None  # no deep link
    url = urllib.parse.urlparse(argv[1])
    params = {k: v[0] for k, v in urllib.parse.parse_qs(url.query).items()}
    return (url.netloc or url.path.lstrip("/")), params

def main():
    # ... existing setup ...
    route = handle_deeplink(sys.argv, db)
    
    root = tk.Tk()
    app = MainWindow(root, db)
    
    if route:
        endpoint, params = route
        from utils.protocol import dispatch_protocol
        dispatch_protocol(endpoint, params, app, db)
```

### Centralized Protocol Router (utils/protocol.py)
```python
import logging
from urllib.parse import unquote

ALLOWED_ENDPOINTS = {"auth", "track", "watching", "add", "sync", "search"}

def _sanitize(s: str, max_len: int = 256) -> str:
    return unquote(s)[:max_len].strip()

def dispatch_protocol(endpoint: str, params: dict, app, db):
    endpoint = (endpoint or "").lower()
    if endpoint not in ALLOWED_ENDPOINTS:
        log.warning("Rejected unknown protocol endpoint: %s", endpoint)
        return

    # Route to appropriate handler
    if endpoint == "auth":
        _handle_auth(params, app)
    elif endpoint == "search":
        q = _sanitize(params.get("q", ""))
        if q:
            app.search_var.set(q)
            app.apply_filter()
    elif endpoint == "add":
        mal_id = params.get("mal_id")
        if mal_id and mal_id.isdigit():
            # Quick-add anime by MAL ID
            pass
    # ... other endpoints
```

## Security Implementation

### Input Validation
- **Allowlist endpoints**: Only accept known commands
- **Sanitize inputs**: Cap string lengths, strip/unquote
- **Rate limiting**: Ignore duplicate commands within 10s
- **No direct SQL**: Use existing repository pattern

### OAuth Security
- **State validation**: CSRF protection with state parameter
- **PKCE**: Code verifier/challenge for public clients
- **Token storage**: Encrypted using Windows DPAPI
- **HTTPS only**: All MAL API calls over HTTPS

## Fallback Options

### If Protocol Registration Fails
1. **Localhost Fallback**: Keep `http://localhost:8888` as backup
2. **Manual Code Entry**: Show dialog for paste code
3. **QR Code**: Generate QR code for mobile auth (future)

## Benefits

### For Users
- **Seamless Authentication**: No localhost issues
- **One-Click Actions**: Add anime from anywhere
- **Auto-Tracking**: Watch progress updates automatically
- **Cross-App Integration**: Works with browser extensions

### For Development
- **Extensible**: Easy to add new commands
- **Platform-Agnostic**: Protocol works across OS
- **Future-Proof**: Ready for streaming integrations
- **Professional**: Modern app behavior

## Testing Strategy

### OAuth Flow
1. Register protocol handler
2. Update MAL app redirect URL
3. Test authentication flow
4. Verify token exchange
5. Test error scenarios

### Protocol Commands
1. Test each command format
2. Verify parameter parsing
3. Test malformed URLs
4. Check security boundaries

## Alternative Approaches Considered

### 1. Localhost Server (Current)
- **Pros**: No registry modification needed
- **Cons**: Firewall issues, port conflicts

### 2. Manual Code Entry
- **Pros**: Always works
- **Cons**: Poor user experience

### 3. Embedded WebView
- **Pros**: Contained in app
- **Cons**: Complex implementation, security concerns

### 4. Polling aeturnis.dev
- **Pros**: No local setup
- **Cons**: Requires internet, complexity

## Decision
Implement custom protocol handler as primary method with localhost fallback for compatibility.

## Next Steps
1. Implement protocol registration for Windows
2. Add command-line argument parsing
3. Update OAuth flow to use protocol
4. Test with MAL
5. Document user setup process
6. Plan browser extension architecture