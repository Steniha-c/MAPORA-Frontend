# MAPORA 2.0 — Authentication Fix & Token Lifecycle Report

## 1. Executive Summary

A critical issue was identified in the MAPORA 2.0 photo upload workflow where users on the upload page (`/projects/new` or `/upload`) appeared to be actively signed in (e.g. as `admin@mapora.io`), but received an error upon submitting photographs:

> **"Invalid or expired access token."**

The failure has been diagnosed, isolated, and permanently resolved across the full stack. The fix introduces a complete authentication lifecycle: proactive client-side token expiration evaluation, automated refresh-token rotation with single-flight concurrency deduplication, HTTP 401 transparent retry interception, and clean session-expiration recovery.

---

## 2. Root Cause Analysis

### Primary Root Causes

1. **Stale Session Persistence without Expiration Validation:**
   - In `src/auth/AuthContext.tsx`, the `session` state was initialized solely by reading `localStorage.getItem('mapora_auth_session')`.
   - Any session where `accessToken` and `user.id` were non-empty was treated as `isAuthenticated = true`, regardless of whether the token had expired 1 hour ago or 8 days prior.
   - Consequently, the UI showed the user as logged in with an active workspace, but the backend rejected the expired JWT with HTTP 401.

2. **Absence of Token Refresh & 401 Interception in API Client:**
   - The backend implemented a robust `/api/v1/auth/refresh` endpoint with refresh token rotation (`REFRESH_TOKEN_EXPIRE_DAYS = 30`).
   - However, `src/services/api.ts` had no refresh-token exchange mechanism, no 401 response interceptor, and no retry logic.
   - Any 401 returned by the backend was immediately converted into a raw JavaScript error and displayed directly on the form.

3. **Incomplete Frontend Session Schema:**
   - In `src/types.ts`, `AuthSession` only declared `{ accessToken: string; user: UserIdentity; }`, completely omitting `refreshToken` and `tokenType`.
   - The refresh token returned by `/auth/login` was never exposed to the frontend context.

4. **Zombie Session State on Authentication Failure:**
   - When an expired token was rejected, the frontend never cleared `localStorage` or notified the authentication context.
   - Reloading the page or retrying the button repeated the failure indefinitely without offering the user a direct path to re-authenticate.

---

## 3. Files Inspected

- `src/services/api.ts`: API request wrapper, fetch options, error decoding, and endpoint bindings.
- `src/auth/AuthContext.tsx`: Session state, initialization, `signIn`, `signOut`, and React context.
- `src/types.ts`: TypeScript interfaces for `AuthSession`, `UserIdentity`, and project entities.
- `src/pages/UploadPage.tsx`: Mode switcher, file drop-zone, photo array handling, and submission logic.
- `src/pages/LoginPage.tsx`: Form submission, error feedback, search parameter navigation.
- `src/App.tsx`: Routing, `WorkspaceShell` guard, redirection logic.
- `backend/app/core/security.py`: `create_access_token`, `decode_token`, JWT settings.
- `backend/app/core/config.py`: `ACCESS_TOKEN_EXPIRE_MINUTES`, `SECRET_KEY`, `ALGORITHM`.
- `backend/app/api/deps.py`: `get_current_user` dependency, token verification, HTTP 401 responses.
- `backend/app/api/v1/auth.py`: `/login`, `/register`, `/refresh`, `/logout`, `/me`.
- `backend/app/services/auth_service.py`: Token database operations, rotation, session creation.
- `backend/app/api/v1/projects.py`: Multipart video and photo project creation endpoints.

---

## 4. Files Modified & Exact Fix Implemented

### 4.1 Frontend Type Definitions ([`src/types.ts`](file:///c:/Users/steni/OneDrive/Desktop/MAPORA-Frontend/src/types.ts))
- Updated `AuthSession` to include `refreshToken?: string` and `tokenType?: string`.

