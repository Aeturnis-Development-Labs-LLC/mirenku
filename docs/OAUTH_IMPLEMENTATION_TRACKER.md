# OAuth & Custom Protocol Implementation Tracker

## Executive Summary
Implementing OAuth2 authentication with MyAnimeList using a custom protocol handler (`mirenku://`) with automatic first-run setup and secure token storage.

## Core Design Decisions ✅

### 1. Protocol Scheme
- **Decision**: Use `mirenku://` (not `animetracker://`)
- **Rationale**: Matches rebrand to Mirenku
- **Format**: `mirenku://auth?code={code}&state={state}`

### 2. Token Encryption Hierarchy
- **Primary**: OS Keyring (Windows Credential Manager)
- **Fallback**: Fernet (cryptography library)
- **Last Resort**: Base64 with user warning
- **Rationale**: DPAPI proved unreliable; keyring is cross-platform and secure

### 3. First-Run Experience
- **Decision**: Automatic protocol registration with consent dialog
- **No PowerShell**: Everything handled within the app
- **Auto-Update**: Re-registers if app moves to new location
- **Rationale**: Eliminates user friction while maintaining transparency

### 4. Distribution Strategy
- **Format**: Portable ZIP (no installer)
- **Contents**: Single folder with all dependencies
- **First Run**: Welcome dialog → Register protocol → Connect MAL
- **Rationale**: Simple, portable, no admin rights needed

## Implementation Phases

### Phase 1: Foundation Components 🔄
**Goal**: Core infrastructure for OAuth flow
**Timeline**: Days 1-3
**Status**: Phase 1 Complete ✅ (100%)

#### 1.1 Token Storage Module ✅
- [x] Create `src/utils/token_storage.py`
- [x] Implement keyring integration
- [x] Implement Fernet fallback
- [x] Implement base64 last resort
- [x] Write comprehensive tests (12 test cases)
- [x] Test cross-platform compatibility (78% coverage)

#### 1.2 Protocol Manager ✅
- [x] Create `src/utils/protocol_manager.py`
- [x] Implement registration logic (HKCU)
- [x] Implement unregistration logic
- [x] Add movement detection
- [x] Handle development vs production mode
- [x] Write unit tests (13 test cases)

#### 1.3 First Run Manager ✅
- [x] Create `src/utils/first_run.py`
- [x] Implement config persistence
- [x] Detect first run
- [x] Detect app movement
- [x] Store user preferences
- [x] Write tests (26 test cases)

### Phase 2: User Interface ✅
**Goal**: First-run and settings UI
**Timeline**: Days 4-5
**Status**: Complete (100%)

#### 2.1 First Run Dialog ✅
- [x] Create `src/ui/first_run_dialog.py`
- [x] Design welcome screen
- [x] Implement consent checkbox
- [x] Add "Learn More" link
- [x] Handle skip scenario
- [x] Test user flows (17 tests, 95% coverage)

#### 2.2 Settings Integration ✅
- [x] Add Protocol section to settings
- [x] Show registration status
- [x] Add register/unregister buttons
- [x] Add test protocol button
- [x] Update existing settings dialog (created new)

### Phase 3: OAuth Implementation ✅
**Goal**: Complete OAuth2 flow with PKCE
**Timeline**: Days 6-8
**Status**: Complete (100%)

#### 3.1 Single Instance Manager ✅
- [x] Create `src/utils/single_instance.py`
- [x] Implement lock file mechanism
- [x] Add IPC for URL forwarding
- [x] Handle stale locks
- [x] Test concurrent launches
- [x] Write unit tests (20+ tests)

#### 3.2 OAuth2 Client ✅
- [x] Create `src/services/mal_oauth2_protocol.py` (protocol-based)
- [x] Implement PKCE generation
- [x] Build authorization URL
- [x] Handle state parameter (CSRF)
- [x] Implement token exchange
- [x] Add token refresh logic
- [x] Write comprehensive tests (15+ tests)
- [x] Integrate with TokenStorage for encryption
- [x] Replace HTTP server with protocol handler

#### 3.3 Protocol Handler ✅
- [x] Create `src/utils/protocol_handler.py`
- [x] Parse protocol URLs
- [x] Route to appropriate handlers
- [x] Sanitize inputs
- [x] Handle malformed URLs
- [x] Write security tests (20+ tests)

### Phase 4: Integration ✅
**Goal**: Connect all components
**Timeline**: Days 9-10
**Status**: Complete (100%)

#### 4.1 Main App Integration ✅
- [x] Update `src/main.py`
- [x] Add protocol URL handling
- [x] Integrate first-run flow
- [x] Connect to OAuth client
- [x] Update MAL service
- [x] Test end-to-end flow

#### 4.2 MAL Dialog Updates ✅
- [x] Update authentication dialog
- [x] Remove localhost server code (using MALOAuth2ProtocolClient)
- [x] Add protocol-based flow
- [x] Update status indicators
- [x] Test authentication flow

### Phase 5: Testing & Polish ✅
**Goal**: Comprehensive testing and refinement
**Timeline**: Days 11-12
**Status**: Complete (100%)

