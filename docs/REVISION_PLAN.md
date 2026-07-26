# Mirenku Revision Plan — v0.3.2 → v0.4.0

**Date:** 2026-07-23
**Status:** Rev 2 — amended after design-critic review of the plan itself; pending owner approval
**Source:** Design-critic review of the full codebase (verdict: NEEDS REVISION; full rewrite REJECTED — refactor in place), followed by a critic pass on this plan (Rev 1 verdict: NEEDS REVISION — amendments incorporated below)

## Guiding principle

Privacy-first is served by **fewer** code paths, not more security modules:

1. One data directory, one app identity.
2. One token store, two tiers (OS keyring → Fernet), nothing decorative.
3. One documented list of hosts the app ever contacts.
4. Zero code paths that cannot be explained or that never execute.

Verified baseline facts driving this plan: the live OAuth flow is the localhost HTTP callback in `mal_oauth2_http.py`; the `mirenku://` protocol flow targets `MALOAuth2ProtocolClient`, which is imported by **nothing** in `src/`; ~130KB of `src/` is dead or supports flows that cannot complete.

---

## Phase 0 — REMOVE (dead code; no behavior change)

Delete outright. Each item's justification is stated so deletions survive review.

### Source files

| File | Size | Why it is dead |
|---|---|---|
| `src/services/mal_oauth2_protocol.py` | 40.8KB | Defines `MALOAuth2ProtocolClient`; zero importers in `src/`. The client actually constructed is `MALOAuth2HTTPClient` (`src/ui/mal_auth_dialog.py:305-308`). |
| `src/services/mal_oauth2_client.py` | 18KB | Zero importers. |
| `src/utils/protocol_manager.py` | 22.3KB | Registry manipulation for the `mirenku://` handler that feeds the dead protocol client. |
| `src/utils/protocol_handler.py` | 9.7KB | Same flow. Imported only by `main.py`'s dead branch (see below). |
| `src/services/offline_queue_service.py` | 11.3KB | Not wired into any live mutation path; superseded by the `sync_queue` table design in `sync_service` (which Phase 1 wires up). |
| `src/utils/key_rotation.py` | 15.3KB | Reachable only via `TokenStorage.enable_key_rotation()` (`src/utils/token_storage.py:173`) — zero callers. |
| `src/utils/security_audit.py` | 14KB | Imported only by dead code (`key_rotation.py:392`, `mal_oauth2_protocol.py:23`). |
| `src/ui/security_dialog.py` | 6KB | Imported nowhere. |
| `oauth_success.html` (repo root) | — | Opened only from the dead protocol branch (`src/main.py:60-68`). The HTTP callback serves its own success page. |

### Code branches (edit, don't delete file)

- `src/main.py:28-78` — `handle_protocol_url()`: calls `oauth_client._handle_oauth_callback` / `.auth_received`, attributes that exist only on the dead protocol client. Any `mirenku://auth` arrival raises `AttributeError` today. Delete the function.
- `src/main.py:81-90` — `handle_message()`: only routes `protocol_url`/`open_url` to the dead handler. Note: second instances send `{"action": "activate"}` (`src/main.py:128`) which this handler does **not** route — bring-to-front has never worked. Phase 1 decides: implement `activate` (deiconify + lift + focus) or drop the IPC listener entirely. **Decision: implement `activate`** — it is the one legitimately useful IPC message; keep the listener with `activate` as its only action.
- `src/main.py:107-111, 120-125, 200-202` — protocol-URL CLI detection and forwarding. Delete.
- `src/utils/single_instance.py` — **keep** the lock; strip the `protocol_url` forwarding path; keep the message channel only for `activate`.
- `src/ui/first_run_dialog.py`, `src/ui/settings_dialog.py` — remove "Register protocol handler" UI and any `protocol_manager` imports.
- `src/utils/first_run.py` — trim the `protocol_registered` preference and `should_register_protocol()` (`first_run.py:243, 265-284`); they belong to the dead protocol flow.
- **Registry cleanup before code deletion:** existing installs have an HKCU `mirenku://` handler registration pointing at the exe, written via `protocol_manager.py` — and Phase 0 deletes the only code able to remove it. Add a one-time startup cleanup that deletes the registry key (Windows; equivalent desktop-file cleanup on Linux), ship it alongside the F5 migration, **then** the `protocol_manager.py` deletion is safe.
- `src/models/database.py:290-303` — `mal_credentials` table (contains a `client_secret` column, never read/written by live code). Drop via migration in Phase 1, and delete the creation code.

