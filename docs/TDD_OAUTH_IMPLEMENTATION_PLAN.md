# TDD Implementation Plan: OAuth2 with Custom Protocol Handler

## Overview
This document outlines a Test-Driven Development approach for implementing OAuth2 authentication with a custom protocol handler (`mirenku://`) and secure token storage.

## Architecture Overview

```
┌──────────────┐      ┌─────────────┐      ┌──────────────┐
│   Browser    │ ───> │  mirenku:// │ ───> │   Mirenku    │
│     MAL      │      │   Protocol  │      │     App      │
└──────────────┘      └─────────────┘      └──────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Single Instance │
                    │    Manager      │
                    └─────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Token Storage   │
                    │ (Keyring/Fernet)│
                    └─────────────────┘
```

## Test Categories & Implementation Order

### Phase 1: Token Storage (Foundation)
**File**: `tests/test_token_storage.py`

#### Test 1.1: Keyring Storage (Primary)
```python
def test_keyring_save_and_load_tokens():
    """Test saving and loading tokens using OS keyring"""
    # Given: A token storage instance with keyring available
    # When: Tokens are saved
    # Then: Tokens can be retrieved correctly
    
def test_keyring_handles_missing_tokens():
    """Test keyring behavior when no tokens exist"""
    # Given: No tokens in keyring
    # When: Attempting to load tokens
    # Then: Returns None gracefully
    
def test_keyring_delete_tokens():
    """Test deleting tokens from keyring"""
    # Given: Tokens stored in keyring
    # When: Delete is called
    # Then: Tokens are removed
```

#### Test 1.2: Fernet Encryption (Fallback)
```python
def test_fernet_save_and_load_tokens():
    """Test Fernet encryption when keyring unavailable"""
    # Given: Keyring unavailable, Fernet available
    # When: Tokens are saved
    # Then: Tokens encrypted with Fernet and retrievable
    
def test_fernet_key_generation():
    """Test secure key generation for Fernet"""
    # Given: No encryption key exists
    # When: Storage initialized
    # Then: Key is generated and stored securely
    
def test_fernet_key_persistence():
    """Test that Fernet key persists across sessions"""
    # Given: Key was previously generated
    # When: New storage instance created
    # Then: Same key is loaded and tokens decrypt correctly
```

#### Test 1.3: Base64 Fallback (Last Resort)
```python
def test_base64_fallback_with_warning():
    """Test base64 encoding when no secure option available"""
    # Given: Neither keyring nor cryptography available
    # When: Tokens are saved
    # Then: Warning logged and tokens base64 encoded
    
def test_base64_migration_to_secure():
    """Test upgrading from base64 to secure storage"""
    # Given: Tokens stored with base64
    # When: Secure storage becomes available
    # Then: Tokens migrated to secure storage
```

### Phase 2: Protocol URL Handling
**File**: `tests/test_protocol_handler.py`

#### Test 2.1: URL Parsing
```python
def test_parse_oauth_callback_url():
    """Test parsing mirenku://auth callback"""
    # Given: URL "mirenku://auth?code=abc&state=xyz"
    # When: URL is parsed
    # Then: Endpoint="auth", params={"code": "abc", "state": "xyz"}
    
def test_parse_malformed_urls():
    """Test handling of malformed protocol URLs"""
    # Given: Various malformed URLs
    # When: URLs are parsed
    # Then: Returns None or safe defaults
    
def test_sanitize_url_parameters():
    """Test parameter sanitization for security"""
    # Given: URL with potentially dangerous parameters
    # When: Parameters are sanitized
    # Then: Safe values returned, dangerous content removed
```

