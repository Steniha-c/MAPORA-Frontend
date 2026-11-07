# MAPORA Frontend ↔ Backend Integration Guide

This guide details how to connect the existing frontend ([MAPORA-Frontend](https://github.com/Steniha-c/MAPORA-Frontend)) to the MAPORA backend.

---

## 1. Frontend Configuration

In the root of your `MAPORA-Frontend` repository, open or create `.env` (or `.env.local`):

```bash
# Point to your running MAPORA backend instance
# Both http://localhost:8000 and http://localhost:8000/api/v1 are supported!
VITE_MAPORA_API_BASE=http://localhost:8000
```

Start the frontend development server:
```bash
npm run dev
```

---

## 2. Authentication & Authorization Headers

All protected endpoints require an `Authorization` header containing the JWT access token:

```http
Authorization: Bearer <accessToken>
```

When unauthenticated or when the token has expired, the backend returns:
```json
{
  "detail": "Invalid or expired access token."
}
```

---

## 3. API Contract Mapping

The table below correlates the frontend functions in `src/services/api.ts` with the backend API endpoints:

| Frontend Function (`maporaApi`) | HTTP Method | Endpoint Path | Request Body | Expected Response Shape |
|---|---|---|---|---|
| `login(email, password)` | `POST` | `/auth/login` | `{ "email": "...", "password": "..." }` | `{ "accessToken": "...", "refreshToken": "...", "user": { "id": "...", "email": "...", "role": "admin" \| "surveyor" } }` |
| `listProjects(token)` | `GET` | `/projects` | None | `MapProject[]` |
| `getProject(projectId, token)` | `GET` | `/projects/{id}` | None | `MapProject` |
| `createMapping(video, token)` | `POST` | `/projects` | Multipart `video: File` | `{ "id": "...", "status": "Processing" }` |
| `renameProject(projectId, name, token)` | `PATCH` | `/projects/{id}` | `{ "name": "..." }` | `MapProject` |
| `deleteProject(projectId, token)` | `DELETE` | `/projects/{id}` | None | `204 No Content` |
| `getProjectVersions(projectId, token)` | `GET` | `/projects/{id}/versions` | None | `ProjectVersion[]` |
| `createProjectVersion(projectId, token)`| `POST` | `/projects/{id}/versions` | Optional `{ "description": "..." }` | `ProjectVersion` |
| `restoreProjectVersion(projectId, versionId, token)` | `POST` | `/projects/{id}/versions/{versionId}/restore` | None | `204 No Content` |
| `getProcessingStatus(projectId, token)` | `GET` | `/projects/{id}/status` | None | `ProcessingStatus` |
| `retryProcessing(projectId, token)` | `POST` | `/projects/{id}/retry` | None | `ProcessingStatus` |
| `getFloorPlan(projectId, token)` | `GET` | `/projects/{id}/floor-plan` | None | `FloorPlanModel` |
| `getScene(projectId, token)` | `GET` | `/projects/{id}/scene` | None | `{ "geometryUrl": "http://..." }` |
| `getAdminAnalytics(token)` | `GET` | `/admin/analytics` | None | `AdminAnalytics` |
| `downloadExport(projectId, format, token)` | `GET` | `/projects/{id}/export?format={format}` | None | Binary file stream (SVG, PDF, DXF, or GLB) |

---

## 4. Detailed Request & Response Examples

### 4.1 Login (`POST /auth/login`)
**Request:**
```http
POST /auth/login HTTP/1.1
Content-Type: application/json

{
  "email": "surveyor@mapora.io",
  "password": "SurveyorPassword123!"
}
```

**Response (`200 OK`):**
```json
{
  "accessToken": "eyJhbGciOiJIUzI1Ni...",
  "refreshToken": "CBx4HCLQFhvaTfkzQmWYey7R99Q2...",
  "token_type": "bearer",
  "user": {
    "id": "c1f7a091-628d-4e92-a169-d3e91c49b6b3",
    "email": "surveyor@mapora.io",
    "role": "surveyor"
  }
}
```

---

### 4.2 Polling Job Status (`GET /projects/{id}/status`)
**Request:**
```http
GET /projects/f47ac10b-58cc-4372-a567-0e02b2c3d479/status HTTP/1.1
Authorization: Bearer <accessToken>
```

**Response (`200 OK`):**
```json
{
  "projectId": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "stage": "estimating_geometry",
  "status": "processing",
  "progress": 65.0,
  "message": "Segmenting walls, floors, and openings...",
  "updatedAt": "2026-10-15T18:00:12Z"
}
```

---

### 4.3 2D Floor Plan (`GET /projects/{id}/floor-plan`)
**Request:**
```http
GET /projects/f47ac10b-58cc-4372-a567-0e02b2c3d479/floor-plan HTTP/1.1
Authorization: Bearer <accessToken>
```

**Response (`200 OK`):**
```json
{
  "coordinateSystem": "normalized-cartesian-2d",
  "units": "meters",
  "measurementsAvailable": true,
  "rooms": [
    {
      "id": "room-a1b2c3",
      "name": "Living Room",
      "bounds": { "x": 0.0, "y": 0.0, "width": 5.4, "height": 4.2 },
      "areaSquareMeters": 22.68
    },
    {
      "id": "room-d4e5f6",
      "name": "Master Bedroom",
      "bounds": { "x": 5.4, "y": 0.0, "width": 4.1, "height": 3.8 },
      "areaSquareMeters": 15.58
    }
  ],
  "walls": [
    {
      "id": "wall-1",
      "start": { "x": 0.0, "y": 0.0 },
      "end": { "x": 5.4, "y": 0.0 },
      "kind": "wall"
    },
    {
      "id": "door-1",
      "start": { "x": 2.2, "y": 0.0 },
      "end": { "x": 3.1, "y": 0.0 },
      "kind": "door"
    }
  ]
}
```

---

### 4.4 3D Scene URL (`GET /projects/{id}/scene`)
**Request:**
```http
GET /projects/f47ac10b-58cc-4372-a567-0e02b2c3d479/scene HTTP/1.1
Authorization: Bearer <accessToken>
```

**Response (`200 OK`):**
```json
{
  "geometryUrl": "/api/v1/storage/models/f47ac10b/scene_job123.glb"
}
```

---

### 4.5 Admin Analytics (`GET /admin/analytics`)
**Request:**
```http
GET /admin/analytics HTTP/1.1
Authorization: Bearer <admin_accessToken>
```

**Response (`200 OK`):**
```json
{
  "projectCount": 14,
  "userCount": 8,
  "jobsRunning": 2,
  "jobsFailed": 1,
  "jobsCompleted": 11,
  "averageProcessingSeconds": 38.4,
  "reconstructionsCompleted": 11,
  "roomsDetected": 47,
  "averageGeometryConfidence": 0.88,
  "updatedAt": "2026-10-15T18:05:00Z",
  "recentJobs": [
    {
      "id": "job-892",
      "projectId": "proj-12",
      "projectName": "Downtown Studio",
      "stage": "completed",
      "status": "completed",
      "durationSeconds": 34.2,
      "updatedAt": "2026-10-15T18:02:11Z"
    }
  ]
}
```

---

## 5. Potential Frontend Improvements / Alignments

Without modifying the frontend repository, here are notes on how the frontend and backend interact:
1. **API Base URL Suffix**: The frontend client in `src/services/api.ts` makes requests without a version prefix (e.g., `/auth/login`). MAPORA backend exposes routes **both** at `/` and at `/api/v1/` so either configuration works automatically.
2. **Error Responses**: When an endpoint fails, the backend returns standard JSON `{ "detail": "Explanation" }` as well as structured `{ "error": "Explanation" }`. The frontend's `request()` helper correctly catches both formats.
3. **Role Checks**: Admin pages are protected on both the frontend and backend. Attempting to call `/admin/*` without an `admin` role JWT will immediately return HTTP `403 Forbidden`.