### Tests

Delete tests that exist solely to protect dead code (they make deletion look expensive; they protect nothing users run):

- `tests/test_mal_oauth2_protocol.py`, `tests/test_mal_oauth2_protocol_extended.py`
- `tests/test_protocol_handler.py`, `tests/test_protocol_manager.py`
- `tests/test_security_audit_logging.py`
- `tests/test_token_encryption_rotation.py` — **audit first**: keep any cases that exercise the two live TokenStorage tiers; delete only rotation cases.
- `tests/test_single_instance.py` — trim protocol-forwarding cases; keep lock + activate cases.
- `tests/test_integration_oauth.py`, `tests/test_pkce_enhancement.py`, `tests/test_oauth_state_timestamp.py`, `tests/test_oauth_rate_limiting.py` — **audit which client they target**; keep everything that targets `mal_oauth2_http.py`, delete what targets the protocol client.
- `tests/test_first_run.py` / `tests/test_first_run_dialog.py` — trim protocol-registration cases.
- `tests/test_error_sanitization.py` — fate is tied to F3's wire-or-delete decision on `ErrorSanitizer`: if the sanitizer is wired into live logging, keep and extend these tests; if it's deleted, delete them with it.

### Repo hygiene

- Delete `coverage.xml` (282KB build artifact) and add to `.gitignore`.
- Delete `SYNC_FIXES_SUMMARY.md` after its open items are transcribed into Phase 1 below (they are).
- Result check: four `mal_oauth2_*` files become **one** (`mal_oauth2_http.py`).

---

## Phase 1 — FIX (live bugs; behavior changes users will notice)

**F1 — Database watcher watches a nonexistent file.**
`src/ui/main_window.py:105` watches `data_dir / "anime.db"`; real DB is `anime_tracker.db` (`src/utils/config.py:32`). Fix: use `config.get_db_path()` — never re-derive the filename. Auto-refresh has never fired; after the fix, verify the watcher's refresh path doesn't fight auto-save.

**F2 — Sync can destroy local data (transcribed from SYNC_FIXES_SUMMARY.md: "Pull Deletes Local Data — NOT FIXED").**

*F2a — PREREQUISITE: normalize timestamps to one clock.* Three clock sources currently write the same rows, and any timestamp-based merge built on top of them will misfire for every user west of UTC:
- SQLite trigger writes `updated_at` in **UTC** (`src/models/database.py:171-176`, `CURRENT_TIMESTAMP`) — and fires on every UPDATE, **including sync's own pull-writes**.
- `sync_service` stamps `last_mal_sync` with naive **local time** (`sync_service.py:598, 621`).
- `anime_service` stamps `date_updated` in **hardcoded EST (UTC-5, no DST)** (`src/utils/timezone.py:7, 17-19`; `anime_service.py:113`).
Concrete failure if skipped: a US-Eastern user's clean pull sets `last_mal_sync` = local now while the trigger sets `updated_at` = UTC now = local+5h, so every synced row permanently reads as locally-modified and gets re-pushed or conflict-flagged forever. `detect_conflicts()` (`sync_service.py:263`) has this bug **today**.
Fix: all timestamps become UTC ISO-8601. Delete the hardcoded-EST `get_current_datetime` (`timezone.py`). Drop the `updated_at` trigger and stamp explicitly in code (so sync pull-writes can stamp `updated_at = last_mal_sync` and not self-flag), or make the trigger conditional. Existing rows get a best-effort migration in the F5 schema pass (assume legacy local-time values; exactness is not required — the first post-fix sync re-baselines).

*F2b — Fix the crash:* `sync_service.py:482`: `from repositories.anime_repository import ...` — package doesn't exist (it's `models.anime_repository`). Currently crashes `pull_from_mal` for any anime not already local. Fix the import; add a test that pulls a novel anime. (Ships in v0.3.3 independent of the merge work.)
**Discovered while fixing (also shipped in v0.3.3):** fresh installs never had the sync schema at all — `_create_schema()` predates v2 (no `sync_status`/`last_mal_sync`/`sync_queue`) and `initialize()` stamped version 2 without running the migration. Fixed by running the idempotent v2 migration on fresh installs. **Note for F5:** when writing schema v3, consolidate the base schema to current so fresh-install and migrated databases are structurally identical by construction, not by migration replay.

