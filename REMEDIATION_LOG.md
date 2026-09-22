# Security Remediation Tracker & Resumable Log

This document tracks the progress, verification, and Git commits for the remediation of security and code-quality issues identified in [`Security_Audit.md`](file:///p:/C_coding/Python/pyrobox/Security_Audit.md).

---

## Workflow Protocol

For each task in the inventory:
1. **Status Transition**: Update status from `PENDING` -> `IN PROGRESS`.
2. **Implementation**: Apply code changes for the target issue only.
3. **Verification**: Execute `ruff check dev_src` and `pytest dev_src/tests` plus issue-specific unit tests.
4. **Git Commit**: Commit with a clean, focused semantic message referencing the issue ID.
5. **Log Update**: Record commit hash, verification notes, and transition status to `VERIFIED & COMMITTED`.

---

## Status Legend
- `[ ] PENDING`: Not yet started.
- `[~] IN PROGRESS`: Currently being worked on.
- `[x] COMMITTED`: Implemented, tested, and committed to Git.

---

## Remediation Inventory & Status

### Phase 0: Quick Wins & Code Hygiene
| ID | Description | Affected Files | Status | Commit SHA | Notes |
|---|---|---|---|---|---|
| **0.1** | Fix boolean operator precedence in `check_size_limit` | `pyroboxCore.py` | `[x] COMMITTED` | `b8c3cd4` | Corrected `not max_size < 0 or ...` logic and added unit tests |
| **0.2** | Fix 13 Ruff standard linter errors (`E711`, `E712`, `E713`) | `_list_maker.py`, `pyroboxCore.py`, `pyrobox_ServerHost.py`, `pyroDB3.py`, `pyroDB2.py` | `[x] COMMITTED` | `b8c3cd4` | Fixed `is None`, `not in`, and boolean comparisons; ruff check clean |

### Phase 1: High & Critical Authorization & Injection Fixes
| ID | Description | Affected Files | Status | Commit SHA | Notes |
|---|---|---|---|---|---|
| **2.1** | Stored XSS in Admin User Management | `script_admin_page.js`, `server.py`, `user_mgmt.py` | `[x] COMMITTED` | `8fe3de5` | Username regex validation (`is_valid_username`) + textContent DOM rendering |
| **1.3** | Path Restriction ACL Bypass on POST Mutations | `server.py` (`del-f`, `del-p`, `rename`, `upload`, etc.) | `[x] COMMITTED` | `671f656` | Enforce `user.is_path_allowed()` on code editor, delete, rename, info, folder, size, and zip operations |
| **2.2** | CSRF on Sensitive Admin Endpoints | `server.py`, `script_admin_page.js` | `[x] COMMITTED` | `e59664c` | Converted `reload`, `shutdown`, `add_user`, `delete_user`, `update_user_perm` to POST + `Sec-Fetch-Site` check |
| **2.3** | Plaintext Password Transmission in Query Parameters | `server.py`, `script_admin_page.js` | `[x] COMMITTED` | `e59664c` | Moved `add_user` credentials and permission attributes from URL query into POST multipart body |
| **2.5** | Attribute Injection in Navigation Breadcrumbs | `_fs_utils.py`, `pyroboxCore.py` | `[x] COMMITTED` | `043cd0f` | Escaped HTML quotes (`quote=True`) in `get_displaypath` and `dir_navigator` href attributes |

### Phase 2: Authentication & Session Hardening
| ID | Description | Affected Files | Status | Commit SHA | Notes |
|---|---|---|---|---|---|
| **1.1** | Session Rotation, Invalidation on Logout, Cookie Flags | `user_mgmt.py`, `server.py` | `[x] COMMITTED` | `5a6d730` | Implemented cryptographically secure tokens (`secrets.token_bytes(32)`), token rotation on login, server-side revocation on logout, and `HttpOnly`/`SameSite=Lax` cookie flags |
| **1.2** | Upgrade Password Hashing to Salted Scrypt | `user_mgmt.py` | `[x] COMMITTED` | `7168834` | Replaced single-round SHA-256 with per-user salted `scrypt` (PBKDF2 fallback) + transparent auto-upgrade on login |
| **2.6** | Prevent Username Enumeration in Login | `server.py`, `user_mgmt.py` | `[x] COMMITTED` | `e7a8d05` | Standardized login failure responses across `server.py` and `user_mgmt.py` to `"Invalid username or password"` |

### Phase 3: Defaults, DoS Mitigation & Security Headers
| ID | Description | Affected Files | Status | Commit SHA | Notes |
|---|---|---|---|---|---|
| **1.4** | Insecure Defaults (Upload password, guest permissions) | `pyrobox_ServerHost.py`, `_arg_parser.py` | `[x] COMMITTED` | `13d4493` | Default guest to read-only; generate random upload password fallback if omitted |
| **2.4** | DoS Mitigations (Subtitle map leak, unbounded tree walk) | `server.py`, `_fs_utils.py` | `[x] COMMITTED` | `e22b480` | Added LRU eviction for subtitles, in-memory QR cache, bounded directory walks |
| **2.7** | Missing HTTP Security Headers | `pyroboxCore.py` | `[x] COMMITTED` | `bfd5509` | Injected `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`, `Referrer-Policy: strict-origin-when-cross-origin` |

---

## Execution Log & Commit History

### Commit `b8c3cd4` - Phase 0: Quick Wins & Code Hygiene
- **Date**: 2026-09-23
- **Summary**:
  - Fixed inverted boolean operator precedence in `DealPostData.check_size_limit` (`pyroboxCore.py:L2288`).
  - Added unit test `test_deal_post_data_check_size_limit` to `dev_src/tests/test_pyrobox_core_standalone.py`.
  - Resolved all 13 Ruff standard linter violations (`E711`, `E712`, `E713`) across `dev_src/_list_maker.py`, `dev_src/pyrobox_ServerHost.py`, `dev_src/pyroboxCore.py`, `dev_src/pyroDB3.py`, and `dev_src/pyroDB2.py`.
  - Created missing fixture directory `dev_src/test-dir/live_served/spaces in folder name/`.
- **Verification**:
  - `ruff check dev_src`: Passed (0 errors).
  - `pytest dev_src/tests`: Passed 121/121 tests.

### Commit `8fe3de5` - Phase 1 / Step 1.1: Stored XSS in Admin User Management (Issue 2.1)
- **Date**: 2026-09-23
- **Summary**:
  - Added strict username validation (`is_valid_username`: 3-32 alphanumeric characters, `_`, `.`, `-`) in `dev_src/user_mgmt.py` (`create_user`, `server_signup`).
  - Enforced `is_valid_username` in `server.py` (`add_user`, `handle_signup_post`).
  - Fixed DOM XSS in `dev_src/script_admin_page.js`:
    - Replaced `row.innerHTML` interpolation in `display_users()` with safe DOM `textContent` and `createElement`.
    - Avoided template literal script injection `var username = "${username}"` in `manage_user()` by passing via `admin_tools.selected_user`.
    - Wrapped username query parameters with `encodeURIComponent` across admin API calls.
  - Added test suite `TestUsernameValidation` in `dev_src/tests/test_accounts_permissions.py` testing XSS payloads and invalid character rejection.
- **Verification**:
  - `ruff check dev_src`: Passed (0 errors).
  - `pytest dev_src/tests`: Passed 138/138 tests.

### Commit `671f656` - Phase 1 / Step 1.2: Path Restriction ACL Bypass (Issue 1.3)
- **Date**: 2026-09-23
- **Summary**:
  - Enforced `user.is_path_allowed()` checks across all mutating and file query endpoints in `dev_src/server.py`:
    - File upload (`upload`)
    - Send to recycle bin (`del_2_recycle`)
    - Permanent file/directory delete (`del_permanently`)
    - Rename content (`rename_content` - validates both source and destination paths)
    - Create new folder (`new_folder`)
    - Get file/folder metadata (`get_info`)
    - Code editor read (`send_code_data`) and save (`save_code_file`)
    - Size query endpoints (`get_size`, `get_size_n_count`)
    - Archive endpoints (`get_zip_id`, `create_zip`, `get_zip`)
  - Added test suite `TestEndpointAclEnforcement` in `dev_src/tests/test_path_acl.py` verifying ACL enforcement on paths and multi-path operations.
- **Verification**:
  - `ruff check dev_src`: Passed (0 errors).
  - `pytest dev_src/tests`: Passed 140/140 tests.

### Commit `e59664c` - Phase 1 / Step 1.3: CSRF & Plaintext Passwords in Admin Endpoints (Issues 2.2 & 2.3)
- **Date**: 2026-09-23
- **Summary**:
  - Converted mutating admin operations from `HEAD`/`GET` to `POST` in `dev_src/server.py`:
    - `reload`
    - `shutdown`
    - `add_user`
    - `delete_user`
    - `update_user_perm`
  - Added `Sec-Fetch-Site: cross-site` defense-in-depth CSRF blocking across all admin mutation endpoints.
  - Moved sensitive credentials (`password`) and attributes (`username`, `perms`, `allowed_paths`) in `add_user`, `delete_user`, and `update_user_perm` from URL query parameters to multipart `FormData` request bodies.
  - Updated frontend `dev_src/script_admin_page.js` to dispatch `POST` requests with `FormData`.
  - Added test suite `TestAdminEndpointsMethodSecurity` in `dev_src/tests/test_server_config_perms.py` verifying that state-changing admin actions are exclusively bound to POST and prohibited on GET/HEAD.
- **Verification**:
  - `ruff check dev_src`: Passed (0 errors).
  - `pytest dev_src/tests`: Passed 141/141 tests.

### Commit `043cd0f` - Phase 1 / Step 1.4: Attribute Injection in Breadcrumbs (Issue 2.5)
- **Date**: 2026-09-23
- **Summary**:
  - Set `quote=True` in `SimpleHTTPRequestHandler.get_displaypath` (`pyroboxCore.py:L1994`) so single and double quotes are escaped into `&#x27;` and `&quot;`.
  - Escaped URLs and directory names in `dir_navigator` (`dev_src/_fs_utils.py:L356`) using `html.escape(..., quote=True)` and double-quoted `href` attributes, eliminating DOM attribute breakout vulnerabilities.
  - Added test suite `TestBreadcrumbAttributeEscaping` in `dev_src/tests/test_path_security.py` verifying quote escaping in `get_displaypath` and `dir_navigator`.
- **Verification**:
  - `ruff check dev_src`: Passed (0 errors).
  - `pytest dev_src/tests`: Passed 143/143 tests.

### Commit `5a6d730` - Phase 2 / Step 2.1: Session Token Rotation, Revocation & Cookie Flags (Issue 1.1)
- **Date**: 2026-09-23
- **Summary**:
  - Added `User.generate_new_token()` using `secrets.token_bytes(32)` (256-bit cryptographically secure entropy).
  - Enforced session token rotation upon each successful login in `dev_src/server.py` (`handle_login_post`).
  - Enforced server-side session token invalidation upon user logout in `dev_src/server.py` (`logout`), invalidating the token in database.
  - Hardened cookie flags in `dev_src/user_mgmt.py`:
    - `cookie['token']['httponly'] = True` to prevent JavaScript/XSS theft of session token.
    - `cookie['token']['samesite'] = 'Lax'` on token, user, and permissions cookies.
  - Added test suite `TestSessionTokenAndCookieSecurity` in `dev_src/tests/test_accounts_permissions.py`.
- **Verification**:
  - `ruff check dev_src`: Passed (0 errors).
  - `pytest dev_src/tests`: Passed 146/146 tests.

### Commit `7168834` - Phase 2 / Step 2.2: Upgrade Password Hashing to Salted Scrypt (Issue 1.2)
- **Date**: 2026-09-23
- **Summary**:
  - Replaced single-round SHA-256 password hashing with per-user salted `scrypt` (16-byte random salt, N=16384, r=8, p=1) and PBKDF2-HMAC fallback in `dev_src/user_mgmt.py`.
  - Implemented transparent backward compatibility with legacy SHA-256 hashes, auto-upgrading to salted scrypt upon successful password verification.
  - Added test suite `TestPasswordHashingScrypt` in `dev_src/tests/test_accounts_permissions.py` covering scrypt hashing, unique per-user salts, and legacy hash transparent auto-upgrade.
- **Verification**:
  - `ruff check dev_src`: Passed (0 errors).
  - `pytest dev_src/tests`: Passed 149/149 tests.

### Commit `e7a8d05` - Phase 2 / Step 2.3: Prevent Username Enumeration in Login (Issue 2.6)
- **Date**: 2026-09-23
- **Summary**:
  - Unified failed login error responses across `dev_src/server.py` (`handle_login_post`) and `dev_src/user_mgmt.py` (`server_login`) to `"Invalid username or password"`.
  - Eliminated account enumeration side-channels that previously allowed attackers to distinguish between nonexistent accounts and valid usernames with bad passwords.
  - Updated tests in `dev_src/tests/test_accounts_permissions.py` to assert identical error status and message.
- **Verification**:
  - `ruff check dev_src`: Passed (0 errors).
  - `pytest dev_src/tests`: Passed 149/149 tests.

### Commit `13d4493` - Phase 3 / Step 3.1: Remove Hardcoded Upload Password & Restrict Guest Defaults (Issue 1.4)
- **Date**: 2026-09-23
- **Summary**:
  - Changed `--password` / `-k` CLI argument default from hardcoded `"SECret"` to `None` in `dev_src/_arg_parser.py`.
  - In `dev_src/pyrobox_ServerHost.py`, if no upload password was provided via CLI, generate a random cryptographically secure password via `secrets.token_urlsafe(9)` and log it to stdout. Explicit passwords supplied via CLI continue to be honored.
  - Restricted default guest permissions in `dev_src/pyrobox_ServerHost.py`:
    - On anonymous/nameless servers, guests no longer receive `MODIFY` or `DELETE` permissions by default; they retain `VIEW`, `DOWNLOAD`, `ZIP`, and `UPLOAD` (gated by the upload password).
    - On named/account-based servers, unauthenticated guests default to read-only (`VIEW`, `DOWNLOAD`, `ZIP`) with no mutation permissions (`UPLOAD`, `MODIFY`, `DELETE`).
  - Added unit tests in `dev_src/tests/test_server_config_perms.py` verifying random upload password generation, explicit password setting, and hardened guest permission defaults.
- **Verification**:
  - `ruff check dev_src`: Passed (0 errors).
  - `pytest dev_src/tests`: Passed 153/153 tests.

### Commit `e22b480` - Phase 3 / Step 3.2: DoS Mitigations for Subtitles, QR Code, and Tree Walks (Issue 2.4)
- **Date**: 2026-09-23
- **Summary**:
  - Replaced disk-backed `/?qr` generation in `dev_src/server.py` with an in-memory `@functools.lru_cache(maxsize=64)` buffer generator (`io.BytesIO`), completely eliminating disk exhaustion and leftover temporary SVG files.
  - Bounded `subtitle_location_map` to `MAX_SUBTITLE_ENTRIES = 256` using an `OrderedDict` with LRU eviction and automatic deletion of evicted temporary `.vtt` files from `CoreConfig.temp_dir`.
  - Added `max_count=50000` bound to `_get_tree_count_n_size` and `get_tree_count_n_size` in `dev_src/_fs_utils.py` to prevent CPU exhaustion and infinite loops during synchronous directory tree walks.
  - Added unit test suite `dev_src/tests/test_dos_mitigations.py` covering in-memory QR caching, subtitle LRU eviction, and tree walk bounds.
- **Verification**:
  - `ruff check dev_src`: Passed (0 errors).
  - `pytest dev_src/tests`: Passed 156/156 tests.

### Commit `bfd5509` - Phase 3 / Step 3.3: Add Defensive HTTP Security Headers (Issue 2.7)
- **Date**: 2026-09-23
- **Summary**:
  - Added helper method `_has_header(keyword)` in `dev_src/pyroboxCore.py` to avoid duplicate header emission.
  - Injected standard security headers into all HTTP responses via `SimpleHTTPRequestHandler.end_headers()`:
    - `X-Content-Type-Options: nosniff` (mitigates MIME type confusion and sniffing attacks on uploads)
    - `X-Frame-Options: SAMEORIGIN` (mitigates clickjacking framing)
    - `Referrer-Policy: strict-origin-when-cross-origin` (prevents path and token leakage in Referer headers)
  - Added unit test `test_security_headers_emitted_in_end_headers` in `dev_src/tests/test_pyrobox_core_standalone.py`.
- **Verification**:
  - `ruff check dev_src`: Passed (0 errors).
  - `pytest dev_src/tests`: Passed 157/157 tests.

### Commit `46fa9dc` - Bugfix: Root Directory Upload Validation & Client Leading Slash Handling
- **Date**: 2026-09-23
- **Summary**:
  - Fixed a regression where uploading files to the root directory (`/`) caused `os.path.dirname(os_f_path)` to evaluate to `""`, causing `path_is_under_directory` to return `False` and reject uploads with `400 Invalid Path`.
  - Updated `resolve_child_path` in `dev_src/pyroboxCore.py` to return `os.path.abspath(fs_path)` matching its API docstring specification.
  - Added fallback `f_dir = os.path.dirname(os_f_path) or os.path.abspath(self.directory)` in `dev_src/server.py` (`upload`).
  - Stripped leading slashes in `dev_src/script_file_list.js` from HTML5 directory drag-and-drop `fullPath` and uploaded file paths.
  - Added unit test `test_resolve_child_path_when_directory_is_dot` in `dev_src/tests/test_upload_path_resolve.py`.
- **Verification**:
  - `ruff check dev_src`: Passed (0 errors).
  - `pytest dev_src/tests`: Passed 158/158 tests.