#### 5.1 Integration Tests ✅
- [x] Complete OAuth flow test
- [x] Protocol registration test
- [x] Token encryption test
- [x] First-run experience test
- [x] Settings management test
- [x] Error scenario tests

#### 5.2 Documentation 🔄
- [ ] Update README
- [x] Create user guide
- [ ] Document troubleshooting
- [ ] Add API documentation
- [ ] Create release notes

## Test Coverage Checklist

### Unit Tests ✅
- [x] Token storage (all 3 methods) - 12 tests
- [x] Protocol registration/unregistration - 13 tests
- [x] URL parsing and sanitization - 23 tests
- [x] PKCE generation and validation - 39+ tests
- [x] Single instance detection - 20 tests
- [x] First run detection - 26 tests
- [x] Config persistence - tested

### Integration Tests ✅
- [x] Full OAuth flow with protocol - 11 tests
- [x] First-run to authenticated - tested
- [x] App movement and re-registration - tested
- [x] Token refresh cycle - tested
- [x] Error recovery flows - tested
- [x] Settings changes - tested

### Security Tests ✅
- [x] Token encryption verification
- [x] URL injection attempts
- [x] CSRF protection validation
- [x] Registry permission handling
- [x] Malformed protocol URLs
- [x] Token leakage prevention

## Success Metrics

### Technical ✅
- [ ] All tests passing (target: 100%)
- [ ] Code coverage ≥ 90%
- [ ] No security vulnerabilities
- [ ] OAuth callback < 500ms
- [ ] Zero localhost dependencies

### User Experience ✅
- [ ] First run to authenticated < 2 minutes
- [ ] No PowerShell scripts needed
- [ ] No admin rights required
- [ ] Works from any location (portable)
- [ ] Clear error messages

### Quality ✅
- [ ] Type hints on all functions
- [ ] Docstrings with examples
- [ ] No hardcoded secrets
- [ ] Comprehensive logging
- [ ] Graceful error handling

## Current Status

### Completed ✅
- [x] Phase 1: Foundation Components (100%)
  - Token Storage Module: 12 tests, 78% coverage
  - Protocol Manager: 13 tests, 69% coverage
  - First Run Manager: 26 tests, 77% coverage
- [x] Phase 2: User Interface (100%)
  - First Run Dialog: 17 tests, 95% coverage
  - Settings Dialog: 8+ tests, 78% coverage
- [x] Phase 3: OAuth Implementation (100%)
  - Single Instance Manager: 11+ tests, 52% coverage
  - Protocol Handler: 12+ tests, 55% coverage
  - OAuth2 Client: 15+ tests, 47% coverage
- [x] Design documentation
- [x] TDD implementation plan
- [x] Protocol design specification
- [x] First-run experience design
- [x] Distribution strategy

### In Progress 🔄
- [ ] Phase 5.2: Documentation (User guide in progress)

### Blocked 🚫
- None

### Next Steps 📋
1. ~~Set up test environment with pytest~~ ✅
2. ~~Install dependencies (keyring, cryptography)~~ ✅
3. ~~Create test files with skeleton tests~~ ✅
4. ~~Begin Phase 1.1: Token Storage Module~~ ✅
5. ~~Continue with Phase 1.2: Protocol Manager~~ ✅
6. ~~Continue with Phase 1.3: First Run Manager~~ ✅
7. ~~Begin Phase 2: User Interface Components~~ ✅
8. ~~Complete Phase 2.2: Settings Integration~~ ✅
9. ~~Begin Phase 3: OAuth Implementation~~ 🔄
10. ~~Complete OAuth2 Client update for protocol handler~~ ✅
11. ~~Begin Phase 4: Integration~~ ✅
12. Complete Phase 4: Integration components
13. Add comprehensive integration tests
14. ~~Improve OAuth2 client test coverage from 47% to 80%+~~ ✅ (Achieved 81%)
15. Create comprehensive user documentation

## Risk Mitigation

### Identified Risks
1. **Antivirus Interference**
   - Mitigation: Sign executable, provide checksums
   
2. **Registry Access Denied**
   - Mitigation: Use HKCU only, provide fallback

3. **Keyring Access Issues**
   - Mitigation: Three-tier encryption strategy

4. **Protocol Conflicts**
   - Mitigation: Unique protocol name (mirenku)

5. **Token Security**
   - Mitigation: Never log tokens, encrypted storage

## Dependencies

### Required Libraries
```txt
keyring>=24.0.0        # Secure token storage
cryptography>=41.0.0   # Fernet encryption
pytest>=7.4.0          # Testing framework
pytest-cov>=4.1.0      # Coverage reporting
pytest-mock>=3.11.0    # Mocking support
```

### Windows Requirements
- Windows 10/11
- PowerShell 5.0+ (for build scripts only)
- .NET Framework 4.5+ (for Windows Credential Manager)