*F2c — Wire the queue with changed-field sets:* `sync_service.py:87` (`queue_sync_operation`) has zero callers, so the queue is never populated and the "Queue: N" label (`src/ui/main_window.py:992`) always reads 0. Fix: call it from every `AnimeService` mutation (add/update/delete/score/progress) when MAL is linked, and **carry the set of changed field names in the `sync_queue.data` JSON payload** (`database.py:268`). This is the mechanism that makes per-field merge possible — one `updated_at` per row cannot support it alone.

*F2d — Merge policy:* `full_sync_from_mal` (`sync_service.py:582-601`) stops overwriting unconditionally. Policy: **per-field newest-wins**, where "locally newer" is determined by the changed-field sets in pending queue entries (from F2c) plus `updated_at` vs `last_mal_sync` (valid after F2a). Fields with no pending local change take the MAL value; fields with a pending local change keep local and remain queued for push. Wire `detect_conflicts()` (post-F2a) to build the per-sync summary dialog listing exactly what changed in each direction.

*F2e — Deletion policy:* `full_sync_from_mal` inserts any MAL entry not present locally (`sync_service.py:603-626`), so a locally-deleted anime with a pending `delete` op is **resurrected** by the next pull. Rule: before re-adding a pulled entry, check the queue for a pending `delete` on that `mal_id` — if present, skip the re-add and let the delete push. (Queue entries thus serve as tombstones; no separate tombstone table needed.)

**F3 — OAuth secrets in logs.**
`src/services/mal_oauth2_http.py:222` logs the full authorization URL at INFO. MAL supports only PKCE `plain` (`:195`), so the logged `code_challenge` **is** the verifier. `:290-295` logs code/verifier prefixes. Logs persist 7 days (`src/main.py:100`). Fix: delete these log lines (log the event, never the parameters). Then either wire `ErrorSanitizer` into the live logging config as a filter, or delete it too — currently it is only imported by dead code, which is the worst of both.

**F4 — Swallowed exception → NameError.**
`src/ui/main_window.py:1050-1055`: `except Exception:` without binding, followed by a lambda using `{e!s}`. Auth failures crash the error dialog. Fix: `except Exception as e:` and bind the message into the lambda's default arg (`lambda msg=str(e): ...`) to avoid late-binding.

**F5 — Consolidate app identity and storage (privacy feature: "delete my data" must have one answer). SHIPS IN v0.4.0 — this is not patch-release material.**
Today: DB+config in `%LOCALAPPDATA%\AnimeTracker` (`src/utils/config.py:16, 44-45`), tokens+Fernet key in `~\.mirenku` (`src/utils/token_storage.py:50`), locks in `%TEMP%\Mirenku` (`src/utils/single_instance.py:56-59`). Also: `token_storage_path` passed at `src/ui/mal_auth_dialog.py:307-308` is accepted then ignored.
Fix: single identity **Mirenku**; migrate everything to the platform app-data dir (`%LOCALAPPDATA%\Mirenku`; XDG dirs on Linux; `~/Library/Application Support/Mirenku` on macOS). Add **Settings → "Delete all my data"** that wipes the one directory + keyring entries.

*Migration procedure (this is the single riskiest change in the plan — the following are requirements, not suggestions):*
- **Full file inventory to migrate:** `anime_tracker.db`, `config.json`, `backups/`, `mal_config.json` (holds the MAL client_id — miss it and every user is re-prompted, `mal_auth_dialog.py:319`), and from `~\.mirenku`: `tokens.enc`, `.key`, `tokens.b64`, `mal_token_metadata.json` (miss it and split-storage users lose auth, `token_storage.py:332-347`), `keys.json`. **Discovered during Phase 0:** there is a FOURTH location — `first_run.json` lives in `%APPDATA%\Mirenku` (Roaming, via `first_run.py:_get_config_dir`) while everything else is in Local/home; include it in the migration. **Caches are deleted, not moved** (`mal_cache/` — its own SQLite, `mal_service.py:104` — and `image_cache/`); they rebuild on demand.
- **Idempotent, per-file copy → verify → delete-source.** The trigger condition is per-file presence in the old location, NOT "new dir exists" — a crash mid-migration must resume on next startup, never orphan files. `tokens.enc` + `.key` are an **atomic pair**: copy and verify both before deleting either (a `tokens.enc` without its key is permanently undecryptable).
- **`Database.backup()` into the new dir before touching the old one.** This also covers the user who later re-runs an old 0.3.2 exe (which will recreate empty old dirs).
- **Run position:** migration executes in `main()` before `Database` connect and before any `TokenStorage` instantiation.
- Leave a `MOVED.txt` breadcrumb in each old location. Registry cleanup of the old `mirenku://` handler (see Phase 0) runs in this same pass.

