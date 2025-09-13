# Security Policy

## Overview

Mirenku takes security seriously. This document outlines our security practices, vulnerability reporting process, and implemented security measures following The Mirenku Way: local-first, privacy by default, and user-controlled security.

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.3.x   | :white_check_mark: |
| 0.2.x   | :x:                |
| 0.1.x   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in Mirenku, please report it responsibly:

1. **DO NOT** create a public GitHub issue
2. Email security details to: [contact email if available]
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We will acknowledge receipt within 48 hours and provide updates on the fix.

## Security Features

### OAuth2 Implementation

#### PKCE (Proof Key for Code Exchange)
- **Maximum entropy**: 128-character code verifier (768 bits)
- **SHA256 challenge method**: Industry standard S256
- **RFC 7636 compliant**: Full specification adherence
- **Protection against**: Authorization code interception attacks

#### State Parameter Protection
- **CSRF prevention**: Unique state for each authorization
- **Timestamp validation**: 5-minute expiration window
- **One-time use**: States invalidated after use
- **Base64-encoded JSON**: Structured state data

#### Token Management
- **Proactive refresh**: 5-minute buffer before expiry
- **Concurrent protection**: Thread-safe refresh operations
- **Secure storage**: Three-tier encryption hierarchy
- **Automatic rotation**: 30-day encryption key rotation

### Rate Limiting

#### Authorization Attempts
- **Limit**: 3 attempts per minute
- **Lockout**: 5-minute lockout after 5 failed attempts
- **Scope**: Per-client rate limiting

#### Token Refresh
- **Limit**: 5 refresh attempts per minute
- **Backoff**: Exponential backoff on failures
- **Protection**: Prevents token exhaustion attacks

### Data Protection

#### Token Storage Hierarchy
1. **OS Keyring** (Primary)
   - System-managed encryption
   - Hardware security module support
   - Automatic credential management

2. **Fernet Encryption** (Fallback)
   - AES 128-bit encryption
   - HMAC authentication
   - Cryptographically secure

3. **No Insecure Fallback**
   - No automatic base64 fallback
   - Explicit user consent required
   - Security warnings displayed

#### Encryption Key Rotation
- **Schedule**: Automatic 30-day rotation
- **Emergency rotation**: Immediate rotation on compromise
- **Multi-key support**: Graceful transition period
- **Secure deletion**: Keys overwritten before removal

### Error Handling

#### Sensitive Data Sanitization
- **Token redaction**: Automatic token masking in logs
- **Client ID protection**: Partial masking (first 4 chars only)
- **Path anonymization**: User paths replaced
- **JSON sanitization**: Payload filtering

#### Sanitization Patterns
```python
# Tokens
Bearer abc123... → Bearer [REDACTED]
token=secret → token=[REDACTED]

# Client IDs
client_id_12345678 → clie...

# User Paths
/Users/john/Documents → /Users/.../Documents

# Emails (in audit logs)
user@example.com → sha256_hash...
```

### Security Audit Logging

#### Events Tracked
- Authentication success/failure
- Token refresh operations
- Rate limit triggers
- Configuration changes
- Suspicious activities
- Data access attempts

#### Privacy Protection
- **PII redaction**: Automatic email/IP masking
- **Local storage**: All logs stored locally
- **User control**: User owns audit data
- **Retention policy**: Configurable cleanup

#### Log Management
- **Rotation**: Size and time-based rotation
- **Encryption**: Optional at-rest encryption
- **Export formats**: JSON, CSV with privacy filtering
- **Query capabilities**: Time range, event type filtering

### Network Security

#### HTTPS Enforcement
- All API calls use HTTPS
- Certificate validation enabled
- No HTTP fallback
- Secure redirect handling

#### Request Security
- User-Agent headers included
- Timeout protection (30 seconds default)
- Retry logic with exponential backoff
- Connection pooling for efficiency

## Security Best Practices

### For Users

1. **Keep Software Updated**
   - Install security updates promptly
   - Check for new releases regularly
   - Review changelog for security fixes

2. **Protect Your Tokens**
   - Never share OAuth tokens
   - Revoke access if compromised
   - Use strong system passwords

3. **Monitor Activity**
   - Review audit logs periodically
   - Check for unauthorized access
   - Report suspicious activity

### For Developers

1. **Code Security**
   - Never commit tokens or secrets
   - Use environment variables for sensitive data
   - Review security implementations

2. **Testing**
   - Run security test suite
   - Test rate limiting locally
   - Verify encryption working