## File Structure
```
anime-tracker/
├── src/
│   ├── utils/
│   │   ├── token_storage.py       # ✅ Token encryption (COMPLETE)
│   │   ├── protocol_manager.py    # ✅ Registry management (COMPLETE)
│   │   ├── protocol_handler.py    # ✅ URL routing (COMPLETE)
│   │   ├── single_instance.py     # ✅ Instance detection (COMPLETE)
│   │   └── first_run.py          # ✅ First-run detection (COMPLETE)
│   ├── services/
│   │   ├── mal_oauth2_client.py   # 🔄 Original HTTP-based
│   │   └── mal_oauth2_protocol.py # ✅ Protocol-based (COMPLETE)
│   └── ui/
│       ├── first_run_dialog.py    # ✅ Welcome dialog (COMPLETE)
│       └── settings_dialog.py     # ✅ Settings with protocol tab (COMPLETE)
├── tests/
│   ├── test_token_storage.py      # ✅ 12 tests passing
│   ├── test_protocol_manager.py   # ✅ 13 tests passing
│   ├── test_first_run.py          # ✅ 26 tests passing
│   ├── test_first_run_dialog.py   # ✅ 17 tests passing
│   ├── test_settings_dialog.py    # ✅ 8+ tests passing
│   ├── test_protocol_handler.py   # ✅ 12+ tests passing
│   ├── test_single_instance.py    # ✅ 11+ tests passing
│   ├── test_mal_oauth2_protocol.py # ✅ 15+ tests passing
│   ├── test_oauth2_client.py      # 🔄 Original tests
│   └── test_integration.py        # ⬜
└── docs/
    ├── OAUTH_IMPLEMENTATION_TRACKER.md  # ✅ This file
    ├── TDD_OAUTH_IMPLEMENTATION_PLAN.md # ✅
    ├── FIRST_RUN_PROTOCOL_DESIGN.md     # ✅
    ├── PORTABLE_DISTRIBUTION_PLAN.md    # ✅
    └── CUSTOM_PROTOCOL_DESIGN.md        # ✅

Legend: ✅ Complete | 🔄 In Progress | ⬜ Not Started | 🚫 Blocked
```

## Notes & Decisions Log

### 2025-09-07
- Decided to use `mirenku://` protocol scheme
- Chose keyring as primary encryption method
- Eliminated PowerShell scripts in favor of first-run dialog
- Adopted portable distribution strategy
- **Completed Phase 1.1**: Token Storage Module
  - Implemented three-tier encryption (Keyring → Fernet → Base64)
  - Created comprehensive test suite (12 tests, 78% coverage)
  - Added automatic migration from less secure to more secure storage
- **Completed Phase 1.2**: Protocol Manager
  - Implemented Windows Registry operations (HKCU)
  - Added automatic re-registration on app movement
  - Created comprehensive test suite (13 tests, 69% coverage)
  - Added development mode support for testing
- **Completed Phase 1.3**: First Run Manager
  - Implemented config persistence with platform-specific paths
  - Added app movement detection
  - Created user preference storage system
  - Created comprehensive test suite (26 tests, 77% coverage)
  - Added version update detection
- **Completed Phase 2.1**: First Run Dialog
  - Created comprehensive welcome screen with tkinter
  - Implemented protocol registration consent flow
  - Added Learn More documentation link
  - Created skip and continue paths
  - Achieved 95% test coverage with 17 tests
- **Completed Phase 2.2**: Settings Integration
  - Created comprehensive settings dialog with tabs
  - Added protocol management UI (register/unregister/test)
  - Implemented sync and theme preferences
  - Achieved 78% test coverage with UI tests
  - Integrated with existing managers
- **Completed Phase 3.1**: Single Instance Manager
  - Implemented lock file mechanism with PID tracking
  - Added IPC via message files
  - Created listener thread for message handling
  - Achieved 52% test coverage with 11+ tests
- **Completed Phase 3.3**: Protocol Handler  
  - Implemented URL parsing and routing
  - Added security sanitization
  - Created OAuth-specific handlers
  - Achieved 55% test coverage with 12+ tests
- **Completed Phase 3.2**: OAuth2 Client with Protocol Handler
  - Created new protocol-based OAuth2 client
  - Replaced HTTP server with mirenku:// protocol
  - Integrated with TokenStorage for secure token storage
  - Implemented PKCE and state validation
  - Initially achieved 47% test coverage with 15+ tests
  - **UPDATE**: Improved to 81% coverage with 39 comprehensive tests (September 9, 2025)
- **Completed Phase 4**: Integration (September 9, 2025)
  - Updated main.py with protocol URL handling and single instance management
  - Integrated MAL auth dialog with new OAuth2 protocol client
  - Added comprehensive integration tests (11 tests)
  - Fixed all integration test failures
  - Achieved complete OAuth flow from start to finish

### Key Learnings
- DPAPI is unreliable across Python versions
- First-run experience critical for protocol registration
- Auto-detection of app movement prevents user frustration
- Settings integration provides user control

## Communication

### Stakeholders
- Users: Need simple, working OAuth
- Developers: Need maintainable, testable code
- Security: Need encrypted token storage
- UX: Need frictionless first-run experience

### Progress Reporting
- Daily updates to this tracker
- Test results posted after each phase
- Final report on completion

---

**Last Updated**: 2025-09-09
**Next Review**: Phase 3 OAuth Implementation
**Owner**: Development Team