*Schema migration v3 (same release, SQLite floor guaranteed by I2's Python 3.10+ raise — `DROP COLUMN` needs SQLite ≥ 3.35, which Python 3.8-era builds don't have; this is why F5 cannot ship in 0.3.3):*
- Drop table `mal_credentials`.
- Drop columns: `mal_sync_date` (referenced only as a dataclass field, `anime.py:41`) and anime's `created_at`. **Survivors are `date_added`, `date_updated`, `updated_at`, `last_mal_sync`** — live code uses both `date_added`/`date_updated` (`anime_service.py:68-69, 113`; `anime_repository.py:99-100, 402`; `persistence.py:209-226`) **and** `updated_at` (F2's merge) — do NOT "keep one of each pair" blindly.
- Then unify `date_updated`/`updated_at` into one column **in the same commit as the code changes** to every call site listed above — a migration-only change breaks export/"recently added"/merge depending on which half survives.
- F2a's timestamp normalization of existing rows happens in this migration.

**F6 — Version triplication.**
`src/utils/config.py:17` says 0.1.1; `src/ui/main_window.py:30` fallback says 0.3.1; `pyproject.toml` says 0.3.2. Fix: single source in `src/__init__.py`; pyproject reads it via `[tool.setuptools.dynamic]`; everything else imports it.

**F8 — OAuth test-coverage gap (created by Phase 0, fill in Phase 1).**
The deleted protocol-client test files (PKCE, state timestamp, rate limiting, refresh buffer) tested the DEAD client; `mal_oauth2_http.py` — the live client — has no dedicated test file. Write `tests/test_mal_oauth2_http.py` covering: PKCE-plain verifier/challenge, CSRF state validation, port fallback, token refresh (success + failure), refusal to report success when token persistence fails, and 401-retry in `make_api_request`. (Partial interim coverage exists via the retargeted `test_mal_sync_integration.py` and `test_token_refresh_buffer`-style flow now folded into it.)

**F7 — Dependency drift.**
`requirements.txt` and `pyproject.toml` disagree (pytz/watchdog only in pyproject; websockets/pystray/jikanpy only in requirements; `psutil` — used by `src/utils/single_instance.py:16` — in **neither**). Fix: `pyproject.toml` is the single source; `requirements.txt` becomes `pip install -e .` instructions or is deleted; scrobbling deps (websockets/pystray) move to an optional extra `[project.optional-dependencies] scrobbling` until that feature ships.

---

## Phase 2 — RETOOL (architecture; makes the GUI swappable)

**R1 — Composition root out of the widget.**
`src/ui/main_window.py:38-121` constructs Database wiring, services, watchers, and managers inside `MainWindow.__init__`. Move construction into an `AppContext` (plain dataclass) built in `main.py` and injected. MainWindow receives collaborators; it stops owning them.

**R2 — One threading policy.**
Ad-hoc `threading.Thread` spawns at `src/ui/main_window.py:899, 1026, 1143` each hand-roll marshaling. Replace with one utility: `run_async(fn, on_done, on_error)` that owns thread creation and `root.after(0, ...)` marshaling. Give `Database` per-thread connections via `threading.local` — this deletes the per-call-site workaround at `main_window.py:1155-1164` and removes the thread-affinity crash class entirely (also a scrobbling prerequisite, see below).
Two additional items belong in this pass:
- **The 30-second status poll can freeze the UI on network.** `update_mal_status` (`main_window.py:985, 995, 1003`) calls `is_authenticated()` on the Tk main thread, and that path can perform a synchronous token refresh over the network (`mal_oauth2_http.py:350-396`) → periodic multi-second freezes. Move the check through `run_async`.
- **`Database.execute()` returns a closed cursor.** `database.py:307-322` returns a cursor whose context manager already closed it; any caller that fetches from the return value breaks. Fix or remove the method.

