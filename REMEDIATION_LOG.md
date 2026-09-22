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
| **2.1** | Stored XSS in Admin User Management | `script_admin_page.js`, `server.py` | `[ ] PENDING` | - | Validate username syntax; sanitize DOM rendering |
| **1.3** | Path Restriction ACL Bypass on POST Mutations | `server.py` (`del-f`, `del-p`, `rename`, `upload`, etc.) | `[ ] PENDING` | - | Add `user.is_path_allowed()` checks before file modifications |
| **2.2** | CSRF on Sensitive Admin Endpoints | `server.py` | `[ ] PENDING` | - | Convert `?add_user`, `?delete_user`, `?reload`, `?shutdown` to POST |
| **2.3** | Plaintext Password Transmission in Query Parameters | `server.py` (`?add_user`) | `[ ] PENDING` | - | Move credentials to request body |
| **2.5** | Attribute Injection in Navigation Breadcrumbs | `_fs_utils.py`, `pyroboxCore.py` | `[ ] PENDING` | - | Escape quotes with `html.escape(quote=True)` |

### Phase 2: Authentication & Session Hardening
| ID | Description | Affected Files | Status | Commit SHA | Notes |
|---|---|---|---|---|---|
| **1.1** | Session Rotation, Invalidation on Logout, Cookie Flags | `user_mgmt.py`, `server.py` | `[ ] PENDING` | - | Add token rotation on login, server-side revocation on logout, `HttpOnly`/`SameSite` |
| **1.2** | Upgrade Password Hashing to Salted Scrypt | `user_mgmt.py` | `[ ] PENDING` | - | Replace single-round SHA-256 with per-user salted `hashlib.scrypt` |
| **2.6** | Prevent Username Enumeration in Login | `server.py` (`?do_login`) | `[ ] PENDING` | - | Standardize failure message to `"Invalid username or password"` |

### Phase 3: Defaults, DoS Mitigation & Security Headers
| ID | Description | Affected Files | Status | Commit SHA | Notes |
|---|---|---|---|---|---|
| **1.4** | Insecure Defaults (Upload password, guest permissions) | `pyrobox_ServerHost.py`, `_arg_parser.py` | `[ ] PENDING` | - | Default guest to read-only; remove hardcoded `"SECret"` fallback |
| **2.4** | DoS Mitigations (Subtitle map leak, unbounded tree walk) | `server.py`, `_sub_extractor.py` | `[ ] PENDING` | - | Add bounded dict / TTL for subtitles and QR codes |
| **2.7** | Missing HTTP Security Headers | `pyroboxCore.py` | `[ ] PENDING` | - | Add `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` |

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