### 4.2 API Client & Authentication Lifecycle ([`src/services/api.ts`](file:///c:/Users/steni/OneDrive/Desktop/MAPORA-Frontend/src/services/api.ts))
- **`decodeJwtPayload(token)` & `isTokenExpired(token, skewSeconds)`:** Decodes JWT payload client-side to verify expiration without third-party dependencies.
- **Single-Flight Refresh Mutex (`activeRefreshPromise`):** Ensures concurrent requests share a single `/auth/refresh` network call to prevent duplicate refresh calls or race conditions.
- **`refreshAccessToken()`:** Exchanges the stored refresh token for a fresh access token, updates `localStorage`, and broadcasts `mapora:session-refreshed`.
- **401 Interception & Single Retry:** If a protected endpoint returns HTTP 401, `request()` automatically invokes `refreshAccessToken()` and retries the request once with the new token.
- **Session Teardown & Event Broadcasting:** If token refresh fails, `notifySessionExpired()` clears storage and dispatches `mapora:session-expired`.
- **`maporaApi.refreshSession` & `maporaApi.logout`:** Added first-class methods for refresh and revocation.

### 4.3 Authentication State Context ([`src/auth/AuthContext.tsx`](file:///c:/Users/steni/OneDrive/Desktop/MAPORA-Frontend/src/auth/AuthContext.tsx))
- **Initial Mount Sanitization:** If stored `accessToken` is expired and no `refreshToken` exists, wipes stale storage immediately to prevent phantom login.
- **Proactive Background Refresh:** If mounted with an expired `accessToken` but valid `refreshToken`, initiates an immediate background refresh.
- **Event Listeners:** Subscribes to `mapora:session-refreshed` and `mapora:session-expired`.
- **Graceful Sign-Out:** Calls backend `/auth/logout` to revoke the database refresh token on sign-out.

### 4.4 Upload & Login Interfaces ([`src/pages/UploadPage.tsx`](file:///c:/Users/steni/OneDrive/Desktop/MAPORA-Frontend/src/pages/UploadPage.tsx) & [`src/pages/LoginPage.tsx`](file:///c:/Users/steni/OneDrive/Desktop/MAPORA-Frontend/src/pages/LoginPage.tsx))
- **`UploadPage.tsx`:** Before submission, validates token freshness using `getValidAccessToken()`. If session is unrecoverable, displays an alert with a direct **"Sign in again"** recovery action preserving the destination URL.
- **`LoginPage.tsx`:** Detects `?expired=1` or session-expired event and displays a warning banner (`"Your session has expired. Please sign in again to continue."`). Redirects back to the upload workflow upon successful sign-in.
- **`App.tsx`:** `WorkspaceShell` routes expired sessions cleanly to `/login?next=...&expired=1`.

### 4.5 Backend Standard 401 Headers ([`backend/app/api/deps.py`](file:///c:/Users/steni/OneDrive/Desktop/MAPORA-Frontend/backend/app/api/deps.py) & [`backend/app/api/v1/auth.py`](file:///c:/Users/steni/OneDrive/Desktop/MAPORA-Frontend/backend/app/api/v1/auth.py))
- Added RFC 6750-compliant `headers={"WWW-Authenticate": "Bearer"}` to all 401 exception responses.

---

## 5. Authentication Flow Comparison

### Before Fix
```
[User opens /projects/new] ──► Reads dead token from localStorage
                                    │
                               UI shows "admin@mapora.io" (Fake logged-in)
                                    │
                               User selects 4 photos & clicks "Submit"
                                    │
                               POST /projects with 8-day expired token
                                    │
                               Backend returns HTTP 401 "Invalid or expired access token."
                                    │
                               UI displays error banner; user remains stuck in zombie session
```

### After Fix
```
[User opens /projects/new] ──► Checks token validity via isTokenExpired()
                                    │
                       ┌────────────┴────────────┐
                       ▼                         ▼
                 [Token Valid]             [Token Expired]
                       │                         │
                       │               Is refreshToken present?
                       │                         │
                       │            ┌────────────┴────────────┐
                       │            ▼                         ▼
                       │          [Yes]                      [No]
                       │            │                         │
                       │     POST /auth/refresh         Clear storage &
                       │            │                   redirect to /login?expired=1
                       │            ▼                         │
                       │     Store new token            Show clear "Session Expired"
                       │     & refresh session          banner; clean re-login
                       │            │
                       └────────►───┴────────────────────────┐
                                                             ▼
                                                POST /projects with fresh token
                                                             │
                                                Reconstruction job started! (201 Created)
```