**R3 — Extract SyncController.**
Sync/auth orchestration moves out of MainWindow into a `SyncController` exposing `on_progress` / `on_complete` / `on_error` callbacks. After R1-R3, `main_window.py` (currently 56.8KB / ~1200 lines) becomes a view. This is the step that makes any future frontend (sv-ttk restyle now, pywebview or PySide6 later) a UI-only project.

**R4 — Theming out of the window class.**
Hand-rolled color constants live at `src/ui/main_window.py:141-198`. Extract to a theme module consumed by the sv-ttk setup in Phase 3.

---

## Phase 3 — IMPROVE (modernization)

**I1 — Look:** apply **sv-ttk** (or ttkbootstrap — decide by prototyping both on the main Treeview for an afternoon) over the existing ttk tree. Dark + light mode, keep the teal brand accent. Replace emoji-glyph buttons (`src/ui/main_window.py:308-346`) with text or bundled icons — emoji rendering is inconsistent on Linux.
**I2 — Toolchain:** raise floor to Python **3.10+** (3.8 EOL Oct 2024). Ruff `target-version = "py310"`. Replace pytz with stdlib `zoneinfo` (drops a dependency). Re-verify PyInstaller matrix on 3.10+.
**I3 — Privacy disclosure:** README + SECURITY.md list every host the app can contact and when: `api.myanimelist.net` (sync, opt-in), MAL CDN (cover images, when MAL features used), `api.jikan.moe` (unauthenticated search — **third party**, must be disclosed), `api.github.com` (update check, off by default). Note in SECURITY.md that keyring split-storage writes the short-lived access token to plaintext JSON (`src/utils/token_storage.py:299-307`) — documented trade-off.
**I4 — Keep:** `mal_oauth2_http.py` (PKCE-plain handling, CSRF state check `:260-262`, port fallback `:136-148`, refusal to claim success when tokens can't persist `:324-330`), `token_storage.py` two live tiers (incl. Windows 2560-byte keyring split `:281-322`), `models/*`, versioned migration skeleton (`src/models/database.py:207-219`), opt-in-by-default posture. These files are the hard-won value; do not rewrite them for style.

---

## Scrobbling — WIP, slated for redesign (do not fix in place)

**Status:** feature-flagged off by default (`src/services/scrobbling_manager.py:31`). It stays off and out of releases until redesigned. The current implementation is a prototype, not a base to patch.

### Why the current design is rejected

1. **Open door:** `src/services/websocket_server.py:263-264` binds localhost:7834 with no Origin validation and no authentication. Browsers permit any webpage to open a WebSocket to localhost — a malicious page can probe the user's library (the `detected` handler at `:135-163` returns match + progress + status) and write to it (`completed` at `:207-237`). For a privacy-first product this is the worst leak vector in the codebase.
2. **Crash on first use:** the server thread calls the main thread's `AnimeService` (`websocket_server.py:149, 221-226`) over a `check_same_thread=True` SQLite connection (`src/models/database.py:29`) → `sqlite3.ProgrammingError` on the first scrobble event. (Fixed as a side effect of R2.)
3. **Data over-sharing by design:** the reply to `detected` leaks library membership + progress + status to whoever asks. The extension doesn't need it.

### Redesign requirements (must-hold before any release)

- **Pairing, not open port:** explicit user-initiated pairing in Settings generates a shared secret; the extension must present it on connect. Unpaired connections are dropped before any payload is processed.
- **Origin allowlist:** accept only `chrome-extension://<id>` / `moz-extension://<id>` origins the user paired. Reject browser-page origins (`https://…`) unconditionally. **Implementation constraint the extension must honor:** WebSockets opened from *content scripts* carry the page's origin, not the extension's — only background/service-worker connections carry `chrome-extension://…`. Therefore the extension **must proxy all socket traffic through its background service worker.** Do not weaken the origin check to accommodate content-script connects; that failure is exactly what the check exists to prevent.
- **Pairing secret storage (extension side):** `chrome.storage.local` only. `chrome.storage.sync` is **prohibited** — it uploads the secret to the browser vendor's cloud, defeating the point of a privacy-first pairing secret.
- **Data minimization:** the extension *sends* detections; the app replies with an ack only. No library lookups exposed over the wire. Any "is this in my list" UI lives in the extension via explicit user action, not automatic probing.
- **Consent surface:** scrobbling toggle stays off by default; first pairing shows exactly what data crosses the boundary; per-site enable in the extension, not blanket.
- **Concurrency:** all DB access through the R2 per-thread-connection layer or a message queue drained on the main thread. No service sharing across threads.
- **Rate limiting** on the socket, and a visible "connected extension" indicator (the pystray tray icon is a natural home).

### Architecture options to evaluate in the redesign spike

| Option | Privacy posture | Cost |
|---|---|---|
| **A. WebSocket + pairing secret + Origin allowlist** (harden current approach) | Good, if requirements above hold | Lowest — keeps `websockets` dep and extension model |
| **B. Native Messaging host** (Chrome/Firefox native messaging) | Best — no open port exists at all; browser spawns the host and only the paired extension can talk to it | Per-browser manifests + an IPC hop from the host process to the running app; more packaging work in PyInstaller builds |
| **C. Local HTTP polling with token** | Weakest of the three; port still open | Not recommended |

**Recommendation to carry into the spike:** prototype **B** first — "no open port" is the strongest possible answer for a privacy-first product and eliminates the Origin problem by construction. Fall back to **A** if native-messaging packaging proves unmanageable across the three platforms.

**Spike exit criteria for option B** (each is a kill criterion — "fall back to A" must be a decision, not a discovery):
1. **Manifest self-healing:** native-messaging manifests embed an *absolute path* to the host binary. With installer-less standalone distribution, a moved/renamed exe silently breaks scrobbling. The app must rewrite/verify its manifests on every startup, and the spike must confirm this works for Chrome + Firefox on all three platforms.
2. **Host spawn cost:** the browser spawns the host per session. A onefile PyInstaller host pays multi-second extraction per spawn — the host must be onedir or a separate tiny binary. Measure it.
3. **Host→app channel is defined, and it preserves "no open port."** If the host relays to the running app over a localhost socket, option B's headline advantage evaporates and A is strictly simpler. Portless candidate: host writes to a WAL-mode SQLite queue table and the (F1-fixed) db watcher picks it up — requires `PRAGMA journal_mode=WAL` (not currently set), and note that WAL writes don't bump the main db file's mtime until checkpoint, so an mtime-based watcher will miss them (watch the `-wal` file or use polling with a query).

Existing tests (`test_websocket_server.py`, `test_scrobbling_manager.py`, `test_settings_scrobbling.py`) are quarantined with the feature — keep them running against the prototype but exclude from the release gate until the redesign lands.

### Expansion notes (post-redesign)

- Streaming-service detection rules live in the extension; app stays service-agnostic (privacy: the app never learns browsing habits beyond explicit detections).
- Offline scrobble buffering can reuse the `sync_queue` table pattern once F2 wires it up.
- pystray tray integration is currently an unused dependency — adopt it only when scrobbling ships (background presence needs a visible indicator), otherwise drop it.

---

## Sequencing & verification

1. Phase 0 lands as one PR: pure deletion + trimmed tests; gate = full suite green, app boots, OAuth connect + sync still work manually.
2. Phase 1 items land individually, each with a regression test. F2 is split: F2b (import fix) is a standalone commit; F2a → F2c → F2d/F2e land in order as separate commits.
3. Phase 2 before Phase 3 — restyling a god object wastes the restyle.
4. Scrobbling redesign spike is scheduled after Phase 2 (it depends on R2) and before v0.5.0 feature work.
5. **Release split (risk-based):**
   - **v0.3.3 — stability, low-risk only:** Phase 0, F1, F3, F4, F6, F7, and F2b (import fix). No storage moves, no schema changes.
   - **v0.4.0 — refactor + look:** F5 (storage + schema migration), F2a/F2c/F2d/F2e (timestamp normalization + merge), Phases 2-3 including the Python 3.10+ floor raise. F5's `DROP COLUMN` migration depends on the floor raise (SQLite ≥ 3.35), which is why it cannot ship earlier.
   - **v0.5.0 — scrobbling** (post-redesign spike).