#### Test 2.2: Protocol Registration (Windows)
```python
def test_check_protocol_registration():
    """Test checking if mirenku:// is registered"""
    # Given: Windows registry
    # When: Registration checked
    # Then: Returns True if registered, False otherwise
    
def test_register_protocol_user_level():
    """Test registering protocol without admin rights"""
    # Given: User-level registry access
    # When: Protocol registered
    # Then: Registry keys created in HKEY_CURRENT_USER
    
def test_unregister_protocol():
    """Test removing protocol registration"""
    # Given: Protocol is registered
    # When: Unregister called
    # Then: Registry keys removed
```

### Phase 3: Single Instance Management
**File**: `tests/test_single_instance.py`

#### Test 3.1: Instance Detection
```python
def test_single_instance_detection():
    """Test that only one instance can run"""
    # Given: One instance running
    # When: Second instance attempted
    # Then: Second instance detects first and exits
    
def test_instance_lock_file_creation():
    """Test lock file creation and cleanup"""
    # Given: No instance running
    # When: Instance starts
    # Then: Lock file created with PID
    
def test_stale_lock_file_cleanup():
    """Test handling of stale lock files"""
    # Given: Lock file exists but process dead
    # When: New instance starts
    # Then: Stale lock removed, new instance proceeds
```

#### Test 3.2: URL Forwarding
```python
def test_forward_url_to_existing_instance():
    """Test forwarding protocol URL to running instance"""
    # Given: Instance running, new protocol URL received
    # When: URL forwarded via IPC
    # Then: Running instance receives and processes URL
    
def test_ipc_communication_timeout():
    """Test IPC timeout handling"""
    # Given: Running instance not responding
    # When: Forwarding attempted
    # Then: Timeout after 5 seconds, error handled
```

### Phase 4: OAuth2 Flow
**File**: `tests/test_oauth2_flow.py`

#### Test 4.1: PKCE Implementation
```python
def test_generate_pkce_challenge():
    """Test PKCE code verifier and challenge generation"""
    # Given: OAuth2 client
    # When: PKCE pair generated
    # Then: Valid verifier (43-128 chars) and SHA256 challenge
    
def test_pkce_verification():
    """Test PKCE challenge verification"""
    # Given: Verifier and challenge pair
    # When: Challenge verified against verifier
    # Then: Verification succeeds
```

#### Test 4.2: Authorization Flow
```python
def test_build_authorization_url():
    """Test building MAL authorization URL"""
    # Given: Client ID and PKCE challenge
    # When: Auth URL generated
    # Then: URL contains all required parameters
    
def test_state_parameter_csrf_protection():
    """Test CSRF protection with state parameter"""
    # Given: Authorization initiated
    # When: Callback received
    # Then: State parameter validated correctly
```

#### Test 4.3: Token Exchange
```python
def test_exchange_code_for_tokens():
    """Test exchanging auth code for tokens"""
    # Given: Valid authorization code
    # When: Token exchange requested
    # Then: Access and refresh tokens received
    
def test_handle_token_exchange_errors():
    """Test error handling in token exchange"""
    # Given: Invalid or expired code
    # When: Token exchange attempted
    # Then: Error handled gracefully
```

#### Test 4.4: Token Refresh
```python
def test_refresh_expired_token():
    """Test automatic token refresh"""
    # Given: Expired access token, valid refresh token
    # When: API call attempted
    # Then: Token refreshed automatically
    
def test_refresh_token_expiry():
    """Test handling of expired refresh token"""
    # Given: Both tokens expired
    # When: Refresh attempted
    # Then: User prompted to re-authenticate
```

### Phase 5: Integration Tests
**File**: `tests/test_oauth_integration.py`

```python
def test_complete_oauth_flow_with_protocol():
    """Test end-to-end OAuth flow using protocol handler"""
    # Given: App not authenticated
    # When: User initiates OAuth flow
    # Then: Browser opens, callback handled, tokens stored
    
def test_oauth_flow_with_existing_instance():
    """Test OAuth when app already running"""
    # Given: App instance running, OAuth initiated
    # When: Callback received
    # Then: Existing instance handles callback
    
def test_mal_api_calls_with_auth():
    """Test MAL API calls with OAuth tokens"""
    # Given: Valid tokens stored
    # When: API request made
    # Then: Request includes auth header, data returned
```