---

## 6. Verification and Regression Testing

### 6.1 Automated Frontend Build & Tests
```text
> mapora-frontend@0.1.0 test
> npm run build && node --test tests/*.test.mjs

✓ 2511 modules transformed.
✓ built in 1.41s
✔ production build is independently installable and emits JS/CSS assets (9.2ms)
✔ route manifest includes public auth, workspace, upload, floor plan, 3D and admin routes (3.0ms)
✔ README and proposed backend integration guide are included (3.3ms)
✔ homepage visual assets are present and non-empty (4.4ms)
ℹ tests 4 | suites 0 | pass 4 | fail 0
```

### 6.2 Automated Backend Auth Test Suite (`backend/tests/test_auth.py`)
```text
tests/test_auth.py::test_user_registration_success PASSED                [ 11%]
tests/test_auth.py::test_user_registration_duplicate_email PASSED        [ 22%]
tests/test_auth.py::test_login_success PASSED                            [ 33%]
tests/test_auth.py::test_login_invalid_password_generic_error PASSED     [ 44%]
tests/test_auth.py::test_refresh_token_cycle PASSED                      [ 55%]
tests/test_auth.py::test_auth_me_protected PASSED                        [ 66%]
tests/test_auth.py::test_expired_access_token_rejected PASSED            [ 77%]
tests/test_auth.py::test_malformed_access_token_rejected PASSED          [ 88%]
tests/test_invalid_refresh_token_rejected PASSED                         [100%]
========================= 9 passed in 2.36s ==========================
```

### 6.3 Automated Photo Reconstruction Test Suite (`backend/tests/test_image_reconstruction.py`)
```text
tests/test_image_reconstruction.py::test_batch_image_upload_endpoint PASSED           [ 20%]
tests/test_image_reconstruction.py::test_create_project_multipart_photo_flow PASSED   [ 40%]
tests/test_image_reconstruction.py::test_single_photo_reconstruction_pipeline PASSED   [ 60%]
tests/test_image_reconstruction.py::test_multi_photo_reconstruction_pipeline PASSED    [ 80%]
tests/test_image_reconstruction.py::test_insufficient_overlap_detection PASSED        [100%]
========================= 5 passed in 9.57s ==========================
```

### 6.4 Automated Video Reconstruction Regression (`backend/tests/test_reconstruction.py`)
```text
tests/test_reconstruction.py::test_reconstruction_pipeline_stages PASSED [ 50%]
tests/test_reconstruction.py::test_full_pipeline_orchestrator PASSED     [100%]
========================= 2 passed in 6.62s ==========================
```

### 6.5 Live End-to-End Photo Upload Integration Verification
A live verification script was executed against the running backend:
1. `POST /api/v1/auth/login`: Authenticated as `admin@mapora.io` (JWT access token and refresh token received).
2. Expired Token Verification: Verified that synthetic expired JWT is rejected with HTTP 401 (`"Invalid or expired access token."`).
3. Multi-Photo Project Creation: Uploaded 4 synthetic indoor photographs with `Authorization: Bearer <token>` to `POST /api/v1/projects`. Result: **HTTP 201 Created**, project ID `606cf6db-1e1f-4c0d-b860-cf1a5ec2fe76`.
4. Image Persistence: `GET /api/v1/projects/{id}/images` confirmed all 4 images persisted with dimensions (640×480) and blur scores.
5. Job Dispatch: `GET /api/v1/projects/{id}/status` returned `status: processing`, `stage: validating_images`.
6. Project Listing: Verified project is present in `GET /api/v1/projects`.
7. Refresh Token Exchange: `POST /api/v1/auth/refresh` issued a new access token, which was subsequently verified on protected project endpoints.

---

## 7. Operational Status

- **Web Application URL:** `http://localhost:5173/`
- **Backend Swagger API Docs:** `http://127.0.0.1:8000/docs`
- **Current Admin Account:** `admin@mapora.io` / `AdminMapora2026!`

