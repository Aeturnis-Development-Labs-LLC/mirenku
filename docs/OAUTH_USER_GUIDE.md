# Mirenku OAuth2 Setup Guide

## Overview
Mirenku uses OAuth2 authentication to securely connect to MyAnimeList (MAL) without storing your password. This guide will walk you through the setup process.

## Table of Contents
- [First-Time Setup](#first-time-setup)
- [Connecting to MyAnimeList](#connecting-to-myanimelist)
- [Protocol Registration](#protocol-registration)
- [Security Features](#security-features)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)

## First-Time Setup

### 1. Launch Mirenku
When you first launch Mirenku, you'll see a welcome dialog:

![Welcome Dialog](screenshots/welcome.png)

This dialog appears only on first run and helps configure essential features.

### 2. Protocol Registration
The welcome dialog includes an option to register the `mirenku://` protocol handler:

- **What it does**: Allows Mirenku to receive OAuth callbacks from your browser
- **Why it's needed**: MyAnimeList redirects back to Mirenku after you log in
- **Security**: Only registers in your user account (no admin rights needed)

**Recommendation**: Check "Register protocol handler" for the smoothest experience.

### 3. Skip or Continue
- **Continue**: Registers the protocol and prepares OAuth
- **Skip**: You can register the protocol later in Settings

## Connecting to MyAnimeList

### Method 1: From the Menu
1. Click **File → Connect to MAL**
2. The authentication dialog opens
3. Click **Connect to MAL** button
4. Your browser opens to MyAnimeList
5. Log in and authorize Mirenku
6. You're automatically returned to Mirenku

### Method 2: From Settings
1. Open **Settings** (File → Settings or Ctrl+,)
2. Go to the **MyAnimeList** tab
3. Click **Connect Account**
4. Follow the browser prompts

### Method 3: Quick Connect
Press **Ctrl+Shift+M** to open the MAL connection dialog directly.

## Protocol Registration

### What is Protocol Registration?
Protocol registration allows Mirenku to handle `mirenku://` URLs. This is how MyAnimeList sends you back to the app after login.

### How to Register/Unregister

#### From Settings:
1. Open Settings (File → Settings)
2. Go to **Protocol** tab
3. Status shows if protocol is registered
4. Use **Register** or **Unregister** buttons

#### Registry Location (Advanced):
The protocol is registered at:
```
HKEY_CURRENT_USER\Software\Classes\mirenku
```

### Portable Installation
If you move Mirenku to a different folder:
- The app detects the move automatically
- You'll be prompted to update the registration
- This ensures the protocol always points to the correct location

## Security Features

### Token Storage
Mirenku uses a three-tier encryption system for storing OAuth tokens:

1. **OS Keyring** (Primary)
   - Windows: Credential Manager
   - macOS: Keychain
   - Linux: Secret Service

2. **Fernet Encryption** (Fallback)
   - Industry-standard symmetric encryption
   - Key derived from machine ID

3. **Base64 Encoding** (Last Resort)
   - Only used if other methods fail
   - You'll see a security warning

### PKCE (Proof Key for Code Exchange)
- Prevents authorization code interception
- Generates unique challenge for each login
- Industry-standard OAuth2 security

### State Parameter
- Prevents CSRF attacks
- Validates OAuth callbacks
- Ensures responses match requests

### No Password Storage
- Mirenku NEVER stores your MAL password
- Only secure OAuth tokens are saved
- Tokens can be revoked anytime

## Troubleshooting

### Browser Doesn't Open
**Problem**: Clicking "Connect to MAL" doesn't open browser

**Solutions**:
1. Check your default browser is set correctly
2. Try copying the URL from the log file
3. Manually open the URL shown in the dialog

### "Not Primary Instance" Error
**Problem**: OAuth fails with "Not primary instance" message

**Solution**:
1. Close all Mirenku windows
2. Check Task Manager for lingering processes
3. Restart Mirenku

### Protocol Not Registered
**Problem**: Browser shows "mirenku:// protocol not found"

**Solutions**:
1. Open Settings → Protocol
2. Click "Register Protocol"
3. Restart your browser
4. Try again

### Token Expired
**Problem**: "Authentication failed" after being logged in

**Solution**:
- Mirenku automatically refreshes tokens
- If refresh fails, reconnect via Settings

### Moved Installation
**Problem**: OAuth stopped working after moving Mirenku

**Solution**:
1. Launch Mirenku from new location
2. Accept the prompt to update protocol registration
3. Reconnect to MAL if needed

## FAQ

### Q: Is my MAL password stored?
**A**: No, never. Mirenku only stores OAuth tokens, which are encrypted.

### Q: Can I use Mirenku on multiple computers?
**A**: Yes, but you'll need to authenticate on each computer separately.

### Q: How do I disconnect from MAL?
**A**: Open the MAL authentication dialog and click "Disconnect".

### Q: What permissions does Mirenku request?
**A**: 
- Read your anime list
- Update your anime list
- Read your profile information

### Q: Can I revoke access?
**A**: Yes, visit [MyAnimeList Settings](https://myanimelist.net/editprofile.php?go=apps) to revoke access.

### Q: Why use OAuth instead of username/password?
**A**: 
- More secure (no password storage)
- Supports 2FA if enabled on MAL
- Can be revoked without changing password
- Industry-standard authentication

### Q: What if I skip protocol registration?
**A**: You can still use Mirenku, but you'll need to manually copy the authorization code from your browser after logging in to MAL.

### Q: Is the protocol registration permanent?
**A**: It persists until you uninstall Mirenku or manually unregister it via Settings.

### Q: Can I use a custom Client ID?
**A**: Advanced users can register their own MAL application and use their Client ID. This is configured in Settings.

## Advanced Configuration

### Custom Client ID
For developers or advanced users:

1. Register your app at [MAL API Config](https://myanimelist.net/apiconfig)
2. Set App Type to "other"
3. Set Redirect URL to `mirenku://auth`
4. Copy your Client ID
5. In Mirenku Settings → MyAnimeList → Enter Client ID

### Manual Token Management
Token files are stored at:
- Windows: `%APPDATA%\Mirenku\mal_tokens.json`
- macOS: `~/Library/Application Support/Mirenku/mal_tokens.json`
- Linux: `~/.config/Mirenku/mal_tokens.json`

**Warning**: These files contain encrypted tokens. Do not share or modify them.

### Logging
OAuth events are logged for debugging:
- Windows: `%APPDATA%\Mirenku\logs\`
- macOS: `~/Library/Logs/Mirenku/`
- Linux: `~/.local/share/Mirenku/logs/`

Log files do NOT contain tokens or sensitive data.

## Getting Help

### Support Channels
- GitHub Issues: [Report problems](https://github.com/yourusername/mirenku/issues)
- Documentation: Check this guide first
- Logs: Include relevant log entries (no tokens!)

### Information to Provide
When reporting OAuth issues:
1. Mirenku version
2. Operating system
3. Error messages (exact text)
4. Steps to reproduce
5. Relevant log entries

### Privacy Note
When sharing logs or screenshots:
- Tokens are automatically redacted
- Remove any personal information
- Don't share your Client ID publicly

---

## Quick Reference

### Keyboard Shortcuts
- `Ctrl+Shift+M`: Open MAL connection dialog
- `Ctrl+,`: Open Settings
- `Esc`: Close dialogs

### Status Indicators
- ✅ **Green**: Connected to MAL
- ❌ **Red**: Not connected
- 🔄 **Blue**: Connecting/Refreshing

### Token Lifetime
- Access Token: 31 days
- Refresh Token: No expiry (until revoked)
- Auto-refresh: 5 minutes before expiry

---

*Last Updated: September 2025*
*Mirenku Version: 0.3.0+*