## Implementation Strategy

### TDD Workflow
1. **Red Phase**: Write failing test
2. **Green Phase**: Write minimal code to pass
3. **Refactor Phase**: Improve code quality

### Implementation Order

#### Week 1: Foundation
1. **Day 1-2**: Token Storage Tests & Implementation
   - Write all token storage tests
   - Implement TokenStorage class with three-tier encryption
   
2. **Day 3-4**: Protocol Handler Tests & Implementation
   - Write URL parsing tests
   - Implement protocol handler
   - Write and implement registration logic

3. **Day 5**: Single Instance Tests & Implementation
   - Write instance detection tests
   - Implement SingleInstanceManager

#### Week 2: OAuth Flow
1. **Day 1-2**: OAuth2 Client Tests & Implementation
   - Write PKCE tests
   - Write authorization flow tests
   - Implement MALOAuth2Client

2. **Day 3-4**: Token Management
   - Write token exchange tests
   - Write refresh tests
   - Implement token lifecycle management

3. **Day 5**: Integration & Polish
   - Write integration tests
   - Fix any failing tests
   - Refactor for code quality

## File Structure

```
anime-tracker/
├── src/
│   ├── utils/
│   │   ├── token_storage.py      # Token encryption/storage
│   │   ├── protocol_handler.py   # URL parsing/routing
│   │   └── single_instance.py    # Instance management
│   └── services/
│       └── mal_oauth2_client.py  # OAuth2 implementation
├── tests/
│   ├── test_token_storage.py
│   ├── test_protocol_handler.py
│   ├── test_single_instance.py
│   ├── test_oauth2_flow.py
│   └── test_oauth_integration.py
└── register_protocol.py          # Windows registry setup
```

## Security Checklist

- [ ] Tokens never logged in plaintext
- [ ] All URL parameters sanitized
- [ ] CSRF protection via state parameter
- [ ] PKCE implemented for public client
- [ ] Secure storage with OS keyring preferred
- [ ] Graceful fallback to less secure methods with warnings
- [ ] Input validation on all protocol URLs
- [ ] Rate limiting on protocol URL processing

## Success Criteria

1. **All tests pass** (100% of test suite)
2. **Code coverage** ≥ 90% for OAuth modules
3. **Security**: No tokens in logs or memory dumps
4. **Performance**: OAuth callback handled < 500ms
5. **Reliability**: Graceful handling of all error cases
6. **User Experience**: One-click authentication

## Testing Tools

```bash
# Run specific test file
python -m pytest tests/test_token_storage.py -v

# Run with coverage
python -m pytest --cov=src/utils --cov=src/services tests/

# Run only failing tests
python -m pytest --lf

# Run tests matching pattern
python -m pytest -k "test_token" -v
```

## Mock Dependencies

For testing, we'll mock:
- `keyring` library responses
- `cryptography.fernet` operations
- Windows registry operations
- Network requests to MAL
- File system operations

## Error Scenarios to Test

1. **Storage Failures**
   - Keyring access denied
   - Corrupted encryption key
   - Disk full

2. **Protocol Issues**
   - Protocol not registered
   - Malformed URLs
   - Missing parameters

3. **OAuth Failures**
   - Network timeout
   - Invalid client ID
   - Expired codes
   - Rate limiting

4. **Instance Management**
   - Lock file permissions
   - IPC failures
   - Process crashes

## Documentation Requirements

Each implemented component needs:
1. Docstrings with examples
2. Type hints
3. Error handling documentation
4. Security considerations
5. Configuration options

## Next Steps

1. Set up test environment with pytest
2. Install test dependencies: `pytest`, `pytest-cov`, `pytest-mock`
3. Create test files with skeleton tests
4. Begin TDD cycle with token storage tests
5. Implement each component following tests