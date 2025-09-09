# Security Improvements for v0.3.2

**Priority**: CRITICAL  
**Timeline**: Immediate next release  
**Philosophy**: Mirenku doesn't compromise on security

## Overview

While v0.3.1 implements OAuth2 with PKCE and secure token storage, security audit has identified several areas for hardening. v0.3.2 will be a security-focused release addressing all findings.

## HIGH PRIORITY (Must Fix)

### 1. Client ID Exposure 🔴
**File**: `src/ui/mal_auth_dialog.py` (line 333)
```python
self.client_id = client_id or "77dcb3ef6a0b47401c5d76e5957bc425"
```
**Issue**: Hardcoded client ID in source code  
**Risk**: Public exposure of application credentials  
**Fix**: 
- Move to environment variable
- Or encrypted configuration file
- Or require user to provide their own
- Document secure configuration in README

### 2. Token Storage Base64 Fallback 🔴
**File**: `src/utils/token_storage.py`
**Issue**: Base64 is encoding, not encryption  
**Risk**: Tokens readable by anyone with file access  
**Fix**:
- When keyring and Fernet fail, refuse to store tokens
- Require user acknowledgment of security risk
- Or implement additional encryption layer
- Consider using system-specific secure storage APIs

### 3. Registry Safety 🟡
**File**: `src/utils/protocol_manager.py`
**Issue**: Modifying registry without backup  
**Risk**: Potential conflicts with other applications  
**Fix**:
- Check for existing `mirenku://` handler before registering
- Offer to backup existing registry keys
- Implement registry restoration function
- Add conflict detection

## MEDIUM PRIORITY (Should Fix)

### 4. Token Refresh Buffer
**Issue**: Tokens refresh only after expiry  
**Risk**: Operations could fail mid-execution  
**Fix**:
- Implement 5-minute refresh buffer
- Add token expiry warning in UI
- Background refresh thread

### 5. State Parameter Enhancement
**File**: `src/services/mal_oauth2_protocol.py`
**Issue**: State parameter could be stronger  
**Fix**:
- Add timestamp to state
- Implement state expiration (5 minutes)
- Store state securely during auth flow

### 6. Error Message Sanitization
**Issue**: Full error details in logs  
**Risk**: Potential information leakage  
**Fix**:
- Sanitize all error messages before logging
- Never log tokens (even partially)
- Implement debug vs production logging levels
- Add log rotation and secure deletion

### 7. Rate Limiting
**Issue**: No rate limiting on OAuth operations  
**Risk**: Brute force attacks on token refresh  
**Fix**:
- Implement exponential backoff
- Add rate limiting to auth attempts
- Track failed authentication attempts
- Temporary lockout after failures

## LOW PRIORITY (Nice to Have)

### 8. Enhanced PKCE
- Increase code verifier length to maximum (128 chars)
- Add additional entropy sources

### 9. Lock File Security
- Improve stale lock detection
- Add lock file encryption
- Implement lock timeout

### 10. Code Signing
- Sign the Windows executable
- Implement signature verification
- Add checksum verification in app

## Additional Security Measures

### New Features for v0.3.2

1. **Security Mode**
   - Strict mode: Refuse to run without secure token storage
   - Normal mode: Current behavior with warnings
   - User choice in settings

2. **Security Audit Log**
   - Log all authentication events
   - Track token usage
   - Monitor for suspicious patterns

3. **Token Encryption Key Rotation**
   - Periodic key rotation for Fernet
   - Automatic token re-encryption
   - Backward compatibility for one version

4. **Security Documentation**
   - Create SECURITY.md
   - Document threat model
   - Provide security best practices
   - Add responsible disclosure policy

## Implementation Plan

### Phase 1 (Day 1)
- [ ] Fix client ID exposure
- [ ] Implement token storage refusal option
- [ ] Add registry safety checks

### Phase 2 (Day 2)
- [ ] Add token refresh buffer
- [ ] Enhance state parameter
- [ ] Sanitize error messages

### Phase 3 (Day 3)
- [ ] Implement rate limiting
- [ ] Add security mode setting
- [ ] Create security documentation

### Testing Requirements
- [ ] Security-focused test suite
- [ ] Penetration testing checklist
- [ ] Token leakage tests
- [ ] Error message sanitization tests
- [ ] Rate limiting tests

## Success Metrics
- Zero hardcoded credentials
- 100% of tokens encrypted (no base64 fallback)
- All errors sanitized before logging
- Rate limiting on all auth endpoints
- Security documentation complete

## Security Commitment

**Mirenku doesn't compromise on security.** Every identified issue will be addressed before v0.3.2 release. Users trust us with their MAL authentication, and we take that responsibility seriously.

## Disclosure

If you discover a security vulnerability, please email security@aeturnis.dev with:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will respond within 48 hours and provide credit (if desired) when the fix is released.

---

**Target Release**: v0.3.2 (September 2025)  
**Priority**: CRITICAL - No other features until security is addressed  
**Philosophy**: Security is not optional