3. **Dependencies**
   - Keep dependencies updated
   - Review security advisories
   - Use dependency scanning

## Implemented Security Measures

### v0.3.2 Security Hardening (Current)

#### Completed Enhancements (87.5%)

1. **Token Storage Security**
   - Eliminated insecure base64 fallback
   - Requires explicit user consent for any insecure storage
   - Automatic migration to secure storage

2. **Registry Safety** (Windows)
   - Backup before modifications
   - Conflict detection
   - Safe restoration capabilities

3. **Token Refresh Buffer**
   - 5-minute proactive refresh
   - Prevents authentication failures
   - Network retry with backoff

4. **OAuth State Timestamps**
   - 5-minute expiration
   - One-time use enforcement
   - Replay attack prevention

5. **Rate Limiting**
   - Authorization attempt limits
   - Token refresh throttling
   - Lockout mechanisms

6. **Error Sanitization**
   - Comprehensive redaction
   - Pattern-based filtering
   - Logging integration

7. **Enhanced PKCE**
   - 128-character verifier
   - Maximum entropy (768 bits)
   - 3x stronger than minimum

8. **Security Audit Logging**
   - Complete event tracking
   - Privacy-safe exports
   - Automatic rotation

9. **Key Rotation**
   - 30-day automatic rotation
   - Emergency procedures
   - Backup/restore support

### Security Testing

Our security implementation includes comprehensive testing:

- **105+ security-specific tests**
- **Test-driven development** approach
- **Thread safety** verification
- **Concurrent access** testing
- **Emergency procedure** validation

## The Mirenku Way Security Principles

1. **Local First**: All security operations happen locally
2. **Privacy by Default**: No data leaves your machine without consent
3. **User Control**: You own and control all security settings
4. **Simple Security**: Clear, understandable security measures
5. **No Bullshit**: Transparent about what we do and don't protect

## Security Limitations

### What We Protect
- OAuth tokens and credentials
- User authentication flow
- API communications
- Local data storage

### What We Don't Protect
- Physical access to your device
- Compromised operating system
- Malware on your system
- Network-level attacks (use VPN)

## Compliance

While Mirenku is a local application, we follow security best practices:

- **OAuth 2.0**: RFC 6749 compliant
- **PKCE**: RFC 7636 compliant
- **Data Protection**: Industry standard encryption
- **Audit Logging**: Forensic capability

## Security Checklist

### Installation
- [ ] Downloaded from official source
- [ ] Verified file integrity
- [ ] Reviewed permissions requested

### Configuration
- [ ] Enabled secure token storage
- [ ] Configured audit logging
- [ ] Set appropriate rotation periods

### Operation
- [ ] Regular security updates
- [ ] Periodic audit log review
- [ ] Token rotation functioning

### Incident Response
- [ ] Know how to revoke tokens
- [ ] Emergency rotation procedure ready
- [ ] Backup restoration tested

## Version History

### v0.3.2 (In Progress)
- Comprehensive security hardening
- 87.5% security tasks completed
- 105+ new security tests

### v0.3.1
- Custom protocol handler (mirenku://)
- Three-tier token encryption
- PKCE implementation

### v0.3.0
- Initial OAuth2 implementation
- Basic token storage
- MAL API integration

## Resources

### Documentation
- [Token Refresh Buffer](docs/SECURITY_IMPLEMENTATION_TOKEN_REFRESH_BUFFER.md)
- [OAuth State Timestamps](docs/SECURITY_IMPLEMENTATION_OAUTH_STATE_TIMESTAMP.md)
- [Rate Limiting](docs/SECURITY_IMPLEMENTATION_RATE_LIMITING.md)
- [Error Sanitization](docs/SECURITY_IMPLEMENTATION_ERROR_SANITIZATION.md)
- [Enhanced PKCE](docs/SECURITY_IMPLEMENTATION_ENHANCED_PKCE.md)
- [Security Audit Logging](docs/SECURITY_IMPLEMENTATION_SECURITY_AUDIT_LOGGING.md)
- [Token Encryption Key Rotation](docs/SECURITY_IMPLEMENTATION_TOKEN_ENCRYPTION_KEY_ROTATION.md)

### External References
- [OAuth 2.0 RFC 6749](https://tools.ietf.org/html/rfc6749)
- [PKCE RFC 7636](https://tools.ietf.org/html/rfc7636)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)

## Contact

For security concerns, please:
1. Check existing GitHub issues (non-security)
2. Review this security policy
3. Contact maintainers for security issues

---

*Last Updated: 2025-09-13*
*Security Policy Version: 1.0.0*
